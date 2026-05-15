"""Trade executor facade. Swap implementations without changing trade.py."""

from abc import ABC, abstractmethod


class Executor(ABC):
    """Interface for trade execution."""

    @abstractmethod
    def buy(self, portfolio_id: int, ticker: str, shares: int, price: float): ...

    @abstractmethod
    def sell(self, portfolio_id: int, ticker: str, shares: int, price: float): ...

    @abstractmethod
    def exchange(self, portfolio_id: int, from_cur: str, to_cur: str, amount: float, rate: float): ...


EXECUTORS = {}


def executor(cls):
    """Decorator: registers an executor class."""
    EXECUTORS[cls.name] = cls
    return cls


def get_executor(name: str = "paper") -> Executor:
    if name not in EXECUTORS:
        raise ValueError(f"Unknown executor: '{name}'. Available: {list(EXECUTORS.keys())}")
    return EXECUTORS[name]()
