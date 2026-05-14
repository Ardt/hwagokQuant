"""Data collector: fetch S&P500/NASDAQ100 tickers and OHLCV data."""

import os
from io import StringIO
import requests
import pandas as pd
import yfinance as yf
import config as cfg
from src.logger import get

log = get("data.collector")

_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _read_html(url: str, **kwargs) -> list[pd.DataFrame]:
    """Read HTML tables with proper headers to avoid 403."""
    resp = requests.get(url, headers=_HEADERS)
    resp.raise_for_status()
    return pd.read_html(StringIO(resp.text), **kwargs)


def get_sp500_tickers() -> list[str]:
    """Scrape S&P500 tickers from Wikipedia."""
    table = _read_html(cfg.SP500_URL, header=0)[0]
    return table["Symbol"].str.replace(".", "-", regex=False).tolist()


def get_nasdaq100_tickers() -> list[str]:
    """Scrape NASDAQ100 tickers from Wikipedia."""
    tables = _read_html(cfg.NASDAQ100_URL, header=0)
    for t in tables:
        for col in ["Ticker", "Symbol"]:
            if col in t.columns:
                return t[col].str.replace(".", "-", regex=False).tolist()
    raise ValueError(f"Could not find ticker column in NASDAQ100 tables. Columns: {[list(t.columns) for t in tables]}")


def get_universe() -> list[str]:
    """Get deduplicated ticker universe from S&P500 + NASDAQ100, sorted by market cap, cached with 1-day TTL."""
    import time
    from src.data.cache import is_valid

    cache_path = os.path.join(cfg.DATA_DIR, "tickers.csv")
    if is_valid("tickers.csv"):
        log.info("Loading cached tickers")
        return pd.read_csv(cache_path)["Ticker"].tolist()
    if os.path.exists(cache_path):
        log.info("Ticker cache expired, refreshing...")

    tickers = list(set(get_sp500_tickers() + get_nasdaq100_tickers()))

    # Sort by market cap (descending)
    log.info(f"Sorting {len(tickers)} tickers by market cap...")
    cap_map = {}
    name_map = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            cap_map[t] = info.get("marketCap", 0) or 0
            name_map[t] = info.get("shortName", t)
        except Exception:
            cap_map[t] = 0
            name_map[t] = t
        time.sleep(0.3)
    tickers.sort(key=lambda t: cap_map[t], reverse=True)
    tickers = tickers[: cfg.MAX_TICKERS] if cfg.MAX_TICKERS else tickers

    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    df = pd.DataFrame({"Ticker": tickers, "Name": [name_map[t] for t in tickers], "MarketCap": [cap_map[t] for t in tickers]})
    df.to_csv(cache_path, index=False)
    log.info(f"Cached {len(tickers)} tickers to {cache_path}")
    return tickers


def fetch_ohlcv(ticker: str, start: str = None) -> pd.DataFrame | None:
    """Download OHLCV data for a single ticker."""
    import time
    try:
        df = yf.download(
            ticker, start=start or cfg.START_DATE, end=cfg.END_DATE, progress=False
        )
        time.sleep(0.5)  # rate limit
        if df.empty:
            return None
        # yfinance 1.x returns MultiIndex columns (Price, Ticker)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df["Ticker"] = ticker
        return df
    except Exception as e:
        log.error(f"Error fetching {ticker}: {e}")
        return None


def fetch_all(tickers: list[str] | None = None) -> pd.DataFrame:
    """Fetch OHLCV for all tickers, only downloading missing date ranges (incremental)."""
    from datetime import date

    if tickers is None:
        tickers = get_universe()

    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    ohlcv_path = os.path.join(cfg.DATA_DIR, "ohlcv.csv")
    today = date.today().strftime("%Y-%m-%d")

    existing = None
    if os.path.exists(ohlcv_path):
        existing = pd.read_csv(ohlcv_path, index_col=0, parse_dates=True)

    frames = []
    for i, ticker in enumerate(tickers):
        if existing is not None and ticker in existing["Ticker"].values:
            ticker_data = existing[existing["Ticker"] == ticker]
            last_date = ticker_data.index.max()
            if str(last_date.date()) >= today:
                frames.append(ticker_data)
                continue
            # Fetch only missing days
            start = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            new = fetch_ohlcv(ticker, start=start)
            if new is not None and not new.empty:
                frames.append(pd.concat([ticker_data, new]))
                log.debug(f"[{i + 1}/{len(tickers)}] {ticker} updated from {start}")
            else:
                frames.append(ticker_data)
        else:
            df = fetch_ohlcv(ticker)
            if df is not None:
                frames.append(df)
                log.debug(f"[{i + 1}/{len(tickers)}] {ticker} ({len(df)} rows)")
            else:
                log.warning(f"[{i + 1}/{len(tickers)}] {ticker} skipped")

    if not frames:
        raise RuntimeError("No data fetched. Check internet connection or try fewer tickers.")

    combined = pd.concat(frames)
    combined.to_csv(ohlcv_path)
    log.info(f"Saved OHLCV to {ohlcv_path}")
    return combined


if __name__ == "__main__":
    data = fetch_all()
    print(data.shape)
