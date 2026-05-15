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
    """Fetch OHLCV for all tickers using batch download where possible."""
    from datetime import date

    if tickers is None:
        tickers = get_universe()

    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    ohlcv_path = os.path.join(cfg.DATA_DIR, "ohlcv.csv")
    today = cfg.END_DATE or date.today().strftime("%Y-%m-%d")

    existing = None
    if os.path.exists(ohlcv_path):
        existing = pd.read_csv(ohlcv_path, index_col=0, parse_dates=True)

    # Split tickers into cached (up to date) vs needs-fetch
    cached_frames = []
    tickers_to_fetch = []
    fetch_start = cfg.START_DATE

    for ticker in tickers:
        if existing is not None and ticker in existing["Ticker"].values:
            ticker_data = existing[existing["Ticker"] == ticker]
            last_date = ticker_data.index.max()
            if str(last_date.date()) >= today:
                cached_frames.append(ticker_data)
                continue
            # Need incremental update from last_date
            cached_frames.append(ticker_data)
            tickers_to_fetch.append(ticker)
            start = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            fetch_start = max(fetch_start, start) if fetch_start != cfg.START_DATE else start
        else:
            tickers_to_fetch.append(ticker)

    # Batch download all tickers that need data
    new_frames = []
    if tickers_to_fetch:
        log.info(f"Batch downloading {len(tickers_to_fetch)} tickers...")
        try:
            batch = yf.download(tickers_to_fetch, start=cfg.START_DATE, end=today, progress=False)
            if not batch.empty:
                # yfinance returns MultiIndex columns: (Price, Ticker)
                if isinstance(batch.columns, pd.MultiIndex):
                    for ticker in tickers_to_fetch:
                        try:
                            df = batch.xs(ticker, level=1, axis=1)[["Open", "High", "Low", "Close", "Volume"]].dropna()
                            if not df.empty:
                                df["Ticker"] = ticker
                                new_frames.append(df)
                        except (KeyError, TypeError):
                            pass
                else:
                    # Single ticker case
                    batch = batch[["Open", "High", "Low", "Close", "Volume"]]
                    batch["Ticker"] = tickers_to_fetch[0]
                    new_frames.append(batch)
        except Exception as e:
            log.error(f"Batch download failed: {e}, falling back to individual")
            for ticker in tickers_to_fetch:
                df = fetch_ohlcv(ticker)
                if df is not None:
                    new_frames.append(df)

    # Merge cached + new, keeping latest data per ticker
    all_frames = []
    new_by_ticker = {df["Ticker"].iloc[0]: df for df in new_frames if not df.empty}
    for frame in cached_frames:
        ticker = frame["Ticker"].iloc[0]
        if ticker in new_by_ticker:
            # Merge: keep cached + append new dates only
            new_data = new_by_ticker.pop(ticker)
            new_data = new_data[new_data.index > frame.index.max()]
            all_frames.append(pd.concat([frame, new_data]))
        else:
            all_frames.append(frame)
    # Add tickers that had no cache
    for df in new_by_ticker.values():
        all_frames.append(df)

    if not all_frames:
        raise RuntimeError("No data fetched. Check internet connection or try fewer tickers.")

    combined = pd.concat(all_frames)
    combined.to_csv(ohlcv_path)
    log.info(f"Saved OHLCV to {ohlcv_path} ({len(tickers_to_fetch)} fetched, {len(cached_frames)} cached)")
    return combined


if __name__ == "__main__":
    data = fetch_all()
    print(data.shape)
