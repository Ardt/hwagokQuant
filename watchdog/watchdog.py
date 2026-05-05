"""Pi 3 Watchdog — health-check OCI instance + pipeline freshness."""

import os
import sys
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import oci
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).parent / ".env")

# Config
OCI_INSTANCE_ID = os.environ["OCI_INSTANCE_ID"]
OCI_COMPARTMENT_ID = os.environ.get("OCI_COMPARTMENT_ID", "")
DB_URL = os.environ["Q_DB_URL"]
STALE_HOURS = int(os.environ.get("STALE_HOURS", "25"))
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")


def get_oci_client():
    config = oci.config.from_file()
    return oci.core.ComputeClient(config)


def check_instance_status() -> str:
    """Return OCI instance lifecycle state."""
    client = get_oci_client()
    instance = client.get_instance(OCI_INSTANCE_ID).data
    return instance.lifecycle_state


def start_instance():
    """Start a stopped OCI instance."""
    client = get_oci_client()
    client.instance_action(OCI_INSTANCE_ID, "START")


def check_pipeline_freshness() -> dict:
    """Check if train/trade ran recently by querying Supabase."""
    engine = create_engine(DB_URL, pool_pre_ping=True)
    results = {}
    with engine.connect() as conn:
        # Last signal
        row = conn.execute(text(
            "SELECT MAX(created_at) as last_at FROM signals"
        )).fetchone()
        results["last_signal"] = row[0] if row else None

        # Last snapshot
        row = conn.execute(text(
            "SELECT MAX(created_at) as last_at FROM portfolio_snapshots"
        )).fetchone()
        results["last_snapshot"] = row[0] if row else None

    return results


def is_stale(timestamp) -> bool:
    """Check if timestamp is older than STALE_HOURS."""
    if timestamp is None:
        return True
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_HOURS)
    return timestamp < cutoff


def send_alert(message: str):
    """Send alert to configured channels."""
    prefix = "🐕 [Watchdog]"
    msg = f"{prefix} {message}"
    print(msg)

    if SLACK_WEBHOOK:
        requests.post(SLACK_WEBHOOK, json={"text": msg}, timeout=10)
    if DISCORD_WEBHOOK:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)


def check_supabase_health() -> bool:
    """Check if Supabase is reachable."""
    engine = create_engine(DB_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def run():
    issues = []

    # 1. Check OCI instance
    try:
        state = check_instance_status()
        if state == "STOPPED":
            send_alert(f"OCI instance STOPPED. Restarting...")
            start_instance()
            send_alert("OCI instance restart initiated ✅")
        elif state != "RUNNING":
            issues.append(f"OCI instance state: {state}")
    except Exception as e:
        issues.append(f"OCI check failed: {e}")

    # 2. Check Supabase connectivity
    try:
        check_supabase_health()
    except Exception as e:
        issues.append(f"Supabase unreachable: {e}")

    # 3. Check pipeline freshness
    try:
        freshness = check_pipeline_freshness()
        if is_stale(freshness["last_signal"]):
            issues.append(f"Signals stale (last: {freshness['last_signal']})")
        if is_stale(freshness["last_snapshot"]):
            issues.append(f"Snapshots stale (last: {freshness['last_snapshot']})")
    except Exception as e:
        issues.append(f"DB check failed: {e}")

    # 3. Report issues
    if issues:
        send_alert("Issues detected:\n• " + "\n• ".join(issues))
    else:
        print(f"[{datetime.now()}] All healthy ✅")


if __name__ == "__main__":
    run()
