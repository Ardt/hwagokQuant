"""Train: non-interactive model training for ticker + ensemble models."""

import os
import sys
from datetime import date
import pandas as pd
import config as cfg
from src import logger
from src.market import detect_market, get_config
from src.data.features import (
    add_technical_indicators, prepare_features,
    create_sequences, build_target, build_target_3output,
)
from src.model.lstm import train_model, predict, save_model, load_model, has_saved_model
from src.backtest.engine import generate_signals, backtest
from src.portfolio import manager as pm
from src import notify
from src import storage

logger.setup()
log = logger.get("train")

# Incremental training config
INCREMENTAL_EPOCHS = 10
INCREMENTAL_LR = 0.0005
INCREMENTAL_DAYS = 90


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


def train_ticker(ticker: str, df: pd.DataFrame, macro_df: pd.DataFrame,
                 market: str, incremental: bool = False, model_name: str = None) -> dict | None:
    """Train LSTM for a single ticker."""
    model_name = model_name or cfg.DEFAULT_MODEL
    mcfg_model = cfg.MODELS[model_name]
    seq_len = mcfg_model["sequence_length"]
    mcfg = get_config(market)
    log.info(f"{'Fine-tuning' if incremental else 'Training'} {ticker} ({market}, {model_name})")

    df = add_technical_indicators(df)

    # Sentiment (US only)
    add_sentiment = _get_sentiment(market)
    if add_sentiment:
        df = add_sentiment(df, ticker)
    else:
        df["Sentiment"] = 0.0

    # Macro
    _, merge_macro = _get_macro(market)
    df = merge_macro(df, macro_df)
    df = df.dropna()

    if len(df) < seq_len + 50:
        log.warning(f"{ticker}: not enough data ({len(df)} rows), skipping")
        return None

    features, scaler = prepare_features(df)
    target = build_target_3output(df)
    # Last row has NaN from shift(-1), exclude it
    features = features[:-1]
    target = target[:-1]
    X, y = create_sequences(features, target, seq_len)

    if incremental:
        if not has_saved_model(ticker, model_name):
            log.warning(f"{ticker}: no existing model, doing full train")
            incremental = False
        else:
            recent = min(INCREMENTAL_DAYS, len(X))
            X_train, y_train = X[-recent:], y[-recent:]
            X_val, y_val = X[-30:], y[-30:]

            model = load_model(ticker, model_name)
            from src.model.lstm import make_dataloader, device, _combined_loss
            import torch

            optimizer = torch.optim.Adam(model.parameters(), lr=INCREMENTAL_LR)
            criterion = _combined_loss
            train_loader = make_dataloader(X_train, y_train, shuffle=True)

            model.train()
            for epoch in range(INCREMENTAL_EPOCHS):
                loss_sum = 0
                for X_batch, y_batch in train_loader:
                    X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                    optimizer.zero_grad()
                    loss = criterion(model(X_batch), y_batch)
                    loss.backward()
                    optimizer.step()
                    loss_sum += loss.item()

            save_model(model, ticker, model_name)
            raw = predict(model, X_val)
            probs = raw[:, 0]
            signals = generate_signals(probs)
            test_prices = df["Close"].iloc[-30:]
            result = backtest(test_prices, signals, mcfg["initial_capital"])
            m = result["metrics"]
            log.info(f"{ticker}: fine-tuned, return={m['total_return']:.2%}")
            return {"ticker": ticker, **m}

    # Full training
    split = int(len(X) * cfg.TRAIN_RATIO)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    if len(X_val) < 10:
        log.warning(f"{ticker}: not enough validation data, skipping")
        return None

    model, history = train_model(X_train, y_train, X_val, y_val)
    save_model(model, ticker, model_name)

    raw = predict(model, X_val)
    probs = raw[:, 0]
    signals = generate_signals(probs)
    test_prices = df["Close"].iloc[split + seq_len:]
    result = backtest(test_prices, signals, mcfg["initial_capital"])

    m = result["metrics"]
    log.info(f"{ticker}: return={m['total_return']:.2%} sharpe={m['sharpe_ratio']:.2f}")
    return {"ticker": ticker, **m}


def train_market(market: str, tickers: list[str], full: bool = False, model_name: str = None):
    """Train all tickers for a given market."""
    model_name = model_name or cfg.DEFAULT_MODEL
    mcfg = get_config(market)
    incremental = not full
    log.info(f"=== Training {market} ({len(tickers)} tickers, {'full' if full else 'incremental'}) ===")

    fetch_all = _get_collector(market)
    fetch_macro, _ = _get_macro(market)

    all_data = fetch_all(tickers)
    macro_df = fetch_macro()

    # Truncate to END_DATE for simulation
    if cfg.END_DATE:
        all_data = all_data[all_data.index <= cfg.END_DATE]
        macro_df = macro_df[macro_df.index <= cfg.END_DATE]

    # Skip if market closed (no new data for today, allow weekend gaps)
    trading_date = cfg.END_DATE or date.today().isoformat()
    if all_data.empty:
        log.info(f"{market}: no data, skipping training")
        return
    days_since_last = (pd.Timestamp(trading_date) - all_data.index.max()).days
    if days_since_last > 4:
        log.info(f"{market}: market closed on {trading_date} (last data {days_since_last} days ago), skipping training")
        return

    results = []
    for ticker in tickers:
        if ticker not in all_data["Ticker"].values:
            continue
        ticker_df = all_data[all_data["Ticker"] == ticker].copy().drop(columns=["Ticker"])
        result = train_ticker(ticker, ticker_df, macro_df, market, incremental=incremental, model_name=model_name)
        if result:
            results.append(result)

    # Save training summary
    if results:
        summary = pd.DataFrame(results).sort_values("total_return", ascending=False)
        os.makedirs(cfg.DATA_DIR, exist_ok=True)
        suffix = f"_{market.lower()}" if market != "US" else ""
        summary.to_csv(os.path.join(cfg.DATA_DIR, f"training_results{suffix}_{model_name}.csv"), index=False)
        log.info(f"\n{summary.to_string(index=False)}")

        # Watchlist management (only for default model to avoid duplicate notifications)
        if model_name == cfg.DEFAULT_MODEL:
            _update_watchlists(market, summary)

    log.info(f"=== {market} Training Complete: {len(results)}/{len(tickers)} models ===")


def _update_watchlists(market: str, summary: pd.DataFrame):
    """Add strong performers / remove poor performers from watchlists."""
    pm.init()
    portfolios = pm.list_all()
    if not portfolios:
        return

    # Filter portfolios that have any ticker in this market
    market_portfolios = []
    for p in portfolios:
        s = pm.summary(p["id"])
        ptickers = [h["ticker"] for h in s.get("holdings", [])] + \
                   [w["ticker"] for w in pm.get_watchlist(p["id"])]
        if any(detect_market(t) == market for t in ptickers):
            market_portfolios.append(p)
    if not market_portfolios:
        return

    universe = _get_universe(market)
    strong = summary[(summary["sharpe_ratio"] > 1.0) & (summary["total_return"] > 0)]
    if not strong.empty:
        added = []
        for _, row in strong.iterrows():
            if row["ticker"] not in set(universe):
                continue
            for p in market_portfolios:
                top_n = p.get("market_cap_top_n") or 100
                if row["ticker"] not in set(universe[:top_n]):
                    continue
                pm.add_to_watchlist(p["id"], row["ticker"])
            added.append(f"{row['ticker']} (sharpe={row['sharpe_ratio']:.2f})")
        if added:
            notify.send(f"[{market}] Strong performers:\n" + "\n".join(added), "Training Alert")

    poor = summary[(summary["sharpe_ratio"] < 0) & (summary["total_return"] < 0)]
    if not poor.empty:
        for _, row in poor.iterrows():
            for p in market_portfolios:
                pm.remove_from_watchlist(p["id"], row["ticker"])
        notify.send(f"[{market}] Removed poor performers", "Training Alert")


def _get_universe(market: str) -> list[str]:
    """Get full ticker universe for a market."""
    if market == "KRX":
        from src.data.krx_collector import get_universe
    else:
        from src.data.collector import get_universe
    return get_universe()


def _get_portfolio_tickers(market: str) -> set[str]:
    """Get all tickers from portfolios that belong to this market."""
    pm.init()
    tickers = set()
    for p in pm.list_all():
        s = pm.summary(p["id"])
        ptickers = [h["ticker"] for h in s.get("holdings", [])] + \
                   [w["ticker"] for w in pm.get_watchlist(p["id"])]
        for t in ptickers:
            if detect_market(t) == market:
                tickers.add(t)
    return tickers


def _sync_ticker_names():
    """Sync ticker names from cached CSVs to DB."""
    from src.portfolio.db import sync_ticker_names
    names = {}
    # KRX names
    krx_path = os.path.join(cfg.DATA_DIR, "krx_tickers.csv")
    if os.path.exists(krx_path):
        df = pd.read_csv(krx_path)
        for _, row in df.iterrows():
            names[str(row["Ticker"])] = row["Name"]
    # US names
    us_path = os.path.join(cfg.DATA_DIR, "tickers.csv")
    if os.path.exists(us_path):
        df = pd.read_csv(us_path)
        if "Name" in df.columns:
            for _, row in df.iterrows():
                names[row["Ticker"]] = row["Name"]
    if names:
        sync_ticker_names(names)
        log.info(f"Synced {len(names)} ticker names to DB")


def _sync_benchmarks():
    """Fetch KOSPI and NASDAQ100 index prices and store in DB."""
    from src.portfolio.db import get_session, text
    import yfinance as yf

    benchmarks = {"KOSPI": "^KS11", "NASDAQ100": "^NDX"}
    try:
        for name, symbol in benchmarks.items():
            df = yf.download(symbol, start=cfg.START_DATE, end=cfg.END_DATE, progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            with get_session() as s:
                for dt, row in df.iterrows():
                    date_str = dt.strftime("%Y-%m-%d")
                    s.execute(text(
                        "INSERT INTO benchmarks (ticker, date, close) VALUES (:t, :d, :c) "
                        "ON CONFLICT (ticker, date) DO UPDATE SET close = :c"
                    ), {"t": name, "d": date_str, "c": float(row["Close"])})
                s.commit()
            log.info(f"Synced {name} benchmark ({len(df)} days)")
    except Exception as e:
        log.warning(f"Benchmark sync failed: {e}")


def main():
    """Train models for each market: universe (top N by market cap) + portfolio extras."""
    full = "--full" in sys.argv
    model_arg = next((a.split("=")[1] for a in sys.argv if a.startswith("--model=")), None)
    models_to_train = [model_arg] if model_arg else list(cfg.MODELS.keys())

    for model_name in models_to_train:
        mcfg_model = cfg.MODELS[model_name]
        log.info(f"=== Training model: {model_name} (seq={mcfg_model['sequence_length']}) ===")

        # Override legacy globals for this model
        cfg.SEQUENCE_LENGTH = mcfg_model["sequence_length"]
        cfg.HIDDEN_SIZE = mcfg_model["hidden_size"]
        cfg.NUM_LAYERS = mcfg_model["num_layers"]
        cfg.DROPOUT = mcfg_model["dropout"]
        cfg.LEARNING_RATE = mcfg_model["learning_rate"]
        cfg.EPOCHS = mcfg_model["epochs"]
        cfg.BATCH_SIZE = mcfg_model["batch_size"]

        for market in cfg.MARKETS:
            log.info(f"--- Preparing {market} ---")

            # 1. Get universe (top N by market cap)
            universe = _get_universe(market)

            # 2. Merge in portfolio tickers not already in universe
            extras = _get_portfolio_tickers(market) - set(universe)
            if extras:
                log.info(f"{market}: {len(extras)} extra tickers from portfolios: {list(extras)}")
            tickers = universe + list(extras)

            # 3. Train
            train_market(market, tickers, full=full, model_name=model_name)

    # Upload to OCI Object Storage (no-op if not configured)
    storage.upload_models()
    storage.upload_results()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Training interrupted")
        sys.exit(130)
    except Exception as e:
        log.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)
