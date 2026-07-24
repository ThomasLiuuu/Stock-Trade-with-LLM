"""
Signal generation module.
Combines Finnhub and Yahoo Finance news sentiment into a unified trading signal.
"""

import yfinance as yf

import config


def fetch_price_info(ticker: str) -> dict:
    """
    Fetch current price and daily change for a ticker using yfinance.

    Returns:
        - price:       float or None
        - change_pct:  float or None (daily percent change)
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info

        price = getattr(info, "last_price", None)
        prev_close = getattr(info, "previous_close", None)

        change_pct = None
        if price and prev_close and prev_close != 0:
            change_pct = round(((price - prev_close) / prev_close) * 100, 2)

        return {
            "price": round(price, 2) if price else None,
            "change_pct": change_pct,
        }
    except Exception as e:
        print(f"  [yfinance] Error fetching price for {ticker}: {e}")
        return {"price": None, "change_pct": None}


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
