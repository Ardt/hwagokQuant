# Architecture & Deployment

## System Overview

```
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   OCI A1 Free     │  │  Raspberry Pi     │  │   Local PC        │
│  (4 OCPU / 24GB)  │  │  (Pi 3 or Pi 4)   │  │                   │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│  train.py (daily) │  │  trade.py (daily) │  │  portfolio.py     │
│  Backtest         │  │  trade_lite.py    │  │  (interactive)    │
│  Upload models    │  │  Notifications    │  │                   │
└────────┬──────────┘  └────────┬──────────┘  └────────┬──────────┘
         │                      │                       │
         ▼                      ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              Supabase (PostgreSQL) — shared DB                   │
└─────────────────────────────────────────────────────────────────┘
         │                      │                       │
         ▼                      ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│         OCI Object Storage (models/*.pt + results CSV)          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                   ┌──────────────────────┐
                   │   Vercel (Hobby)     │
                   │   Dashboard (web)    │
                   │   hwagok-quant.      │
                   │   vercel.app         │
                   └──────────────────────┘
```

## Feature → Hardware Mapping

| Feature | Deployed To | Reason |
|---------|-------------|--------|
| `train.py` | OCI A1 | CPU-heavy (2-3h), needs RAM |
| `trade.py` | Pi 4B | Lightweight inference, always-on |
| `trade_lite.py` | Pi 3 | Memory-optimized for 1GB RAM |
| `portfolio.py` | Local PC | Interactive CLI |
| Dashboard | Vercel | Auto-deploy on push |
| Portfolio DB | Supabase | Shared PostgreSQL |
| Models + Results | OCI Object Storage | Central file store |

---

## Data Flow

```
train.py (OCI)
    ├── models/*.pt ──upload──→ OCI Object Storage
    ├── results.csv ──upload──→ OCI Object Storage
    └── DB writes   ──────────→ Supabase (signals, backtest_results)

trade.py / trade_lite.py (Pi)
    ├── models/*.pt ←─download── OCI Object Storage
    ├── DB reads    ←────────── Supabase (portfolio, holdings)
    └── DB writes   ──────────→ Supabase (transactions, snapshots)

portfolio.py (PC)
    └── DB read/write ────────→ Supabase

Dashboard (Vercel)
    ├── results    ←────────── OCI Object Storage (pre-auth URL)
    └── DB reads   ←────────── Supabase
```

---

## Pipeline Flow

### train.py — Model Training

```
For each market (US, KRX):
  1. get_universe() → top 100 by market cap + portfolio extras
  2. Fetch OHLCV (yfinance / pykrx, incremental)
  3. Fetch macro (FRED)
  4. Build features (17 technical indicators + sentiment + macro)
  5. Create 60-day sequences
  6. Train LSTM per ticker (walk-forward, early stopping)
  7. Save model → data/models/{ticker}_lstm.pt
  8. Backtest → training_results.csv
  9. Upload to OCI Object Storage
```

### trade.py — Signal Generation + Paper Trading

```
  1. Select portfolio → detect market from tickers
  2. Download models from OCI Object Storage
  3. Fetch OHLCV + macro (market-specific)
  4. Build features → Load model → Predict
  5. Ensemble adjustment (VIX, concentration, cash)
  6. Plan trades (equal-weight buys, ratio sells)
  7. Execute paper trades → Record to DB
  8. Take snapshot → Send notifications
```

### Market Detection

```
ticker.isdigit() → KRX (e.g. "005930")
else             → US  (e.g. "AAPL")
```

No CLI flags needed — market inferred from portfolio tickers.

---

## Market Configs

| Setting | US | KRX |
|---------|-----|-----|
| Currency | USD | KRW |
| Capital | $100,000 | ₩100,000,000 |
| OHLCV | yfinance | pykrx |
| Tickers | Wikipedia (S&P500 + NASDAQ100) | pykrx (KOSPI + KOSDAQ) |
| Macro | FRED (VIX, Fed Funds, Treasury, CPI, Unemployment, HY Spread) | FRED VIX + Korean BaseRate, CPI, Unemployment |
| Sentiment | FinBERT | Disabled |

---

## Cron Schedules

### OCI A1 — Daily Training
```bash
0 1 * * *  cd ~/q && source venv/bin/activate && python train.py
```

### Raspberry Pi — Daily Trading
```bash
30 9 * * 1-5  cd ~/q && source venv/bin/activate && python trade.py --auto
```

### Auto-Deploy (all nodes)
```bash
*/5 * * * *  cd ~/q && git fetch origin && git reset --hard origin/main
```

---

## External Services

| Service | Purpose | Tier | Status |
|---------|---------|------|--------|
| Supabase | PostgreSQL database | Free (500 MB) | ✅ |
| OCI Object Storage | Models + results | Free (10 GB) | ✅ |
| OCI A1 Compute | Training server | Free (4 OCPU / 24 GB) | ⬜ |
| Vercel | Dashboard hosting | Free (Hobby) | ✅ |
| GitHub | Code repo + deploy | Free | ✅ |
| Slack | Trade/training alerts | Free | ✅ |
| Discord | Trade/training alerts | Free | ✅ |
| Mailgun | Email alerts | Free (5k/month) | ✅ |
| FRED | Macro economic data | Free | ✅ |

---

## Service Setup

### Supabase
```bash
# .env
Q_DB_URL=postgresql+psycopg2://postgres.REF:PASS@HOST:5432/postgres?sslmode=require
```
- Project Settings → Database → Connection string (Pooler mode)
- Project Settings → API → URL + anon key (for dashboard)

### OCI Object Storage
```bash
# .env
Q_OCI_NAMESPACE=your_namespace
Q_OCI_BUCKET=qtradeBucket
```
- Single bucket with prefix-based organization: `models/`, `results/`
- Pre-authenticated request URL for Vercel dashboard (scope to `results/` prefix)

### Notifications
```bash
# .env (any/all optional)
SLACK_WEBHOOK=https://hooks.slack.com/services/...
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
MAILGUN_API_KEY=...
MAILGUN_DOMAIN=...
EMAIL_RECIPIENT=...
```

---

## Node Setup

### OCI A1
```bash
sudo apt update && sudo apt install -y python3.10 python3.10-venv git
git clone <repo> ~/q && cd ~/q
python3.10 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in secrets
```

### GPU PC (5600X + 3060Ti)
```bash
git clone <repo> ~/q && cd ~/q
python -m venv venv && venv\Scripts\activate
pip install -r requirements-gpu.txt
pip install -r requirements.txt
cp .env.example .env  # fill in secrets
python train.py --full  # ~1.5-3 hours for all tickers
```

### Raspberry Pi (Pi 4)
```bash
sudo apt update && sudo apt install -y python3 python3-venv git
git clone <repo> ~/q && cd ~/q
python3 -m venv venv && source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Raspberry Pi 3 (low memory)
```bash
# Same as Pi 4, plus:
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
# Use trade_lite.py instead of trade.py
```

### Vercel Dashboard
- Import repo → Root Directory: `dashboard`
- Set env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `OCI_RESULTS_URL`

---

## Hardware Specs

| | OCI A1 | Pi 4B | Pi 3 | Vercel | Supabase |
|--|--------|-------|------|--------|----------|
| CPU | 4 OCPU ARM | A72 4-core | A53 4-core | Serverless | — |
| RAM | 24 GB | 4-8 GB | 1 GB | 1 GB/fn | — |
| Storage | 50 GB | USB SSD | SD card | Stateless | 500 MB |
| Cost | Free | ~$50 | ~$35 | Free | Free |
| Script | train.py | trade.py | trade_lite.py | dashboard | DB |
