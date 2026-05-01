# Quant Strategies Reference

## Current Implementation: LSTM + Sentiment + Macro

### Architecture
```
Input (60-day window, 26 features)
  → LSTM (2 layers, 64 hidden, dropout 0.2)
  → FC (64 → 1)
  → Sigmoid
  → Binary output: P(price_up_tomorrow)
```

### Why LSTM?
- Stock prices are sequential — order matters
- LSTM captures long-term dependencies (e.g., 60-day trend patterns)
- Handles variable-length patterns (consolidation → breakout)
- Multi-feature input: combines price, volume, indicators, macro in one model

### Feature Groups (26 total)

| Group | Features | Purpose |
|-------|----------|---------|
| Price (5) | Open, High, Low, Close, Volume | Raw market data |
| Trend (6) | SMA(20), SMA(50), EMA(12), MACD, MACD Signal, MACD Hist | Direction and momentum |
| Momentum (2) | RSI, Stochastic RSI | Overbought/oversold |
| Volatility (4) | BB High, BB Low, BB Width, ATR | Range and risk |
| Volume (1) | OBV | Accumulation/distribution |
| Returns (3) | 1-day, 5-day, 20-day volatility | Recent performance |
| Sentiment (1) | FinBERT score (-1 to +1) | News sentiment (US only) |
| Macro (4) | VIX, Rate, CPI, Unemployment | Economic context |

### Training Process
```
1. Walk-forward split (80% train / 20% val, chronological)
2. MinMaxScaler normalization (0-1)
3. 60-day sliding window → sequences
4. Binary target: next-day close > today's close
5. BCELoss + Adam optimizer (lr=0.001)
6. Early stopping (patience=10 epochs)
7. Save best model by validation loss
```

### Signal Generation
```
P(up) > 0.5 → BUY
P(up) < 0.5 → SELL (i.e., P(down) > 0.5)
Ensemble adjustment → may downgrade BUY to HOLD
```

### Ensemble Adjustment (Post-Model)
Adjusts raw signals based on portfolio context:

| Condition | Effect |
|-----------|--------|
| VIX > 30 (high fear) | Reduce buy confidence (×0.6) |
| VIX > 40 (extreme) | Reduce buy confidence (×0.3) |
| Yield curve inverted (US) | Reduce buy confidence (×0.7) |
| Ticker concentration > 25% | Reduce buy confidence (×0.5) |
| Cash < 10% of portfolio | Reduce buy confidence (×0.5) |
| High fear + sell signal | More aggressive selling |

If adjusted probability drops below 0.5 → BUY becomes HOLD.

### Backtesting Rules
- Walk-forward (no lookahead bias)
- Stop-loss: -5% from entry
- Take-profit: +10% from entry
- Position sizing: equal-weight across buy signals
- Metrics: total return, Sharpe ratio, win rate, max drawdown

---

## Why This Strategy?

### Strengths
- **Multi-signal**: combines technical, fundamental (macro), and alternative (sentiment) data
- **Adaptive**: LSTM learns regime-specific patterns (bull/bear/sideways)
- **Risk-aware**: ensemble layer prevents overconcentration and respects macro environment
- **Per-ticker models**: each stock gets its own model, capturing unique behavior

### Weaknesses
- **Overfitting risk**: LSTM can memorize noise, especially with limited data
- **Sentiment gap (KRX)**: no Korean news sentiment yet
- **Binary simplification**: real markets have magnitude, not just direction
- **Latency**: daily signals only, can't capture intraday moves
- **Black box**: hard to explain why a specific signal was generated

### Mitigations
- Early stopping + dropout (0.2) to reduce overfitting
- Walk-forward validation (never random split)
- Incremental training on recent data (adapt to regime changes)
- Ensemble layer adds interpretable rules on top of black-box model
- Backtest metrics provide confidence before live trading

---

## Future Strategy Enhancements

### Near-term
| Enhancement | Impact | Effort |
|-------------|--------|--------|
| Korean sentiment (multilingual FinBERT) | +2-5% accuracy for KRX | Medium |
| Multi-class output (UP/DOWN/FLAT) | Fewer false signals | Low |
| Confidence threshold tuning | Better precision/recall tradeoff | Low |
| Sector rotation signals | Avoid correlated losses | Medium |

### Medium-term
| Enhancement | Impact | Effort |
|-------------|--------|--------|
| Attention mechanism (Transformer) | Better long-range patterns | Medium |
| Cross-ticker features (sector ETF returns) | Market context per ticker | Medium |
| Lead-lag analysis | Predict followers from leaders | Medium |
| Volatility forecasting (GARCH) | Better position sizing | Low |

### Long-term
| Enhancement | Impact | Effort |
|-------------|--------|--------|
| Graph Neural Network | Learn inter-stock relationships | High |
| Reinforcement learning | Optimize portfolio-level decisions | High |
| Multi-ticker LSTM | Single model captures market dynamics | High |
| Options overlay | Hedge tail risk, generate income | High |

---

## Alternative Strategies (Not Implemented)

### Trend Following
- Moving Average Crossover (Golden Cross / Death Cross)
- Momentum — buy winners, sell losers based on past returns
- Breakout — trade on support/resistance breaks

### Mean Reversion
- Pairs Trading — long/short correlated assets on divergence
- Bollinger Bands — buy lower band, sell upper band
- RSI Reversion — buy oversold, sell overbought

### Statistical Arbitrage
- Cointegration-based pairs trading
- Market-neutral long/short portfolios
- Cross-sectional momentum/value factors

### Factor Investing
- Fama-French factors (value, size, momentum, profitability, investment)
- Risk parity
- Quality factor (ROE, low debt, stable earnings)

### High Frequency (advanced)
- Market making
- Order flow imbalance
- Latency arbitrage
