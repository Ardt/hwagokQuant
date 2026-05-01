# hwagokQuant Quant Trading System

LSTM + Sentiment analysis for US (S&P500/NASDAQ100) and KRX (KOSPI/KOSDAQ) markets.
Distributed architecture: Train (OCI A1), Trade (Raspberry Pi), Dashboard (Vercel).

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys in `.env`:
- `FRED_API_KEY` — [FRED](https://fred.stlouisfed.org/docs/api/api_key.html)
- `KRX_ID` / `KRX_PW` — pykrx login (for KRX index data)

Optional:
- `SLACK_WEBHOOK`, `DISCORD_WEBHOOK` — notifications
- `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `EMAIL_RECIPIENT` — email alerts
- `Q_DB_URL` — PostgreSQL URL (default: local SQLite)
- `Q_OCI_NAMESPACE` — OCI Object Storage (for distributed deployment)

## How to Run

### 1. Create a portfolio

```bash
python portfolio.py
```
```
Select: 2 (Create portfolio)
  Name: KRX_Test
  Capital [100000]: 100000000
  Tickers: 005930,000660,035420
```

Market is auto-detected from ticker format:
- 6-digit numeric → KRX (e.g. `005930`)
- Alphabetic → US (e.g. `AAPL`)

### 2. Train models

```bash
python train.py          # incremental (default)
python train.py --full   # full retrain
```

Trains LSTM per ticker → saves to `data/models/{ticker}_lstm.pt`.
Uploads models + results to OCI Object Storage (if configured).

### 3. Generate signals & paper trade

```bash
python trade.py          # interactive
python trade.py --auto   # headless (for cron)
```

Downloads latest models from OCI (if configured), generates signals, executes paper trades.

## Architecture

```
┌───────────┐     ┌───────────┐     ┌───────────────────┐
│   TRAIN   │     │   TRADE   │     │    PORTFOLIO      │
│  OCI A1   │     │  Pi 4B    │     │  Vercel + PC      │
├───────────┤     ├───────────┤     ├───────────────────┤
│ train.py  │     │ trade.py  │     │ dashboard/        │
│ backtest  │     │ --auto    │     │ portfolio.py      │
└─────┬─────┘     └─────┬─────┘     └────────┬──────────┘
      │                  │                     │
      ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────┐
│  Supabase (PostgreSQL)  +  OCI Object Storage           │
└─────────────────────────────────────────────────────────┘
```

## File Structure

```
├── train.py              # Model training + backtest (daily, OCI)
├── trade.py              # Signal generation + paper trade (daily, Pi)
├── portfolio.py          # Portfolio management CLI (local PC)
├── config.py             # Configuration (reads from .env)
├── .env                  # Secrets (not in git)
├── .env.example          # Template
├── requirements.txt
├── src/
│   ├── data/             # Collectors, features, sentiment, macro
│   ├── model/            # LSTM, ensemble
│   ├── portfolio/        # DB models, manager (24 functions)
│   ├── backtest/         # Walk-forward engine
│   ├── storage.py        # OCI Object Storage helper
│   ├── market.py         # Market detection
│   ├── logger.py         # Logging
│   └── notify.py         # Slack, Discord, Telegram, Email
├── dashboard/            # Next.js app (Vercel)
├── docs/                 # Architecture, flow, strategies
└── data/                 # Models, CSVs, DB (gitignored)
```

## Summary

```
portfolio.py  →  create portfolio + add tickers (one-time)
train.py      →  train models + backtest (run daily)
trade.py      →  generate signals + execute (run daily, after market open)
```

See `docs/deploy.md` for distributed deployment details.
