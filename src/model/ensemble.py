"""Ensemble model: adjusts per-ticker signals based on macro + portfolio state."""

import numpy as np
import config as cfg
from src.logger import get

log = get("model.ensemble")


def adjust_signals(ticker_signals: list[dict], macro: dict, portfolio_state: dict, strategy: dict = None) -> list[dict]:
    """
    Adjust raw ticker signals using macro context and portfolio state.

    Args:
        ticker_signals: [{"ticker": str, "signal": int, "probability": float, "price": float}, ...]
        macro: {"VIX": float, "FedFundsRate": float, "TreasurySpread": float, ...}
        portfolio_state: {"cash_pct": float, "concentration": dict, "num_holdings": int}
        strategy: {"signal_threshold": str, "vix_threshold": str, "max_position_pct": str, "min_cash_pct": str}

    Returns:
        Same list with adjusted signal/probability.
    """
    strategy = strategy or {}
    signal_threshold = float(strategy.get("signal_threshold", cfg.SIGNAL_THRESHOLD))
    vix_threshold = float(strategy.get("vix_threshold", 30))
    max_position_pct = float(strategy.get("max_position_pct", 0.25))
    min_cash_pct = float(strategy.get("min_cash_pct", 0.10))

    vix = macro.get("VIX", 20)
    spread = macro.get("TreasurySpread", 1.0)

    # Risk multiplier: high VIX or inverted yield curve → reduce buy confidence
    risk_mult = _risk_multiplier(vix, spread, vix_threshold)
    log.debug(f"Risk multiplier: {risk_mult:.2f} (VIX={vix:.1f}, spread={spread:.2f})")

    cash_pct = portfolio_state.get("cash_pct", 1.0)
    concentration = portfolio_state.get("concentration", {})

    adjusted = []
    for s in ticker_signals:
        ticker = s["ticker"]
        signal = s["signal"]
        prob = s["probability"]

        # Skip macro risk adjustment for KRX tickers (VIX not applicable)
        is_krx = ticker.isdigit()

        # Apply risk multiplier to buy signals
        if signal == 1:
            if not is_krx:
                prob = prob * risk_mult
            # Reduce if already concentrated in this ticker
            weight = concentration.get(ticker, 0)
            if weight > max_position_pct:
                prob *= 0.5
                log.debug(f"{ticker}: concentration penalty (weight={weight:.1%})")
            # Reduce if low cash
            if cash_pct < min_cash_pct:
                prob *= 0.5
                log.debug(f"{ticker}: low cash penalty (cash={cash_pct:.1%})")

        # Apply risk multiplier to hold threshold for sells
        elif signal == -1:
            if not is_krx:
                prob = prob * (2 - risk_mult)

        # Re-evaluate signal based on adjusted probability
        if signal == 1 and prob < signal_threshold:
            signal = 0  # downgrade BUY to HOLD
            log.info(f"{ticker}: BUY → HOLD (adjusted prob={prob:.2%})")

        adjusted.append({**s, "signal": signal, "probability": prob, "original_signal": s["signal"]})

    return adjusted


def _risk_multiplier(vix: float, treasury_spread: float, vix_threshold: float = 30) -> float:
    """
    Returns 0.0-1.0 multiplier. Lower = more risk = reduce buys.
    """
    if vix > vix_threshold + 10:
        vix_score = 0.3
    elif vix > vix_threshold:
        vix_score = 0.6
    elif vix > vix_threshold - 5:
        vix_score = 0.8
    else:
        vix_score = 1.0

    # Yield curve: positive=healthy, negative=recession signal
    if treasury_spread < -0.5:
        spread_score = 0.4
    elif treasury_spread < 0:
        spread_score = 0.7
    else:
        spread_score = 1.0

    return vix_score * spread_score
