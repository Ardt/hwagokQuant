"""Korean macro data: fetch series defined in config, source-agnostic."""

import os
from datetime import date
import pandas as pd
from fredapi import Fred
import config as cfg
from src.market import get_config
from src.logger import get

log = get("data.krx_macro")
_mcfg = get_config("KRX")
_fred = None


def _get_fred() -> Fred:
    global _fred
    if _fred is None:
        _fred = Fred(api_key=cfg.FRED_API_KEY)
    return _fred


def fetch_macro() -> pd.DataFrame:
    """Fetch Korean macro data from FRED. Incremental."""
    cache_path = os.path.join(cfg.DATA_DIR, _mcfg["data_files"]["macro"])
    today = cfg.END_DATE or date.today().strftime("%Y-%m-%d")
    series_map = _mcfg["macro_series"]

    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        last_date = df.index.max().strftime("%Y-%m-%d")
        if last_date >= today:
            log.info("KRX macro data is current")
            return df
        log.info(f"KRX macro: updating from {last_date}...")
        fred = _get_fred()
        for series_id, col_name in series_map.items():
            try:
                s = fred.get_series(series_id, observation_start=last_date)
                if not s.empty:
                    for idx, val in s[s.index > df.index.max()].items():
                        df.loc[idx, col_name] = val
            except Exception as e:
                log.error(f"{series_id} failed: {e}")
        df = df.ffill().bfill()
        df.to_csv(cache_path)
        return df

    # Full fetch
    log.info("Fetching KRX macro data (full)...")
    fred = _get_fred()
    frames = {}
    for series_id, col_name in series_map.items():
        try:
            s = fred.get_series(series_id, observation_start=cfg.START_DATE)
            frames[col_name] = s
            log.debug(f"{series_id} ({col_name}): {len(s)} obs")
        except Exception as e:
            log.error(f"{series_id} failed: {e}")

    if not frames:
        log.warning("No macro data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    df = df.ffill().bfill()
    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    df.to_csv(cache_path)
    log.info(f"Cached KRX macro ({len(df)} rows)")
    return df


def merge_macro(ticker_df: pd.DataFrame, macro_df: pd.DataFrame) -> pd.DataFrame:
    """Merge macro columns into a ticker DataFrame.
    Applies feature weights from config if defined."""
    weights = _mcfg.get("macro_weights", {})
    for col in macro_df.columns:
        values = macro_df[col].reindex(ticker_df.index).ffill().bfill()
        w = weights.get(col, 1.0)
        if w != 1.0:
            values = values * w
        ticker_df[col] = values
    return ticker_df
