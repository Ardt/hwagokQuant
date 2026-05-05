"""Equal Weight Strategy

Simplest allocation: split available cash equally among all BUY signals.
SELL signals sell proportional to confidence (higher sell confidence = sell more).

Behavior:
- BUY: cash / num_buys = amount per ticker → buy as many whole shares as possible
- SELL: sell (1 - probability) ratio of held shares
- HOLD: do nothing

Example (cash=₩5M, 2 BUY signals):
  Each gets ₩2.5M → buy floor(2.5M / price) shares

Limitations:
- Does NOT rebalance existing positions
- Does NOT free cash from HOLDs for new BUYs
- Can get stuck when cash runs out (all HOLD, no new buys possible)
"""

from . import strategy


@strategy
def equal_weight(signals, holdings, cash, portfolio_value, params):
    """Split cash equally among BUY signals. Sell proportional to confidence."""
    holdings_map = {h["ticker"]: h for h in holdings}
    trades = []

    # BUY: equal cash allocation
    buy_signals = [s for s in signals if s["signal"] == 1]
    if buy_signals:
        cash_per = cash / len(buy_signals)
        for s in buy_signals:
            shares = int(cash_per // s["price"])
            if shares > 0:
                trades.append({"ticker": s["ticker"], "action": "BUY",
                               "shares": shares, "price": s["price"],
                               "total": shares * s["price"],
                               "reason": f"confidence {s['probability']:.1%}"})

    # SELL: proportional to sell confidence
    for s in signals:
        if s["signal"] == -1 and s["ticker"] in holdings_map:
            held = holdings_map[s["ticker"]]["shares"]
            sell_ratio = 1 - s["probability"]  # e.g. prob=0.3 → sell 70%
            shares = int(held * sell_ratio)
            if shares > 0:
                trades.append({"ticker": s["ticker"], "action": "SELL",
                               "shares": shares, "price": s["price"],
                               "total": shares * s["price"],
                               "reason": f"sell {sell_ratio:.0%}"})

    return trades
