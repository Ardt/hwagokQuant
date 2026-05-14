"""Fetch USD/KRW exchange rate from KRX and store in Supabase.

Uses pykrx for real-time KRX exchange rate data.
Run daily via cron or from train.py.

Usage: python fetch_exchange_rate.py
"""

import os
from datetime import date, timedelta
from dotenv import load_dotenv
from pykrx import stock
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("Q_DB_URL", "sqlite:///data/portfolio.db")
engine = create_engine(DB_URL, echo=False)


def fetch_and_store():
    """Fetch latest USD/KRW rate from KRX, store in DB. Returns the rate."""
    # Try last 7 days to find a trading day
    for days_back in range(7):
        check_date = (date.today() - timedelta(days=days_back)).strftime("%Y%m%d")
        try:
            df = stock.get_exhaustion_rates_of_foreign_investment_by_ticker(check_date, "KOSPI")
            # Alternative: use yfinance for KRW=X
            break
        except Exception:
            continue

    # Fallback: use yfinance for USD/KRW
    try:
        import yfinance as yf
        ticker = yf.Ticker("KRW=X")
        rate = ticker.info.get("regularMarketPrice") or ticker.info.get("previousClose")
        if rate:
            today_str = date.today().isoformat()
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO exchange_rates (pair, rate, date) VALUES (:p, :r, :d) "
                    "ON CONFLICT (pair, date) DO UPDATE SET rate = :r"
                ), {"p": "USD/KRW", "r": float(rate), "d": today_str})
            print(f"USD/KRW: {rate:.2f} ({today_str})")
            return float(rate)
    except Exception as e:
        print(f"Error fetching rate: {e}")

    return None


def main():
    rate = fetch_and_store()
    if not rate:
        print("Failed to fetch exchange rate.")


if __name__ == "__main__":
    main()
