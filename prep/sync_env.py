"""Sync .env to remote nodes via SSH (Windows compatible)."""
import subprocess
import sys
import os

PI_HOST = os.environ.get("PI_HOST", "pi@100.64.0.2")
OCI_HOST = os.environ.get("OCI_HOST", "ubuntu@100.64.0.3")
PROJECT_DIR = "~/q"
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")

if not os.path.exists(ENV_FILE):
    print(f"Error: {ENV_FILE} not found")
    sys.exit(1)

nodes = [
    ("Pi", PI_HOST),
    ("OCI", OCI_HOST),
]

print("=== Syncing .env to remote nodes ===")
for name, host in nodes:
    dest = f"{host}:{PROJECT_DIR}/.env"
    print(f"  → {name} ({host})... ", end="", flush=True)
    result = subprocess.run(["scp", "-q", ENV_FILE, dest], capture_output=True)
    print("✓" if result.returncode == 0 else "✗ (unreachable)")

print("\nUpdate hosts: set PI_HOST / OCI_HOST env vars or edit this script.")
