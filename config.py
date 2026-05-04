"""Configuration for LSTM + Sentiment quant trading system."""
import os
from dotenv import load_dotenv

load_dotenv()

# Data
DATA_DIR = "data"
START_DATE = "2020-01-01"
END_DATE = None  # None = today
SEQUENCE_LENGTH = 60

# LSTM Model
HIDDEN_SIZE = 64
NUM_LAYERS = 2
DROPOUT = 0.2
LEARNING_RATE = 0.001
EPOCHS = 50
BATCH_SIZE = 32
TRAIN_RATIO = 0.8

# Backtesting
SIGNAL_THRESHOLD = 0.5
STOP_LOSS = -0.05
TAKE_PROFIT = 0.10

# Watchlist
WATCHLIST_MAX_PER_MARKET = 10

# Cache TTL (seconds)
CACHE_TTL_DEFAULT = 86400
CACHE_TTL = {
    "tickers.csv": 864000,
    "ohlcv.csv": None,
    "fred.csv": None,
    "krx_tickers.csv": 864000,
    "krx_ohlcv.csv": None,
    "krx_macro.csv": None,
}

# Notifications
NOTIFICATIONS = {
    "slack": {
        "enabled": bool(os.environ.get("SLACK_WEBHOOK")),
        "webhook_url": os.environ.get("SLACK_WEBHOOK", ""),
    },
    "discord": {
        "enabled": bool(os.environ.get("DISCORD_WEBHOOK")),
        "webhook_url": os.environ.get("DISCORD_WEBHOOK", ""),
    },
    "telegram": {
        "enabled": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
    },
    "email": {
        "enabled": bool(os.environ.get("MAILGUN_API_KEY")),
        "domain": os.environ.get("MAILGUN_DOMAIN", ""),
        "sender": os.environ.get("MAILGUN_SENDER", ""),
        "recipient": os.environ.get("EMAIL_RECIPIENT", ""),
        "api_key": os.environ.get("MAILGUN_API_KEY", ""),
    },
}

# Database
DB_URL = os.environ.get("Q_DB_URL") or "sqlite:///data/portfolio.db"

# API Keys
FRED_API_KEY = os.environ.get("FRED_API_KEY") or ""
KRX_ID = os.environ.get("KRX_ID") or ""
KRX_PW = os.environ.get("KRX_PW") or ""

# Sentiment
SENTIMENT_MODEL = "ProsusAI/finbert"
NEWS_LOOKBACK_DAYS = 3

# ===== Market Configs =====
MARKETS = {
    "US": {
        "currency": "USD",
        "initial_capital": 100_000,
        "max_tickers": 100,
        "ohlcv_lib": "yfinance",
        "ticker_sources": {
            "SP500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            "NASDAQ100": "https://en.wikipedia.org/wiki/Nasdaq-100#Components",
        },
        "macro_series": {
            "VIXCLS": "VIX",
            "DFF": "FedFundsRate",
            "T10Y2Y": "TreasurySpread",
            "CPIAUCSL": "CPI",
            "UNRATE": "Unemployment",
            "BAMLH0A0HYM2": "HYSpread",
        },
        "sentiment_enabled": True,
        "data_files": {
            "tickers": "tickers.csv",
            "ohlcv": "ohlcv.csv",
            "macro": "fred.csv",
        },
    },
    "KRX": {
        "currency": "KRW",
        "initial_capital": 100_000_000,
        "max_tickers": 100,
        "ohlcv_lib": "pykrx",
        "krx_markets": ["KOSPI", "KOSDAQ"],
        "macro_series": {
            "VIXCLS": "VIX",
            "INTDSRKRM193N": "BaseRate",
            "KORCPIALLMINMEI": "CPI",
            "LRUNTTTTKRM156S": "Unemployment",
        },
        "macro_weights": {
            "VIX": 0.5,
        },
        "sentiment_enabled": False,
        "data_files": {
            "tickers": "krx_tickers.csv",
            "ohlcv": "krx_ohlcv.csv",
            "macro": "krx_macro.csv",
        },
    },
}

# Legacy aliases
SP500_URL = MARKETS["US"]["ticker_sources"]["SP500"]
NASDAQ100_URL = MARKETS["US"]["ticker_sources"]["NASDAQ100"]
MAX_TICKERS = MARKETS["US"]["max_tickers"]
INITIAL_CAPITAL = MARKETS["US"]["initial_capital"]
FRED_SERIES = MARKETS["US"]["macro_series"]
