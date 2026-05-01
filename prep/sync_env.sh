#!/bin/bash
# Sync .env to all remote nodes
# Usage: ./sync_env.sh

PI_HOST="${PI_HOST:-pi@100.64.0.2}"
OCI_HOST="${OCI_HOST:-ubuntu@100.64.0.3}"
PROJECT_DIR="~/q"
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found in current directory"
    exit 1
fi

echo "=== Syncing .env to remote nodes ==="

echo -n "  → Pi ($PI_HOST)... "
scp -q "$ENV_FILE" "$PI_HOST:$PROJECT_DIR/.env" && echo "✓" || echo "✗ (unreachable)"

echo -n "  → OCI ($OCI_HOST)... "
scp -q "$ENV_FILE" "$OCI_HOST:$PROJECT_DIR/.env" && echo "✓" || echo "✗ (unreachable)"

echo ""
echo "Done. Update hosts by editing this script or setting env vars:"
echo "  PI_HOST=user@ip OCI_HOST=user@ip ./sync_env.sh"
