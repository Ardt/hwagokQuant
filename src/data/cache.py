"""Cache utility: TTL check, list, and clear for data files."""

import os
import time
import config as cfg


def get_ttl(filename: str) -> int:
    """Get TTL for a file. Uses per-file config or default."""
    return cfg.CACHE_TTL.get(filename, cfg.CACHE_TTL_DEFAULT)


def is_valid(filename: str) -> bool:
    """Check if a cached file exists and is within TTL. None TTL = never expires."""
    path = os.path.join(cfg.DATA_DIR, filename)
    if not os.path.exists(path):
        return False
    ttl = get_ttl(filename)
    if ttl is None:
        return True
    age = time.time() - os.path.getmtime(path)
    return age < ttl


def age_str(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"


def list_cache():
    """Print status of all cached files."""
    if not os.path.exists(cfg.DATA_DIR):
        print("No data directory.")
        return
    files = [f for f in os.listdir(cfg.DATA_DIR) if not f.endswith(".db")]
    if not files:
        print("No cached files.")
        return
    print(f"\n{'File':<20} {'Size':>10} {'Age':>8} {'TTL':>8} {'Status':>10}")
    print("-" * 60)
    for f in sorted(files):
        path = os.path.join(cfg.DATA_DIR, f)
        size = os.path.getsize(path)
        age = time.time() - os.path.getmtime(path)
        ttl = get_ttl(f)
        if ttl is None:
            status = "valid"
            ttl_str = "never"
        else:
            status = "valid" if age < ttl else "EXPIRED"
            ttl_str = age_str(ttl)
        size_str = f"{size / 1024:.1f}KB" if size < 1048576 else f"{size / 1048576:.1f}MB"
        print(f"  {f:<18} {size_str:>10} {age_str(age):>8} {ttl_str:>8} {status:>10}")
    print()


def clear(filename: str = None):
    """Clear a specific cached file or all cached files (excludes .db)."""
    if not os.path.exists(cfg.DATA_DIR):
        return
    if filename:
        path = os.path.join(cfg.DATA_DIR, filename)
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed {filename}")
        else:
            print(f"{filename} not found")
    else:
        removed = 0
        for f in os.listdir(cfg.DATA_DIR):
            if not f.endswith(".db"):
                os.remove(os.path.join(cfg.DATA_DIR, f))
                removed += 1
        print(f"Cleared {removed} cached files")


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args or args[0] == "list":
        list_cache()
    elif args[0] == "clear":
        clear(args[1] if len(args) > 1 else None)
    else:
        print("Usage: python -m src.data.cache [list|clear [filename]]")
