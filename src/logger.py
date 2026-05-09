"""Shared logging configuration for the project."""

import os
import logging
import config as cfg

LOG_FILE = os.path.join(cfg.DATA_DIR, "pipeline.log")


def setup(level=logging.INFO):
    """Configure root logger with console + file handlers."""
    os.makedirs(cfg.DATA_DIR, exist_ok=True)

    root = logging.getLogger("HwagokQuant")
    root.setLevel(logging.DEBUG)

    if root.handlers:
        return root

    # Console: INFO level, clean format
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))

    # File: DEBUG level, with timestamps
    file = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))

    root.addHandler(console)
    root.addHandler(file)

    # Suppress noisy third-party loggers
    for name in ("urllib3", "yfinance", "transformers", "httpx"):
        logging.getLogger(name).setLevel(logging.INFO)

    return root


def get(name: str) -> logging.Logger:
    """Get a child logger. Call setup() first."""
    return logging.getLogger(f"HwagokQuant.{name}")
