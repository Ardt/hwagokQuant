"""Migrate data from local SQLite to Supabase PostgreSQL."""
import sqlite3
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = "data/portfolio.db"
PG_URL = os.environ.get("Q_DB_URL")

if not PG_URL:
    print("Q_DB_URL not set in .env")
    exit(1)

if not os.path.exists(SQLITE_PATH):
    print(f"{SQLITE_PATH} not found")
    exit(1)

# Connect
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
pg_engine = create_engine(PG_URL)

TABLES = [
    "portfolios",
    "holdings",
    "transactions",
    "signals",
    "backtest_results",
    "watchlist",
    "allocations",
    "portfolio_snapshots",
]

with pg_engine.connect() as pg:
    for table in TABLES:
        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: 0 rows (skip)")
            continue

        cols = rows[0].keys()
        placeholders = ", ".join([f":{c}" for c in cols])
        col_names = ", ".join(cols)
        insert_sql = text(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")

        pg.execute(insert_sql, [dict(r) for r in rows])
        pg.commit()
        print(f"  {table}: {len(rows)} rows migrated")

sqlite_conn.close()
print("\nMigration complete!")
