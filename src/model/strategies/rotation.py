"""Rotation Strategy (Bench/Playing)

Holdings = Playing members (active positions)
Watchlist = Bench members (discovered, waiting)

Rules:
- Holdings + NOT watchlist + SELL → sell all (immediate exit)
- Holdings + in watchlist + SELL → partial sell (gradual demotion)
- Holdings + in watchlist + HOLD → keep (model says ok)
- Holdings + in watchlist + BUY → remove from watchlist (recovered)
- Watchlist + NOT holdings + BUY → buy (promote from bench)
- All HOLD → compare by rotation_metric, swap if bench > playing * (1 + threshold)

Params:
- rotation_metric: "confidence" | "return_5d" | "return_20d" | "sharpe"
- rotation_threshold: minimum gap to trigger rotation (default 0.10 = 10%)
"""

import math
from . import strategy


@strategy
def rotation(signals, holdings, cash, portfolio_value, params):
    """Bench/playing rotation with gradual demotion."""
    watchlist = params.get("_watchlist", [])
    holdings_tickers = params.get("_holdings", [])
    holdings_map = {h["ticker"]: h for h in holdings}
    rotation_metric = params.get("rotation_metric", "confidence")
    rotation_threshold = float(params.get("rotation_threshold", 0.10))
    trades = []

    watchlist_set = set(watchlist)
    holdings_set = set(holdings_tickers)

    buy_signals = [s for s in signals if s["signal"] == 1]
    sell_signals = [s for s in signals if s["signal"] == -1]
    hold_signals = [s for s in signals if s["signal"] == 0]

    # --- SELL logic ---
    for s in sell_signals:
        ticker = s["ticker"]
        if ticker not in holdings_map:
            continue
        held = holdings_map[ticker]["shares"]

        if ticker in watchlist_set:
            # In watchlist + SELL → partial sell (gradual demotion)
            sell_ratio = 1 - s["probability"]
            shares = max(1, int(held * sell_ratio))
        else:
            # NOT in watchlist + SELL → sell all (immediate exit)
            shares = held

        if shares > 0:
            trades.append({"ticker": ticker, "action": "SELL",
                           "shares": shares, "price": s["price"],
                           "total": shares * s["price"],
                           "reason": f"{'demote' if ticker in watchlist_set else 'exit'} ({s['probability']:.0%})"})
            cash += shares * s["price"]

    # --- BUY logic (promote from bench) ---
    promote_signals = [s for s in buy_signals if s["ticker"] in watchlist_set and s["ticker"] not in holdings_map]
    if promote_signals and cash > 0:
        cash_per = cash / len(promote_signals)
        for s in promote_signals:
            shares = int(cash_per // s["price"])
            if shares > 0:
                trades.append({"ticker": s["ticker"], "action": "BUY",
                               "shares": shares, "price": s["price"],
                               "total": shares * s["price"],
                               "reason": f"promote ({s['probability']:.0%})"})
                cash -= shares * s["price"]

    # --- BUY for existing holdings with BUY signal (add to position) ---
    add_signals = [s for s in buy_signals if s["ticker"] in holdings_map]
    if add_signals and cash > 0:
        cash_per = cash / len(add_signals)
        for s in add_signals:
            shares = int(cash_per // s["price"])
            if shares > 0:
                trades.append({"ticker": s["ticker"], "action": "BUY",
                               "shares": shares, "price": s["price"],
                               "total": shares * s["price"],
                               "reason": f"add position ({s['probability']:.0%})"})
                cash -= shares * s["price"]

    # --- ROTATION logic (all HOLD, compare bench vs playing) ---
    if not buy_signals and not sell_signals:
        bench_holds = [s for s in hold_signals if s["ticker"] in watchlist_set and s["ticker"] not in holdings_map]
        playing_holds = [s for s in hold_signals if s["ticker"] in holdings_map]

        if bench_holds and playing_holds:
            best_bench = max(bench_holds, key=lambda s: _metric_score(s, rotation_metric))
            worst_playing = min(playing_holds, key=lambda s: _metric_score(s, rotation_metric))

            bench_score = _metric_score(best_bench, rotation_metric)
            playing_score = _metric_score(worst_playing, rotation_metric)

            # Rotate only if bench exceeds playing by threshold
            if bench_score > playing_score * (1 + rotation_threshold):
                # Sell worst playing (all shares)
                held = holdings_map[worst_playing["ticker"]]["shares"]
                sell_total = held * worst_playing["price"]
                trades.append({"ticker": worst_playing["ticker"], "action": "SELL",
                               "shares": held, "price": worst_playing["price"],
                               "total": sell_total,
                               "reason": f"rotate out (score {playing_score:.2f})"})

                # Buy best bench with proceeds
                buy_cash = sell_total
                shares = int(buy_cash // best_bench["price"])
                if shares > 0:
                    trades.append({"ticker": best_bench["ticker"], "action": "BUY",
                                   "shares": shares, "price": best_bench["price"],
                                   "total": shares * best_bench["price"],
                                   "reason": f"rotate in (score {bench_score:.2f})"})

    return trades


def _metric_score(signal: dict, metric: str) -> float:
    """Score a signal by the chosen rotation metric."""
    if metric == "confidence":
        return signal["probability"]
    # For return-based metrics, use probability as fallback
    # (actual return data would need to be passed in signals)
    return signal["probability"]
