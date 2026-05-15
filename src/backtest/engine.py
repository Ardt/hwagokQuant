"""Backtesting: walk-forward backtest with signal generation."""

import numpy as np
import pandas as pd
import config as cfg

ANNUALIZE = np.sqrt(252)  # annualization factor for daily returns


def generate_signals(probabilities: np.ndarray, threshold: float = None) -> np.ndarray:
    """Convert model probabilities to signals: 1=buy, 0=hold, -1=sell."""
    threshold = threshold or cfg.SIGNAL_THRESHOLD
    signals = np.zeros(len(probabilities))
    signals[probabilities > threshold] = 1
    signals[probabilities < (1 - threshold)] = -1
    return signals


def backtest(prices: pd.Series, signals: np.ndarray, initial_capital: float = None) -> dict:
    """Run backtest on a single ticker. Returns performance metrics and equity curve."""
    initial_capital = initial_capital or cfg.INITIAL_CAPITAL
    prices = prices.values[-len(signals):]

    cash = initial_capital
    position = 0
    equity = []
    trades = []

    for i in range(len(signals)):
        price = prices[i]

        # Check stop loss / take profit on open position
        if position != 0 and i > 0:
            entry_price = trades[-1]["entry_price"]
            ret = (price - entry_price) / entry_price * (1 if position > 0 else -1)
            if ret <= cfg.STOP_LOSS or ret >= cfg.TAKE_PROFIT:
                cash += position * price
                trades[-1].update({"exit_price": price, "exit_idx": i, "return": ret})
                position = 0

        # New signal
        if signals[i] == 1 and position == 0:
            shares = int(cash // price)
            if shares > 0:
                position = shares
                cash -= shares * price
                trades.append({"entry_price": price, "entry_idx": i, "shares": shares})
        elif signals[i] == -1 and position > 0:
            cash += position * prices[i]
            ret = (price - trades[-1]["entry_price"]) / trades[-1]["entry_price"]
            trades[-1].update({"exit_price": price, "exit_idx": i, "return": ret})
            position = 0

        equity.append(cash + position * price)

    # Close any open position
    if position > 0:
        cash += position * prices[-1]
        ret = (prices[-1] - trades[-1]["entry_price"]) / trades[-1]["entry_price"]
        trades[-1].update({"exit_price": prices[-1], "exit_idx": len(signals) - 1, "return": ret})

    equity = np.array(equity)
    total_return = (equity[-1] - initial_capital) / initial_capital
    completed = [t for t in trades if "return" in t]
    returns = [t["return"] for t in completed]

    metrics = {
        "total_return": total_return,
        "num_trades": len(completed),
        "win_rate": np.mean([r > 0 for r in returns]) if returns else 0,
        "avg_return": np.mean(returns) if returns else 0,
        "max_drawdown": _max_drawdown(equity),
        "sharpe_ratio": _sharpe(equity),
        "final_equity": equity[-1],
    }
    return {"metrics": metrics, "equity": equity, "trades": completed}


def _max_drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return dd.min()


def _sharpe(equity: np.ndarray, risk_free: float = 0.02) -> float:
    returns = np.diff(equity) / equity[:-1]
    if returns.std() == 0:
        return 0.0
    daily_rf = risk_free / 252
    return (returns.mean() - daily_rf) / returns.std() * ANNUALIZE


def information_ratio(equity: np.ndarray, benchmark_prices: np.ndarray) -> float:
    """Information ratio: excess return over benchmark / tracking error."""
    if len(equity) < 2 or len(benchmark_prices) < 2:
        return 0.0
    n = min(len(equity), len(benchmark_prices))
    port_returns = np.diff(equity[:n]) / equity[:n - 1]
    bench_returns = np.diff(benchmark_prices[:n]) / benchmark_prices[:n - 1]
    excess = port_returns - bench_returns
    if excess.std() == 0:
        return 0.0
    return excess.mean() / excess.std() * ANNUALIZE


def print_report(result: dict, ticker: str = ""):
    """Print backtest results."""
    m = result["metrics"]
    print(f"\n{'='*40}")
    print(f"Backtest Report {ticker}")
    print(f"{'='*40}")
    print(f"Total Return:  {m['total_return']:.2%}")
    print(f"Final Equity:  ${m['final_equity']:,.2f}")
    print(f"Num Trades:    {m['num_trades']}")
    print(f"Win Rate:      {m['win_rate']:.2%}")
    print(f"Avg Return:    {m['avg_return']:.2%}")
    print(f"Max Drawdown:  {m['max_drawdown']:.2%}")
    print(f"Sharpe Ratio:  {m['sharpe_ratio']:.2f}")
    print(f"{'='*40}\n")
