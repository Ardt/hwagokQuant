# -*- coding: utf-8 -*-
"""KRX data collector: fetch KOSPI/KOSDAQ tickers and OHLCV via pykrx."""

import os
import time
from datetime import date
import pandas as pd
import config as cfg

# Set KRX credentials before importing pykrx
if hasattr(cfg, 'KRX_ID') and cfg.KRX_ID:
    os.environ.setdefault("KRX_ID", cfg.KRX_ID)
    os.environ.setdefault("KRX_PW", cfg.KRX_PW)

from pykrx import stock
from src.market import get_config
from src.logger import get

log = get("data.krx_collector")
_mcfg = get_config("KRX")


def get_universe() -> list[str]:
    """Get top N KRX tickers by market cap, cached."""
    from src.data.cache import is_valid

    cache_file = _mcfg["data_files"]["tickers"]
    cache_path = os.path.join(cfg.DATA_DIR, cache_file)

    if is_valid(cache_file):
        log.info("Loading cached KRX tickers")
        return pd.read_csv(cache_path)["Ticker"].tolist()

    today = date.today().strftime("%Y%m%d")
    log.info(f"Fetching KRX tickers for {today}...")

    all_tickers = []
    for market in _mcfg["krx_markets"]:
        tickers = stock.get_market_ticker_list(today, market=market)
        all_tickers.extend(tickers)
        time.sleep(1)

    # Sort by market cap
    cap_df = stock.get_market_cap_by_ticker(today)
    time.sleep(1)
    cap_df = cap_df[cap_df.index.isin(all_tickers)]
    cap_df = cap_df.sort_values("시가총액", ascending=False)
    top = cap_df.head(_mcfg["max_tickers"]).index.tolist()

    # Save with names
    rows = []
    for t in top:
        name = stock.get_market_ticker_name(t)
        rows.append({"Ticker": t, "Name": name, "MarketCap": cap_df.loc[t, "시가총액"]})
        time.sleep(0.3)

    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    pd.DataFrame(rows).to_csv(cache_path, index=False)
    log.info(f"Cached {len(top)} KRX tickers")
    return top


def fetch_ohlcv(ticker: str, start: str = None) -> pd.DataFrame | None:
    """Download OHLCV for a single KRX ticker."""
    try:
        s = start or cfg.START_DATE
        from_date = s.replace("-", "")
        to_date = date.today().strftime("%Y%m%d")

        df = stock.get_market_ohlcv_by_date(from_date, to_date, ticker)
        time.sleep(1)
        if df.empty:
            return None

        df = df.rename(columns={
            "시가": "Open", "고가": "High", "저가": "Low",
            "종가": "Close", "거래량": "Volume",
        })
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df["Ticker"] = ticker
        return df
    except Exception as e:
        log.error(f"Error fetching {ticker}: {e}")
        return None


def fetch_all(tickers: list[str] | None = None) -> pd.DataFrame:
    """Fetch OHLCV for all KRX tickers, incremental."""
    if tickers is None:
        tickers = get_universe()

    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    ohlcv_path = os.path.join(cfg.DATA_DIR, _mcfg["data_files"]["ohlcv"])
    today = date.today().strftime("%Y-%m-%d")

    existing = None
    if os.path.exists(ohlcv_path):
        existing = pd.read_csv(ohlcv_path, index_col=0, parse_dates=True, low_memory=False)

    frames = []
    for i, ticker in enumerate(tickers):
        if existing is not None and ticker in existing["Ticker"].values:
            ticker_data = existing[existing["Ticker"] == ticker]
            last_date = ticker_data.index.max()
            if str(last_date.date()) >= today:
                frames.append(ticker_data)
                continue
            start = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            new = fetch_ohlcv(ticker, start=start)
            if new is not None and not new.empty:
                frames.append(pd.concat([ticker_data, new]))
                log.debug(f"[{i+1}/{len(tickers)}] {ticker} updated")
            else:
                frames.append(ticker_data)
        else:
            df = fetch_ohlcv(ticker)
            if df is not None:
                frames.append(df)
                log.debug(f"[{i+1}/{len(tickers)}] {ticker} ({len(df)} rows)")
            else:
                log.warning(f"[{i+1}/{len(tickers)}] {ticker} skipped")

    if not frames:
        raise RuntimeError("No KRX data fetched.")

    combined = pd.concat(frames)
    combined.to_csv(ohlcv_path)
    log.info(f"Saved KRX OHLCV ({len(combined)} rows)")
    return combined
