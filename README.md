# hwagokQuant

LSTM + Sentiment analysis for US (S&P500/NASDAQ100) and KRX (KOSPI/KOSDAQ) markets.
Distributed architecture: Train (OCI A1), Trade (Raspberry Pi), Dashboard (Vercel).

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
cp .env.example .env         # fill in API keys
```

```bash
python portfolio.py          # create portfolio + add tickers
python train.py              # train models + backtest
python trade.py              # generate signals + paper trade
python trade_lite.py         # low-memory version (Pi 3)
```

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/progress.md](docs/progress.md) | Project status, tasks, libraries, notes |
| [docs/architecture.md](docs/architecture.md) | System architecture, deployment, services, data flow |
| [docs/strategies.md](docs/strategies.md) | Strategy explanation (English) |
| [docs/strategies_kr.md](docs/strategies_kr.md) | 전략 설명 (한국어) |
| [docs/dashboard.md](docs/dashboard.md) | Dashboard analysis, UI redesign, auth design |

## Architecture

```
train.py (OCI A1)  →  models + results  →  OCI Object Storage
trade.py (Pi)      ←  download models   ←  OCI Object Storage
                   →  trades + signals  →  Supabase (PostgreSQL)
dashboard (Vercel) ←  read data         ←  Supabase + OCI Storage
```

## Dashboard

Live at: https://hwagok-quant.vercel.app/
