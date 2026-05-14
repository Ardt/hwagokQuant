"""FRED macro data: fetch, cache, and merge into ticker DataFrames."""

import os
import pandas as pd
from fredapi import Fred
import config as cfg
from src.logger import get

log = get("data.fred")

_fred = None


def _get_fred() -> Fred:
    global _fred
    if _fred is None:
        _fred = Fred(api_key=cfg.FRED_API_KEY)
    return _fred


def fetch_fred_data() -> pd.DataFrame:
    """Fetch all FRED series, cache to CSV. Incremental — only fetches new days."""
    from datetime import date

    cache_path = os.path.join(cfg.DATA_DIR, "fred.csv")
    today = cfg.END_DATE or date.today().strftime("%Y-%m-%d")

    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        last_date = df.index.max().strftime("%Y-%m-%d")
        if last_date >= today:
            log.info("FRED data is current")
            return df
        # Fetch only new days
        log.info(f"FRED: fetching from {last_date} to today...")
        fred = _get_fred()
        for series_id, col_name in cfg.FRED_SERIES.items():
            try:
                s = fred.get_series(series_id, observation_start=last_date, observation_end=None)
                if not s.empty:
                    new_data = s[s.index > df.index.max()]
                    if not new_data.empty:
                        for idx, val in new_data.items():
                            df.loc[idx, col_name] = val
            except Exception as e:
                log.error(f"{series_id} failed: {e}")
        df = df.ffill().bfill()
        df.to_csv(cache_path)
        log.info("FRED data updated incrementally")
        return df

    # First fetch — full download
    log.info("Fetching FRED macro data (full)...")
    fred = _get_fred()
    frames = {}
    for series_id, col_name in cfg.FRED_SERIES.items():
        try:
            s = fred.get_series(series_id, observation_start=cfg.START_DATE, observation_end=None)
            frames[col_name] = s
            log.debug(f"{series_id} ({col_name}): {len(s)} observations")
        except Exception as e:
            log.error(f"{series_id} failed: {e}")

    df = pd.DataFrame(frames)
    df = df.ffill().bfill()
    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    df.to_csv(cache_path)
    log.info(f"Cached FRED data to {cache_path}")
    return df


def merge_fred(ticker_df: pd.DataFrame, fred_df: pd.DataFrame) -> pd.DataFrame:
    """Merge FRED columns into a ticker DataFrame by date index."""
    for col in fred_df.columns:
        ticker_df[col] = fred_df[col].reindex(ticker_df.index).ffill().bfill()
    return ticker_df
