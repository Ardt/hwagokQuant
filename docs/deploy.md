# Deployment Architecture

## Overview

Feature별 하드웨어 용량에 따라 분산 배포. Git push → 각 노드 자동 배포.
외부 스토리지 + DB로 노드 간 파일/데이터 동기화 불필요.

```
┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────┐
│   OCI A1 Free Tier   │  │   Raspberry Pi 4B    │  │  Local PC      │
│  (4 OCPU / 24GB)     │  │  (4 core / 4-8GB)    │  │  (Desktop)     │
├──────────────────────┤  ├──────────────────────┤  ├────────────────┤
│                      │  │                      │  │                │
│  ▶ train.py (daily) │  │  ▶ trade.py (daily)  │ │  ▶ portfolio.py│
│    - Cron daily      │  │    - Cron 9:30 KST   │  │  (interactive) │
│    - US + KRX        │  │    - Load models      │ │                │
│    - Heavy compute   │  │    - Generate signals │ │  ▶ Ad-hoc ops  │
│                      │  │    - Paper trade      │ │                │
│  ▶ Backtest (daily) │  │    - Record to DB    │  │                │
│    - Walk-forward    │  │                      │  │                │
│    - Results upload  │  │  ▶ Notifications     │  │                │
│                      │  │    - Slack/Discord    │  │                │
└──────────┬───────────┘  └──────────┬───────────┘  └───────┬────────┘
           │                         │                       │
           ▼                         ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Supabase (PostgreSQL)                             │
│                    All nodes read/write directly                     │
└─────────────────────────────────────────────────────────────────────┘
           │                         │                       │
           ▼                         ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 OCI Object Storage (10GB free)                       │
│                 models/*.pt + results (CSV/JSON)                     │
└─────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                        ┌──────────────────────┐
                        │   Vercel (Hobby)     │
                        │   Dashboard (web)    │
                        │   - Read from Object │
                        │     Storage + DB     │
                        └──────────────────────┘
```

## Deployment Flow

```
Developer (Local PC)
    │
    ├── git push ──→ GitHub
    │                  │
    │                  ├──→ Vercel: auto-deploy dashboard
    │                  ├──→ OCI A1: poll → git pull (code only)
    │                  └──→ Pi 4B:  poll → git pull (code only)
    │
    └── Done. All nodes updated. No file sync needed.
```

## Feature → Hardware Mapping

| Feature | Deployed To | Reason |
|---------|-------------|--------|
| `train.py` | OCI A1 | CPU-heavy (2-3h), needs RAM, daily |
| Backtest | OCI A1 | CPU-heavy, runs after training |
| `trade.py` | Pi 4B | Lightweight inference (<20 sec), daily, always-on |
| `portfolio.py` | Local PC | Interactive CLI, manual decisions |
| Notifications | Pi 4B | Triggered after trade execution |
| Dashboard | Vercel | Read-only web UI, auto-deploy on push |
| Portfolio DB | Supabase | Shared PostgreSQL, all nodes access |
| Models + Results | OCI Object Storage | Central file store, no rsync |

## External Services

### Supabase (PostgreSQL) — Portfolio DB

Replaces `sqlite:///data/portfolio.db`. All nodes connect directly.

```python
# config.py
DB_URL = "postgresql://user:pass@db.xxxx.supabase.co:5432/postgres"
```

No code changes needed — SQLAlchemy handles PostgreSQL natively.

| | SQLite (before) | Supabase (after) |
|--|-----------------|------------------|
| Access | Single node | All nodes simultaneously |
| Sync | rsync needed | Not needed |
| Backup | Manual | Automatic (Supabase) |
| Cost | Free | Free (500 MB) |
| Latency | 0ms (local) | ~50-100ms (network) |

### OCI Object Storage — Models + Results

Replaces rsync for model/data file sharing.

| Bucket | Contents | Producer | Consumer |
|--------|----------|----------|----------|
| `q-models` | `*.pt` (~46MB total) | OCI (train.py) | Pi (trade.py) |
| `q-results` | `training_results.csv`, `backtest_results.json` | OCI (train.py) | Vercel (dashboard) |

```bash
# OCI after training — upload models
oci os object bulk-upload --bucket q-models --src-dir data/models/ --overwrite

# Pi before trading — download models
oci os object bulk-download --bucket q-models --download-dir data/models/

# Vercel — read results via pre-authenticated URL
fetch("https://objectstorage.ap-chuncheon-1.oraclecloud.com/p/.../q-results/results.json")
```

## Hardware Specs

| | OCI A1 Free | Raspberry Pi 4B | Vercel Hobby | Supabase Free | OCI Object Storage |
|--|-------------|-----------------|--------------|---------------|-------------------|
| CPU | 4 OCPU ARM | Cortex-A72 4-core | Serverless | — | — |
| RAM | 24 GB | 4-8 GB | 1 GB/fn | — | — |
| Storage | 50 GB boot | USB SSD | Stateless | 500 MB DB | 10 GB |
| Cost | Free | ~$50 one-time | Free | Free | Free |
| Role | Compute | Execute | Serve | Store (DB) | Store (files) |

## Data Flow (No rsync, No file sync)

```
train.py (OCI)
    │
    ├── models/*.pt ──upload──→ OCI Object Storage
    ├── results.csv ──upload──→ OCI Object Storage
    └── DB writes   ──────────→ Supabase (signals, backtest_results)

trade.py (Pi)
    │
    ├── models/*.pt ←─download── OCI Object Storage
    ├── DB reads    ←────────── Supabase (portfolio, holdings)
    └── DB writes   ──────────→ Supabase (transactions, snapshots)

portfolio.py (PC)
    │
    └── DB read/write ────────→ Supabase

Vercel Dashboard
    │
    ├── results    ←────────── OCI Object Storage (pre-auth URL)
    └── DB reads   ←────────── Supabase (portfolio summary, signals)
```

## Repo Structure (Monorepo)

Single repo, each node clones the same code but only runs its assigned feature.

```
q/
├── train.py              ← OCI runs this
├── trade.py              ← Pi runs this
├── portfolio.py          ← PC runs this
├── config.py             ← shared config (all nodes)
├── requirements.txt
├── src/                  ← shared library (all nodes have it)
│   ├── data/
│   ├── model/
│   ├── portfolio/
│   ├── backtest/
│   ├── market.py
│   ├── logger.py
│   └── notify.py
├── dashboard/            ← Vercel deploys this folder only
│   └── (Next.js app)
├── deploy/
│   ├── oci.cron          ← OCI cron config
│   ├── pi.cron           ← Pi cron config
│   └── vercel.json       ← Vercel config
├── docs/
└── .gitignore            ← data/, models/, *.pt, *.db excluded
```

No submodules. No data files in git. Each node does `git pull` and runs its feature.

## Auto-Deploy on Git Push

### OCI A1 + Pi: Cron-based pull
```bash
# /etc/cron.d/q-deploy — check for code updates every 5 min
*/5 * * * *  cd ~/q && git fetch origin && git reset --hard origin/main
```

## Cron Schedules

### OCI A1 — Daily Training + Backtest
```bash
# Daily 1:00 AM KST
0 1 * * *  cd ~/q && source venv/bin/activate && python train.py
# train.py uploads models + results to Object Storage after completion
```

### Raspberry Pi 4B — Daily Trading
```bash
# Mon-Fri 9:30 AM KST
30 9 * * 1-5  cd ~/q && source venv/bin/activate && python trade.py --auto
# trade.py downloads latest models from Object Storage before inference
```

## Setup Per Node

### Environment Variables

Each node has its own `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
# Edit .env with node-specific values
```

| Env Var | OCI A1 | Pi 4B | Local PC |
|---------|--------|-------|----------|
| `FRED_API_KEY` | ✅ | ✅ | ✅ |
| `KRX_ID` / `KRX_PW` | ✅ | ✅ | ✅ |
| `SLACK_WEBHOOK` | ✅ | ✅ | optional |
| `DISCORD_WEBHOOK` | ✅ | ✅ | optional |
| `MAILGUN_*` | optional | ✅ | optional |
| `Q_DB_URL` | ✅ (Supabase) | ✅ (Supabase) | ✅ (Supabase) |
| `Q_OCI_NAMESPACE` | ✅ | ✅ | optional |

### OCI A1
```bash
sudo apt update && sudo apt install -y python3.10 python3.10-venv git
git clone <repo> ~/q && cd ~/q
python3.10 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Configure: config.py (DB_URL, FRED key, OCI bucket config)
# Install OCI CLI: bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
```

### Raspberry Pi 4B
```bash
sudo apt update && sudo apt install -y python3 python3-venv git
git clone <repo> ~/q && cd ~/q
python3 -m venv venv && source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
# Install OCI CLI for model downloads
# Add swap: sudo fallocate -l 2G /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
```

### Vercel Dashboard
```bash
cd ~/q/dashboard
vercel link
vercel --prod
# Auto-deploys on git push. Reads from Object Storage + Supabase.
```

## TODO

### Done ✅
- [x] `--auto` flag for `trade.py`
- [x] Switch DB to Supabase PostgreSQL
- [x] OCI Object Storage upload/download in train.py and trade.py
- [x] Scaffold Vercel dashboard (Next.js)
- [x] Settings table + control panel (pause trading, change strategy)
- [x] Status/monitoring page on dashboard
- [x] Secrets management (.env + python-dotenv)
- [x] Migrate SQLite data to Supabase

### Remaining ⬜
- [ ] Set up OCI account + create buckets (`q-models`, `q-results`)
- [ ] Create pre-authenticated request URL for Vercel
- [ ] Provision OCI A1 instance (use `prep/oci_a1_launcher.py`)
- [ ] Push repo to GitHub
- [ ] Deploy dashboard to Vercel
- [ ] Set up Raspberry Pi 4B (install Python, clone repo, configure cron)
- [ ] Set up Tailscale across all nodes
- [ ] Test full cycle: train (OCI) → upload → trade (Pi) → download → dashboard (Vercel)
