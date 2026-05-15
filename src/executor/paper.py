"""Paper trade executor — records trades to DB only."""

from . import Executor, executor
from src.portfolio import manager as pm
from src.portfolio import db as _db


@executor
class PaperExecutor(Executor):
    name = "paper"

    def buy(self, portfolio_id: int, ticker: str, shares: int, price: float):
        pm.buy(portfolio_id, ticker, shares, price)

    def sell(self, portfolio_id: int, ticker: str, shares: int, price: float):
        pm.sell(portfolio_id, ticker, shares, price)

    def exchange(self, portfolio_id: int, from_cur: str, to_cur: str, amount: float, rate: float):
        received = amount * rate if to_cur == "KRW" else amount / rate
        _db.add_transaction(portfolio_id, f"CASH_{from_cur}", "WITHDRAW", 1, amount)
        _db.add_transaction(portfolio_id, f"CASH_{to_cur}", "DEPOSIT", 1, received)
