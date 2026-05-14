"""Trade: generate signals from saved models, execute paper trades."""

import os
import sys
import config as cfg
from src import logger
from src.market import detect_market, detect_portfolio_market, get_config
from src.data.features import (
    add_technical_indicators, prepare_features,
    create_sequences, build_target,
)
from src.model.lstm import load_model, predict, has_saved_model, MODELS_DIR
from src.model.ensemble import adjust_signals
from src.backtest.engine import generate_signals
from src.portfolio import manager as pm
from src.portfolio.db import get_all_settings
from src.model.strategies import get_allocator
from src import notify
from src import storage

logger.setup()
log = logger.get("trade")

AUTO_MODE = "--auto" in sys.argv
STRATEGY_NAME = next((a.split("=")[1] for a in sys.argv if a.startswith("--strategy=")), None)
PORTFOLIO_ID = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--portfolio=")), None)


def _get_collector(market: str):
    if market == "KRX":
        from src.data.krx_collector import fetch_all
        return fetch_all
    from src.data.collector import fetch_all
    return fetch_all


def _get_macro(market: str):
    if market == "KRX":
        from src.data.krx_macro import fetch_macro, merge_macro
        return fetch_macro, merge_macro
    from src.data.fred import fetch_fred_data, merge_fred
    return fetch_fred_data, merge_fred


def _get_sentiment(market: str):
    mcfg = get_config(market)
    if mcfg["sentiment_enabled"]:
        from src.data.sentiment import add_sentiment_to_df
        return add_sentiment_to_df
    return None


def select_portfolio() -> dict | None:
    """Select portfolio. In auto mode, selects by ID or first with tickers."""
    pm.init()
    portfolios = pm.list_all()
    if not portfolios:
        log.warning("No portfolios. Run portfolio.py first.")
        return None

    if AUTO_MODE:
        if PORTFOLIO_ID:
            s = pm.summary(PORTFOLIO_ID)
            if not s:
                log.warning(f"Portfolio ID {PORTFOLIO_ID} not found.")
                return None
            return s["portfolio"]
        # Fallback: first portfolio with tickers
        for p in portfolios:
            s = pm.summary(p["id"])
            tickers = [h["ticker"] for h in s.get("holdings", [])] + \
                      [w["ticker"] for w in pm.get_watchlist(p["id"])]
            if tickers:
                return s["portfolio"]
        log.warning("No portfolios with tickers found.")
        return None

    print("\n=== Portfolios ===")
    for i, p in enumerate(portfolios, 1):
        s = pm.summary(p["id"])
        tickers = [h["ticker"] for h in s.get("holdings", [])] + \
                  [w["ticker"] for w in pm.get_watchlist(p["id"])]
        market = detect_portfolio_market(tickers) or "?"
        mcfg = get_config(market) if market != "?" else {"currency": "?"}
        currency = mcfg["currency"]
        print(f"  {i}. {p['name']} ({market}, {currency} {p['total_value']:,.0f})")

    choice = input(f"\nSelect [1-{len(portfolios)}]: ").strip()
    try:
        return pm.summary(portfolios[int(choice) - 1]["id"])["portfolio"]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return None


def predict_ticker(ticker: str, df, macro_df, market: str, settings: dict = None) -> dict | None:
    """Load model and generate signal for a ticker."""
    settings = settings or {}
    if not has_saved_model(ticker):
        log.warning(f"{ticker}: no saved model")
        return None

    df = add_technical_indicators(df)

    add_sentiment = _get_sentiment(market)
    if add_sentiment:
        df = add_sentiment(df, ticker)
    else:
        df["Sentiment"] = 0.0

    _, merge_macro = _get_macro(market)
    df = merge_macro(df, macro_df)
    df = df.dropna()

    if len(df) < cfg.SEQUENCE_LENGTH + 10:
        log.warning(f"{ticker}: not enough data")
        return None

    features, _ = prepare_features(df)
    target = build_target(df)
    X, _ = create_sequences(features, target, cfg.SEQUENCE_LENGTH)

    model = load_model(ticker)
    raw_output = predict(model, X[-30:])
    probs = raw_output[:, 0]
    signals = generate_signals(probs, threshold=float(settings.get("signal_threshold", 0.5)))

    latest_price = float(df["Close"].iloc[-1])
    from src.market import round_to_tick
    high_pct, low_pct = float(raw_output[-1][1]), float(raw_output[-1][2])

    return {
        "ticker": ticker,
        "latest_signal": int(signals[-1]),
        "latest_prob": float(probs[-1]),
        "latest_price": latest_price,
        "predicted_high": round_to_tick(latest_price * (1 + high_pct), market),
        "predicted_low": round_to_tick(latest_price * (1 + low_pct), market),
    }





def main():
    """Generate signals and execute paper trades."""
    # Read settings from DB
    settings = get_all_settings()
    if settings.get("trading_enabled") != "true":
        log.info("Trading is paused (trading_enabled=false). Exiting.")
        return

    portfolio = select_portfolio()
    if not portfolio:
        return
    pid = portfolio["id"]

    # Per-portfolio strategy params (with defaults)
    strategy = {
        "signal_threshold": str(portfolio.get("signal_threshold") or 0.5),
        "vix_threshold": str(portfolio.get("vix_threshold") or 30),
        "max_position_pct": str(portfolio.get("max_position_pct") or 0.25),
        "min_cash_pct": str(portfolio.get("min_cash_pct") or 0.10),
        "rotation_metric": portfolio.get("rotation_metric") or "confidence",
        "rotation_threshold": str(portfolio.get("rotation_threshold") or 0.10),
    }

    # Detect market from portfolio tickers
    holdings = [h["ticker"] for h in pm.summary(pid).get("holdings", [])]
    watchlist = [w["ticker"] for w in pm.get_watchlist(pid)]
    tickers = list(set(holdings + watchlist))
    if not tickers:
        # Auto-populate watchlist from both markets
        log.info("No tickers in portfolio. Auto-populating watchlist from universe...")
        from src.data.collector import get_universe as get_us_universe
        from src.data.krx_collector import get_universe as get_krx_universe
        for t in get_us_universe()[:cfg.WATCHLIST_MAX_PER_MARKET]:
            pm.add_to_watchlist(pid, t)
        for t in get_krx_universe()[:cfg.WATCHLIST_MAX_PER_MARKET]:
            pm.add_to_watchlist(pid, t)
        watchlist = [w["ticker"] for w in pm.get_watchlist(pid)]
        tickers = list(set(watchlist))

    # Group tickers by market
    tickers_by_market = {}
    for t in tickers:
        m = detect_market(t)
        tickers_by_market.setdefault(m, []).append(t)

    log.info(f"Trading portfolio: {portfolio['name']} (markets={list(tickers_by_market.keys())})")

    # Download latest models from OCI (no-op if not configured)
    storage.download_models()

    # Fetch data and generate signals per market
    log.info("Fetching market data...")
    results = []
    for market, market_tickers in tickers_by_market.items():
        fetch_all = _get_collector(market)
        fetch_macro, _ = _get_macro(market)
        all_data = fetch_all(market_tickers)
        macro_df = fetch_macro()

        for ticker in market_tickers:
            if ticker not in all_data["Ticker"].values:
                continue
            ticker_df = all_data[all_data["Ticker"] == ticker].copy().drop(columns=["Ticker"])
            result = predict_ticker(ticker, ticker_df, macro_df, market, strategy)
            if result:
                results.append(result)

    if not results:
        log.warning("No signals generated.")
        return

    # Ensemble adjustment
    port_summary = pm.summary(pid)
    conc = {c["ticker"]: c["weight"] for c in pm.concentration(pid)}
    total_cash = sum(port_summary["cash"].values()) if isinstance(port_summary["cash"], dict) else port_summary["cash"]
    portfolio_state = {
        "cash_pct": total_cash / port_summary["total_value"] if port_summary["total_value"] else 1.0,
        "concentration": conc,
        "num_holdings": len(port_summary["holdings"]),
    }
    # Use first market's macro for ensemble (VIX is global)
    first_market = list(tickers_by_market.keys())[0]
    fetch_macro_ens, _ = _get_macro(first_market)
    macro_ens = fetch_macro_ens()
    macro_latest = macro_ens.iloc[-1].to_dict() if not macro_ens.empty else {}
    adjusted = adjust_signals(
        [{"ticker": r["ticker"], "signal": r["latest_signal"],
          "probability": r["latest_prob"], "price": r["latest_price"]} for r in results],
        macro_latest, portfolio_state, strategy,
    )
    for r, adj in zip(results, adjusted):
        r["latest_signal"] = adj["signal"]
        r["latest_prob"] = adj["probability"]

    # Show signals
    markets_str = "+".join(tickers_by_market.keys())
    print(f"\n=== Signals ({markets_str}, ensemble-adjusted) ===")
    for r in results:
        label = {1: "BUY", 0: "HOLD", -1: "SELL"}[r["latest_signal"]]
        cur = "₩" if detect_market(r["ticker"]) == "KRX" else "$"
        print(f"  {r['ticker']}: {label} ({r['latest_prob']:.2%}, {cur}{r['latest_price']:,.0f})")

    # Plan trades via allocator
    strategy_name = STRATEGY_NAME or portfolio.get("allocator_strategy") or "equal_weight"
    allocator = get_allocator(strategy_name)
    log.info(f"Using allocation strategy: {strategy_name}")

    port_summary = pm.summary(pid)
    cash_by_cur = port_summary["cash"] if isinstance(port_summary["cash"], dict) else {"USD": port_summary["cash"]}
    from src.portfolio.db import get_exchange_rate
    alloc_signals = [{"ticker": r["ticker"], "signal": r["latest_signal"],
                      "probability": r["latest_prob"], "price": r["latest_price"]} for r in results]
    strategy["_watchlist"] = watchlist
    strategy["_holdings"] = holdings
    strategy["_cash_by_currency"] = cash_by_cur
    strategy["_exchange_rate"] = get_exchange_rate()
    trades = allocator(alloc_signals, port_summary["holdings"],
                       total_cash, port_summary["total_value"], strategy)
    if not trades:
        log.info("No trades (HOLD only)")
        for r in results:
            pm.record_signal(pid, r["ticker"], r["latest_signal"], r["latest_prob"],
                             predicted_high=r.get("predicted_high"), predicted_low=r.get("predicted_low"))
        pm.take_snapshot(pid)
        return

    print(f"\n=== Proposed Trades ===")
    print(f"  {'Action':<6} {'Ticker':<8} {'Shares':>8} {'Price':>12} {'Total':>14}")
    print(f"  {'-'*50}")
    for t in trades:
        cur = "₩" if detect_market(t["ticker"]) == "KRX" else "$"
        print(f"  {t['action']:<6} {t['ticker']:<8} {t['shares']:>8} {cur}{t['price']:>10,.0f} {cur}{t['total']:>12,.0f}")

    confirm = "y" if AUTO_MODE else input("\nExecute paper trades? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        log.info("Cancelled")
        return

    # Execute
    log.info(f"Paper trading {len(trades)} orders")
    for r in results:
        pm.record_signal(pid, r["ticker"], r["latest_signal"], r["latest_prob"],
                         predicted_high=r.get("predicted_high"), predicted_low=r.get("predicted_low"))

    holdings_before = {h["ticker"]: h for h in pm.summary(pid)["holdings"]}
    trade_lines = []
    for t in trades:
        if t["action"] == "EXCHANGE":
            # Record exchange: source currency loses, target currency gains
            from_cur = t["ticker"].replace("CASH_", "")
            to_cur = "KRW" if from_cur == "USD" else "USD"
            rate = t["shares"]
            amount = t["price"]  # amount in source currency
            received = t["total"]  # amount in target currency
            from src.portfolio import db as _db
            # Withdraw from source (total = 1 * amount)
            _db.add_transaction(pid, f"CASH_{from_cur}", "WITHDRAW", 1, amount)
            # Deposit to target (total = 1 * received)
            _db.add_transaction(pid, f"CASH_{to_cur}", "DEPOSIT", 1, received)
            trade_lines.append(f"EXCHANGE {from_cur}→{to_cur} @{rate:.0f}")
            continue
        cur = "₩" if detect_market(t["ticker"]) == "KRX" else "$"
        if t["action"] == "BUY":
            pm.buy(pid, t["ticker"], t["shares"], t["price"])
            trade_lines.append(f"BUY {t['shares']} {t['ticker']} @ {cur}{t['price']:,.0f}")
        else:
            h = holdings_before.get(t["ticker"])
            avg_cost = h["avg_cost"] if h else t["price"]
            pnl = (t["price"] - avg_cost) * t["shares"]
            pm.sell(pid, t["ticker"], t["shares"], t["price"])
            trade_lines.append(f"SELL {t['shares']} {t['ticker']} | P&L: {cur}{pnl:+,.0f}")

    pm.take_snapshot(pid)
    log.info("Trade session complete")
    notify.send(f"[{markets_str}] Trades:\n" + "\n".join(trade_lines), "Trade Executed")
    pm.print_report(pid)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Trade interrupted")
        sys.exit(130)
    except Exception as e:
        log.error(f"Trade failed: {e}", exc_info=True)
        sys.exit(1)
