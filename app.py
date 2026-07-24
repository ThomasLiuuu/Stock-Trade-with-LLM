"""
Flask web application for the Trading Signal Dashboard.
Serves the frontend and provides API endpoints for scanning, watchlist management,
and ticker detail views.
"""

import time
from flask import Flask, render_template, jsonify, request

import config
from scraper import fetch_finnhub_news, fetch_yahoo_news
from sentiment import score_articles, aggregate_sentiment
from signals import generate_signal, fetch_price_info


app = Flask(__name__)

# In-memory watchlist — starts from config, editable at runtime
watchlist = list(config.DEFAULT_WATCHLIST)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the dashboard page."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API: Scanning
# ---------------------------------------------------------------------------

def _process_ticker(ticker: str) -> dict:
    """Run the full signal pipeline for a single ticker."""
    finnhub_articles = fetch_finnhub_news(ticker)
    time.sleep(0.4)

    yahoo_articles = fetch_yahoo_news(ticker)
    time.sleep(0.8)

    scored_finnhub = score_articles(finnhub_articles)
    scored_yahoo = score_articles(yahoo_articles)

    finnhub_summary = aggregate_sentiment(scored_finnhub)
    yahoo_summary = aggregate_sentiment(scored_yahoo)

    price_info = fetch_price_info(ticker)
    time.sleep(0.3)

    signal = generate_signal(ticker, finnhub_summary, yahoo_summary, price_info)
    return signal


@app.route("/api/scan")
def scan():
    """Run the pipeline across the full watchlist and return results as JSON."""
    results = []
    for ticker in watchlist:
        try:
            result = _process_ticker(ticker)
            results.append(result)
        except Exception as e:
            results.append({
                "ticker": ticker,
                "price": None,
                "change_pct": None,
                "bullish": 0,
                "bearish": 0,
                "finnhub_score": 0.0,
                "yahoo_score": 0.0,
                "finnhub_count": 0,
                "yahoo_count": 0,
                "combined_score": 0.0,
                "signal": "HOLD",
                "total_articles": 0,
                "error": str(e),
            })

    # Sort by combined score descending
    results.sort(key=lambda r: r["combined_score"], reverse=True)

    return jsonify({
        "results": results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "watchlist": watchlist,
    })


# ---------------------------------------------------------------------------
# API: Watchlist Management
# ---------------------------------------------------------------------------

@app.route("/api/watchlist", methods=["GET"])
def get_watchlist():
    """Return the current watchlist."""
    return jsonify({"watchlist": watchlist})


@app.route("/api/watchlist", methods=["POST"])
def add_to_watchlist():
    """Add a ticker to the watchlist."""
    data = request.get_json()
    ticker = data.get("ticker", "").upper().strip()

    if not ticker:
        return jsonify({"error": "No ticker provided"}), 400
    if ticker in watchlist:
        return jsonify({"error": f"{ticker} already in watchlist"}), 409

    watchlist.append(ticker)
    return jsonify({"watchlist": watchlist, "added": ticker})


@app.route("/api/watchlist/<ticker>", methods=["DELETE"])
def remove_from_watchlist(ticker):
    """Remove a ticker from the watchlist."""
    ticker = ticker.upper().strip()

    if ticker not in watchlist:
        return jsonify({"error": f"{ticker} not in watchlist"}), 404

    watchlist.remove(ticker)
    return jsonify({"watchlist": watchlist, "removed": ticker})


# ---------------------------------------------------------------------------
# API: Ticker Detail
# ---------------------------------------------------------------------------

@app.route("/api/ticker/<ticker>")
def ticker_detail(ticker):
    """
    Return detailed news + sentiment for a single ticker.
    Includes per-article sentiment scores.
    """
    ticker = ticker.upper().strip()

    finnhub_articles = fetch_finnhub_news(ticker)
    time.sleep(0.4)
    yahoo_articles = fetch_yahoo_news(ticker)
    time.sleep(0.8)

    scored_finnhub = score_articles(finnhub_articles)
    scored_yahoo = score_articles(yahoo_articles)

    finnhub_summary = aggregate_sentiment(scored_finnhub)
    yahoo_summary = aggregate_sentiment(scored_yahoo)

    price_info = fetch_price_info(ticker)

    signal = generate_signal(ticker, finnhub_summary, yahoo_summary, price_info)

    return jsonify({
        "signal": signal,
        "finnhub_articles": scored_finnhub[:20],  # Cap for frontend performance
        "yahoo_articles": scored_yahoo[:10],
        "finnhub_summary": finnhub_summary,
        "yahoo_summary": yahoo_summary,
    })


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n  Dashboard running at http://localhost:{config.FLASK_PORT}\n")
    app.run(debug=True, port=config.FLASK_PORT)
