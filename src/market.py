"""Market detection: infer market from ticker format."""

import config as cfg


def detect_market(ticker: str) -> str:
    """KRX tickers are 6-digit numeric, US tickers are alphabetic."""
    return "KRX" if ticker.isdigit() else "US"


def detect_portfolio_market(tickers: list[str]) -> str | None:
    """Infer market from a list of tickers. Returns None if empty."""
    if not tickers:
        return None
    return detect_market(tickers[0])


def get_config(market: str) -> dict:
    """Get market-specific config dict."""
    return cfg.MARKETS[market]
