# Quant Project Progress

## Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│  train.py (background)          │  trade.py (interactive)       │
│  Model Training                 │  Portfolio Trading            │
└────────────────┬────────────────┴──────────────┬────────────────┘
                 │                                │
    ┌────────────┼────────────┐      ┌───────────┼───────────┐
    ▼            ▼            ▼      ▼           ▼           ▼
 collector   features     sentiment  lstm      ensemble   portfolio
 krx_coll      .py          .py     (load)     (adjust)   manager
    │            │            │       │           │           │
    ▼            ▼            ▼       ▼           ▼           ▼
 yfinance      ta         FinBERT  PyTorch    macro+state  SQLAlchemy
 pykrx       sklearn       (HF)    models                  (DB)
                                     │
                                     ▼
                              data/models/*.pt

  config.py → MARKETS dict (US/KRX configs)
  src/market.py → detect_market(), get_config()
  src/logger.py → console + data/pipeline.log
  src/data/cache.py → TTL management

DATA FLOW — train.py:
  For each market (US, KRX):
    get_universe() → top N by market cap
    + portfolio extras not in universe
    → yfinance/pykrx → OHLCV + FRED macro
       → Features (17 indicators + sentiment + macro)
       → 60-day sequences → Train LSTM → Save model
       → Backtest → training_results.csv

DATA FLOW — trade.py:
  Select portfolio → Detect market from tickers
       → Fetch OHLCV + macro (market-specific)
       → Features → Load model → Predict → Signals
       → Ensemble (VIX + concentration + cash)
       → Adjusted signals → Confirm → Execute trades
       → Update portfolio DB + snapshot
```

## Status: v3 Distributed Deployment Complete ✅

## Tasks
- [x] Research quant strategies and models
- [x] Data collection and preprocessing
- [x] Model development
- [x] Backtesting
- [x] Portfolio database & management
- [x] FRED macro features integration
- [x] KRX (Korean stock market) support
- [x] Mailgun email notifications
- [x] Distributed architecture (OCI A1 + Pi 4B + Vercel)
- [x] Secrets management (dotenv)
- [x] Dashboard (Next.js / Vercel)
- [ ] Optimization and tuning
- [x] Redesign trade.py: portfolio-only tickers
  - [x] Remove model discovery (only use holdings + watchlist)
  - [x] Add --portfolio=<id> flag for auto mode
- [x] Rotation strategy (bench/playing)
  - [x] Implement rotation logic (promote, demote, rotate)
  - [x] rotation_metric setting (confidence, return_5d, return_20d, sharpe)
  - [x] rotation_threshold (Option B, default 10%)
  - [x] Dashboard: strategy editor with rotation options
  - [x] Mixed-market portfolio support (KRX + US in one portfolio)
  - [x] Per-currency cash (KRW/USD separated, no negative balance)
  - [x] Skip VIX adjustment for KRX tickers
  - [x] Auto-exchange (USD↔KRW when target currency insufficient)
- [ ] 3-output LSTM model (direction + predicted high% + low%)
  - [x] Modify LSTMModel: output size 1 → 3
  - [x] Update loss function (BCE + MSE combined)
  - [x] Prepare target labels (next-day high%, low%)
  - [ ] Retrain all models
  - [x] Update trade.py: extract high/low from inference
  - [x] Tick size rounding (KRX price-dependent, US $0.01)
  - [x] DB: add predicted_high, predicted_low columns to signals table
  - [x] Dashboard: display price targets on signals page
- [ ] Risk management rules (stop-loss layer)
  - [ ] Stop-loss pre-filter (price vs entry check)
  - [ ] Hold freed cash on rule trigger (no reallocation same day)
- [ ] Multi-portfolio support in trade.py (shared data, sequential loop)
- [x] Dashboard: add "Transfer In" and "Adjust" transaction types (no cash impact)
- [ ] Watchlist source tracking
  - [ ] Add source column to watchlist ("user" / "auto")
  - [ ] train.py only removes "auto" items
  - [ ] On buy → remove from watchlist
  - [ ] On full sell → add back only if source was "auto"
- [ ] Market hours awareness (for real broker execution)
  - [ ] Per-market execution scheduling (KRX 09:30 KST, US 23:30 KST)
  - [ ] Order queue: generate signals once, execute when market opens
  - [ ] Handle cross-market cash dependency (sell US → buy KRX next day)
- [ ] Ticker locking (protect manually-added holdings from model sell signals)
- [x] Executor facade (paper/broker abstraction)
- [x] Market-hour aware execution (KRX/US order by proximity, skip closed markets)
- [x] Simulation script (simulate.py with END_DATE, correct timestamps)
- [x] Ticker name sync (train.py → DB)
- [x] Exchange rate from yfinance (replaces FRED)
- [x] Fix realized P&L calculation (only SELL transactions)
- [ ] Live testing / Paper trading

## Implementation (v1 → v2)
- **Strategy**: LSTM + Sentiment Analysis (FinBERT)
- **Markets**: US (S&P500 + NASDAQ100) + KRX (KOSPI + KOSDAQ)
- **Data**: 2020-01-01 to present

### Market Detection
```python
def detect_market(ticker: str) -> str:
    return "KRX" if ticker.isdigit() else "US"
```
- No CLI flags, no DB schema changes
- Market inferred from portfolio tickers
- Empty portfolios skipped

### Files
| File | Description |
|------|-------------|
| `config.py` | Shared params + MARKETS dict (US/KRX) |
| `train.py` | Market-aware training (trains full universe + portfolio extras per market) |
| `trade.py` | Market-aware trading (detects from portfolio) |
| `portfolio.py` | Interactive portfolio management |
| `src/market.py` | `detect_market()`, `get_config()` |
| `src/data/collector.py` | US: S&P500/NASDAQ100 tickers + OHLCV via yfinance |
| `src/data/krx_collector.py` | KRX: KOSPI/KOSDAQ tickers + OHLCV via pykrx |
| `src/data/features.py` | 17 technical indicators + dynamic macro columns |
| `src/data/sentiment.py` | FinBERT sentiment (US only) |
| `src/data/fred.py` | US macro (6 FRED series) |
| `src/data/krx_macro.py` | Korean macro (VKOSPI via FRED VIX + BaseRate, CPI, Unemployment) |
| `src/data/cache.py` | Cache TTL management |
| `src/model/lstm.py` | PyTorch LSTM (2-layer) with early stopping |
| `src/model/ensemble.py` | Signal adjustment (macro risk + concentration) |
| `src/model/strategies/` | Pluggable allocation strategies (plugin pattern) |
| `src/backtest/engine.py` | Walk-forward backtest with stop-loss/take-profit |
| `src/portfolio/db.py` | SQLAlchemy models + CRUD |
| `src/portfolio/manager.py` | 24 portfolio functions |
| `src/logger.py` | Logging (console + file) |
| `src/notify.py` | Notifications (Slack, Discord, Telegram, Email) |
| `src/storage.py` | OCI Object Storage upload/download |

### KRX-Specific Notes
- OHLCV via pykrx (no yfinance dependency for Korean stocks)
- Ticker format: 6-digit codes (005930=삼성전자, 000660=SK하이닉스)
- VKOSPI: pykrx has pandas 2.2 compat bug → falls back to FRED global VIX
- Sentiment disabled (no Korean FinBERT yet)
- Macro: FRED Korean series (BaseRate, CPI, Unemployment) + VIX as fear proxy
- Capital: ₩100,000,000 (KRW)

### Advanced: Inter-Ticker Analysis (Future)
| Method | Description | Status |
|--------|-------------|--------|
| Correlation matrix | Price movement similarity between holdings | ✅ Implemented |
| Lead-lag analysis | Does ticker A predict ticker B with delay? | ⬜ |
| Cross-ticker features | Add sector ETF / correlated ticker returns as LSTM input | ⬜ |
| Multi-ticker LSTM | Single model for all tickers, captures inter-ticker dynamics | ⬜ |
| Granger causality | Statistical test: does A's past predict B's future? | ⬜ |
| Graph Neural Network | Learn ticker relationships as a graph | ⬜ |

### How to Run
```bash
pip install -r requirements.txt

# US market
python portfolio.py   # create portfolio, add US tickers (AAPL, MSFT, ...)
python train.py       # trains US models
python trade.py       # select US portfolio, generate signals

# KRX market
python portfolio.py   # create portfolio, add KRX tickers (005930, 000660, ...)
python train.py       # auto-detects KRX, trains KRX models
python trade.py       # select KRX portfolio, generate signals

# train.py trains ALL markets that have portfolios with tickers
# --full flag forces full retrain (default: incremental)
python train.py --full
```

## Portfolio Database Design (v2)

SQLAlchemy-based. Defaults to SQLite (`data/portfolio.db`).

### Schema
```
portfolios ──┬── holdings
             ├── transactions
             ├── signals
             ├── backtest_results
             ├── watchlist
             ├── allocations
             └── portfolio_snapshots
```

Market is NOT stored in DB — inferred from ticker format at runtime.

### Portfolio Manager Features
| Category | Functions |
|----------|-----------|
| Core | `create`, `buy`, `sell`, `summary`, `record_signal`, `record_backtest` |
| Position Mgmt | `add_to_watchlist`, `remove_from_watchlist`, `refresh_prices`, `position_size` |
| P&L | `gross_pnl`, `realized_pnl`, `take_snapshot`, `equity_curve`, `benchmark_compare` |
| Risk | `portfolio_sharpe`, `max_drawdown`, `concentration`, `correlation_matrix`, `value_at_risk` |
| Allocation | `set_target_allocation`, `drift`, `rebalance_suggestions` |
| Reporting | `print_report`, `export_csv`, `plot_equity` |
| Multi-Portfolio | `list_all`, `compare`, `clone`, `delete` |

## FRED Macro Features

### US
| Series ID | Name | Frequency |
|-----------|------|-----------|
| `VIXCLS` | VIX | Daily |
| `DFF` | Federal Funds Rate | Daily |
| `T10Y2Y` | 10Y-2Y Treasury Spread | Daily |
| `CPIAUCSL` | CPI | Monthly |
| `UNRATE` | Unemployment | Monthly |
| `BAMLH0A0HYM2` | High-Yield Bond Spread | Daily |

### KRX
| Series ID | Name | Frequency |
|-----------|------|-----------|
| `VIXCLS` | VIX (global fear proxy) | Daily |
| `INTDSRKRM193N` | BOK Base Rate | Monthly |
| `KORCPIALLMINMEI` | Korean CPI | Monthly |
| `LRUNTTTTKRM156S` | Korean Unemployment | Monthly |

## Python Libraries

### Data — Gathering
- [x] `yfinance` — US stocks OHLCV
- [x] `pykrx` — Korean stocks OHLCV (KOSPI/KOSDAQ)
- [x] `fredapi` — FRED economic data (US + Korean series)
- [ ] `financedatabase` — 300k+ financial products metadata
- [ ] `pandas-datareader` — FRED, World Bank, OECD
- [ ] `ccxt` — crypto exchange data
- [ ] `alpha_vantage` — stocks, forex, crypto
- [ ] `polygon-api-client` — real-time US market data

### Data — Processing
- [x] `pandas` / `numpy` — data manipulation
- [x] `ta` — technical indicators
- [x] `scikit-learn` — MinMaxScaler

### Machine Learning
- [x] `torch` — LSTM model
- [x] `transformers` — FinBERT sentiment

### Infrastructure
- [x] `sqlalchemy` — portfolio DB
- [x] `matplotlib` — equity curve plots
- [x] `lxml` / `html5lib` — Wikipedia scraping

## Allocation Strategies (Plugin System)

Pluggable trade allocation via `src/model/strategies/`. Drop a `.py` file → auto-registered.

```
src/model/strategies/
├── __init__.py          # auto-loader + @strategy decorator
├── equal_weight.py      # split cash equally among BUY signals
└── rebalance.py         # trim weakest HOLDs + rebalance for new BUYs
```

### Available Strategies

| Strategy | Behavior |
|----------|----------|
| `equal_weight` | Split cash equally among BUYs. No rebalancing. Default. |
| `rebalance` | Trim overweight HOLDs (weakest first) to free cash for new BUYs. |

### Selection Priority

1. `--strategy=` CLI arg (override)
2. Portfolio's `allocator_strategy` field in DB (per-portfolio)
3. `"equal_weight"` (default)

### Adding a New Strategy

```python
# src/model/strategies/my_strategy.py
from . import strategy

@strategy
def my_strategy(signals, holdings, cash, portfolio_value, params):
    # signals: [{ticker, signal (1/0/-1), probability, price}, ...]
    # holdings: [{ticker, shares, avg_cost, current_price}, ...]
    # Return: [{ticker, action, shares, price, total, reason}, ...]
    ...
```

No other files need editing. Available immediately on next run.

## Notifications

Sent on:
- **Strong performers added to watchlist** — per market tag
- **Poor performers removed** — per market tag
- **Trades executed** — BUY with amount, SELL with P&L

Configure in `config.py` → `NOTIFICATIONS` dict.

## Notes
- Started: 2026-04-27
- KRX support added: 2026-04-29
- Distributed deployment (v3): 2026-04-30
- Language: Python
- Core stack: yfinance + pykrx + pandas + numpy + ta + torch + transformers + sqlalchemy + fredapi + python-dotenv
- Secrets: `.env` file (python-dotenv), never committed to git
- DB: Supabase PostgreSQL (shared across all nodes)
- Storage: OCI Object Storage for models + results (single bucket `qtradeBucket`, prefixes: `models/`, `results/`)
- Multi-currency cash: per-currency tracking via transactions (DEPOSIT/WITHDRAW/EXCHANGE)
- Notifications: auto-enabled if webhook/key is set in `.env`
- First run of train.py will download FinBERT model (~400MB) for US market
- Models saved to data/models/*.pt (one per ticker, both markets share directory)
- KRX tickers (6-digit) and US tickers (alphabetic) don't conflict in filenames
- Logs written to data/pipeline.log (DEBUG level)
- pykrx 1.2.7 requires KRX login for index data
- torch requires numpy<2 (torch 2.2.1) or torch>=2.4 for numpy 2.x — update together

## External Services

### Infrastructure

| Service | Purpose | Tier | Status |
|---------|---------|------|--------|
| Supabase | PostgreSQL database (shared) | Free (500 MB) | ✅ Connected |
| OCI Object Storage | Model files + training results | Free (10 GB) | ✅ Connected |
| Vercel | Dashboard hosting (Next.js) | Free (Hobby) | ✅ Deployed |
| OCI A1 Compute | train.py server (daily) | Free (4 OCPU / 24 GB) | ⬜ Pending |
| GitHub | Code repo + deploy trigger | Free | ✅ Connected |

### Notifications

| Service | Purpose | Status |
|---------|---------|--------|
| Slack | Trade/training alerts | ✅ Active |
| Discord | Trade/training alerts | ✅ Active |
| Mailgun | Email alerts | ✅ Active |

### Data APIs

| Service | Purpose | Status |
|---------|---------|--------|
| FRED | US + Korean macro data | ✅ Active |
| yfinance | US stock OHLCV | ✅ Active |
| pykrx | KRX stock OHLCV | ✅ Active |


## v3 — Distributed Deployment

### Architecture
- 3 features: Train (OCI A1), Trade (Pi 4B), Portfolio/Dashboard (Vercel + PC)
- External DB: Supabase (PostgreSQL)
- External Storage: OCI Object Storage (models + results)
- Git = code only, monorepo
- See `docs/deploy.md` for full architecture

### Train Feature — Tasks

Core logic complete ✅. Remaining: adapt for distributed deployment.

| # | Task | Status |
|---|------|--------|
| 1 | DB_URL → Supabase PostgreSQL | ✅ |
| 2 | Upload models to OCI Object Storage after training | ✅ |
| 3 | Upload results (CSV) to OCI Object Storage | ✅ |
| 4 | Storage abstraction (read/write models via bucket) | ✅ |
| 5 | Headless mode hardening (no prompts, clean exit codes) | ✅ |
| 6 | Cron-compatible logging (no console dependency) | ✅ (already supported) |

### Trade Feature — Tasks (next)

| # | Task | Status |
|---|------|--------|
| 1 | `--auto` flag (non-interactive, auto-select portfolio) | ✅ |
| 2 | Download models from OCI Object Storage before inference | ✅ |
| 3 | DB_URL → Supabase PostgreSQL | ✅ (shared with Train) |
| 4 | Cron-compatible (headless, exit codes) | ✅ |

### Portfolio/Dashboard Feature — Tasks

| # | Task | Status |
|---|------|--------|
| 1 | Scaffold Vercel dashboard (Next.js) | ✅ |
| 2 | Read results from OCI Object Storage | ✅ |
| 3 | Read portfolio data from Supabase | ✅ |
| 4 | Display: training results, backtest, holdings, P&L | ✅ |
| 5 | Deploy to Vercel (GitHub auto-deploy) | ✅ |
| 6 | Vercel Analytics + Speed Insights | ✅ |
| 7 | UI Redesign (Tailwind + shadcn/ui + Recharts) | ✅ |
| 8 | Auth (Supabase OAuth + allowlist) | ✅ |
| 9 | Trade recording form | ✅ |
| 10 | Multi-currency (USD/KRW) | ✅ |
| 11 | Portfolio comparison | ✅ |
| 12 | Connect OCI Object Storage (set `OCI_RESULTS_URL` env var on Vercel) | ✅ |
