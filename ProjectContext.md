# ProjectContext.md — Glizzness Accounting Automation

> **For LLMs:** Read this file at the start of any new session to get full context.
> Also read SETUP.md for detailed workflow docs and env var reference.

---

## What This Is

Python-based accounting automation for **The Glizzness LLC** — a food truck
operated by James T. Johnson in Columbia, MO. The system pulls Square POS data,
computes double-entry journal entries, and posts them to Wave Accounting
(cloud bookkeeping app). It also tracks weekly Weenie Wagon loan payments.

**Owner / contacts:** James Jason Trinton Johnson (operator), Lance McCarter
(consultant, developer). GitHub user: lazrex.

---

## Data Flow

```
Square POS API
    ↓  sync_square.py (CLI) / sync.py:sync_square() (dashboard)
Supabase (Postgres)       ←→ glizzness.db (SQLite, local CLI only)
    ↓  post_to_wave.py (CLI) / sync.py:build_wave_entries() + post_to_wave()
Wave Accounting (GraphQL API)
```

```
Lender CSV (amortization)
    ↓  post_loan_payments.py --import (CLI) / manual Supabase upsert
Supabase: loan_payments table
    ↓  sync.py:build_loan_entries() + post_loan_payments()
Wave Accounting (two transactions per payment)
```

---

## Architecture: Two Parallel Systems

### 1. CLI scripts (SQLite, original)
`sync_square.py`, `post_to_wave.py`, `post_loan_payments.py`, `check_variances.py`
— still work standalone with `glizzness.db`. Use these for ad-hoc CLI operations.

### 2. Dashboard modules (Supabase, cloud)
`db.py` — status queries + variance check  
`sync.py` — all sync/post logic using Supabase  
`dashboard.py` — Streamlit UI  
These are what Streamlit Community Cloud runs. No local file system needed.

---

## Database Schema (12 tables)

| Table | Key | Purpose |
|-------|-----|---------|
| `payouts` | `payout_id` TEXT | Square payout header (one per bank deposit) |
| `payout_entries` | `entry_id` TEXT | Line items inside a payout (CHARGE/REFUND/DEPOSIT_FEE) |
| `payments` | `payment_id` TEXT | Square payment detail |
| `orders` | `order_id` TEXT | Square order (has tax/discount totals) |
| `journal_entries` | `payout_id` TEXT | Wave entry staged/posted per payout |
| `journal_entry_lines` | `id` SERIAL | DR/CR lines for each journal entry |
| `wave_posts` | `payout_id` TEXT | Legacy post tracker (superseded by journal_entries.status) |
| `wave_accounts` | `account_id` TEXT | Wave chart of accounts cache |
| `wave_transactions` | `row_key` TEXT | Wave CSV import rows |
| `loan_payments` | `payment_date` TEXT | Weenie Wagon amortization schedule |
| `loan_journal_entries` | `payment_date` TEXT | Loan payment staged/posted entries |
| `sync_log` | `id` SERIAL | Audit log of each Square sync run |

Schema file: `supabase_schema.sql`

---

## Key Business Logic

### Square sales journal entry (per payout)
Built in `sync.py:build_wave_entries()` and `post_to_wave.py:build_entries()`:

```
DR  Square Settlements Clearing   payout_net_cents    ← anchor (DEPOSIT direction in Wave)
DR  Merchant Account Fees         fees_cents
DR  Customer Discounts            discounts_cents      ← only if > 0
DR  Sales Returns                 returns_cents        ← only if > 0
    CR  Food & Beverage Sales     gross_sales_cents    ← sale - tax + disc (pre-discount revenue)
    CR  Tips Collected            tips_cents           ← only if > 0
    CR  Columbia Sales Tax        taxes_cents          ← only if > 0
```

Entry type math:
- **CHARGE**: `gross_sales += sale_cents - tax_cents + disc_cents`
  (discount added back so CR Sales = pre-discount; DR Discounts = reduction)
- **REFUND**: `returns += abs(e_gross)`
- **DEPOSIT_FEE**: `fees += abs(e_gross)` (Square instant-deposit fee, fee_cents=0)
- All types: `fees += e_fee`

Balance check: `abs(total_DR - total_CR) <= 1` (1-cent rounding allowed)

Wave `externalId`: `{payout_id}:clr` — prevents duplicate posting on re-run

### Loan payments (Weenie Wagon, $77.07/week)
Two Wave transactions per payment date (Wave doesn't allow liability in line items):

**Tx1 — Interest:**
- Anchor: Weenie Wagon Loan Clearing, WITHDRAWAL, $interest
- Line: Interest Expense, DEBIT, $interest

**Tx2 — Principal:**
- Anchor: The First Weenie Wagon (liability), DEPOSIT, $principal
  (`DEPOSIT` into a liability = DR liability = reduces balance)
- Line: Weenie Wagon Loan Clearing, CREDIT, $principal

`externalId`s: `weenie-interest-{date}` and `weenie-principal-{date}`  
Cutoff: payments **after** 2025-05-12 (prior entered manually in Wave)  
`wave_entry_id` stored as `int:{wave_id}|pri:{wave_id}`

---

## Wave API Notes

- GraphQL endpoint: `https://gql.waveapps.com/graphql/public`
- Auth: `Bearer {WAVE_TOKEN}` header
- Mutation: `moneyTransactionCreate` — one call per journal entry
- Amounts: dollar strings `f"{cents / 100:.2f}"`
- `externalId` deduplication: Wave rejects duplicate externalIds with
  `ALREADY_EXISTS` / `DUPLICATE` error code — scripts treat this as success
- Anchor account is NOT included in lineItems — it auto-balances
- Anchor direction: DEBIT on an asset = `"DEPOSIT"`, CREDIT on an asset = `"WITHDRAWAL"`

---

## Square API Notes

- Base URL: `https://connect.squareup.com/v2`
- Auth: `Bearer {SQUARE_TOKEN}` + `Square-Version: 2025-01-23`
- **Payout date quirk:** Square filters `/v2/payouts` by `created_at`, not `arrival_date`.
  Workaround: fetch with 7-day wider window, filter by `arrival_date` in Python.
- Money: all amounts in **cents** (integers) — stored as cents in DB
- Only PAID/SENT payouts stored; only COMPLETED payments stored
- Payout entries endpoint: `GET /v2/payouts/{id}/payout-entries`

---

## Supabase Notes

- URL: `https://ikhcbncnaojrndilmnnd.supabase.co`
- Access: service_role key only (set as `SUPABASE_SERVICE_KEY` env var or Streamlit secret)
- RLS: enabled on all tables, no policies → anon/authenticated keys blocked entirely
- Pagination: default limit 1000 rows. `db.py:_fetch_all_rows()` paginates.
- Upsert: `supabase.table(t).upsert(records).execute()` — uses PK on conflict
- In-filter URL limit: batch at ≤150 IDs per `.in_()` call

---

## Environment Variables / Secrets

All secrets read by `_get_secret(name)` helper in `db.py` and `sync.py`:
tries `st.secrets[name]` first (Streamlit runtime), falls back to `os.environ`.

| Variable | Used by |
|----------|---------|
| `SUPABASE_SERVICE_KEY` | db.py, sync.py |
| `SQUARE_TOKEN` | sync.py:sync_square |
| `WAVE_TOKEN` | sync.py:post_to_wave, post_loan_payments |
| `WAVE_BUSINESS_ID` | sync.py:post_to_wave, post_loan_payments |
| `WAVE_CLEARING_ACCOUNT_ID` | sync.py:build_wave_entries, post_to_wave |
| `WAVE_BANK_ACCOUNT_ID` | sync.py (included in accounts dict, not currently used in entries) |
| `WAVE_SALES_REVENUE_ID` | sync.py:build_wave_entries |
| `WAVE_TIPS_INCOME_ID` | sync.py:build_wave_entries |
| `WAVE_PROCESSING_FEES_ID` | sync.py:build_wave_entries |
| `WAVE_SALES_TAX_ID` | sync.py:build_wave_entries |
| `WAVE_SALES_RETURNS_ID` | sync.py:build_wave_entries |
| `WAVE_DISCOUNTS_ID` | sync.py:build_wave_entries |
| `WAVE_WEENIE_CLEARING_ID` | sync.py:post_loan_payments |
| `WAVE_WEENIE_NOTE_PAYABLE_ID` | sync.py:post_loan_payments |
| `WAVE_INTEREST_EXPENSE_ID` | sync.py:post_loan_payments |
| `APP_PASSWORD` | dashboard.py (shared login) |

Actual Wave account ID values (base64 strings) are in `SETUP.md` and `run_daily.ps1`.

---

## File Inventory

| File | Status | Notes |
|------|--------|-------|
| `sync_square.py` | Active CLI | SQLite, standalone |
| `post_to_wave.py` | Active CLI | SQLite, standalone |
| `post_loan_payments.py` | Active CLI | SQLite, standalone; import CSV with --import |
| `check_variances.py` | Active CLI | SQLite read-only, ~20 lines |
| `sync_wave.py` | Active CLI | Syncs Wave chart of accounts, imports CSV |
| `post_sams_correction.py` | Active CLI | Annual Sam's Club sales tax correction |
| `valuation.py` | Active CLI | Business valuation report (SDE/Revenue/Asset) |
| `db.py` | Dashboard | Supabase client + status queries |
| `sync.py` | Dashboard | Supabase-backed sync functions |
| `dashboard.py` | Dashboard | Streamlit UI |
| `migrate_to_supabase.py` | Done (one-time) | SQLite → Supabase migration, ~54K rows |
| `supabase_schema.sql` | Done (one-time) | Postgres schema, run in Supabase SQL Editor |
| `requirements.txt` | Streamlit Cloud | streamlit, supabase, requests |
| `.streamlit/secrets.toml` | Local dev | Gitignored — template with blank values |
| `.streamlit/config.toml` | Tracked | Dark theme config |
| `SETUP.md` | Docs | Detailed workflow + env var reference |
| `ProjectContext.md` | Docs (this file) | LLM handoff context |
| `run_daily.ps1` | Gitignored | Task Scheduler script with live tokens |
| `glizzness.db` | Gitignored | Local SQLite database |

---

## Deployment Status (as of 2026-06-17)

- [x] Supabase schema created
- [x] All ~54,773 rows migrated from SQLite to Supabase
- [x] RLS enabled, service_role-only access
- [x] `db.py`, `sync.py`, `dashboard.py` written
- [x] `requirements.txt` created
- [x] `.streamlit/secrets.toml` template created (gitignored)
- [ ] Fill actual API token values into `.streamlit/secrets.toml`
- [ ] Test dashboard locally (`streamlit run dashboard.py`)
- [ ] Deploy to Streamlit Community Cloud
- [ ] Set secrets in Streamlit Cloud app settings
- [ ] Share URL with James

---

## Known Gotchas

1. **Square `created_at` vs `arrival_date`:** Always fetch with a 7-day wider window;
   filter to `arrival_date` in Python.

2. **Wave `moneyTransactionCreate` liability restriction:** Can't use a liability account
   as a line item. Weenie Wagon principal reduction requires the liability as the ANCHOR
   with `direction: DEPOSIT` (which debits the liability = reduces balance).

3. **DEPOSIT_FEE entries:** `gross_cents` is negative, `fee_cents` is 0. Treat
   `abs(gross_cents)` as a fee. DO NOT use `fee_cents` for this type.

4. **Discounts restore gross revenue:** `gross_sales += sale_cents - tax_cents + disc_cents`
   so that CR Food Sales = pre-discount revenue, and DR Discounts = the reduction.
   This gives Wave correct revenue figures for P&L.

5. **Supabase 1000-row default limit:** Always paginate large table fetches.
   `_fetch_all_rows()` in `db.py` handles this. For `.in_()` calls, batch at ≤150 IDs.

6. **Wave externalId collision = idempotent:** If a posting fails partway through and
   is re-run, Wave rejects the duplicate externalId with `ALREADY_EXISTS`. The scripts
   treat this as success (entry was already posted in a prior run).

7. **Loan cutoff:** Payments on or before 2025-05-12 were entered manually in Wave.
   Both `post_loan_payments.py` and `sync.py:build_loan_entries` skip these.

8. **Supabase client singleton:** `db.py` caches the client in `_client`. If secrets
   change mid-run (rare), restart the Streamlit app to reset.
