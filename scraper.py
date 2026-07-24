"""
Data scrapers for Finnhub and Yahoo Finance.
Fetches financial news articles for a given ticker from two independent sources.
"""

import requests
import time
from datetime import datetime, timedelta

import yfinance as yf

import config


# ---------------------------------------------------------------------------
# Finnhub Company News
# ---------------------------------------------------------------------------

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def fetch_finnhub_news(ticker: str, api_key: str = None) -> list[dict]:
    """
    Fetch recent company news from Finnhub.

    Returns a list of dicts, each with:
        - headline: str
        - summary:  str
        - datetime: str  (ISO timestamp)
        - source:   str
        - url:      str
    """
    api_key = api_key or config.FINNHUB_API_KEY
    if not api_key:
        print("  [Finnhub] No API key configured -- skipping news fetch.")
        return []

    today = datetime.now()
    from_date = (today - timedelta(days=config.FINNHUB_NEWS_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    url = f"{FINNHUB_BASE_URL}/company-news"
    params = {
        "symbol": ticker,
        "from": from_date,
        "to": to_date,
        "token": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  [Finnhub] Error fetching news for {ticker}: {e}")
        return []

    articles = []
    for article in data[:50]:  # Cap at 50 most recent to avoid overload
        articles.append({
            "headline": article.get("headline", ""),
            "summary": article.get("summary", ""),
            "datetime": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
            "source": article.get("source", ""),
            "url": article.get("url", ""),
        })

    return articles


# ---------------------------------------------------------------------------
# Yahoo Finance News (via yfinance)
# ---------------------------------------------------------------------------

def fetch_yahoo_news(ticker: str) -> list[dict]:
    """
    Fetch recent news for a ticker from Yahoo Finance via yfinance.

    Returns a list of dicts, each with:
        - headline: str
        - summary:  str
        - datetime: str  (ISO timestamp)
        - source:   str
        - url:      str
    """
    try:
        stock = yf.Ticker(ticker)
        raw_news = stock.news or []
    except Exception as e:
        print(f"  [Yahoo] Error fetching news for {ticker}: {e}")
        return []

    articles = []
    for item in raw_news:
        content = item.get("content", {})

        headline = content.get("title", "")
        summary = content.get("summary", "")
        pub_date = content.get("pubDate", "")
        source = content.get("provider", {}).get("displayName", "")
        url_data = content.get("canonicalUrl", {})
        url = url_data.get("url", "") if isinstance(url_data, dict) else ""

        articles.append({
            "headline": headline,
            "summary": summary,
            "datetime": pub_date,
            "source": source,
            "url": url,
        })

    return articles
