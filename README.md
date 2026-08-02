# Stock Trade with LLM

A trading signal system inspired by the paper *"Wisdom of the Crowds or Ignorance of the Masses?"* (Semenova et al., Oxford, 2023). The paper studies whether retail investor discussions on r/WallStreetBets can predict stock returns, finding that forum sentiment is largely reactive — but niche clusters and due diligence posts can carry genuine predictive signal.

This project builds a practical signal scanner that aggregates financial news sentiment from multiple sources to generate BUY / SELL / HOLD signals for a configurable watchlist of stocks. It includes both a CLI tool and a web dashboard.

---

## How It Works

```
Finnhub API (company news) ──► VADER sentiment ──┐
                                                  ├──► Weighted blend ──► BUY / SELL / HOLD
Yahoo Finance (news)       ──► VADER sentiment ──┘
                                                          ▲
                                                   yfinance (price context)
```

1. **Scrape** — Fetches recent news articles for each ticker from Finnhub and Yahoo Finance
2. **Score** — Runs VADER (rule-based) sentiment analysis on every headline
3. **Combine** — Blends scores from both sources, weighted by article count
4. **Signal** — Generates BUY / SELL / HOLD based on configurable thresholds
5. **Output** — Displays results in a web dashboard (or CLI table) and exports to CSV

## Quick Start

### Prerequisites

- Python 3.11+
- A free Finnhub API key from [finnhub.io](https://finnhub.io/register)

### Setup

```bash
# Install dependencies
pip install vaderSentiment python-dotenv yfinance pandas numpy requests flask

# Create your .env file with your Finnhub API key
echo FINNHUB_API_KEY=your_key_here > .env
```

### Run

**Web Dashboard** (recommended):
```bash
python app.py
# Open http://localhost:5000 in your browser
```

**CLI mode**:
```bash
python main.py
```

---

## Project Structure

| File | Purpose |
|------|---------|
| `app.py` | Flask web server. Serves the dashboard frontend and exposes REST API endpoints for scanning (`/api/scan`), watchlist management (`/api/watchlist`), and ticker detail views (`/api/ticker/<symbol>`). |
| `main.py` | CLI entry point. Orchestrates the full pipeline, prints a formatted signal table to the console, and exports results to CSV. |
| `config.py` | Central configuration. Loads the Finnhub API key from `.env`, defines the default watchlist, scraper settings, signal thresholds, and Flask port. |
| `scraper.py` | Data fetching. Contains `fetch_finnhub_news()` for the Finnhub company news API and `fetch_yahoo_news()` for Yahoo Finance news via yfinance. Both return normalized article dicts. |
| `sentiment.py` | Sentiment scoring. Uses VADER to score news headlines on a −1 to +1 scale. Provides `score_articles()` for per-article scoring and `aggregate_sentiment()` for summary statistics. |
| `signals.py` | Signal generation. Blends sentiment from both sources (weighted by article count), fetches prices via batch `yf.download()` (single request for all tickers), and outputs BUY / SELL / HOLD. Includes an in-memory cache (5-min TTL, cleared on restart) and retry with backoff to handle rate limits. Falls back to the most recent historical close when the market is closed. |
| `templates/index.html` | Dashboard HTML. Single-page app with a signal table, watchlist management bar, summary cards, and a ticker detail modal. |
| `static/style.css` | Dashboard styling. Dark theme with glassmorphism cards, gradient accents, color-coded signals, and responsive layout. |
| `static/app.js` | Dashboard logic. Handles API calls for scanning, watchlist CRUD, dynamic table rendering, and the ticker detail modal with per-article sentiment display. |
| `.env` | Stores the Finnhub API key. **Not tracked by git.** |
| `.gitignore` | Excludes `.env`, `__pycache__/`, and CSV output files from version control. |

---

## Reference Paper

**"Wisdom of the Crowds or Ignorance of the Masses? A data-driven guide to WSB"**
Semenova, Gorduza, Wildi, Dong, Zohren — University of Oxford, 2023
[arXiv:2308.09485](https://arxiv.org/abs/2308.09485)
