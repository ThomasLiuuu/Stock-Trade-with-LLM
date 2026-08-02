"""
Signal generation module.
Combines Finnhub and Yahoo Finance news sentiment into a unified trading signal.
Uses in-memory caching and batch downloading to minimize API calls.
"""

import time
import yfinance as yf

import config


# ---------------------------------------------------------------------------
# In-Memory Price Cache
# ---------------------------------------------------------------------------
# Stores fetched prices so repeated scans don't re-hit Yahoo Finance.
# Cleared automatically when the app restarts.
_price_cache = {}   # {ticker: {"price": float, "change_pct": float, "cached_at": float}}
CACHE_TTL = 300     # Cache is valid for 5 minutes (300 seconds)


def _is_cache_valid(ticker: str) -> bool:
    """Check if the cached price for a ticker is still fresh."""
    if ticker not in _price_cache:
        return False
    cached_at = _price_cache[ticker].get("cached_at", 0)
    return (time.time() - cached_at) < CACHE_TTL


def fetch_all_prices(tickers: list[str], force_refresh: bool = False) -> dict:
    """
    Batch fetch prices for all tickers in a single yf.download() call.
    Results are cached in memory. Subsequent calls return cached data
    unless force_refresh is True or the cache has expired.

    Returns a dict of {ticker: {"price": float, "change_pct": float}}.
    """
    # Figure out which tickers actually need fetching
    if force_refresh:
        tickers_to_fetch = list(tickers)
    else:
        tickers_to_fetch = [t for t in tickers if not _is_cache_valid(t)]

    if not tickers_to_fetch:
        # Everything is cached and fresh
        return {t: _price_cache[t] for t in tickers if t in _price_cache}

    try:
        # Single batch request for all tickers, with retry on rate limit.
        # yf.download() silently returns empty data on rate limits instead of
        # raising, so we detect empty results and retry with backoff.
        data = None
        max_retries = 3
        for attempt in range(max_retries):
            data = yf.download(
                tickers_to_fetch,
                period="5d",
                progress=False,
                auto_adjust=True,
                threads=True,
            )
            if data is not None and not data.empty:
                break  # Success
            if attempt < max_retries - 1:
                wait = [5, 15, 30][attempt]
                print(f"  [yfinance] No data returned, retrying in {wait}s... ({attempt + 1}/{max_retries})")
                time.sleep(wait)

        if data is None or data.empty:
            now = time.time()
            for ticker in tickers_to_fetch:
                _price_cache[ticker] = {"price": None, "change_pct": None, "cached_at": now}
            return {t: _price_cache.get(t, {"price": None, "change_pct": None}) for t in tickers}

        now = time.time()

        for ticker in tickers_to_fetch:
            try:
                # Extract close prices for this ticker
                if len(tickers_to_fetch) == 1:
                    closes = data["Close"].dropna()
                else:
                    closes = data["Close"][ticker].dropna()

                if closes.empty:
                    _price_cache[ticker] = {
                        "price": None,
                        "change_pct": None,
                        "cached_at": now,
                    }
                    continue

                price = float(closes.iloc[-1])
                prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else None

                change_pct = None
                if price and prev_close and prev_close != 0:
                    change_pct = round(((price - prev_close) / prev_close) * 100, 2)

                _price_cache[ticker] = {
                    "price": round(price, 2),
                    "change_pct": change_pct,
                    "cached_at": now,
                }
            except Exception as e:
                print(f"  [yfinance] Error parsing {ticker}: {e}")
                _price_cache[ticker] = {
                    "price": None,
                    "change_pct": None,
                    "cached_at": now,
                }

    except Exception as e:
        print(f"  [yfinance] Batch download error: {e}")
        now = time.time()
        for ticker in tickers_to_fetch:
            if ticker not in _price_cache:
                _price_cache[ticker] = {
                    "price": None,
                    "change_pct": None,
                    "cached_at": now,
                }

    return {t: _price_cache.get(t, {"price": None, "change_pct": None}) for t in tickers}


def fetch_price_info(ticker: str) -> dict:
    """
    Get price for a single ticker. Uses cache if available,
    otherwise fetches via batch download for just this ticker.

    Returns:
        - price:       float or None
        - change_pct:  float or None
    """
    if _is_cache_valid(ticker):
        cached = _price_cache[ticker]
        return {"price": cached["price"], "change_pct": cached["change_pct"]}

    # Fetch just this one ticker
    result = fetch_all_prices([ticker])
    entry = result.get(ticker, {})
    return {"price": entry.get("price"), "change_pct": entry.get("change_pct")}


# ---------------------------------------------------------------------------
# Signal Logic
# ---------------------------------------------------------------------------

def compute_combined_score(finnhub_summary: dict, yahoo_summary: dict) -> float:
    """
    Compute a weighted combined sentiment score from two news sources.

    Both inputs should have an 'avg_score' field on a -1 to +1 scale.
    Returns a combined score on a -1 to +1 scale.
    """
    fh_score = finnhub_summary.get("avg_score", 0.0)
    yh_score = yahoo_summary.get("avg_score", 0.0)

    has_finnhub = finnhub_summary.get("total_count", 0) > 0
    has_yahoo = yahoo_summary.get("total_count", 0) > 0

    if has_finnhub and has_yahoo:
        # Weight by article count for a more balanced blend
        fh_count = finnhub_summary["total_count"]
        yh_count = yahoo_summary["total_count"]
        total = fh_count + yh_count
        combined = (fh_score * fh_count + yh_score * yh_count) / total
    elif has_finnhub:
        combined = fh_score
    elif has_yahoo:
        combined = yh_score
    else:
        combined = 0.0

    return round(combined, 4)


def determine_signal(combined_score: float, total_articles: int) -> str:
    """
    Determine BUY / SELL / HOLD based on combined score and data sufficiency.
    """
    if total_articles < config.MIN_MESSAGES_FOR_SIGNAL:
        return "HOLD"  # Not enough data to be confident

    if combined_score >= config.SIGNAL_BUY_THRESHOLD:
        return "BUY"
    elif combined_score <= config.SIGNAL_SELL_THRESHOLD:
        return "SELL"
    else:
        return "HOLD"


def generate_signal(
    ticker: str,
    finnhub_summary: dict,
    yahoo_summary: dict,
    price_info: dict,
) -> dict:
    """
    Generate a complete signal for a single ticker.

    Returns a dict with all relevant info for display and export.
    """
    combined_score = compute_combined_score(finnhub_summary, yahoo_summary)

    total_articles = finnhub_summary.get("total_count", 0) + yahoo_summary.get("total_count", 0)
    signal = determine_signal(combined_score, total_articles)

    bullish = finnhub_summary.get("bullish_count", 0) + yahoo_summary.get("bullish_count", 0)
    bearish = finnhub_summary.get("bearish_count", 0) + yahoo_summary.get("bearish_count", 0)

    return {
        "ticker": ticker,
        "price": price_info.get("price"),
        "change_pct": price_info.get("change_pct"),
        "bullish": bullish,
        "bearish": bearish,
        "finnhub_score": finnhub_summary.get("avg_score", 0.0),
        "yahoo_score": yahoo_summary.get("avg_score", 0.0),
        "finnhub_count": finnhub_summary.get("total_count", 0),
        "yahoo_count": yahoo_summary.get("total_count", 0),
        "combined_score": combined_score,
        "signal": signal,
        "total_articles": total_articles,
    }
