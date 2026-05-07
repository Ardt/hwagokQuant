"""Feature engineering: technical indicators and preprocessing."""

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
from sklearn.preprocessing import MinMaxScaler


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to OHLCV DataFrame."""
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    # Trend
    df["SMA_20"] = SMAIndicator(c, window=20).sma_indicator()
    df["SMA_50"] = SMAIndicator(c, window=50).sma_indicator()
    df["EMA_12"] = EMAIndicator(c, window=12).ema_indicator()
    macd = MACD(c)
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"] = macd.macd_diff()

    # Momentum
    df["RSI"] = RSIIndicator(c).rsi()
    stoch = StochRSIIndicator(c)
    df["StochRSI_K"] = stoch.stochrsi_k()

    # Volatility
    bb = BollingerBands(c)
    df["BB_High"] = bb.bollinger_hband()
    df["BB_Low"] = bb.bollinger_lband()
    df["BB_Width"] = bb.bollinger_wband()
    df["ATR"] = AverageTrueRange(h, l, c).average_true_range()

    # Volume
    df["OBV"] = OnBalanceVolumeIndicator(c, v).on_balance_volume()

    # Returns
    df["Return_1d"] = c.pct_change(1)
    df["Return_5d"] = c.pct_change(5)
    df["Volatility_20d"] = df["Return_1d"].rolling(20).std()

    return df


# Base feature columns (always present)
_BASE_COLS = [
    "Open", "High", "Low", "Close", "Volume",
    "SMA_20", "SMA_50", "EMA_12",
    "MACD", "MACD_Signal", "MACD_Hist",
    "RSI", "StochRSI_K",
    "BB_High", "BB_Low", "BB_Width", "ATR",
    "OBV", "Return_1d", "Return_5d", "Volatility_20d",
    "Sentiment",
]


def prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, MinMaxScaler]:
    """Scale feature columns, return array and fitted scaler.
    Dynamically includes any macro columns present in the DataFrame."""
    # Use base cols + any extra columns (macro) that exist
    cols = [c for c in _BASE_COLS if c in df.columns]
    # Add macro columns (anything not in base and not standard OHLCV metadata)
    skip = set(_BASE_COLS) | {"Ticker", "Date"}
    extra = [c for c in df.columns if c not in skip and df[c].dtype in ("float64", "int64", "float32")]
    cols.extend(extra)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[cols].values)
    return scaled, scaler


def create_sequences(data: np.ndarray, targets: np.ndarray, seq_len: int):
    """Create sliding window sequences for LSTM input."""
    X, y = [], []
    for i in range(seq_len, len(data)):
        X.append(data[i - seq_len : i])
        y.append(targets[i])
    return np.array(X), np.array(y)


def build_target(df: pd.DataFrame) -> np.ndarray:
    """Binary target: 1 if next-day return > 0, else 0."""
    return (df["Close"].pct_change().shift(-1) > 0).astype(int).values


def build_target_3output(df: pd.DataFrame) -> np.ndarray:
    """3-output target: [direction, high%, low%] for next day.
    - direction: 1 if next close > current close, else 0
    - high%: (next_high - current_close) / current_close
    - low%: (next_low - current_close) / current_close
    Returns shape (N, 3). Last row is NaN (no next day).
    """
    close = df["Close"].values
    high = df["High"].shift(-1).values
    low = df["Low"].shift(-1).values
    next_close = df["Close"].shift(-1).values

    direction = (next_close > close).astype(float)
    high_pct = (high - close) / close
    low_pct = (low - close) / close

    return np.column_stack([direction, high_pct, low_pct])
