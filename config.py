"""
Configuration for the WSB-style Trading Signal System.
Loads API keys from .env and defines default settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# ---------------------------------------------------------------------------
# Default Watchlist
# ---------------------------------------------------------------------------
# Popular tickers across different sectors — a good starting set for scanning.
DEFAULT_WATCHLIST = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Alphabet
    "AMZN",   # Amazon
    "TSLA",   # Tesla
    "NVDA",   # Nvidia
    "META",   # Meta
    "AMD",    # AMD
    "PLTR",   # Palantir
    "GME",    # GameStop
    "AMC",    # AMC Entertainment
    "SOFI",   # SoFi Technologies
    "NIO",    # NIO
    "BAC",    # Bank of America
    "DIS",    # Disney
]

# ---------------------------------------------------------------------------
# Scraper Settings
# ---------------------------------------------------------------------------
FINNHUB_NEWS_LOOKBACK_DAYS = 7     # How many days of Finnhub news to fetch
FINNHUB_MAX_ARTICLES = 50          # Cap Finnhub articles per ticker

# ---------------------------------------------------------------------------
# Signal Thresholds
# ---------------------------------------------------------------------------
SIGNAL_BUY_THRESHOLD = 0.15        # Combined score above this = BUY
SIGNAL_SELL_THRESHOLD = -0.15      # Combined score below this = SELL
MIN_MESSAGES_FOR_SIGNAL = 3        # Need at least this many articles to generate a signal

# ---------------------------------------------------------------------------
# Output Settings
# ---------------------------------------------------------------------------
OUTPUT_CSV = "signals_output.csv"
