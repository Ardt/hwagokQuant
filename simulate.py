"""Backtest simulation: run train.py + trade.py day by day.

Simulates daily operation from START to END date.
Sets config.END_DATE for each day so data fetchers stop at that date.

Usage: python simulate.py --start=2026-04-01 --end=2026-05-10
"""

import sys
import importlib
from datetime import date, timedelta
from src import logger

logger.setup()
log = logger.get("simulate")

START = next((a.split("=")[1] for a in sys.argv if a.startswith("--start=")), "2026-04-01")
END = next((a.split("=")[1] for a in sys.argv if a.startswith("--end=")), "2026-05-10")
SKIP_TRAIN = "--skip-train" in sys.argv


def daterange(start: str, end: str):
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    while s <= e:
        # Skip weekends
        if s.weekday() < 5:
            yield s
        s += timedelta(days=1)


def main():
    import config as cfg

    print(f"=== Simulation: {START} → {END} ===")
    days = list(daterange(START, END))
    log.info(f"Simulation: {START} → {END} ({len(days)} trading days)")

    for i, day in enumerate(days):
        day_str = day.isoformat()
        log.info(f"--- Day {i+1}/{len(days)}: {day_str} ---")

        # Set END_DATE so fetchers stop at this day
        cfg.END_DATE = day_str

        # Clear data caches so each day fetches fresh
        # (don't clear — let incremental fetching work)

        # Train (optional, can skip for speed)
        if not SKIP_TRAIN:
            try:
                import train
                importlib.reload(train)
                train.main()
            except Exception as e:
                log.error(f"[TRAIN ERROR] {e}")

        # Trade
        try:
            # Force auto mode
            if "--auto" not in sys.argv:
                sys.argv.append("--auto")
            import trade
            importlib.reload(trade)
            trade.main()
        except Exception as e:
            log.error(f"[TRADE ERROR] {e}")

    log.info(f"Simulation complete: {len(days)} days")


if __name__ == "__main__":
    main()
