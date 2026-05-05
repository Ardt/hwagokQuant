"""Pluggable allocation strategies. Drop a .py file here to register."""

import importlib
import pkgutil
import pathlib

STRATEGIES = {}


def strategy(func):
    """Decorator: registers function as an allocation strategy."""
    STRATEGIES[func.__name__] = func
    return func


# Auto-import all modules in this package
_pkg_dir = pathlib.Path(__file__).parent
for _mod in pkgutil.iter_modules([str(_pkg_dir)]):
    importlib.import_module(f".{_mod.name}", __package__)


def get_allocator(name: str = "equal_weight"):
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: '{name}'. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]
