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
        to_date = (cfg.END_DATE or date.today().isoformat()).replace("-", "")

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
    """Fetch OHLCV for all KRX tickers. Uses batch daily fetch for incremental updates."""
    if tickers is None:
        tickers = get_universe()

    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    ohlcv_path = os.path.join(cfg.DATA_DIR, _mcfg["data_files"]["ohlcv"])
    today = cfg.END_DATE or date.today().strftime("%Y-%m-%d")
    today_fmt = today.replace("-", "")

    existing = None
    if os.path.exists(ohlcv_path):
        existing = pd.read_csv(ohlcv_path, index_col=0, parse_dates=True, low_memory=False)

    tickers_set = set(tickers)

    # Check if cache is up to date
    if existing is not None and not existing.empty:
        last_date = str(existing.index.max().date())
        if last_date >= today:
            # All cached, just filter to requested tickers
            log.info("KRX OHLCV cache up to date")
            return existing[existing["Ticker"].isin(tickers_set)]

        # Incremental: fetch missing days using batch (one call per day)
        log.info(f"KRX incremental update from {last_date} to {today}...")
        start_date = (existing.index.max() + pd.Timedelta(days=1)).strftime("%Y%m%d")
        new_frames = []
        current = start_date
        while current <= today_fmt:
            try:
                day_df = stock.get_market_ohlcv_by_ticker(current, market="ALL")
                time.sleep(1)
                if not day_df.empty:
                    day_df = day_df.rename(columns={
                        "시가": "Open", "고가": "High", "저가": "Low",
                        "종가": "Close", "거래량": "Volume",
                    })
                    day_df = day_df[["Open", "High", "Low", "Close", "Volume"]]
                    day_df["Ticker"] = day_df.index
                    day_df.index = pd.DatetimeIndex([current] * len(day_df))
                    day_df = day_df[day_df["Ticker"].isin(tickers_set)]
                    if not day_df.empty:
                        new_frames.append(day_df)
            except Exception:
                pass
            current = (pd.Timestamp(current) + pd.Timedelta(days=1)).strftime("%Y%m%d")

        if new_frames:
            new_data = pd.concat(new_frames)
            combined = pd.concat([existing, new_data])
        else:
            combined = existing
        combined = combined[combined["Ticker"].isin(tickers_set)]
        combined.to_csv(ohlcv_path)
        log.info(f"Saved KRX OHLCV ({len(combined)} rows, {len(new_frames)} days added)")
        return combined

    # Full fetch (no cache) — fall back to per-ticker
    log.info(f"KRX full fetch for {len(tickers)} tickers...")
    frames = []
    for i, ticker in enumerate(tickers):
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
