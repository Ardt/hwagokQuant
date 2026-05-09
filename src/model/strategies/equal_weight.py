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

from . import strategy, get_available_cash


@strategy
def equal_weight(signals, holdings, cash, portfolio_value, params):
    """Split cash equally among BUY signals. Sell proportional to confidence."""
    holdings_map = {h["ticker"]: h for h in holdings}
    cash_by_cur = params.get("_cash_by_currency", {"USD": cash})
    exchange_rate = float(params.get("_exchange_rate", 1370))
    trades = []

    # SELL: proportional to sell confidence
    for s in signals:
        if s["signal"] == -1 and s["ticker"] in holdings_map:
            held = holdings_map[s["ticker"]]["shares"]
            sell_ratio = 1 - s["probability"]  # e.g. prob=0.3 → sell 70%
            shares = int(held * sell_ratio)
            if shares > 0:
                cur = "KRW" if s["ticker"].isdigit() else "USD"
                trades.append({"ticker": s["ticker"], "action": "SELL",
                               "shares": shares, "price": s["price"],
                               "total": shares * s["price"],
                               "reason": f"sell {sell_ratio:.0%}"})
                cash_by_cur[cur] = cash_by_cur.get(cur, 0) + shares * s["price"]

    # BUY: equal cash allocation per currency
    buy_signals = [s for s in signals if s["signal"] == 1]
    if buy_signals:
        # Group by currency
        buys_by_cur = {}
        for s in buy_signals:
            cur = "KRW" if s["ticker"].isdigit() else "USD"
            buys_by_cur.setdefault(cur, []).append(s)

        for cur, cur_buys in buys_by_cur.items():
            available, ex_trades = get_available_cash(cur_buys[0]["ticker"], cash_by_cur, exchange_rate, cur_buys[0]["price"])
            trades.extend(ex_trades)
            if available <= 0:
                continue
            cash_per = available / len(cur_buys)
            for s in cur_buys:
                shares = int(cash_per // s["price"])
                if shares > 0:
                    trades.append({"ticker": s["ticker"], "action": "BUY",
                                   "shares": shares, "price": s["price"],
                                   "total": shares * s["price"],
                                   "reason": f"confidence {s['probability']:.1%}"})

    return trades
