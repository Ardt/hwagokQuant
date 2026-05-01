# External Services Setup Guide

## 1. Supabase (Database) ✅

PostgreSQL database shared across all nodes.

### Setup
1. Go to [supabase.com](https://supabase.com) → Create account → New Project
2. Region: choose closest (e.g. `ap-northeast-1` for Korea/Japan)
3. Set a database password (no special characters recommended)
4. Wait for project to provision (~1 min)

### Get Connection String
- Project Settings → Database → Connection string → select **Pooler** mode
- Copy URI format: `postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require`

### Get API Keys (for Dashboard)
- Project Settings → API
- **Project URL**: `https://xxxx.supabase.co`
- **anon public key**: `sb_publishable_...` (safe for frontend)

### Configure
```bash
# .env
Q_DB_URL=postgresql+psycopg2://postgres.PROJECT_REF:PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require
```

### Create Tables
```bash
python -c "from src.portfolio.db import init_db; init_db(); print('Done')"
```

### Migrate Existing Data (optional)
```bash
python migrate.py
```

### Settings
- ❌ Disable "Enable automatic RLS" (or add permissive policies)
- ✅ Enable "Automatically expose new tables and functions"

---

## 2. OCI Object Storage (Model/Result Files) ⬜

Stores trained models (*.pt) and training results (CSV) for sharing between nodes.

### Setup
1. Go to [cloud.oracle.com](https://cloud.oracle.com) → Create free account
2. Navigate to: Storage → Object Storage → Create Bucket
3. Create two buckets:
   - `q-models` — for LSTM model files
   - `q-results` — for training result CSVs

### Get Credentials
- Profile → Tenancy → copy **Namespace**
- Install OCI CLI: `bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"`
- Run `oci setup config` → generates `~/.oci/config` with API key

### Configure
```bash
# .env
Q_OCI_NAMESPACE=your_namespace
Q_OCI_BUCKET_MODELS=q-models
Q_OCI_BUCKET_RESULTS=q-results
```

### Verify
```bash
oci os bucket list --compartment-id YOUR_TENANCY_OCID
```

### How It's Used
- `train.py` → uploads models + results after training
- `trade.py` → downloads models before inference
- Vercel dashboard → reads results via pre-authenticated URL

### Pre-Authenticated Request (for Vercel)
- Bucket → Pre-Authenticated Requests → Create
- Access Type: ObjectRead, Expiration: 1 year
- Copy URL → set as `OCI_RESULTS_URL` in Vercel env vars

---

## 3. OCI A1 Compute (Training Server) ⬜

Always-on ARM server for daily model training.

### Setup
1. Use `oci_a1_launcher.py` to auto-provision (retries until capacity available)
2. Or manually: Compute → Create Instance → VM.Standard.A1.Flex → 4 OCPU / 24 GB

### Configure Instance
```bash
sudo apt update && sudo apt install -y python3.10 python3.10-venv git
git clone YOUR_REPO ~/q && cd ~/q
python3.10 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in secrets
```

### Cron (daily training)
```bash
crontab -e
# Add:
0 1 * * * cd ~/q && source venv/bin/activate && python train.py
```

### Free Tier Limits
- 4 OCPUs + 24 GB RAM (total across all A1 instances)
- 50 GB boot volume
- Always free (not 12-month trial)

---

## 4. Vercel (Dashboard Hosting) ⬜

Hosts the Next.js dashboard with auto-deploy on git push.

### Setup
1. Go to [vercel.com](https://vercel.com) → Sign up with GitHub
2. New Project → Import your repo
3. Set **Root Directory**: `dashboard`
4. Framework: Next.js (auto-detected)

### Environment Variables (set in Vercel dashboard)
```
NEXT_PUBLIC_SUPABASE_URL = https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY = sb_publishable_...
OCI_RESULTS_URL = https://objectstorage.../p/.../o
```

### Deploy
- Click Deploy → get URL (e.g. `q-dashboard.vercel.app`)
- Every `git push` to main auto-deploys

### Free Tier Limits
- 100 GB bandwidth/month
- Serverless functions: 10s timeout
- Unlimited deploys

---

## 5. GitHub (Code Repository) ⬜

Stores code, triggers deployments to all nodes.

### Setup
```bash
cd ~/q
git init
git remote add origin https://github.com/YOUR_USER/hwagokQuant.git
git add -A
git commit -m "initial commit"
git push -u origin main
```

### .gitignore (already configured)
```
.env          # secrets
data/         # models, CSVs, DB
venv/         # Python packages
__pycache__/  # bytecode
```

### Deploy Flow
```
git push → GitHub → Vercel auto-deploys dashboard
                  → OCI/Pi poll and git pull (every 5 min via cron)
```

---

## 6. Slack (Notifications) ✅

### Setup
1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App
2. Incoming Webhooks → Activate → Add to channel
3. Copy webhook URL

### Configure
```bash
# .env
SLACK_WEBHOOK=https://hooks.slack.com/services/T.../B.../...
```

---

## 7. Discord (Notifications) ✅

### Setup
1. Server Settings → Integrations → Webhooks → New Webhook
2. Select channel → Copy Webhook URL

### Configure
```bash
# .env
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

---

## 8. Mailgun (Email Notifications) ✅

### Setup
1. Go to [mailgun.com](https://www.mailgun.com) → Sign up (free: 5000 emails/month)
2. Add domain (or use sandbox domain for testing)
3. Get API key from: Settings → API Keys

### Configure
```bash
# .env
MAILGUN_API_KEY=your-api-key
MAILGUN_DOMAIN=sandbox...mailgun.org
MAILGUN_SENDER=alerts@your-domain
EMAIL_RECIPIENT=your@email.com
```

---

## 9. FRED (Macro Economic Data) ✅

### Setup
1. Go to [fred.stlouisfed.org](https://fred.stlouisfed.org) → Create account
2. My Account → API Keys → Request API Key

### Configure
```bash
# .env
FRED_API_KEY=your-32-char-key
```

---

## Summary: What Goes Where

| Node | Services Used |
|------|--------------|
| OCI A1 (train) | Supabase, OCI Storage, FRED, Slack/Discord |
| Pi 4B (trade) | Supabase, OCI Storage, FRED, yfinance/pykrx, Slack/Discord/Email |
| Vercel (dashboard) | Supabase, OCI Storage |
| Local PC (portfolio) | Supabase |
