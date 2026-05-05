"""Rebalance Strategy

Two-stage allocation that actively manages positions:

Stage 0: Process SELL signals (same as equal_weight)
Stage 1: Trim weakest HOLDs to free cash when new BUYs exist but cash is low
Stage 2: Allocate freed cash to BUY signals (equal weight)

Behavior:
- When cash >= min_cash_pct: same as equal_weight (just buy)
- When cash < min_cash_pct AND new BUYs exist:
    → Sort HOLD positions by confidence (weakest first)
    → Trim overweight positions toward equal weight target
    → Use freed cash to buy new tickers

Example (₩5M portfolio, 3 tickers, cash=₩200K):
  Target per ticker: ₩5M / 3 = ₩1.67M
  Ticker A (HOLD 0.55): worth ₩2.4M → overweight → trim ₩730K
  Ticker B (HOLD 0.60): worth ₩2.3M → overweight → trim ₩630K
  Ticker C (BUY 0.65): buy with freed cash

Advantages over equal_weight:
- Doesn't get stuck when cash runs out
- Automatically rotates into stronger signals
- Maintains balanced position sizes

Params used:
- min_cash_pct: threshold below which trimming is triggered (default: 0.10)
"""

import math
from . import strategy


@strategy
def rebalance(signals, holdings, cash, portfolio_value, params):
    """Trim weakest HOLDs when cash is low, rebalance toward equal weight."""
    min_cash_pct = float(params.get("min_cash_pct", 0.10))
    holdings_map = {h["ticker"]: h for h in holdings}
    trades = []

    buy_signals = [s for s in signals if s["signal"] == 1]
    hold_signals = [s for s in signals if s["signal"] == 0 and s["ticker"] in holdings_map]
    sell_signals = [s for s in signals if s["signal"] == -1]

    # Stage 0: process SELL signals first
    for s in sell_signals:
        if s["ticker"] in holdings_map:
            held = holdings_map[s["ticker"]]["shares"]
            sell_ratio = 1 - s["probability"]
            shares = int(held * sell_ratio)
            if shares > 0:
                trades.append({"ticker": s["ticker"], "action": "SELL",
                               "shares": shares, "price": s["price"],
                               "total": shares * s["price"],
                               "reason": f"sell signal {sell_ratio:.0%}"})
                cash += shares * s["price"]

    if not buy_signals:
        return trades

    # Stage 1: trim weakest HOLDs if cash < min_cash_pct
    cash_pct = cash / portfolio_value if portfolio_value else 1.0
    if cash_pct < min_cash_pct and hold_signals:
        # Weakest confidence first → trim these before stronger holds
        hold_signals_sorted = sorted(hold_signals, key=lambda s: s["probability"])

        # Equal weight target across all active tickers
        num_active = len(hold_signals) + len(buy_signals)
        target_per_ticker = portfolio_value / num_active

        for s in hold_signals_sorted:
            if cash_pct >= min_cash_pct:
                break
            h = holdings_map.get(s["ticker"])
            if not h:
                continue
            current_value = h["shares"] * s["price"]
            excess = current_value - target_per_ticker
            if excess <= 0:
                continue
            shares_to_sell = math.ceil(excess / s["price"])
            shares_to_sell = min(shares_to_sell, h["shares"] - 1)  # keep at least 1 share
            if shares_to_sell > 0:
                trades.append({"ticker": s["ticker"], "action": "SELL",
                               "shares": shares_to_sell, "price": s["price"],
                               "total": shares_to_sell * s["price"],
                               "reason": f"trim for rebalance (conf {s['probability']:.1%})"})
                cash += shares_to_sell * s["price"]
                cash_pct = cash / portfolio_value

    # Stage 2: allocate cash to BUY signals (equal weight)
    if buy_signals:
        cash_per = cash / len(buy_signals)
        for s in buy_signals:
            shares = int(cash_per // s["price"])
            if shares > 0:
                trades.append({"ticker": s["ticker"], "action": "BUY",
                               "shares": shares, "price": s["price"],
                               "total": shares * s["price"],
                               "reason": f"confidence {s['probability']:.1%}"})

    return trades
