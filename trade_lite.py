"""Trade Lite: memory-optimized trade.py for low-powered devices (Pi 3, 1GB RAM).

Differences from trade.py:
- Processes tickers one at a time (no bulk OHLCV load)
- Explicit model cleanup after each prediction
- Caps new ticker scan
- Uses float32 for DataFrames
- Skips sentiment analysis (saves ~200MB from transformers)

Usage: python trade_lite.py [--auto]
"""

import os
import sys
import gc
import glob
import numpy as np
import pandas as pd
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
from src import notify
from src import storage

logger.setup()
log = logger.get("trade_lite")

AUTO_MODE = "--auto" in sys.argv
MAX_NEW_SCAN = 10  # limit new ticker discovery to save memory


def _to_float32(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast float64 columns to float32."""
    float_cols = df.select_dtypes("float64").columns
    if len(float_cols):
        df[float_cols] = df[float_cols].astype(np.float32)
    return df


def _fetch_single_ticker(ticker: str, market: str) -> pd.DataFrame | None:
    """Fetch OHLCV for a single ticker (no CSV cache load)."""
    try:
        if market == "KRX":
            from pykrx import stock as krx
            from datetime import date, timedelta
            end = date.today().strftime("%Y%m%d")
            start = (date.today() - timedelta(days=365 * 5)).strftime("%Y%m%d")
            df = krx.get_market_ohlcv(start, end, ticker)
            if df.empty:
                return None
            df = df.rename(columns={"시가": "Open", "고가": "High", "저가": "Low", "종가": "Close", "거래량": "Volume"})
            df.index.name = "Date"
        else:
            import yfinance as yf
            df = yf.download(ticker, start=cfg.START_DATE, progress=False)
            if df.empty:
                return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        return _to_float32(df[["Open", "High", "Low", "Close", "Volume"]])
    except Exception as e:
        log.warning(f"{ticker}: fetch failed — {e}")
        return None


def _get_macro(market: str):
    if market == "KRX":
        from src.data.krx_macro import fetch_macro, merge_macro
        return fetch_macro, merge_macro
    from src.data.fred import fetch_fred_data, merge_fred
    return fetch_fred_data, merge_fred


def select_portfolio() -> dict | None:
    pm.init()
    portfolios = pm.list_all()
    if not portfolios:
        log.warning("No portfolios.")
        return None

    if AUTO_MODE:
        for p in portfolios:
            s = pm.summary(p["id"])
            tickers = [h["ticker"] for h in s.get("holdings", [])] + \
                      [w["ticker"] for w in pm.get_watchlist(p["id"])]
            if tickers:
                return s["portfolio"]
        return None

    print("\n=== Portfolios ===")
    for i, p in enumerate(portfolios, 1):
        s = pm.summary(p["id"])
        tickers = [h["ticker"] for h in s.get("holdings", [])] + \
                  [w["ticker"] for w in pm.get_watchlist(p["id"])]
        market = detect_portfolio_market(tickers) or "?"
        mcfg = get_config(market) if market != "?" else {"currency": "?"}
        print(f"  {i}. {p['name']} ({market}, {mcfg['currency']} {p['total_value']:,.0f})")

    choice = input(f"\nSelect [1-{len(portfolios)}]: ").strip()
    try:
        return pm.summary(portfolios[int(choice) - 1]["id"])["portfolio"]
    except (ValueError, IndexError):
        return None


def predict_ticker(ticker: str, df: pd.DataFrame, macro_df: pd.DataFrame, market: str, settings: dict) -> dict | None:
    """Load model, predict, and immediately free memory."""
    if not has_saved_model(ticker):
        return None

    df = add_technical_indicators(df)
    df["Sentiment"] = np.float32(0.0)  # skip sentiment to save memory

    _, merge_macro = _get_macro(market)
    df = merge_macro(df, macro_df)
    df = df.dropna()

    if len(df) < cfg.SEQUENCE_LENGTH + 10:
        return None

    features, _ = prepare_features(df)
    target = build_target(df)
    X, _ = create_sequences(features, target, cfg.SEQUENCE_LENGTH)

    # Load model, predict, free immediately
    model = load_model(ticker)
    probs = predict(model, X[-30:])
    del model, X, features, target
    gc.collect()

    signals = generate_signals(probs, threshold=float(settings.get("signal_threshold", 0.5)))

    return {
        "ticker": ticker,
        "latest_signal": int(signals[-1]),
        "latest_prob": float(probs[-1]),
        "latest_price": float(df["Close"].iloc[-1]),
    }


def plan_trades(portfolio_id: int, results: list[dict]) -> list[dict]:
    s = pm.summary(portfolio_id)
    cash = s["cash"]
    holdings_map = {h["ticker"]: h for h in s["holdings"]}
    trades = []

    buy_results = [r for r in results if r["latest_signal"] == 1]
    if buy_results:
        cash_per_ticker = cash / len(buy_results)
        for r in buy_results:
            shares = int(cash_per_ticker // r["latest_price"])
            if shares > 0:
                trades.append({"ticker": r["ticker"], "action": "BUY", "shares": shares,
                               "price": r["latest_price"], "total": shares * r["latest_price"],
                               "reason": f"confidence {r['latest_prob']:.1%}"})

    for r in results:
        if r["latest_signal"] == -1 and r["ticker"] in holdings_map:
            held = holdings_map[r["ticker"]]["shares"]
            shares = int(held * (1 - r["latest_prob"]))
            if shares > 0:
                trades.append({"ticker": r["ticker"], "action": "SELL", "shares": shares,
                               "price": r["latest_price"], "total": shares * r["latest_price"],
                               "reason": f"sell {1 - r['latest_prob']:.0%}"})
    return trades


def main():
    settings = get_all_settings()
    if settings.get("trading_enabled") != "true":
        log.info("Trading paused. Exiting.")
        return

    portfolio = select_portfolio()
    if not portfolio:
        return
    pid = portfolio["id"]

    holdings = [h["ticker"] for h in pm.summary(pid).get("holdings", [])]
    watchlist = [w["ticker"] for w in pm.get_watchlist(pid)]
    tickers = list(set(holdings + watchlist))
    if not tickers:
        log.warning("No tickers in portfolio.")
        return

    market = detect_market(tickers[0])
    mcfg = get_config(market)
    log.info(f"Trade Lite: {portfolio['name']} (market={market}, {len(tickers)} tickers)")

    # Download models from OCI
    storage.download_models()

    # Limit new ticker scan
    all_models = [os.path.basename(f).replace("_lstm.pt", "")
                  for f in glob.glob(os.path.join(MODELS_DIR, "*_lstm.pt"))]
    new_tickers = [t for t in all_models if t not in tickers and detect_market(t) == market][:MAX_NEW_SCAN]

    # Fetch macro once (small, shared)
    fetch_macro, _ = _get_macro(market)
    macro_df = _to_float32(fetch_macro())

    # Process tickers ONE AT A TIME
    log.info("Generating signals (sequential, low-memory)...")
    results = []
    for ticker in tickers:
        df = _fetch_single_ticker(ticker, market)
        if df is None:
            continue
        result = predict_ticker(ticker, df, macro_df, market, settings)
        del df
        gc.collect()
        if result:
            results.append(result)
            log.debug(f"  {ticker}: signal={result['latest_signal']} prob={result['latest_prob']:.2%}")

    # Scan new tickers (BUY signals only)
    for ticker in new_tickers:
        df = _fetch_single_ticker(ticker, market)
        if df is None:
            continue
        result = predict_ticker(ticker, df, macro_df, market, settings)
        del df
        gc.collect()
        if result and result["latest_signal"] == 1:
            results.append(result)

    if not results:
        log.warning("No signals generated.")
        return

    # Ensemble adjustment
    macro_latest = macro_df.iloc[-1].to_dict() if not macro_df.empty else {}
    port_summary = pm.summary(pid)
    conc = {c["ticker"]: c["weight"] for c in pm.concentration(pid)}
    adjusted = adjust_signals(
        [{"ticker": r["ticker"], "signal": r["latest_signal"],
          "probability": r["latest_prob"], "price": r["latest_price"]} for r in results],
        macro_latest,
        {"cash_pct": port_summary["cash"] / port_summary["total_value"] if port_summary["total_value"] else 1.0,
         "concentration": conc, "num_holdings": len(port_summary["holdings"])},
    )
    for r, adj in zip(results, adjusted):
        r["latest_signal"] = adj["signal"]
        r["latest_prob"] = adj["probability"]

    # Display signals
    currency = mcfg["currency"]
    print(f"\n=== Signals ({market}) ===")
    for r in results:
        label = {1: "BUY", 0: "HOLD", -1: "SELL"}[r["latest_signal"]]
        print(f"  {r['ticker']}: {label} ({r['latest_prob']:.2%}, {currency} {r['latest_price']:,.0f})")

    # Plan and execute trades
    trades = plan_trades(pid, results)
    if not trades:
        log.info("No trades (HOLD only)")
        for r in results:
            pm.record_signal(pid, r["ticker"], r["latest_signal"], r["latest_prob"])
        pm.take_snapshot(pid)
        return

    print(f"\n=== Proposed Trades ===")
    for t in trades:
        print(f"  {t['action']:<6} {t['ticker']:<8} {t['shares']:>6} @ {currency} {t['price']:>10,.0f}")

    confirm = "y" if AUTO_MODE else input("\nExecute? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        return

    # Execute
    holdings_before = {h["ticker"]: h for h in pm.summary(pid)["holdings"]}
    trade_lines = []
    for r in results:
        pm.record_signal(pid, r["ticker"], r["latest_signal"], r["latest_prob"])

    for t in trades:
        if t["action"] == "BUY":
            pm.buy(pid, t["ticker"], t["shares"], t["price"])
            trade_lines.append(f"BUY {t['shares']} {t['ticker']} @ {currency} {t['price']:,.0f}")
        else:
            h = holdings_before.get(t["ticker"])
            avg_cost = h["avg_cost"] if h else t["price"]
            pnl = (t["price"] - avg_cost) * t["shares"]
            pm.sell(pid, t["ticker"], t["shares"], t["price"])
            trade_lines.append(f"SELL {t['shares']} {t['ticker']} | P&L: {currency} {pnl:+,.0f}")

    pm.take_snapshot(pid)
    log.info("Trade session complete")
    notify.send(f"[{market}] Trades:\n" + "\n".join(trade_lines), "Trade Executed")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        log.error(f"Trade failed: {e}", exc_info=True)
        sys.exit(1)
