"""Market detection: infer market from ticker format."""

import math
import config as cfg


def detect_market(ticker: str) -> str:
    """KRX tickers are 6-digit numeric or 5-digit + letter suffix (preferred). US tickers are alphabetic."""
    if ticker.isdigit():
        return "KRX"
    # KRX preferred: 5 digits + letter suffix (e.g., 37550K, 005935)
    if len(ticker) == 6 and ticker[:5].isdigit() and ticker[5].isalpha():
        return "KRX"
    return "US"


def detect_portfolio_market(tickers: list[str]) -> str | None:
    """Infer market from a list of tickers. Returns None if empty."""
    if not tickers:
        return None
    return detect_market(tickers[0])


def get_config(market: str) -> dict:
    """Get market-specific config dict."""
    return cfg.MARKETS[market]


def round_to_tick(price: float, market: str) -> float:
    """Round price to valid tick size for the given market."""
    if market == "US":
        return round(price, 2)
    # KRX tick size table
    if price < 2000:
        tick = 1
    elif price < 5000:
        tick = 5
    elif price < 20000:
        tick = 10
    elif price < 50000:
        tick = 50
    elif price < 200000:
        tick = 100
    elif price < 500000:
        tick = 500
    else:
        tick = 1000
    return math.floor(price / tick) * tick
