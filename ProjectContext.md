# ProjectContext.md — Glizzness Accounting Automation
## LLM Handoff Document

> **Start here.** Read this entire file before touching any code. It contains
> hard-won business logic, critical gotchas, and incident history that are not
> obvious from the code alone. The companion file `SETUP.md` has step-by-step
> workflow instructions and CLI command reference.

---

## Project Overview

**Business:** The Glizzness LLC — a food truck operated by James Jason Trinton Johnson
("Trint") in Columbia, MO. He runs it solo.

**Consultant/Developer:** Lance McCarter (`lazrex` on GitHub).

**What this system does:** Pulls Square POS payout data into a cloud database,
computes double-entry journal entries, and posts them to Wave Accounting via
GraphQL API. Eliminates the need to manually split every "SQUARE INC SQ######"
bank deposit in Wave. Also tracks weekly Weenie Wagon truck loan payments.

**GitHub:** https://github.com/lazrexmc/glizzness (branch: `master`)

**Live dashboard:** Deployed on Streamlit Community Cloud (share.streamlit.io).
Trint uses it from anywhere. Password-protected (shared `APP_PASSWORD` secret).

---

## Current Status (as of 2026-06-17)

- Square sync: **working** — syncs payouts/entries/payments/orders into Supabase
- Wave posting: **working** — posts staged journal entries to Wave via GraphQL
- Loan payments: **working** — manual single-payment entry form in dashboard
- Financial Reports: **working** — Annual P&L, monthly bar chart, key metrics, expense breakdown
- Streamlit Cloud: **live and deployed** at share.streamlit.io (lazrexmc/glizzness)
- 2022–2024 books: **closed** — status='closed' in DB, hard date floor in code
- Known open issue: 2024-11-11 payout has status='error' (UNBALANCED, $42.26 gap) — investigate separately

---

## Architecture: Two Parallel Systems

### 1. CLI scripts (SQLite `glizzness.db`, local only)
`sync_square.py`, `post_to_wave.py`, `post_loan_payments.py`, `sync_wave.py`,
`check_variances.py`, `valuation.py`, `post_sams_correction.py`

Use these for ad-hoc CLI operations, historical backfills, and the Sam's Club
tax correction. They all read/write `glizzness.db` (SQLite, gitignored).

### 2. Dashboard modules (Supabase Postgres, cloud)
`db.py` — Supabase client + status/variance/financial queries  
`sync.py` — all sync/post/import functions (Supabase-backed)  
`dashboard.py` — Streamlit UI  

These are what Streamlit Community Cloud runs. No local SQLite needed.

---

## Data Flow

```
Square POS API
    ↓  sync_square.py (CLI)  OR  sync.py:sync_square() (dashboard)
Supabase (Postgres)  ←→  glizzness.db (SQLite, local CLI only)
    ↓  sync.py:build_wave_entries() then post_to_wave()
Wave Accounting (GraphQL API — write-only for transactions)

Wave Accounting (CSV export — only way to read transaction history)
    ↓  dashboard "Import Wave Transactions CSV" button
    ↓  sync.py:import_wave_csv()
Supabase: wave_transactions table
```

```
Bank statement (Trint looks up payment date + principal + interest)
    ↓  dashboard "Log Loan" button → entry form
    ↓  sync.py:post_single_loan_payment()
Supabase: loan_payments + loan_journal_entries
    ↓  two Wave transactions (interest + principal)
Wave Accounting
```

---

## Database Schema (12 tables, Supabase Postgres)

| Table | PK | Purpose |
|---|---|---|
| `payouts` | `payout_id` TEXT | Square payout header (one per bank deposit) |
| `payout_entries` | `entry_id` TEXT | Line items inside a payout (CHARGE/REFUND/DEPOSIT_FEE) |
| `payments` | `payment_id` TEXT | Square payment detail |
| `orders` | `order_id` TEXT | Square order (tax/discount totals) |
| `journal_entries` | `payout_id` TEXT | Wave entry per payout — status: staged/posted/closed/error |
| `journal_entry_lines` | `id` SERIAL | DR/CR lines for each journal entry |
| `wave_posts` | `payout_id` TEXT | Legacy tracker (superseded by journal_entries.status) |
| `wave_accounts` | `account_id` TEXT | Wave chart of accounts cache |
| `wave_transactions` | `row_key` TEXT | Wave CSV import rows (debit/credit per account) |
| `loan_payments` | `payment_date` TEXT | Weenie Wagon payment records |
| `loan_journal_entries` | `payment_date` TEXT | Loan entries — status: staged/posted/error |
| `sync_log` | `id` SERIAL | Audit log of each Square sync run |

Schema DDL: `supabase_schema.sql`

**Supabase notes:**
- URL: `https://ikhcbncnaojrndilmnnd.supabase.co`
- Access: `service_role` key only — RLS enabled, no policies → anon key blocked
- Default row limit: 1000 rows. Always paginate large fetches.
  `db.py:_fetch_all_rows()` handles pagination. For `.in_()` calls, batch ≤150 IDs.
- Upsert uses ON CONFLICT on PK. Duplicate PKs in the same batch cause errors —
  deduplicate before upserting (Square API sometimes returns duplicate payout IDs
  when paginating wide date ranges).

---

## Key Business Logic

### Square sales journal entry (per payout)

Built by `sync.py:build_wave_entries()` and `post_to_wave.py:build_entries()`:

```
DR  Square Settlements Clearing   payout_net_cents    ← anchor (DEPOSIT direction in Wave)
DR  Merchant Account Fees         fees_cents
DR  Customer Discounts            discounts_cents      ← only if > 0
DR  Sales Returns                 returns_cents        ← only if > 0
    CR  Food & Beverage Sales     gross_sales_cents
    CR  Tips Collected            tips_cents           ← only if > 0
    CR  Columbia Sales Tax        taxes_cents          ← only if > 0
```

**Payout entry type math** (each `payout_entry` record contributes to the totals):
- **CHARGE**: `gross_sales += sale_cents - tax_cents + disc_cents`
  (discount is added BACK to gross_sales so CR Sales = pre-discount revenue,
  DR Discounts = the reduction. This keeps Wave P&L correct.)
- **REFUND**: `returns += abs(e_gross)`
- **DEPOSIT_FEE**: `fees += abs(e_gross)` — this is Square's instant-deposit fee.
  Note: for DEPOSIT_FEE, `fee_cents = 0` and `gross_cents` is negative. Use
  `abs(gross_cents)` as the fee amount — DO NOT use `fee_cents`.
- All types: `fees += e_fee` (regular processing fee)

Balance check: `abs(total_DR - total_CR) <= 1` (1-cent rounding tolerance)

Wave `externalId`: `{payout_id}:clr` — prevents double-posting on re-run.
If Wave returns `ALREADY_EXISTS` or `DUPLICATE`, treat it as success.

### Clearing account pattern

The Wave public API cannot read or categorize existing bank imports. The solution:
"Square Settlements Clearing" (Other Short-Term Asset) is the API anchor.
- API posts a DEPOSIT (DR) to the clearing account
- Trint's manual bank categorization CREDITs clearing (one click per deposit)
- Net result: clearing account = $0, revenue accounts properly populated

### Loan payments (Weenie Wagon, ~$77.07/week)

Wave's `moneyTransactionCreate` cannot use a liability account as a line item.
Workaround: two transactions per payment date.

**Tx1 — Interest expense:**
```
Anchor: Weenie Wagon Loan Clearing  WITHDRAWAL  $interest
Line:   Interest Expense            DEBIT        $interest
```

**Tx2 — Principal reduction:**
```
Anchor: The First Weenie Wagon (liability)  DEPOSIT   $principal
Line:   Weenie Wagon Loan Clearing          CREDIT     $principal
```
`DEPOSIT` into a liability account = DR liability = reduces balance. This is
the only way to post a liability payment through the Wave API.

`externalId`s: `weenie-interest-{date}` and `weenie-principal-{date}`  
Stored in `loan_journal_entries.wave_entry_id` as `int:{wave_id}|pri:{wave_id}`

**Cutoff:** Payments on or before `2025-05-12` were entered manually in Wave.
All dashboard/script code skips payments on or before this date.

**Current workflow (dashboard):** Trint looks up the bank statement, sees the
payment date and the split (e.g., $65.38 principal / $11.69 interest), enters
it in the "Log Loan" form, clicks "Send to Wave." The form prevents re-posting
the same date.

---

## Closed-Year Protection (CRITICAL — read carefully)

**History:** In a prior session, the assistant told the user to "click Post to Wave"
after building entries. This caused 345 staged entries — including 2022–2024 closed
books — to be posted to Wave as duplicates. User deleted them manually.

**Two-layer protection added:**

1. **DB status = 'closed'**: `sync.py:close_year(year)` sets all journal entries for
   that year to status='closed'. `build_wave_entries()` skips both 'posted' AND
   'closed' entries. If only 'posted' is skipped, a Close Year run followed by
   Full Sync would rebuild and re-stage all those entries.

2. **Hard date floor in `post_to_wave()`**: `CLOSED_YEAR_CUTOFF = "2025-01-01"` —
   the function refuses to post any entry with `arrival_date < 2025-01-01` regardless
   of status. This is a code-level safety net that can't be bypassed from the UI.

**Rule:** Never tell the user to click "Post to Wave" without confirming which date
range they intend to post and that it doesn't include closed years.

**Current state:** 2022, 2023, 2024 are all marked closed in the DB.

---

## Wave API Notes

- Endpoint: `https://gql.waveapps.com/graphql/public`
- Auth: `Authorization: Bearer {WAVE_TOKEN}`
- Mutation: `moneyTransactionCreate` — one call per payout
- Amounts: dollar strings `f"{cents / 100:.2f}"`
- `externalId`: Wave deduplicates on this field. `ALREADY_EXISTS`/`DUPLICATE` = success.
- Anchor account is NOT included in `lineItems` — it auto-balances.
- Direction on anchor: `DEPOSIT` = DR (increase asset / decrease liability),
  `WITHDRAWAL` = CR (decrease asset)
- **Wave API is write-only for transactions.** `business.transactions` does not
  exist on the public API. Transaction history is only available via CSV export
  from Wave → Accounting → Transactions → Export.
- Wave GraphQL introspection: `introspect_wave.py` (CLI tool for exploring schema)

---

## Square API Notes

- Base URL: `https://connect.squareup.com/v2`
- Auth: `Authorization: Bearer {SQUARE_TOKEN}` + `Square-Version: 2025-01-23`
- Money: all amounts in **cents** (integers) — stored as cents in DB
- **Date filter quirk:** `/v2/payouts` filters by `created_at` in the API, but the
  useful date is `arrival_date` (when money actually arrived in bank). Workaround:
  fetch with a 7-day wider API window, filter by `arrival_date` in Python.
- Only PAID/SENT payouts stored; only COMPLETED payments stored
- Payout entries endpoint: `GET /v2/payouts/{id}/payout-entries`
- **Duplicate payout IDs:** Square sometimes returns the same payout ID in multiple
  pages when fetching a wide date range. Deduplicate by `payout_id` before upsert.

---

## Dashboard Features (current state)

### Status cards (top of page)
Four cards: Square (last payout date, staleness), Entries (unbuilt/errors),
Wave (staged/posted), Loan (unposted/errors). Auto-loads on page open; ↻ Refresh reloads.

### Expander controls
1. **Square sync date range** — begin/end dates for Sync Square button
2. **Wave post date** — minimum date for Post to Wave (hard min: 2025-01-01)
3. **⚠ Close a Year** — select year + confirmation checkbox → marks all entries 'closed'
4. **Import Wave Transactions CSV** — file uploader → calls `sync.py:import_wave_csv()`

### Action buttons
- **Sync Square** — pulls Square payouts/entries/payments/orders into Supabase
- **Build Entries** — computes Wave journal entries from Square data (no Wave API calls)
- **Post to Wave** — posts staged entries to Wave (respects wave post date picker)
- **Log Loan** — opens the loan payment entry form
- **Full Sync** — runs Sync Square → Build Entries → Post to Wave in sequence
- **Check Variances** — verifies payout totals match entry totals (shows table if any found)

### Loan payment form
Opened by "Log Loan" button. Fields: payment date, principal ($), interest ($).
Shows calculated total. "Send to Wave" calls `post_single_loan_payment()`.
Guards against double-posting the same date (raises ValueError if already posted).

### Financial Reports (bottom expander)
1. **Annual P&L table** — years as columns, rows: Gross Sales, Discounts, Returns,
   Net Sales, Sales Tax Collected, Tips Collected, Processing Fees, Loan Interest,
   Net to Bank, # Payouts
2. **Monthly revenue bar chart** — current year, Gross Sales by month
3. **Key metrics** — Avg Monthly, Annualized, Tip Rate, Processing Fee Rate
4. **Operating Expenses table** — rows: Loan Interest (from loan_journal_entries),
   + each Wave expense account (from wave_transactions × wave_accounts.type_value).
   Only shows if data is available; prompts to import Wave CSV otherwise.

---

## Wave CSV Import

Since Wave API is write-only, `wave_transactions` is populated by periodic CSV exports.

**Wave export:** Accounting → Transactions → Export → Transactions CSV  
**Dashboard:** Import Wave Transactions CSV expander → upload → Import to Supabase

`sync.py:import_wave_csv()` parses the Wave CSV format:
- Skips 4 metadata rows at top
- Handles account-name section headers (non-data rows with no amounts)
- Row key: `date|description|account|debit|credit`
- "Replace" checkbox drops rows from that source file and re-imports clean

The financial reports Operating Expenses section reads from `wave_transactions`
filtered to expense-type accounts (via `wave_accounts.type_value ILIKE '%expense%'`).
To get expense categories showing in the dashboard, import a Wave CSV.

---

## File Inventory

| File | Status | Notes |
|------|--------|-------|
| `sync_square.py` | Active CLI | SQLite, standalone Square sync |
| `post_to_wave.py` | Active CLI | SQLite, standalone Wave post |
| `post_loan_payments.py` | Active CLI | SQLite, standalone loan posts |
| `check_variances.py` | Active CLI | SQLite read-only variance check |
| `sync_wave.py` | Active CLI | Sync Wave accounts; import CSV |
| `post_sams_correction.py` | Active CLI | Annual Sam's Club tax correction |
| `valuation.py` | Active CLI | Business valuation report |
| `reset_entry.py` | Utility CLI | Reset a specific entry status |
| `reset_errors.py` | Utility CLI | Batch reset error entries |
| `debug_date.py` | Utility CLI | Date/payout debugging |
| `db.py` | Dashboard module | Supabase client + status/variance/financials queries |
| `sync.py` | Dashboard module | All Supabase sync/post/import functions |
| `dashboard.py` | Dashboard UI | Streamlit app — the main interface |
| `migrate_to_supabase.py` | Done (one-time) | SQLite → Supabase migration (54K rows) |
| `supabase_schema.sql` | Done (one-time) | Postgres schema DDL |
| `delete_wave_overpost.py` | Emergency tool | Deletes Wave transactions by payout ID + marks closed |
| `requirements.txt` | Streamlit Cloud | `streamlit`, `supabase`, `requests` |
| `.streamlit/secrets.toml` | Local dev only | **GITIGNORED — NEVER COMMIT** |
| `.streamlit/config.toml` | Tracked | Dark theme |
| `SETUP.md` | Docs | Workflow reference + CLI command cheatsheet |
| `ProjectContext.md` | Docs | This file — LLM handoff |
| `run_daily.ps1` | **Gitignored** | Task Scheduler script with live tokens |
| `glizzness.db` | **Gitignored** | Local SQLite database |
| `Sales/` | **Gitignored** | PDF sales reports |

---

## Environment Variables / Secrets

Read by `_get_secret(name)` in `db.py` and `sync.py`:
tries `st.secrets[name]` first (Streamlit), falls back to `os.environ`.

| Variable | Used by |
|---|---|
| `APP_PASSWORD` | dashboard.py — shared login password |
| `SUPABASE_SERVICE_KEY` | db.py, sync.py |
| `SQUARE_TOKEN` | sync.py:sync_square |
| `WAVE_TOKEN` | sync.py:post_to_wave, post_single_loan_payment |
| `WAVE_BUSINESS_ID` | sync.py:post_to_wave, post_single_loan_payment |
| `WAVE_CLEARING_ACCOUNT_ID` | sync.py:build_wave_entries — "Square Settlements Clearing" |
| `WAVE_BANK_ACCOUNT_ID` | sync.py accounts dict |
| `WAVE_SALES_REVENUE_ID` | sync.py — "Food & Beverage Sales" |
| `WAVE_TIPS_INCOME_ID` | sync.py — "Tips Collected" |
| `WAVE_PROCESSING_FEES_ID` | sync.py — "Merchant Account Fees" |
| `WAVE_SALES_TAX_ID` | sync.py — "Columbia Sales Tax" |
| `WAVE_SALES_RETURNS_ID` | sync.py — "Sales Returns & Allowances" |
| `WAVE_DISCOUNTS_ID` | sync.py — "Customer Discounts" |
| `WAVE_WEENIE_CLEARING_ID` | sync.py — "Weenie Wagon Loan Clearing" |
| `WAVE_WEENIE_NOTE_PAYABLE_ID` | sync.py — "The First Weenie Wagon" (liability) |
| `WAVE_INTEREST_EXPENSE_ID` | sync.py — "Interest Expense" |

The actual base64 Wave account ID values are in `.streamlit/secrets.toml` (local)
and in Streamlit Cloud app settings. They are NOT stored in tracked files.

---

## Critical Gotchas (read before writing any code)

### 1. Closed years — NEVER post 2022–2024
The 2022, 2023, 2024 books are finalized and closed. Do not post, re-build,
or modify journal entries for these years. Two safeguards are in place (see
"Closed-Year Protection" section above). If you see "345 to post to wave"
after a sync, do NOT tell the user to click "Post to Wave" — first check the
date distribution of staged entries.

### 2. DEPOSIT_FEE entries use `gross_cents`, not `fee_cents`
For payout entries with `type = "DEPOSIT_FEE"`: `fee_cents = 0` and
`gross_cents` is a negative dollar amount representing Square's instant-deposit
fee. Use `abs(gross_cents)` as the fee. Using `fee_cents` gives $0.

### 3. Discounts restore gross revenue
`gross_sales += sale_cents - tax_cents + disc_cents` — discount is added BACK
so that CR Food Sales = pre-discount revenue and DR Customer Discounts = the
reduction. This is intentional GAAP treatment. Do not "simplify" this.

### 4. Wave liability restriction
`moneyTransactionCreate` cannot include a liability account as a line item.
Weenie Wagon principal reduction uses the liability as the ANCHOR with
`direction: DEPOSIT` (DR liability = reduces balance). This is the only valid
pattern.

### 5. Square `created_at` vs `arrival_date`
Square's `/v2/payouts` API accepts `begin_time`/`end_time` which filters on
`created_at`, not `arrival_date`. Always fetch with a 7-day wider window and
filter to `arrival_date` in Python.

### 6. Supabase 1000-row default limit
Any query returning more than 1000 rows will be silently truncated. Always use
`.range(offset, offset + 999)` pagination for large tables. `db.py:_fetch_all_rows()`
handles this. For `.in_()` calls with many IDs, batch ≤150 per call.

### 7. Wave externalId = idempotent
If posting fails mid-batch and is re-run, Wave returns `ALREADY_EXISTS` for
already-posted entries. All posting code treats this as success (already done).

### 8. Loan cutoff date
`MANUAL_LOAN_CUTOFF = "2025-05-12"` — payments on or before this date were
entered manually in Wave and must never be processed by the scripts. All loan
code uses `.gt("payment_date", MANUAL_LOAN_CUTOFF)`.

### 9. build_wave_entries must skip 'closed' AND 'posted'
Only skipping 'posted' will cause the function to rebuild all closed-year entries
on the next run, creating thousands of queries and a connection drop. The skip
condition is: `status in ("posted", "closed")`.

### 10. wave_transactions debit/credit are dollars, not cents
The `wave_transactions` table stores amounts as floats (dollars) matching the
Wave CSV export format. The `journal_entries` amounts are in INTEGER CENTS.
Never mix them without conversion.

---

## Known Open Issues

- **2024-11-11 UNBALANCED entry**: `arrival_date = 2024-11-11`, status='error',
  DR=$1,676.22, CR=$1,633.96, $42.26 gap. Needs investigation. Since 2024 is a
  closed year, this entry is isolated and not affecting current operations.
  Do not modify it without a clear reason.

---

## Normal Weekly Workflow (Trint's perspective)

1. Open the Streamlit dashboard URL in any browser
2. Look at the four status cards
3. If Square is stale → **Sync Square**
4. If Entries shows unbuilt → **Build Entries**
5. If Wave shows staged → **Post to Wave**
6. If Loan shows unposted → **Log Loan**, enter principal + interest from bank statement
7. Periodically: export Wave CSV, upload via "Import Wave Transactions CSV"

Or just hit **Full Sync** (runs steps 3–5 automatically).

---

## Development Workflow (Lance's perspective)

- Edit on local machine: `streamlit run dashboard.py` (requires `.streamlit/secrets.toml`)
- `git push` to `master` → Streamlit Cloud auto-redeploys within ~60 seconds
- If Streamlit Cloud shows a stale version: reboot the app in the Streamlit Cloud dashboard
- CLI scripts still work with `glizzness.db` (SQLite) for ad-hoc work
- `run_daily.ps1` runs via Windows Task Scheduler at 9 AM daily (CLI path, SQLite)

---

## Vending Circuit (sub-project — food-truck event sourcing)

A separate effort from the accounting automation: a researched master list of festivals, fairs,
and food-truck-friendly events The Glizzness could vend at, within ~480 mi of Columbia.

A researched master list of **127 events** (124 published) feeds a live Supabase database and a
static web map. Distinct from the accounting automation but lives in the same repo + Supabase project.

**Deliverables (tracked in git):**
- `VendingCircuit.csv` — authoritative flat master, 127 events, 14 columns
  (gitignored `*.csv` rule has `!VendingCircuit.csv` + `!data/*.csv` exceptions — public event data, no financials)
- `VendingCircuit.md` — human-readable view, regenerated from the CSV, grouped by trip type
- `DATA_MODEL.md` — locked normalization spec (schema, enums, 17 market hubs, publish scope, status map)
- `vending_circuit_etl.py` — Phase 2 transform (flat CSV → `data/markets.csv` + `data/events.csv`)
- `vending_circuit_geocode.py` — Phase 3 geocode + schedule parse (→ fills lat/lng, `data/event_schedules.csv`)
- `data/markets.csv` (17), `data/events.csv` (127), `data/event_schedules.csv` (127)
- `supabase_vending_schema.sql` — DDL + `vending_published_events` gate view + public-read RLS
- `supabase_vending_data.sql` — generated INSERTs (17 + 127 + 127)
- `vending-map/` — static Leaflet map (index.html / app.js / config.js / README.md)

**Live data (Supabase, same project):** tables `vending_markets`, `vending_events`,
`vending_event_schedules`, `vending_sources` (stub), `vending_fees` (stub), view
`vending_published_events` (124 rows). Public-read RLS on `vending_*` only; accounting tables
remain anon-blocked. The map reads via the anon key (safe to expose).

**How the data was built:** 12 deep-research passes (3 foundational + 9 per-market regional), each
adversarially fact-checked. Lesson learned: run research workflows **one at a time** — firing many
in parallel trips the web-search rate limiter (9 concurrent failed; sequential succeeded clean).

**Regenerate the data pipeline:** `python vending_circuit_etl.py && python vending_circuit_geocode.py`
(then re-generate INSERTs if reloading the DB). Order matters: ETL before geocode.

**Run the map:** open `vending-map/index.html` (anon key already in `config.js`), or host the
`vending-map/` folder on GitHub Pages / Netlify. See `vending-map/README.md`.

**Keep data fresh (manual, no scheduler):**
- `python freshness_report.py` — offline punch-list (needs_confirmation / partial / past-year /
  `last_verified` >365 days). Run anytime to see what needs attention.
- ~Annually (Jan–Mar), trigger a re-date research pass on existing events, bump `LAST_VERIFIED`
  in `vending_circuit_etl.py`, regenerate (`etl` → `geocode` → `gen_sql`), and reload.
- Reload is idempotent: re-running `supabase_vending_data.sql` (truncate+insert) fully refreshes
  the DB — no patches. (Note: pins are city-level/approximate by design, not exact addresses.)

**Status / roadmap:**
- ✅ Phase 1 — publish scope + schema/enums locked (`DATA_MODEL.md`)
- ✅ Phase 2 — ETL (`vending_circuit_etl.py`; 0 dupes, all mapped, enums normalized)
- ✅ Phase 3 — geocoded 127/127 (city-level + jitter) + schedules parsed
- ✅ Phase 4 — loaded to Supabase; validation gate satisfied (17 / 127 / 127 / 124, all confirmed)
- ✅ Phase 5 — two-tier Leaflet map built + data path verified (markets→events→detail drawer, conditional homepage link)
- ⬜ Phase 6 — filters (month / food-truck-friendly / day-trip), defunct-toggle, marker clustering, mobile polish

**Workflow rule:** update docs + commit/push to `master` after each phase (checkpoint "just in case").
