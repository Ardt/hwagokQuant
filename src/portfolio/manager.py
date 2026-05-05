"""Portfolio manager: full-featured portfolio management API."""

import os
import csv
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from src.portfolio import db
from src.logger import get
import config as cfg

log = get("portfolio")


# ============================================================
# Init
# ============================================================

def init():
    db.init_db()


# ============================================================
# Core
# ============================================================

def create(name: str, description: str = "", capital: float = None) -> dict:
    pid = db.create_portfolio(name, description, capital)
    log.info(f"Created portfolio '{name}' (id={pid})")
    return db.get_portfolio(pid)


def buy(portfolio_id: int, ticker: str, shares: float, price: float):
    db.add_transaction(portfolio_id, ticker, "BUY", shares, price)
    holdings = {h["ticker"]: h for h in db.get_holdings(portfolio_id)}
    if ticker in holdings:
        old = holdings[ticker]
        total_shares = old["shares"] + shares
        avg_cost = (old["shares"] * old["avg_cost"] + shares * price) / total_shares
    else:
        total_shares, avg_cost = shares, price
    db.upsert_holding(portfolio_id, ticker, total_shares, avg_cost, price)
    log.debug(f"BUY {shares} {ticker} @ ${price:.2f} → holding {total_shares} shares")


def sell(portfolio_id: int, ticker: str, shares: float, price: float):
    db.add_transaction(portfolio_id, ticker, "SELL", shares, price)
    holdings = {h["ticker"]: h for h in db.get_holdings(portfolio_id)}
    if ticker not in holdings:
        return
    remaining = holdings[ticker]["shares"] - shares
    if remaining <= 0:
        db.remove_holding(portfolio_id, ticker)
        log.debug(f"SELL {shares} {ticker} @ ${price:.2f} → position closed")
    else:
        db.upsert_holding(portfolio_id, ticker, remaining, holdings[ticker]["avg_cost"], price)
        log.debug(f"SELL {shares} {ticker} @ ${price:.2f} → holding {remaining} shares")


def record_signal(portfolio_id: int, ticker: str, signal: int, probability: float = None, source: str = "lstm_v1"):
    return db.add_signal(portfolio_id, ticker, signal, probability, source)


def record_backtest(portfolio_id: int, ticker: str, metrics: dict):
    return db.add_backtest_result(portfolio_id, ticker, metrics)


# ============================================================
# Position Management
# ============================================================

def add_to_watchlist(portfolio_id: int, ticker: str):
    from src.market import detect_market
    market = detect_market(ticker)
    current = db.get_watchlist(portfolio_id)
    same_market = [w for w in current if detect_market(w["ticker"]) == market]
    if len(same_market) >= cfg.WATCHLIST_MAX_PER_MARKET:
        log.warning(f"Watchlist limit ({cfg.WATCHLIST_MAX_PER_MARKET}) reached for {market}")
        return
    db.add_to_watchlist(portfolio_id, ticker)


def remove_from_watchlist(portfolio_id: int, ticker: str):
    db.remove_from_watchlist(portfolio_id, ticker)


def get_watchlist(portfolio_id: int) -> list[dict]:
    return db.get_watchlist(portfolio_id)


def refresh_prices(portfolio_id: int) -> list[dict]:
    """Bulk update current prices for all holdings via yfinance."""
    holdings = db.get_holdings(portfolio_id)
    if not holdings:
        return []
    tickers = [h["ticker"] for h in holdings]
    data = yf.download(tickers, period="1d", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"].iloc[-1]
    else:
        prices = data["Close"].iloc[-1:].values[0] if len(tickers) == 1 else data["Close"].iloc[-1]
    updated = []
    for h in holdings:
        t = h["ticker"]
        price = float(prices[t]) if len(tickers) > 1 else float(prices)
        db.upsert_holding(portfolio_id, t, h["shares"], h["avg_cost"], price)
        updated.append({"ticker": t, "price": price})
    return updated


def position_size(portfolio_id: int, ticker: str, weight: float, price: float = None) -> int:
    """Calculate shares to buy for a target portfolio weight %."""
    s = summary(portfolio_id)
    if price is None:
        price = float(yf.download(ticker, period="1d", progress=False)["Close"].iloc[-1])
    target_value = s["total_value"] * weight
    return int(target_value // price)


# ============================================================
# P&L & Performance
# ============================================================

def gross_pnl(portfolio_id: int) -> list[dict]:
    """Unrealized P&L per holding."""
    holdings = db.get_holdings(portfolio_id)
    result = []
    for h in holdings:
        price = h["current_price"] or h["avg_cost"]
        cost_basis = h["shares"] * h["avg_cost"]
        market_val = h["shares"] * price
        pnl = market_val - cost_basis
        pct = pnl / cost_basis if cost_basis else 0
        result.append({"ticker": h["ticker"], "shares": h["shares"], "avg_cost": h["avg_cost"],
                        "current_price": price, "cost_basis": cost_basis,
                        "market_value": market_val, "unrealized_pnl": pnl, "pnl_pct": pct})
    return result


def realized_pnl(portfolio_id: int) -> list[dict]:
    """Realized P&L from closed (SELL) transactions."""
    txns = db.get_transactions(portfolio_id)
    buys = {}
    realized = []
    for t in txns:
        ticker = t["ticker"]
        if t["action"] == "BUY":
            buys.setdefault(ticker, []).append({"shares": t["shares"], "price": t["price"]})
        else:
            sell_shares = t["shares"]
            sell_price = t["price"]
            cost = 0
            remaining = sell_shares
            while remaining > 0 and buys.get(ticker):
                lot = buys[ticker][0]
                used = min(remaining, lot["shares"])
                cost += used * lot["price"]
                lot["shares"] -= used
                remaining -= used
                if lot["shares"] <= 0:
                    buys[ticker].pop(0)
            pnl = sell_shares * sell_price - cost
            realized.append({"ticker": ticker, "shares": sell_shares, "sell_price": sell_price,
                              "cost_basis": cost, "realized_pnl": pnl, "timestamp": t["timestamp"]})
    return realized


def _calc_cash(portfolio_id: int) -> float:
    p = db.get_portfolio(portfolio_id)
    cash = 0.0
    for t in db.get_transactions(portfolio_id):
        if t["action"] == "DEPOSIT":
            cash += t["total"]
        elif t["action"] == "WITHDRAW":
            cash -= t["total"]
        elif t["action"] == "SELL":
            cash += t["total"]
        elif t["action"] == "BUY":
            cash -= t["total"]
    return cash


def summary(portfolio_id: int) -> dict:
    portfolio = db.get_portfolio(portfolio_id)
    if not portfolio:
        return {}
    holdings = db.get_holdings(portfolio_id)
    cash = _calc_cash(portfolio_id)
    market_value = sum(h["shares"] * (h["current_price"] or h["avg_cost"]) for h in holdings)
    total_value = cash + market_value
    total_return = (total_value - portfolio["initial_capital"]) / portfolio["initial_capital"]
    return {"portfolio": portfolio, "holdings": holdings, "cash": cash,
            "market_value": market_value, "total_value": total_value, "total_return": total_return}


def take_snapshot(portfolio_id: int):
    """Save current portfolio state for equity curve tracking."""
    s = summary(portfolio_id)
    if s:
        db.add_snapshot(portfolio_id, s["total_value"], s["cash"], s["market_value"])


def equity_curve(portfolio_id: int) -> pd.DataFrame:
    """Return equity curve from snapshots as DataFrame."""
    snaps = db.get_snapshots(portfolio_id)
    if not snaps:
        return pd.DataFrame()
    df = pd.DataFrame(snaps)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp")[["total_value", "cash", "market_value"]]


def benchmark_compare(portfolio_id: int, benchmark: str = "^GSPC") -> dict:
    """Compare portfolio return vs benchmark (default S&P500)."""
    snaps = db.get_snapshots(portfolio_id)
    if len(snaps) < 2:
        return {"error": "Need at least 2 snapshots"}
    start = snaps[0]["timestamp"][:10]
    end = snaps[-1]["timestamp"][:10]
    bench = yf.download(benchmark, start=start, end=end, progress=False)
    if bench.empty:
        return {"error": "Could not fetch benchmark data"}
    if isinstance(bench.columns, pd.MultiIndex):
        bench.columns = bench.columns.get_level_values(0)
    bench_return = (bench["Close"].iloc[-1] - bench["Close"].iloc[0]) / bench["Close"].iloc[0]
    port_return = (snaps[-1]["total_value"] - snaps[0]["total_value"]) / snaps[0]["total_value"]
    return {"portfolio_return": float(port_return), "benchmark_return": float(bench_return),
            "alpha": float(port_return - bench_return), "benchmark": benchmark}


# ============================================================
# Risk
# ============================================================

def portfolio_sharpe(portfolio_id: int, risk_free: float = 0.02) -> float:
    snaps = db.get_snapshots(portfolio_id)
    if len(snaps) < 3:
        return 0.0
    values = np.array([s["total_value"] for s in snaps])
    returns = np.diff(values) / values[:-1]
    if returns.std() == 0:
        return 0.0
    daily_rf = risk_free / 252
    return float((returns.mean() - daily_rf) / returns.std() * np.sqrt(252))


def max_drawdown(portfolio_id: int) -> float:
    snaps = db.get_snapshots(portfolio_id)
    if len(snaps) < 2:
        return 0.0
    values = np.array([s["total_value"] for s in snaps])
    peak = np.maximum.accumulate(values)
    dd = (values - peak) / peak
    return float(dd.min())


def concentration(portfolio_id: int) -> list[dict]:
    """Weight of each holding as % of total portfolio."""
    s = summary(portfolio_id)
    if not s or s["total_value"] == 0:
        return []
    return [{"ticker": h["ticker"],
             "value": h["shares"] * (h["current_price"] or h["avg_cost"]),
             "weight": h["shares"] * (h["current_price"] or h["avg_cost"]) / s["total_value"]}
            for h in s["holdings"]]


def correlation_matrix(portfolio_id: int, period: str = "1y") -> pd.DataFrame:
    """Correlation matrix between holdings using historical returns."""
    holdings = db.get_holdings(portfolio_id)
    if len(holdings) < 2:
        return pd.DataFrame()
    tickers = [h["ticker"] for h in holdings]
    data = yf.download(tickers, period=period, progress=False)["Close"]
    if isinstance(data, pd.Series):
        return pd.DataFrame()
    return data.pct_change().dropna().corr()


def value_at_risk(portfolio_id: int, confidence: float = 0.95, period: str = "1y") -> dict:
    """Historical VaR for the portfolio."""
    holdings = db.get_holdings(portfolio_id)
    if not holdings:
        return {}
    tickers = [h["ticker"] for h in holdings]
    weights = []
    s = summary(portfolio_id)
    for h in holdings:
        val = h["shares"] * (h["current_price"] or h["avg_cost"])
        weights.append(val / s["market_value"] if s["market_value"] else 0)
    data = yf.download(tickers, period=period, progress=False)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(tickers[0])
    returns = data.pct_change().dropna()
    port_returns = (returns * weights).sum(axis=1)
    var = float(np.percentile(port_returns, (1 - confidence) * 100))
    return {"var": var, "confidence": confidence, "var_dollar": var * s["total_value"],
            "period": period, "observations": len(port_returns)}


# ============================================================
# Allocation
# ============================================================

def set_target_allocation(portfolio_id: int, allocations: dict[str, float]):
    """Set target weights. allocations = {'AAPL': 0.3, 'TSLA': 0.2, ...}"""
    for ticker, weight in allocations.items():
        db.upsert_allocation(portfolio_id, ticker, weight)


def get_target_allocation(portfolio_id: int) -> list[dict]:
    return db.get_allocations(portfolio_id)


def drift(portfolio_id: int) -> list[dict]:
    """Compare current weights vs target allocation."""
    targets = {a["ticker"]: a["target_weight"] for a in db.get_allocations(portfolio_id)}
    if not targets:
        return []
    conc = {c["ticker"]: c["weight"] for c in concentration(portfolio_id)}
    result = []
    for ticker, target in targets.items():
        current = conc.get(ticker, 0.0)
        result.append({"ticker": ticker, "target": target, "current": current,
                        "drift": current - target, "drift_pct": (current - target) / target if target else 0})
    return result


def rebalance_suggestions(portfolio_id: int) -> list[dict]:
    """Suggest trades to reach target allocation."""
    s = summary(portfolio_id)
    if not s:
        return []
    targets = {a["ticker"]: a["target_weight"] for a in db.get_allocations(portfolio_id)}
    holdings_map = {h["ticker"]: h for h in s["holdings"]}
    suggestions = []
    for ticker, target_weight in targets.items():
        target_value = s["total_value"] * target_weight
        h = holdings_map.get(ticker)
        price = h["current_price"] or h["avg_cost"] if h else None
        if price is None:
            try:
                price = float(yf.download(ticker, period="1d", progress=False)["Close"].iloc[-1])
            except Exception:
                continue
        current_value = h["shares"] * price if h else 0
        diff_value = target_value - current_value
        diff_shares = int(diff_value / price) if price else 0
        if diff_shares != 0:
            suggestions.append({"ticker": ticker, "action": "BUY" if diff_shares > 0 else "SELL",
                                 "shares": abs(diff_shares), "price": price, "value": abs(diff_value)})
    return suggestions


# ============================================================
# Reporting
# ============================================================

def print_report(portfolio_id: int):
    """Print formatted portfolio report to console."""
    s = summary(portfolio_id)
    if not s:
        print("Portfolio not found.")
        return
    p = s["portfolio"]
    print(f"\n{'='*60}")
    print(f"  Portfolio: {p['name']}")
    print(f"  {p['description']}")
    print(f"{'='*60}")
    print(f"  Initial Capital:  ${p['initial_capital']:>14,.2f}")
    print(f"  Cash:             ${s['cash']:>14,.2f}")
    print(f"  Market Value:     ${s['market_value']:>14,.2f}")
    print(f"  Total Value:      ${s['total_value']:>14,.2f}")
    print(f"  Total Return:     {s['total_return']:>14.2%}")

    pnl = gross_pnl(portfolio_id)
    if pnl:
        print(f"\n  {'Ticker':<8} {'Shares':>8} {'AvgCost':>10} {'Price':>10} {'P&L':>12} {'%':>8}")
        print(f"  {'-'*56}")
        for row in pnl:
            print(f"  {row['ticker']:<8} {row['shares']:>8.1f} ${row['avg_cost']:>9.2f} "
                  f"${row['current_price']:>9.2f} ${row['unrealized_pnl']:>11.2f} {row['pnl_pct']:>7.2%}")
        total_pnl = sum(r["unrealized_pnl"] for r in pnl)
        print(f"  {'-'*56}")
        print(f"  {'Total Unrealized P&L':>38} ${total_pnl:>11.2f}")

    rpnl = realized_pnl(portfolio_id)
    if rpnl:
        total_realized = sum(r["realized_pnl"] for r in rpnl)
        print(f"  {'Total Realized P&L':>38} ${total_realized:>11.2f}")

    conc = concentration(portfolio_id)
    if conc:
        print(f"\n  Concentration:")
        for c in sorted(conc, key=lambda x: x["weight"], reverse=True):
            bar = "#" * int(c["weight"] * 40)
            print(f"  {c['ticker']:<8} {c['weight']:>6.1%}  {bar}")

    print(f"{'='*60}\n")


def export_csv(portfolio_id: int, path: str = None) -> str:
    """Export portfolio to CSV."""
    if path is None:
        p = db.get_portfolio(portfolio_id)
        path = os.path.join(cfg.DATA_DIR, f"portfolio_{p['name']}.csv")
    pnl = gross_pnl(portfolio_id)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=pnl[0].keys() if pnl else [])
        writer.writeheader()
        writer.writerows(pnl)
    return path


def plot_equity(portfolio_id: int, save_path: str = None):
    """Plot equity curve from snapshots."""
    ec = equity_curve(portfolio_id)
    if ec.empty:
        print("No snapshots to plot.")
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(ec.index, ec["total_value"], label="Total Value")
    ax.fill_between(ec.index, ec["cash"], alpha=0.3, label="Cash")
    ax.set_title(f"Equity Curve — Portfolio {portfolio_id}")
    ax.set_ylabel("Value ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    else:
        p = db.get_portfolio(portfolio_id)
        path = os.path.join(cfg.DATA_DIR, f"equity_{p['name']}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# Multi-Portfolio
# ============================================================

def list_all() -> list[dict]:
    """List all portfolios with summary stats."""
    portfolios = db.list_portfolios()
    result = []
    for p in portfolios:
        s = summary(p["id"])
        result.append({"id": p["id"], "name": p["name"], "initial_capital": p["initial_capital"],
                        "total_value": s.get("total_value", 0), "total_return": s.get("total_return", 0),
                        "num_holdings": len(s.get("holdings", []))})
    return result


def compare(portfolio_ids: list[int]) -> pd.DataFrame:
    """Compare performance across portfolios."""
    rows = []
    for pid in portfolio_ids:
        s = summary(pid)
        if not s:
            continue
        rows.append({"id": pid, "name": s["portfolio"]["name"],
                      "initial_capital": s["portfolio"]["initial_capital"],
                      "total_value": s["total_value"], "return": s["total_return"],
                      "cash": s["cash"], "market_value": s["market_value"],
                      "holdings": len(s["holdings"]),
                      "sharpe": portfolio_sharpe(pid), "max_dd": max_drawdown(pid)})
    return pd.DataFrame(rows)


def clone(portfolio_id: int, new_name: str) -> dict:
    new_id = db.clone_portfolio(portfolio_id, new_name)
    return db.get_portfolio(new_id)


def delete(portfolio_id: int):
    db.delete_portfolio(portfolio_id)
