# Watchdog (Pi 3)

Monitors OCI instance health and pipeline freshness. Restarts OCI if stopped, alerts if pipeline is stale.

## What it does

1. **OCI instance check** — if STOPPED, auto-restarts via OCI API
2. **Pipeline freshness** — queries Supabase for last signal/snapshot timestamp
3. **Alerts** — sends Slack/Discord notification on issues

## Setup (Raspberry Pi 3)

```bash
cd ~/q/watchdog
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in values
```

### OCI config

Copy `~/.oci/config` and `oci_api_key.pem` from your main machine to the Pi:

```bash
mkdir -p ~/.oci
scp user@main-pc:~/.oci/config ~/.oci/
scp user@main-pc:~/.oci/oci_api_key.pem ~/.oci/
chmod 600 ~/.oci/oci_api_key.pem
```

### Find your OCI Instance ID

OCI Console → Compute → Instances → your instance → OCID

## Run

```bash
python watchdog.py
```

## Cron (every 10 min)

```bash
crontab -e
```

```
*/10 * * * * cd ~/q/watchdog && source venv/bin/activate && python watchdog.py >> /tmp/watchdog.log 2>&1
```

## Alerts

On issues, sends to configured Slack/Discord webhooks:
```
🐕 [Watchdog] OCI instance STOPPED. Restarting...
🐕 [Watchdog] Issues detected:
• Signals stale (last: 2026-05-04 01:30:00)
```
