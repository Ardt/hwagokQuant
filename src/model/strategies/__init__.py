"""Pluggable allocation strategies. Drop a .py file here to register."""

import importlib
import pkgutil
import pathlib

STRATEGIES = {}


def strategy(func):
    """Decorator: registers function as an allocation strategy."""
    STRATEGIES[func.__name__] = func
    return func


def get_available_cash(ticker: str, cash_by_cur: dict, exchange_rate: float, min_price: float = 0) -> tuple[float, list[dict]]:
    """Get available cash for a ticker, auto-exchanging if needed.
    Auto-exchanges when available cash < min_price (price of 1 share).
    Returns (available_cash, exchange_trades)."""
    cur = "KRW" if ticker.isdigit() else "USD"
    other = "USD" if cur == "KRW" else "KRW"
    available = cash_by_cur.get(cur, 0)
    exchange_trades = []

    if available < min_price and cash_by_cur.get(other, 0) > 0:
        # Auto-exchange from other currency
        other_cash = cash_by_cur[other]
        if cur == "KRW":
            # USD → KRW
            exchanged = other_cash * exchange_rate
            exchange_trades.append({"ticker": f"CASH_USD", "action": "EXCHANGE",
                                    "shares": exchange_rate, "price": other_cash,
                                    "total": exchanged,
                                    "reason": f"auto-exchange USD→KRW @{exchange_rate:.0f}"})
        else:
            # KRW → USD
            exchanged = other_cash / exchange_rate
            exchange_trades.append({"ticker": f"CASH_KRW", "action": "EXCHANGE",
                                    "shares": exchange_rate, "price": other_cash,
                                    "total": exchanged,
                                    "reason": f"auto-exchange KRW→USD @{exchange_rate:.0f}"})
        cash_by_cur[other] = 0
        cash_by_cur[cur] = cash_by_cur.get(cur, 0) + exchanged
        available = cash_by_cur[cur]

    return available, exchange_trades


# Auto-import all modules in this package
_pkg_dir = pathlib.Path(__file__).parent
for _mod in pkgutil.iter_modules([str(_pkg_dir)]):
    importlib.import_module(f".{_mod.name}", __package__)


def get_allocator(name: str = "equal_weight"):
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: '{name}'. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]
