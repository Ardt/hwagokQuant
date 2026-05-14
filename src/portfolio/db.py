"""Portfolio database: SQLAlchemy models and CRUD operations."""

from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, Float, Text, CheckConstraint,
    ForeignKey, UniqueConstraint, text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import config as cfg

engine = create_engine(cfg.DB_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Models ---

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text, default="")
    allocator_strategy = Column(Text, default="equal_weight")
    signal_threshold = Column(Float)
    vix_threshold = Column(Float)
    max_position_pct = Column(Float)
    min_cash_pct = Column(Float)
    rotation_metric = Column(Text, default="confidence")
    rotation_threshold = Column(Float, default=0.10)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(Text, nullable=False)
    shares = Column(Float, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0)
    current_price = Column(Float)
    updated_at = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("portfolio_id", "ticker"),)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    shares = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    timestamp = Column(Text, nullable=False)
    __table_args__ = (CheckConstraint("action IN ('BUY','SELL','DEPOSIT','WITHDRAW')"),)


class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(Text, nullable=False)
    signal = Column(Integer, nullable=False)
    probability = Column(Float)
    predicted_high = Column(Float)
    predicted_low = Column(Float)
    source = Column(Text)
    timestamp = Column(Text, nullable=False)
    __table_args__ = (CheckConstraint("signal IN (-1,0,1)"),)


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(Text, nullable=False)
    total_return = Column(Float)
    num_trades = Column(Integer)
    win_rate = Column(Float)
    avg_return = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    final_equity = Column(Float)
    run_date = Column(Text, nullable=False)


class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(Text, nullable=False)
    added_at = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("portfolio_id", "ticker"),)


class Allocation(Base):
    __tablename__ = "allocations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(Text, nullable=False)
    target_weight = Column(Float, nullable=False)
    updated_at = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("portfolio_id", "ticker"),)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    total_value = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False)
    timestamp = Column(Text, nullable=False)


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(Text, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


# --- Init ---

def init_db():
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()


def get_exchange_rate(pair: str = "USD/KRW") -> float:
    """Get latest exchange rate from DB. Falls back to 1370."""
    with get_session() as s:
        row = s.execute(
            text("SELECT rate FROM exchange_rates WHERE pair = :pair ORDER BY date DESC LIMIT 1"),
            {"pair": pair}
        ).fetchone()
        return float(row[0]) if row else 1370.0


# --- Portfolios ---

def create_portfolio(name: str, description: str = "") -> int:
    now = _now()
    with get_session() as s:
        p = Portfolio(name=name, description=description, created_at=now, updated_at=now)
        s.add(p)
        s.commit()
        return p.id


def get_portfolio(portfolio_id: int) -> dict | None:
    with get_session() as s:
        p = s.get(Portfolio, portfolio_id)
        return _to_dict(p) if p else None


def list_portfolios() -> list[dict]:
    with get_session() as s:
        return [_to_dict(p) for p in s.query(Portfolio).order_by(Portfolio.created_at.desc()).all()]


# --- Holdings ---

def upsert_holding(portfolio_id: int, ticker: str, shares: float, avg_cost: float, current_price: float = None):
    now = _now()
    with get_session() as s:
        h = s.query(Holding).filter_by(portfolio_id=portfolio_id, ticker=ticker).first()
        if h:
            h.shares, h.avg_cost, h.current_price, h.updated_at = shares, avg_cost, current_price, now
        else:
            s.add(Holding(portfolio_id=portfolio_id, ticker=ticker, shares=shares,
                          avg_cost=avg_cost, current_price=current_price, updated_at=now))
        s.commit()


def get_holdings(portfolio_id: int) -> list[dict]:
    with get_session() as s:
        return [_to_dict(h) for h in s.query(Holding).filter(
            Holding.portfolio_id == portfolio_id, Holding.shares > 0).all()]


def remove_holding(portfolio_id: int, ticker: str):
    with get_session() as s:
        s.query(Holding).filter_by(portfolio_id=portfolio_id, ticker=ticker).delete()
        s.commit()


# --- Transactions ---

def add_transaction(portfolio_id: int, ticker: str, action: str, shares: float, price: float) -> int:
    with get_session() as s:
        t = Transaction(portfolio_id=portfolio_id, ticker=ticker, action=action,
                        shares=shares, price=price, total=shares * price, timestamp=_now())
        s.add(t)
        s.commit()
        return t.id


def get_transactions(portfolio_id: int, ticker: str = None) -> list[dict]:
    with get_session() as s:
        q = s.query(Transaction).filter_by(portfolio_id=portfolio_id)
        if ticker:
            q = q.filter_by(ticker=ticker)
        return [_to_dict(t) for t in q.order_by(Transaction.timestamp).all()]


# --- Signals ---

def add_signal(portfolio_id: int, ticker: str, signal: int, probability: float = None, source: str = None, predicted_high: float = None, predicted_low: float = None) -> int:
    with get_session() as s:
        sig = Signal(portfolio_id=portfolio_id, ticker=ticker, signal=signal,
                     probability=probability, predicted_high=predicted_high,
                     predicted_low=predicted_low, source=source, timestamp=_now())
        s.add(sig)
        s.commit()
        return sig.id


def get_signals(portfolio_id: int, ticker: str = None) -> list[dict]:
    with get_session() as s:
        q = s.query(Signal).filter_by(portfolio_id=portfolio_id)
        if ticker:
            q = q.filter_by(ticker=ticker)
        return [_to_dict(sig) for sig in q.order_by(Signal.timestamp).all()]


# --- Backtest Results ---

def add_backtest_result(portfolio_id: int, ticker: str, metrics: dict) -> int:
    with get_session() as s:
        r = BacktestResult(
            portfolio_id=portfolio_id, ticker=ticker, run_date=_now(),
            total_return=metrics.get("total_return"), num_trades=metrics.get("num_trades"),
            win_rate=metrics.get("win_rate"), avg_return=metrics.get("avg_return"),
            max_drawdown=metrics.get("max_drawdown"), sharpe_ratio=metrics.get("sharpe_ratio"),
            final_equity=metrics.get("final_equity"),
        )
        s.add(r)
        s.commit()
        return r.id


def get_backtest_results(portfolio_id: int) -> list[dict]:
    with get_session() as s:
        return [_to_dict(r) for r in s.query(BacktestResult).filter_by(
            portfolio_id=portfolio_id).order_by(BacktestResult.run_date.desc()).all()]


# --- Watchlist ---

def add_to_watchlist(portfolio_id: int, ticker: str):
    with get_session() as s:
        exists = s.query(Watchlist).filter_by(portfolio_id=portfolio_id, ticker=ticker).first()
        if not exists:
            s.add(Watchlist(portfolio_id=portfolio_id, ticker=ticker, added_at=_now()))
            s.commit()


def remove_from_watchlist(portfolio_id: int, ticker: str):
    with get_session() as s:
        s.query(Watchlist).filter_by(portfolio_id=portfolio_id, ticker=ticker).delete()
        s.commit()


def get_watchlist(portfolio_id: int) -> list[dict]:
    with get_session() as s:
        return [_to_dict(w) for w in s.query(Watchlist).filter_by(portfolio_id=portfolio_id).all()]


# --- Allocations ---

def upsert_allocation(portfolio_id: int, ticker: str, target_weight: float):
    now = _now()
    with get_session() as s:
        a = s.query(Allocation).filter_by(portfolio_id=portfolio_id, ticker=ticker).first()
        if a:
            a.target_weight, a.updated_at = target_weight, now
        else:
            s.add(Allocation(portfolio_id=portfolio_id, ticker=ticker, target_weight=target_weight, updated_at=now))
        s.commit()


def get_allocations(portfolio_id: int) -> list[dict]:
    with get_session() as s:
        return [_to_dict(a) for a in s.query(Allocation).filter_by(portfolio_id=portfolio_id).all()]


def remove_allocation(portfolio_id: int, ticker: str):
    with get_session() as s:
        s.query(Allocation).filter_by(portfolio_id=portfolio_id, ticker=ticker).delete()
        s.commit()


# --- Snapshots ---

def add_snapshot(portfolio_id: int, total_value: float, cash: float, market_value: float):
    with get_session() as s:
        s.add(PortfolioSnapshot(portfolio_id=portfolio_id, total_value=total_value,
                                cash=cash, market_value=market_value, timestamp=_now()))
        s.commit()


def get_snapshots(portfolio_id: int) -> list[dict]:
    with get_session() as s:
        return [_to_dict(snap) for snap in s.query(PortfolioSnapshot).filter_by(
            portfolio_id=portfolio_id).order_by(PortfolioSnapshot.timestamp).all()]


# --- Delete / Clone Portfolio ---

def delete_portfolio(portfolio_id: int):
    with get_session() as s:
        for model in [PortfolioSnapshot, Allocation, Watchlist, BacktestResult, Signal, Transaction, Holding]:
            s.query(model).filter_by(portfolio_id=portfolio_id).delete()
        s.query(Portfolio).filter_by(id=portfolio_id).delete()
        s.commit()


def clone_portfolio(portfolio_id: int, new_name: str) -> int:
    src = get_portfolio(portfolio_id)
    if not src:
        raise ValueError(f"Portfolio {portfolio_id} not found")
    new_id = create_portfolio(new_name, src["description"])
    with get_session() as s:
        for h in s.query(Holding).filter_by(portfolio_id=portfolio_id).all():
            s.add(Holding(portfolio_id=new_id, ticker=h.ticker, shares=h.shares,
                          avg_cost=h.avg_cost, current_price=h.current_price, updated_at=_now()))
        for a in s.query(Allocation).filter_by(portfolio_id=portfolio_id).all():
            s.add(Allocation(portfolio_id=new_id, ticker=a.ticker, target_weight=a.target_weight, updated_at=_now()))
        for w in s.query(Watchlist).filter_by(portfolio_id=portfolio_id).all():
            s.add(Watchlist(portfolio_id=new_id, ticker=w.ticker, added_at=_now()))
        s.commit()
    return new_id


# --- Helpers ---

def _to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}



# --- Settings ---

DEFAULTS = {
    "trading_enabled": "true",
    "signal_threshold": "0.5",
    "stop_loss": "-0.05",
    "take_profit": "0.10",
    "max_position_pct": "0.25",
    "vix_threshold": "30",
}


def get_setting(key: str) -> str:
    with get_session() as s:
        row = s.query(Setting).filter_by(key=key).first()
        return row.value if row else DEFAULTS.get(key, "")


def set_setting(key: str, value: str):
    with get_session() as s:
        row = s.query(Setting).filter_by(key=key).first()
        if row:
            row.value = value
            row.updated_at = _now()
        else:
            s.add(Setting(key=key, value=value, updated_at=_now()))
        s.commit()


def get_all_settings() -> dict:
    with get_session() as s:
        rows = {r.key: r.value for r in s.query(Setting).all()}
    return {**DEFAULTS, **rows}


def sync_ticker_names(names: dict):
    """Upsert ticker names to DB. names = {"005930": "삼성전자", "AAPL": "Apple Inc."}"""
    with get_session() as s:
        for ticker, name in names.items():
            existing = s.execute(
                text("SELECT 1 FROM ticker_names WHERE ticker = :t"), {"t": ticker}
            ).fetchone()
            if existing:
                s.execute(text("UPDATE ticker_names SET name = :n WHERE ticker = :t"), {"t": ticker, "n": name})
            else:
                s.execute(text("INSERT INTO ticker_names (ticker, name) VALUES (:t, :n)"), {"t": ticker, "n": name})
        s.commit()
