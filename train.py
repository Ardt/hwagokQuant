"""Train: non-interactive model training for ticker + ensemble models."""

import os
import sys
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
                 market: str, incremental: bool = False) -> dict | None:
    """Train LSTM for a single ticker."""
    mcfg = get_config(market)
    log.info(f"{'Fine-tuning' if incremental else 'Training'} {ticker} ({market})")

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

    if len(df) < cfg.SEQUENCE_LENGTH + 50:
        log.warning(f"{ticker}: not enough data ({len(df)} rows), skipping")
        return None

    features, scaler = prepare_features(df)
    target = build_target_3output(df)
    # Last row has NaN from shift(-1), exclude it
    features = features[:-1]
    target = target[:-1]
    X, y = create_sequences(features, target, cfg.SEQUENCE_LENGTH)

    if incremental:
        if not has_saved_model(ticker):
            log.warning(f"{ticker}: no existing model, doing full train")
            incremental = False
        else:
            recent = min(INCREMENTAL_DAYS, len(X))
            X_train, y_train = X[-recent:], y[-recent:]
            X_val, y_val = X[-30:], y[-30:]

            model = load_model(ticker)
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

            save_model(model, ticker)
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
    save_model(model, ticker)

    raw = predict(model, X_val)
    probs = raw[:, 0]
    signals = generate_signals(probs)
    test_prices = df["Close"].iloc[split + cfg.SEQUENCE_LENGTH:]
    result = backtest(test_prices, signals, mcfg["initial_capital"])

    m = result["metrics"]
    log.info(f"{ticker}: return={m['total_return']:.2%} sharpe={m['sharpe_ratio']:.2f}")
    return {"ticker": ticker, **m}


def train_market(market: str, tickers: list[str], full: bool = False):
    """Train all tickers for a given market."""
    mcfg = get_config(market)
    incremental = not full
    log.info(f"=== Training {market} ({len(tickers)} tickers, {'full' if full else 'incremental'}) ===")

    fetch_all = _get_collector(market)
    fetch_macro, _ = _get_macro(market)

    all_data = fetch_all(tickers)
    macro_df = fetch_macro()

    results = []
    for ticker in tickers:
        if ticker not in all_data["Ticker"].values:
            continue
        ticker_df = all_data[all_data["Ticker"] == ticker].copy().drop(columns=["Ticker"])
        result = train_ticker(ticker, ticker_df, macro_df, market, incremental=incremental)
        if result:
            results.append(result)

    # Save training summary
    if results:
        summary = pd.DataFrame(results).sort_values("total_return", ascending=False)
        os.makedirs(cfg.DATA_DIR, exist_ok=True)
        suffix = f"_{market.lower()}" if market != "US" else ""
        summary.to_csv(os.path.join(cfg.DATA_DIR, f"training_results{suffix}.csv"), index=False)
        log.info(f"\n{summary.to_string(index=False)}")

        # Watchlist management
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

    strong = summary[(summary["sharpe_ratio"] > 1.0) & (summary["total_return"] > 0)]
    if not strong.empty:
        added = []
        for _, row in strong.iterrows():
            for p in market_portfolios:
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


def main():
    """Train models for each market: universe (top N by market cap) + portfolio extras."""
    full = "--full" in sys.argv

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
        train_market(market, tickers, full=full)

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
