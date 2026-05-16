"""Sync ticker names + benchmark prices to Supabase.

Run separately from train.py to avoid slowing down training.
Can run on any machine with DB access.

Usage: python sync_ticker_db.py
"""

import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

import config as cfg
from src.portfolio.db import get_session, text, sync_ticker_names
from src import logger

logger.setup()
log = logger.get("sync_ticker_db")


def sync_names():
    """Sync ticker names from cached CSVs to DB."""
    names = {}
    krx_path = os.path.join(cfg.DATA_DIR, "krx_tickers.csv")
    if os.path.exists(krx_path):
        df = pd.read_csv(krx_path)
        for _, row in df.iterrows():
            names[str(row["Ticker"])] = row["Name"]
    us_path = os.path.join(cfg.DATA_DIR, "tickers.csv")
    if os.path.exists(us_path):
        df = pd.read_csv(us_path)
        if "Name" in df.columns:
            for _, row in df.iterrows():
                names[row["Ticker"]] = row["Name"]
    if names:
        sync_ticker_names(names)
        log.info(f"Synced {len(names)} ticker names")


def sync_benchmarks():
    """Fetch KOSPI and NASDAQ100 index prices and store in DB."""
    import yfinance as yf

    benchmarks = {"KOSPI": "^KS11", "NASDAQ100": "^NDX"}
    for name, symbol in benchmarks.items():
        df = yf.download(symbol, start=cfg.START_DATE, end=cfg.END_DATE, progress=False)
        if df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        with get_session() as s:
            for dt, row in df.iterrows():
                date_str = dt.strftime("%Y-%m-%d")
                s.execute(text(
                    "INSERT INTO benchmarks (ticker, date, close) VALUES (:t, :d, :c) "
                    "ON CONFLICT (ticker, date) DO UPDATE SET close = :c"
                ), {"t": name, "d": date_str, "c": float(row["Close"])})
            s.commit()
        log.info(f"Synced {name} benchmark ({len(df)} days)")


def sync_exchange_rate():
    """Fetch latest USD/KRW rate."""
    try:
        from fetch_exchange_rate import fetch_and_store
        fetch_and_store()
    except Exception as e:
        log.warning(f"Exchange rate failed: {e}")


def main():
    sync_names()
    sync_benchmarks()
    sync_exchange_rate()
    log.info("Sync complete")


if __name__ == "__main__":
    main()
