"""Fetch USD/KRW exchange rate from FRED and store in Supabase.

FRED series: DEXKOUS (Korean Won per USD, daily)
Run daily via cron or manually.

Usage: python fetch_exchange_rate.py
"""

import os
from datetime import date, timedelta
from dotenv import load_dotenv
from fredapi import Fred
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("Q_DB_URL", "sqlite:///data/portfolio.db")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

engine = create_engine(DB_URL, echo=False)


def main():
    if not FRED_API_KEY:
        print("Error: FRED_API_KEY not set in .env")
        return

    fred = Fred(api_key=FRED_API_KEY)

    # Fetch last 30 days to backfill any gaps
    start = date.today() - timedelta(days=30)
    series = fred.get_series("DEXKOUS", observation_start=start)
    series = series.dropna()

    if series.empty:
        print("No data from FRED.")
        return

    with engine.begin() as conn:
        for dt, rate in series.items():
            conn.execute(text(
                "INSERT INTO exchange_rates (pair, rate, date) VALUES (:p, :r, :d) "
                "ON CONFLICT (pair, date) DO UPDATE SET rate = :r"
            ), {"p": "USD/KRW", "r": float(rate), "d": dt.date().isoformat()})

    latest = series.iloc[-1]
    print(f"USD/KRW: {latest:.2f} ({series.index[-1].date()})")
    print(f"Stored {len(series)} days of rates.")


if __name__ == "__main__":
    main()
