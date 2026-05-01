# Project Flow

## Overview

```
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│      train.py          │  │    portfolio.py        │  │      trade.py          │
│  (background, auto)    │  │  (interactive, manual) │  │  (interactive, signals)│
├────────────────────────┤  ├────────────────────────┤  ├────────────────────────┤
│ 1. Each market universe  │  │ 1. Create portfolio    │  │ 1. Select portfolio    │
│ 2. + portfolio extras   │  │ 2. Add/remove tickers  │  │ 2. Detect market       │
│ 3. Fetch OHLCV + macro │  │ 3. Manual buy/sell     │  │ 3. Load saved models   │
│ 4. Build features      │  │ 4. Set allocations     │  │ 4. Generate signals    │
│ 5. Train LSTM/ticker   │  │ 5. View reports        │  │ 5. Ensemble adjust     │
│ 6. Save models         │  │ 6. Refresh prices      │  │ 6. Paper trade         │
│ 7. Backtest + log      │  │ 7. Delete portfolio    │  │ 7. Record to DB        │
│                        │  │                        │  │                        │
│ Reads: config + DB     │  │ Reads/Writes: DB       │  │ Reads: DB + models     │
│ Writes: models/*.pt    │  │                        │  │ Writes: DB (trades)    │
└───────────┬────────────┘  └───────────┬────────────┘  └───────────┬────────────┘
            │                           │                           │
            └───── data/models/*.pt ────┘───── data/portfolio.db ───┘
```

---

## Market Detection

```
ticker.isdigit() → KRX (e.g. "005930", "000660")
else             → US  (e.g. "AAPL", "MSFT")

train.py:  scan all portfolios → group tickers by market → train each
trade.py:  select portfolio → detect market from tickers → use correct pipeline
Empty portfolios: skipped (no train, no trade)
```

---

## Market Configs (config.py → MARKETS dict)

| Setting | US | KRX |
|---------|-----|-----|
| Currency | USD | KRW |
| Capital | $100,000 | ₩100,000,000 |
| OHLCV source | yfinance | pykrx |
| Ticker source | Wikipedia (S&P500 + NASDAQ100) | pykrx (KOSPI + KOSDAQ) |
| Macro source | FRED (VIX, Fed Funds, Treasury, CPI, Unemployment, HY Spread) | FRED VIX + Korean BaseRate, CPI, Unemployment |
| Sentiment | FinBERT (English news) | Disabled |
| Ticker format | Alphabetic (AAPL) | 6-digit numeric (005930) |

---

## train.py — Model Training Pipeline

### Step 1. Universe + Portfolio Extras
```
For each market (US, KRX):
  get_universe() → top 100 tickers by market cap
  + portfolio tickers (holdings + watchlist) not already in universe
  = combined training list
```

### Step 2. Data Collection
```
US:  Wikipedia → Tickers → yfinance → OHLCV (incremental)
KRX: pykrx → KOSPI/KOSDAQ tickers by market cap → OHLCV (incremental)
     Cache: data/tickers.csv (US), data/krx_tickers.csv (KRX)
     Cache: data/ohlcv.csv (US), data/krx_ohlcv.csv (KRX)
```

### Step 3. Feature Engineering (`src/data/features.py`)
```
Raw OHLCV → 17 Technical Indicators (same for both markets):
            Trend: SMA(20), SMA(50), EMA(12), MACD, MACD Signal, MACD Hist
            Momentum: RSI, Stochastic RSI
            Volatility: Bollinger Bands (High/Low/Width), ATR
            Volume: OBV
            Returns: 1-day, 5-day, 20-day volatility
         → MinMaxScaler (normalize 0-1)
         → Sliding window → 60-day sequences
```

### Step 4. Sentiment (`src/data/sentiment.py`)
```
US:  yfinance news → FinBERT → score (-1 to +1)
KRX: Disabled (set to 0.0) — no Korean FinBERT yet
```

### Step 5. Macro Data
```
US:  FRED → VIX, Fed Funds, Treasury Spread, CPI, Unemployment, HY Spread
KRX: FRED VIX (global fear proxy) + Korean BaseRate, CPI, Unemployment
     Cache: data/fred.csv (US), data/krx_macro.csv (KRX)
```

### Step 6. LSTM Training (`src/model/lstm.py`)
```
Combined features as 60-day sequences
         → Train/Val split (80/20, walk-forward)
         → PyTorch LSTM (2 layers, 64 hidden, dropout 0.2)
         → Binary: price UP (1) or DOWN (0) tomorrow?
         → Early stopping (patience=10)
         → Save → data/models/{ticker}_lstm.pt
```

### Step 7. Backtest (`src/backtest/engine.py`)
```
Model predictions → Signals (>0.5=BUY, <0.5=SELL)
         → Walk-forward backtest (stop-loss -5%, take-profit +10%)
         → Metrics: return, Sharpe, win rate, max drawdown
         → Output: data/training_results.csv (US), data/training_results_krx.csv (KRX)
```

---

## trade.py — Signal Generation + Paper Trading

### Step 1. Portfolio Selection
```
DB → List portfolios (shows market + currency) → Select one
  → Detect market from tickers
```

### Step 2. Signal Generation
```
Portfolio tickers → Fetch OHLCV + macro (market-specific)
         → Build features (same pipeline)
         → Load saved model (data/models/{ticker}_lstm.pt)
         → Predict → Raw signal per ticker
```

### Step 3. Ensemble Adjustment (`src/model/ensemble.py`)
```
Raw signals + macro state + portfolio state
         → Risk multiplier (VIX/VKOSPI > 30 → reduce buys)
         → Concentration check (>25% in one ticker → reduce)
         → Cash check (<10% cash → reduce buys)
         → Output: adjusted signals (BUY may become HOLD)
```

### Step 4. Paper Trade Execution
```
Adjusted signals → Plan trades:
  BUY:  split cash equally among buy signals
  SELL: sell_ratio = 1 - probability
  HOLD: log only
         → Show proposed trades → Confirm
         → Execute paper trade (simulated fill)
         → Record transactions to portfolio DB
         → Take snapshot
```

---

## portfolio.py — Portfolio Management

```
Interactive menu:
  1. List portfolios
  2. Create portfolio (name, capital, tickers)
  3. View report (P&L, holdings, concentration)
  4. Add/remove tickers (watchlist)
  5. Manual buy/sell (record transactions)
  6. Set target allocations
  7. Refresh prices (yfinance)
  8. Delete portfolio

Market is implicit from tickers — no flag needed.
KRX tickers: 005930, 000660, 035420, ...
US tickers: AAPL, MSFT, GOOGL, ...
```

---

## Shared Infrastructure

| Component | Purpose |
|-----------|---------|
| `config.py` | Shared params + MARKETS dict (US/KRX specific settings) |
| `src/market.py` | `detect_market()`, `detect_portfolio_market()`, `get_config()` |
| `src/logger.py` | Console (INFO) + file (DEBUG) logging → `data/pipeline.log` |
| `src/notify.py` | Notifications: Slack, Discord, Telegram, Email |
| `src/data/cache.py` | TTL management: `python -m src.data.cache list|clear` |
| `src/data/features.py` | Technical indicators + dynamic feature preparation |
| `src/data/collector.py` | US: yfinance + Wikipedia |
| `src/data/krx_collector.py` | KRX: pykrx (KOSPI + KOSDAQ) |
| `src/data/fred.py` | US macro (FRED) |
| `src/data/krx_macro.py` | Korean macro (FRED + VKOSPI) |
| `src/data/sentiment.py` | FinBERT sentiment (US only) |
| `src/portfolio/db.py` | SQLAlchemy ORM (SQLite/PostgreSQL) |
| `src/portfolio/manager.py` | 24 portfolio functions (P&L, risk, allocation, reporting) |

## Notifications

Sent on:
- **Strong performers added to watchlist** — per market
- **Poor performers removed** — per market
- **Trades executed** — BUY with amount, SELL with P&L

## Cache Files
| File | Source | Market | Expires |
|------|--------|--------|---------|
| `data/tickers.csv` | Wikipedia | US | 10 days |
| `data/ohlcv.csv` | yfinance | US | never (incremental) |
| `data/fred.csv` | FRED | US | never (incremental) |
| `data/krx_tickers.csv` | pykrx | KRX | 10 days |
| `data/krx_ohlcv.csv` | pykrx | KRX | never (incremental) |
| `data/krx_macro.csv` | FRED + pykrx | KRX | never (incremental) |
| `data/portfolio.db` | Local | shared | never |
| `data/models/*.pt` | train.py | both | never (retrain manually) |
