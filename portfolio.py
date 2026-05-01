"""Portfolio management: create, configure, and view portfolios."""

from src import logger
from src.portfolio import manager as pm
from src.portfolio.db import get_all_settings, set_setting

logger.setup()
log = logger.get("portfolio")


def menu():
    pm.init()
    while True:
        print("\n=== Portfolio Manager ===")
        print("  1. List portfolios")
        print("  2. Create portfolio")
        print("  3. View report")
        print("  4. Add tickers")
        print("  5. Remove ticker")
        print("  6. Manual buy")
        print("  7. Manual sell")
        print("  8. Set allocation")
        print("  9. Refresh prices")
        print("  10. Delete portfolio")
        print("  11. Settings (strategy / trading control)")
        print("  0. Exit")

        choice = input("\nSelect: ").strip()

        if choice == "1":
            list_portfolios()
        elif choice == "2":
            create()
        elif choice == "3":
            report()
        elif choice == "4":
            add_tickers()
        elif choice == "5":
            remove_ticker()
        elif choice == "6":
            manual_buy()
        elif choice == "7":
            manual_sell()
        elif choice == "8":
            set_allocation()
        elif choice == "9":
            refresh()
        elif choice == "10":
            delete()
        elif choice == "11":
            settings_menu()
        elif choice == "0":
            break


def list_portfolios():
    portfolios = pm.list_all()
    if not portfolios:
        print("  No portfolios.")
        return
    print(f"\n  {'ID':<4} {'Name':<20} {'Value':>12} {'Return':>10} {'Holdings':>10}")
    print(f"  {'-'*58}")
    for p in portfolios:
        print(f"  {p['id']:<4} {p['name']:<20} ${p['total_value']:>11,.2f} {p['total_return']:>9.2%} {p['num_holdings']:>10}")


def _select_pid() -> int | None:
    portfolios = pm.list_all()
    if not portfolios:
        print("  No portfolios.")
        return None
    if len(portfolios) == 1:
        return portfolios[0]["id"]
    list_portfolios()
    pid = input("  Portfolio ID: ").strip()
    try:
        return int(pid)
    except ValueError:
        return None


def create():
    name = input("  Name: ").strip() or "Default"
    capital = input("  Capital [100000]: ").strip()
    capital = float(capital) if capital else 100000
    p = pm.create(name, capital=capital)
    log.info(f"Created '{name}' (id={p['id']})")
    print(f"  Created '{name}' (id={p['id']})")
    tickers = input("  Tickers (comma-separated): ").strip().upper()
    if tickers:
        for t in tickers.split(","):
            t = t.strip()
            if t:
                pm.add_to_watchlist(p["id"], t)
        print(f"  Added tickers to watchlist")


def report():
    pid = _select_pid()
    if pid:
        pm.print_report(pid)


def add_tickers():
    pid = _select_pid()
    if not pid:
        return
    tickers = input("  Tickers to add: ").strip().upper()
    for t in tickers.split(","):
        t = t.strip()
        if t:
            pm.add_to_watchlist(pid, t)
            print(f"    Added {t}")


def remove_ticker():
    pid = _select_pid()
    if not pid:
        return
    wl = pm.get_watchlist(pid)
    if wl:
        print(f"  Watchlist: {[w['ticker'] for w in wl]}")
    ticker = input("  Ticker to remove: ").strip().upper()
    if ticker:
        pm.remove_from_watchlist(pid, ticker)
        print(f"    Removed {ticker}")


def manual_buy():
    pid = _select_pid()
    if not pid:
        return
    ticker = input("  Ticker: ").strip().upper()
    shares = float(input("  Shares: ").strip())
    price = float(input("  Price: ").strip())
    pm.buy(pid, ticker, shares, price)
    log.info(f"Manual BUY {shares} {ticker} @ ${price:.2f}")
    print(f"  Bought {shares} {ticker} @ ${price:.2f}")


def manual_sell():
    pid = _select_pid()
    if not pid:
        return
    ticker = input("  Ticker: ").strip().upper()
    shares = float(input("  Shares: ").strip())
    price = float(input("  Price: ").strip())
    pm.sell(pid, ticker, shares, price)
    log.info(f"Manual SELL {shares} {ticker} @ ${price:.2f}")
    print(f"  Sold {shares} {ticker} @ ${price:.2f}")


def set_allocation():
    pid = _select_pid()
    if not pid:
        return
    print("  Enter allocations (e.g. AAPL=0.3,TSLA=0.2):")
    raw = input("  > ").strip().upper()
    allocs = {}
    for pair in raw.split(","):
        if "=" in pair:
            ticker, weight = pair.split("=")
            allocs[ticker.strip()] = float(weight.strip())
    if allocs:
        pm.set_target_allocation(pid, allocs)
        print(f"  Set: {allocs}")


def refresh():
    pid = _select_pid()
    if not pid:
        return
    updated = pm.refresh_prices(pid)
    for u in updated:
        print(f"  {u['ticker']}: ${u['price']:.2f}")


def delete():
    pid = _select_pid()
    if not pid:
        return
    confirm = input(f"  Delete portfolio {pid}? [y/N]: ").strip().lower()
    if confirm == "y":
        pm.delete(pid)
        print("  Deleted.")


def settings_menu():
    settings = get_all_settings()
    print("\n=== Settings ===")
    for i, (k, v) in enumerate(settings.items(), 1):
        print(f"  {i}. {k} = {v}")
    print(f"  0. Back")

    choice = input("\n  Edit which? [0]: ").strip()
    if not choice or choice == "0":
        return
    try:
        idx = int(choice) - 1
        key = list(settings.keys())[idx]
    except (ValueError, IndexError):
        return

    current = settings[key]
    if key == "trading_enabled":
        new_val = "false" if current == "true" else "true"
        print(f"  Toggled {key}: {current} → {new_val}")
    else:
        new_val = input(f"  {key} [{current}]: ").strip()
        if not new_val:
            return

    set_setting(key, new_val)
    print(f"  ✓ {key} = {new_val}")


if __name__ == "__main__":
    menu()
