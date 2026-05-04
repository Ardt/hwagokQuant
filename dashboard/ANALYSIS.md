# Dashboard Analysis (2026-05-04)

## Tech Stack
- **Framework**: Next.js 15 (App Router) on Vercel
- **Data**: Supabase (PostgreSQL) + OCI Object Storage (training results CSV)
- **UI**: Raw inline styles, no CSS framework or component library
- **Dependencies**: `@supabase/supabase-js`, `@vercel/analytics`, `@vercel/speed-insights`

## Pages

| Page | Data Source | Type | Description |
|------|-------------|------|-------------|
| `/` (Home) | Supabase | Server | Portfolios list + last 10 signals |
| `/training` | OCI Storage | Server | US/KRX training results (return, sharpe, win rate, max DD) |
| `/portfolio` | Supabase | Server | Holdings per portfolio (ticker, shares, avg cost, current price) |
| `/signals` | Supabase | Server | Last 100 signals with BUY/SELL/HOLD + confidence |
| `/control` | Supabase API | Client | Toggle trading on/off + edit strategy params |
| `/status` | Supabase API | Client | System health: trading state, last signal/trade/snapshot |

## API Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings` | GET/PUT | Read/write strategy settings |
| `/api/status` | GET | Last signal, trade, snapshot + trading state |
| `/api/training?market=` | GET | CSV → JSON from OCI |
| `/api/portfolio?id=` | GET | Portfolio + holdings + transactions |
| `/api/signals?portfolio_id=&limit=` | GET | Filtered signals |

## What's Working ✅
- Full data pipeline from Supabase (portfolios, holdings, signals, transactions, snapshots)
- OCI Object Storage integration for training results (pending actual bucket URL)
- Remote control panel (pause/resume trading, adjust parameters)
- System health monitoring with staleness detection
- Vercel Analytics + Speed Insights

## Gaps & Improvement Opportunities

1. **No styling framework** — all inline styles, no responsive design, no consistent design system
2. **No charts/visualizations** — equity curves, P&L over time, signal distribution (tables only)
3. **No real-time updates** — Status page polls every 60s, other pages are static SSR
4. **No loading/error states** — server pages silently show "No data" on failure
5. **No filtering/sorting** — signals and training results can't be filtered or sorted
6. **No P&L display** — portfolio page shows holdings but not unrealized/realized P&L
7. **OCI not connected** — `OCI_RESULTS_URL` env var still pending
8. **No authentication** — control panel is publicly accessible
9. **No backtest results page** — backtest data exists in DB but isn't displayed
10. **No notifications history** — notifications are sent but not logged/viewable

## Suggested Priority Improvements

1. Add a charting library (e.g., `recharts` or `lightweight-charts`) for equity curves and signal history
2. Add Tailwind CSS for consistent, responsive styling
3. Add P&L calculations to portfolio page (unrealized gains, total value)
4. Add ISR/revalidation so pages refresh periodically
5. Add market filter to signals and training pages
6. Connect OCI (set `OCI_RESULTS_URL` env var on Vercel)

---

## Improvement Plan — UI Redesign

### Reference: KokonutUI Dashboard Template (v0.app)

Source: `bCVx09sGDJ1` — a v0.app-generated dashboard using KokonutUI + shadcn/ui.

### Current vs Target

| Aspect | Current | Target (Reference) |
|--------|---------|-------------------|
| CSS | Raw inline styles | Tailwind CSS + CSS variables |
| Components | Plain HTML | shadcn/ui (Radix) + KokonutUI |
| Theme | Dark only, hardcoded | Dark/Light toggle (next-themes) |
| Icons | None | Lucide React |
| Charts | None | Recharts |
| Layout | Simple top nav bar | Sidebar + TopNav + Content area |
| Responsive | Not responsive | Mobile sidebar drawer |

### New Dependencies Required

```
tailwindcss, postcss, tailwindcss-animate
class-variance-authority, clsx, tailwind-merge
lucide-react
next-themes
recharts
@radix-ui/react-* (as needed by shadcn/ui)
```

### Component Mapping

| Reference Component | Q Dashboard Use |
|--------------------|-----------------|
| `list-01` (Accounts + balances) | Portfolio holdings |
| `list-02` (Transactions) | Recent signals / trades |
| `list-03` (Goals with progress) | Training results per ticker |
| Sidebar nav | Navigation (Training, Portfolio, Signals, Control, Status) |
| Theme toggle | Dark/Light mode switch |
| Recharts | Equity curves, signal confidence, backtest charts |

### Design Patterns to Adopt

- **Layout**: Fixed sidebar (collapsible on mobile) + top nav + scrollable content
- **Cards**: `border border-zinc-200 dark:border-zinc-800 rounded-xl p-6`
- **Colors**: CSS variables for theming, zinc palette for neutrals, emerald/red for +/-
- **Typography**: `text-xs` / `text-sm` with clear hierarchy
- **Dark mode**: `dark:` classes + `next-themes` provider

### Migration Steps

| # | Task | Status |
|---|------|--------|
| 1 | Add Tailwind CSS + PostCSS + globals.css with CSS variables | ⬜ |
| 2 | Add `cn()` utility (clsx + tailwind-merge) | ⬜ |
| 3 | Add lucide-react icons | ⬜ |
| 4 | Add next-themes + ThemeProvider + ThemeToggle | ⬜ |
| 5 | Implement sidebar + top-nav layout (replace current nav) | ⬜ |
| 6 | Redesign home page with card-based layout | ⬜ |
| 7 | Redesign portfolio page (list-01 pattern) | ⬜ |
| 8 | Redesign signals page (list-02 pattern) | ⬜ |
| 9 | Redesign training page (list-03 pattern + recharts) | ⬜ |
| 10 | Redesign control panel with shadcn/ui inputs | ⬜ |
| 11 | Redesign status page with status cards | ⬜ |
| 12 | Add recharts equity curve / backtest charts | ⬜ |
| 13 | Mobile responsive testing | ⬜ |


---

## Future: Authentication (Multi-User Support)

### Plan: Supabase Auth

Use Supabase's built-in authentication to gate dashboard access and support multi-user.

### Why Supabase Auth

- **RLS (Row Level Security)** — each user only sees their own data, enforced at DB level
- **User-scoped data** — `user_id` column on portfolios, holdings, signals, etc.
- **No password management** — Supabase handles hashing, reset, email verification
- **OAuth providers** — Google/GitHub/Kakao with a toggle, no code changes
- **Free tier** — 50,000 MAU on Supabase free plan
- **Session management** — token refresh, expiry, multi-device handled automatically
- **API route protection** — verify JWT in API routes

### Schema Change

```sql
ALTER TABLE portfolios ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own portfolios" ON portfolios
  FOR ALL USING (user_id = auth.uid());
```

### Implementation Steps

| # | Task | Status |
|---|------|--------|
| 1 | Install `@supabase/ssr` | ⬜ |
| 2 | Create server-side Supabase client (`lib/supabase-server.ts`) | ⬜ |
| 3 | Add Next.js middleware (redirect unauthenticated → /login) | ⬜ |
| 4 | Create `/login` page (email + password) | ⬜ |
| 5 | Add logout button to top-nav | ⬜ |
| 6 | Protect API routes (verify session) | ⬜ |
| 7 | Add `user_id` column to tables + RLS policies | ⬜ |
| 8 | Enable OAuth providers in Supabase dashboard | ⬜ |

### Dependencies

- `@supabase/ssr` (server-side auth for Next.js App Router)

### Files

| File | Purpose |
|------|---------|
| `middleware.ts` | Redirect unauthenticated users to /login |
| `app/login/page.tsx` | Login form |
| `lib/supabase-server.ts` | Server-side Supabase client with cookie handling |
| `components/top-nav.tsx` | Add logout button |


---

## Future: Multi-Portfolio Dashboard Features

Backend already supports multiple portfolios. Dashboard improvements:

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 1 | Portfolio comparison chart | Overlay equity curves of multiple portfolios | ⬜ |
| 2 | Combined total value | Aggregate value across all portfolios (header/home) | ⬜ |
| 3 | Portfolio selector/filter | Filter signals, trades, snapshots by portfolio | ⬜ |
| 4 | Per-portfolio P&L summary | Unrealized/realized gains per portfolio card | ⬜ |
| 5 | Portfolio performance table | Side-by-side metrics (return, sharpe, drawdown) | ⬜ |


---

## Auth Design: Allowlist + OAuth Only

### Approach

- Login page with OAuth buttons only (Google/GitHub)
- `allowed_users` table controls who can access
- No public signup, no passwords

### Phase 1: Auth as Gate (Current Target)

Auth controls who can access the dashboard. All logged-in users see all shared data.

```
User → OAuth login → email in allowed_users? → YES → access all data
                                              → NO  → denied
```

**Database changes (Phase 1):**
```sql
CREATE TABLE allowed_users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  role TEXT DEFAULT 'viewer',
  created_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO allowed_users (email, role) VALUES ('admin@gmail.com', 'admin');
```

**Supabase dashboard setup:**
- Enable Google/GitHub OAuth providers
- Disable "Allow new users to sign up"
- Set redirect URL to `https://your-domain.vercel.app/auth/callback`

### Phase 2: Full Multi-User with RLS (Future)

Each user sees only their own data. Admin sees all.

**Database changes (Phase 2):**
```sql
-- Add auth_id to allowed_users
ALTER TABLE allowed_users ADD COLUMN auth_id UUID REFERENCES auth.users(id);

-- Add user_id to all data tables
ALTER TABLE portfolios ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE holdings ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE signals ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE transactions ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE portfolio_snapshots ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE backtest_results ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE settings ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Enable RLS (repeat for each table)
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_or_admin" ON portfolios FOR ALL USING (
  user_id = auth.uid()
  OR auth.uid() IN (SELECT auth_id FROM allowed_users WHERE role = 'admin')
);

-- Assign existing data to admin after first login
UPDATE portfolios SET user_id = 'your-auth-uuid';
```

**Access matrix:**
| Role | Sees |
|------|------|
| `admin` | All users' data |
| `viewer` | Own data only |

### Implementation Steps (Phase 1)

| # | Task | Status |
|---|------|--------|
| 1 | Create `allowed_users` table in Supabase | ⬜ |
| 2 | Enable Google/GitHub OAuth in Supabase dashboard | ⬜ |
| 3 | Install `@supabase/ssr` | ⬜ |
| 4 | Create server-side Supabase client with cookies | ⬜ |
| 5 | Create `/login` page (OAuth buttons only) | ⬜ |
| 6 | Create `/auth/callback` route (handle OAuth + allowlist check) | ⬜ |
| 7 | Add middleware (session check + allowlist) | ⬜ |
| 8 | Add logout button to top-nav | ⬜ |
| 9 | Protect API routes | ⬜ |
| 10 | Build and verify | ⬜ |
