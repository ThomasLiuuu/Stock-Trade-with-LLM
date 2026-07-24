"""
Main entry point for the Trading Signal System.
Orchestrates the full pipeline: scrape news -> score sentiment -> generate signals -> display.
"""

import sys
import io
import time

import pandas as pd

import config
from scraper import fetch_finnhub_news, fetch_yahoo_news
from sentiment import score_articles, aggregate_sentiment
from signals import generate_signal, fetch_price_info

# Force UTF-8 output on Windows to handle special characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def process_ticker(ticker: str) -> dict:
    """Run the full pipeline for a single ticker."""

    # 1. Fetch news from both sources
    finnhub_articles = fetch_finnhub_news(ticker)
    time.sleep(0.5)  # Respect Finnhub rate limit (60/min)

    yahoo_articles = fetch_yahoo_news(ticker)
    time.sleep(1.0)  # Respect yfinance rate limits

    # 2. Score sentiment on both
    scored_finnhub = score_articles(finnhub_articles)
    scored_yahoo = score_articles(yahoo_articles)

    finnhub_summary = aggregate_sentiment(scored_finnhub)
    yahoo_summary = aggregate_sentiment(scored_yahoo)

    # 3. Fetch price
    price_info = fetch_price_info(ticker)
    time.sleep(0.5)

    # 4. Generate combined signal
    signal = generate_signal(ticker, finnhub_summary, yahoo_summary, price_info)

    return signal


def print_results(results: list[dict]):
    """Print a formatted table of signals to console."""

    print()
    print("=" * 105)
    print(f"  {'TRADING SIGNAL SCANNER':^101}")
    print(f"  {'Finnhub + Yahoo Finance News | ' + time.strftime('%Y-%m-%d %H:%M'):^101}")
    print("=" * 105)
    print()

    header = (
        f"  {'Ticker':<8}"
        f"{'Price':>10}"
        f"{'Chg%':>8}"
        f"{'Bull':>6}"
        f"{'Bear':>6}"
        f"{'Finnhub':>9}"
        f"{'Yahoo':>9}"
        f"{'Combined':>10}"
        f"{'Articles':>10}"
        f"  {'Signal':<10}"
    )
    print(header)
    print("  " + "-" * 101)

    for r in results:
        price_str = f"${r['price']:.2f}" if r["price"] else "N/A"
        chg_str = f"{r['change_pct']:+.1f}%" if r["change_pct"] is not None else "N/A"

        signal = r["signal"]
        if signal == "BUY":
            signal_display = "[+] BUY"
        elif signal == "SELL":
            signal_display = "[-] SELL"
        else:
            signal_display = "[ ] HOLD"

        row = (
            f"  {r['ticker']:<8}"
            f"{price_str:>10}"
            f"{chg_str:>8}"
            f"{r['bullish']:>6}"
            f"{r['bearish']:>6}"
            f"{r['finnhub_score']:>+9.3f}"
            f"{r['yahoo_score']:>+9.3f}"
            f"{r['combined_score']:>+10.3f}"
            f"{r['total_articles']:>10}"
            f"  {signal_display:<10}"
        )
        print(row)

    print()
    print("=" * 105)

    buys = sum(1 for r in results if r["signal"] == "BUY")
    sells = sum(1 for r in results if r["signal"] == "SELL")
    holds = sum(1 for r in results if r["signal"] == "HOLD")
    print(f"  Summary: {buys} BUY | {sells} SELL | {holds} HOLD")
    print("=" * 105)
    print()


def export_csv(results: list[dict], filepath: str):
    """Export results to CSV."""
    df = pd.DataFrame(results)
    df.to_csv(filepath, index=False)
    print(f"  Results exported to {filepath}")


def main():
    """Run the full signal scanning pipeline."""
    watchlist = config.DEFAULT_WATCHLIST

    print()
    print(f"  Scanning {len(watchlist)} tickers...")
    print(f"  Sources: Finnhub (company news) + Yahoo Finance (news)")
    print()

    results = []
    for i, ticker in enumerate(watchlist, 1):
        print(f"  [{i}/{len(watchlist)}] Processing {ticker}...")
        result = process_ticker(ticker)
        results.append(result)

    # Sort by combined score (strongest signal first)
    results.sort(key=lambda r: r["combined_score"], reverse=True)

    # Display and export
    print_results(results)
    export_csv(results, config.OUTPUT_CSV)


if __name__ == "__main__":
    main()
