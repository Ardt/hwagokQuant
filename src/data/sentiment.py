"""Sentiment analysis: FinBERT-based scoring from news headlines."""

import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import config as cfg

_sentiment_pipeline = None


def get_pipeline():
    """Lazy-load FinBERT sentiment pipeline."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        tokenizer = AutoTokenizer.from_pretrained(cfg.SENTIMENT_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(cfg.SENTIMENT_MODEL)
        _sentiment_pipeline = pipeline(
            "sentiment-analysis", model=model, tokenizer=tokenizer, truncation=True
        )
    return _sentiment_pipeline


def score_texts(texts: list[str]) -> list[float]:
    """Score a list of texts. Returns float in [-1, 1] per text."""
    pipe = get_pipeline()
    results = pipe(texts, batch_size=cfg.BATCH_SIZE)
    scores = []
    for r in results:
        label, conf = r["label"], r["score"]
        if label == "positive":
            scores.append(conf)
        elif label == "negative":
            scores.append(-conf)
        else:
            scores.append(0.0)
    return scores


def fetch_news_yfinance(ticker: str) -> pd.DataFrame:
    """Fetch news headlines for a ticker via yfinance."""
    import yfinance as yf

    stock = yf.Ticker(ticker)
    news = stock.news or []
    rows = []
    for item in news:
        content = item.get("content", {})
        title = content.get("title", "")
        pub = content.get("pubDate", "")
        if title:
            rows.append({"date": pub, "headline": title})
    if not rows:
        return pd.DataFrame(columns=["date", "headline"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.tz_localize(None).dt.normalize()
    return df


def get_sentiment_for_ticker(ticker: str, dates: pd.DatetimeIndex) -> pd.Series:
    """Get daily sentiment scores for a ticker aligned to trading dates."""
    news_df = fetch_news_yfinance(ticker)
    if news_df.empty:
        return pd.Series(0.0, index=dates, name="Sentiment")

    news_df["score"] = score_texts(news_df["headline"].tolist())
    daily = news_df.groupby("date")["score"].mean()

    # Rolling average over lookback window
    sentiment = daily.reindex(dates).ffill().fillna(0.0)
    sentiment = sentiment.rolling(cfg.NEWS_LOOKBACK_DAYS, min_periods=1).mean()
    sentiment.name = "Sentiment"
    return sentiment


def add_sentiment_to_df(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Add Sentiment column to a ticker's OHLCV DataFrame."""
    sentiment = get_sentiment_for_ticker(ticker, df.index)
    df["Sentiment"] = sentiment
    return df
