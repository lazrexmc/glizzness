# Glizzness — Accounting Automation Setup Guide

## Scripts overview

| Script | Purpose |
|--------|---------|
| `sync_square.py` | Download Square payouts / payments / orders into DB |
| `post_to_wave.py` | Build, review, and post Square sales journal entries to Wave |
| `sync_wave.py` | Sync Wave chart of accounts; import Wave CSV exports |
| `post_loan_payments.py` | Post Weenie Wagon loan payment splits to Wave |
| `post_sams_correction.py` | Post annual Sam's Club sales tax correction to Wave |
| `check_variances.py` | Verify all Square payouts balance to $0 |
| `valuation.py` | Business valuation report (SDE, Revenue, Asset-Based methods) |

---

## Step 1: Install Python dependencies

```powershell
pip install requests
```

---

## Step 2: Set environment variables

```powershell
$env:SQUARE_TOKEN     = "your_square_production_access_token"
$env:WAVE_TOKEN       = "your_wave_api_token"
$env:WAVE_BUSINESS_ID = "your_wave_business_id"
```

**Square token**: Square Developer Dashboard → your app → Production → Access Token
**Wave token**: Wave → Settings → Developer → Manage API tokens
**Wave Business ID**: Wave → Settings → Business — copy the ID from the URL

---

## Step 3: Wave account IDs

Run `python sync_wave.py --sync-accounts` to pull the chart of accounts into the DB.

### Square sales automation

| Env Var | Account |
|---------|---------|
| `WAVE_CLEARING_ACCOUNT_ID` | Square Settlements Clearing (Other ST Asset) |
| `WAVE_BANK_ACCOUNT_ID` | Checking (529) |
| `WAVE_SALES_REVENUE_ID` | Food & Beverage Sales |
| `WAVE_TIPS_INCOME_ID` | Tips Collected |
| `WAVE_PROCESSING_FEES_ID` | Merchant Account Fees |
| `WAVE_SALES_TAX_ID` | Columbia Sales Tax |
| `WAVE_SALES_RETURNS_ID` | Sales Returns & Allowances |
| `WAVE_DISCOUNTS_ID` | Customer Discounts |

```powershell
$env:WAVE_CLEARING_ACCOUNT_ID = "QWNjb3VudDoyNTUxMzY3NzMwMTA4MzQ1MjgzO0J1c2luZXNzOmJhMmQwOGFkLTNhNzUtNDkxOC1iZDljLTc4MWFlZmFkMzczNg=="
$env:WAVE_BANK_ACCOUNT_ID     = "QWNjb3VudDo..."
$env:WAVE_SALES_REVENUE_ID    = "QWNjb3VudDo..."
$env:WAVE_TIPS_INCOME_ID      = "QWNjb3VudDo..."
$env:WAVE_PROCESSING_FEES_ID  = "QWNjb3VudDo..."
$env:WAVE_SALES_TAX_ID        = "QWNjb3VudDo..."
$env:WAVE_SALES_RETURNS_ID    = "QWNjb3VudDo..."
$env:WAVE_DISCOUNTS_ID        = "QWNjb3VudDo..."
```

### Weenie Wagon loan automation

| Env Var | Account |
|---------|---------|
| `WAVE_WEENIE_CLEARING_ID` | Weenie Wagon Loan Clearing (Other ST Asset) |
| `WAVE_WEENIE_NOTE_PAYABLE_ID` | The First Weenie Wagon (Long-Term Liability) |
| `WAVE_INTEREST_EXPENSE_ID` | Interest Expense |

```powershell
$env:WAVE_WEENIE_CLEARING_ID     = "QWNjb3VudDoyNTUxODg3MzUwNTQ0MjQ3MTY1O0J1c2luZXNzOmJhMmQwOGFkLTNhNzUtNDkxOC1iZDljLTc4MWFlZmFkMzczNg=="
$env:WAVE_WEENIE_NOTE_PAYABLE_ID = "QWNjb3VudDoyMjQ1OTQzNTUwNTk4NDkxMDUwO0J1c2luZXNzOmJhMmQwOGFkLTNhNzUtNDkxOC1iZDljLTc4MWFlZmFkMzczNg=="
$env:WAVE_INTEREST_EXPENSE_ID    = "QWNjb3VudDoyMjQ1OTU4OTUxMzAyNjM4MjMwO0J1c2luZXNzOmJhMmQwOGFkLTNhNzUtNDkxOC1iZDljLTc4MWFlZmFkMzczNg=="
```

---

## Square sales — daily workflow

**One-time setup per new bank deposit:**
1. In Wave bank feed: change "SQUARE INC SQ######" category → "Square Settlements Clearing"
2. Run the post script (see below)

**New day's payout:**
```powershell
python sync_square.py                              # sync latest from Square
python post_to_wave.py --build <date>              # compute entry
python post_to_wave.py --review <date>             # verify
python post_to_wave.py --post <date>               # post to Wave
```

**Backfill a date range:**
```powershell
python sync_square.py 2025-01-01 2025-12-31
python post_to_wave.py --build 2025-01-01 2025-12-31
python post_to_wave.py --post  2025-01-01 2025-12-31
```

**Journal entry structure (per payout):**
```
DR  Square Settlements Clearing   $XXX.XX   anchor — nets to $0 against bank import
DR  Merchant Account Fees          $X.XX    Square processing fee
DR  Customer Discounts             $X.XX    (only if discounts)
DR  Sales Returns                  $X.XX    (only if refunds)
    CR  Food & Beverage Sales      $XXX.XX  gross pre-discount revenue
    CR  Tips Collected              $XX.XX  (only if tips > $0)
    CR  Columbia Sales Tax          $XX.XX  (only if tax > $0)
```

---

## Weenie Wagon loan — workflow

Loan: $77.07/week auto-drafted from Checking (529). Each payment splits into
principal (reduces The First Weenie Wagon liability) and interest (Interest Expense).

**First time / new CSV from lender:**
```powershell
python post_loan_payments.py --import "Weenie Wagon Transactions 6.9.26.csv"
python post_loan_payments.py --build
python post_loan_payments.py --review
python post_loan_payments.py --post
```

**In Wave:** categorize each "WEENIEWAGON-INTERNET" bank withdrawal →
"Weenie Wagon Loan Clearing" (one click each — clears the anchor).

**Journal entry structure (two Wave transactions per payment):**
```
Tx1 — Interest expense
  CR  Weenie Wagon Loan Clearing   $X.XX   anchor WITHDRAWAL → nets to $0 against bank import
      DR  Interest Expense          $X.XX

Tx2 — Principal payment (reduces loan liability)
  DR  The First Weenie Wagon       $XX.XX  anchor DEPOSIT (deposit-into-loan = pay down balance)
      CR  Weenie Wagon Loan Clearing $XX.XX → nets to $0 against bank import
```

Wave's `moneyTransactionCreate` does not allow liability accounts as line items.
The workaround is to anchor Tx2 on the liability itself with `direction: DEPOSIT`
(Wave treats deposit-into-loan as the payment direction: DR liability, CR clearing).

> Cutoff: payments through 2025-05-12 were entered manually. Script only
> processes payments on or after 2025-05-13.

---

## Sam's Club annual tax correction

Sam's charges Missouri food sales tax (5.975%) on purchases even though
Glizzness is tax-exempt. Run once per year after pulling the annual total
from Sam's Club purchase history website.

```powershell
# Preview (no changes)
python post_sams_correction.py --preview <sams_total> <year>

# Post to Wave
python post_sams_correction.py --post <sams_total> <year>
```

Example: `python post_sams_correction.py --post 16193.60 2025`

**Journal entry:**
```
DR  SamsTax2 - 5.975%     $XXX.XX   reduces sales tax liability
    CR  COGS - Food/Bev   $XXX.XX   removes tax from cost of goods
```

Entry date is always 12/31 of the year being corrected.

---

## Wave data sync

```powershell
python sync_wave.py --sync-accounts                         # refresh chart of accounts
python sync_wave.py --import-csv "file.csv"                 # import Wave CSV (warns if already imported)
python sync_wave.py --import-csv "file.csv" --preview       # dry-run: show counts without writing
python sync_wave.py --import-csv "file.csv" --replace       # clean re-import (use after corrections)
python sync_wave.py --status                                # row counts / date ranges
python sync_wave.py --list 2025-10                          # browse transactions
```

**To export from Wave:** Accounting → Transactions → Export → set date range → Download CSV

**After making corrections in Wave** (journal entries, depreciation, cash infusions, etc.):
1. Re-export the affected year's CSV from Wave
2. Run `--import-csv "file.csv" --preview` to see what changed (soft conflicts = corrections)
3. Run `--import-csv "file.csv" --replace` to apply the corrections cleanly

`--replace` drops all rows from that source file and re-imports fresh. Safe to run repeatedly.

---

## Schedule daily (Windows Task Scheduler)

`run_daily.ps1` is pre-built in this folder (gitignored — safe for tokens).
All Wave account IDs are pre-filled. You only need to set three secrets.

**First-time setup:**

1. Open `run_daily.ps1` and replace the three placeholders near the top:
   ```
   YOUR_SQUARE_PRODUCTION_TOKEN_HERE
   YOUR_WAVE_API_TOKEN_HERE
   YOUR_WAVE_BUSINESS_ID_HERE
   ```
   Square token: Square Developer Dashboard -> your app -> Production -> Access Token
   Wave token: Wave -> Settings -> Developer -> Manage API tokens
   Wave Business ID: Wave -> Settings -> Business -> copy ID from URL

2. Create the Task Scheduler task:
   - Open Task Scheduler -> Create Basic Task
   - Name: `Glizzness Daily Accounting`
   - Trigger: Daily, 9:00 AM
   - Action: Start a Program
     - Program: `powershell.exe`
     - Arguments: `-NonInteractive -File "C:\Users\lance\OneDrive\Desktop\MidMoConsultant\James Jason Trinton Johnson\Glizzness\run_daily.ps1"`

**What it does each run:**
1. Syncs latest Square payouts into glizzness.db
2. Builds the journal entry for today's payout date
3. Posts to Wave (duplicate guard prevents double-posting if re-run)

**Log file:** `run_daily.log` in this folder (gitignored). Check it if the task
fails — each step is timestamped with an `[ERROR]` tag on failure.

**If refunds start occurring:** create a "Sales Returns & Allowances" account
in Wave, then set `WAVE_SALES_RETURNS_ID` in `run_daily.ps1`.

---

## Business valuation

Run the valuation report at any time to get a snapshot of the business value
based on current DB data. No API calls — reads only from glizzness.db.

```powershell
python valuation.py              # summary report (basis: most recent full year)
python valuation.py --detail     # same but with extra breakdown (reserved)
python valuation.py --year 2024  # force a specific basis year
```

**Output sections:**
- Revenue (Square preferred for 2025+, Wave CSV for 2023-2024)
- P&L Summary (Revenue, COGS, Gross Profit, EBITDA, SDE add-backs)
- Balance Sheet (assets, equipment net book value, loan balance)
- Valuation: Method 1 SDE Multiple, Method 2 Revenue Multiple, Method 3 Asset-Based
- Data Completeness flags (uncategorized income/expense; years with no Square sync at all — closed years with synced payouts are not flagged)

**Keeping numbers current:** whenever you add journal entries, depreciation, or
corrections in Wave, re-export the affected year's CSV and run:
```powershell
python sync_wave.py --import-csv "The Glizzness, LLC Account Transactions 2025.csv" --replace
```
Then re-run `python valuation.py` to refresh the report.

---

## Streamlit Dashboard (cloud-accessible)

A browser-based dashboard that shows sync status and provides buttons to run each
step — accessible from any machine (phone, James's computer, etc.).

**Files:**
| File | Purpose |
|------|---------|
| `dashboard.py` | Streamlit UI — status cards, action buttons, run log |
| `db.py` | Supabase client, status queries, variance check |
| `sync.py` | Supabase-backed versions of all sync/post functions |
| `requirements.txt` | Python dependencies for Streamlit Cloud |
| `.streamlit/secrets.toml` | Local dev secrets (gitignored — never commit) |
| `.streamlit/config.toml` | Theme (tracked in git) |

**Run locally:**
```powershell
pip install streamlit supabase requests
streamlit run dashboard.py
```

**Deploy to Streamlit Community Cloud:**
1. Push repo to GitHub (already set up at github.com/lazrexmc/glizzness)
2. Go to share.streamlit.io → New app → select repo/branch → `dashboard.py`
3. In "Advanced settings → Secrets", paste the full contents of `.streamlit/secrets.toml`
4. Replace all placeholder values with real API keys/tokens
5. Share the app URL with James

**Secrets required (Streamlit Cloud → App Settings → Secrets):**
```toml
APP_PASSWORD = "a shared password for Lance and James"
SUPABASE_SERVICE_KEY = "..."
SQUARE_TOKEN = "..."
WAVE_TOKEN = "..."
WAVE_BUSINESS_ID = "..."
WAVE_CLEARING_ACCOUNT_ID = "..."
WAVE_BANK_ACCOUNT_ID = "..."
WAVE_SALES_REVENUE_ID = "..."
WAVE_TIPS_INCOME_ID = "..."
WAVE_PROCESSING_FEES_ID = "..."
WAVE_SALES_TAX_ID = "..."
WAVE_SALES_RETURNS_ID = "..."
WAVE_DISCOUNTS_ID = "..."
WAVE_WEENIE_CLEARING_ID = "..."
WAVE_WEENIE_NOTE_PAYABLE_ID = "..."
WAVE_INTEREST_EXPENSE_ID = "..."
```

**Dashboard workflow (normal weekly use):**
1. Open dashboard URL in browser
2. Check the four status cards — Square, Entries, Wave, Loan
3. If Square is stale → click **Sync Square**
4. If Entries shows unbuilt → click **Build Entries**
5. If Wave shows staged → click **Post to Wave**
6. If Loan shows unposted → click **Post Loans**
7. Or click **Full Sync** to run all four in one shot

---

## Supabase (hosted database)

All scripts can still use the local `glizzness.db` (SQLite) for CLI use.
The dashboard uses Supabase (Postgres) so it runs without a local database file.

- **Project URL:** `https://ikhcbncnaojrndilmnnd.supabase.co`
- **Schema:** `supabase_schema.sql` — run once in Supabase SQL Editor
- **Migration:** `migrate_to_supabase.py` — one-time SQLite → Supabase copy (done)
- **Access:** service_role key only; RLS enabled with no policies (anon key blocked)

---

## New machine setup

```powershell
git clone https://github.com/lazrexmc/glizzness
cd glizzness
pip install requests supabase streamlit
# set all $env: vars listed in Step 3
python sync_square.py 2023-01-01 2026-12-31     # rebuild Square DB
python sync_wave.py --sync-accounts              # rebuild Wave accounts
# import Wave CSVs for each year
# or just open the Streamlit dashboard URL — no local setup needed
```

---

## Vending Circuit (food-truck event map)

A separate sub-project: a researched, fact-checked list of 301 events (298 published; Missouri covered
statewide via a county-by-county sweep, plus regional metros incl. Indianapolis and the I-70/I-74/Louisville-Evansville
corridors; 31 market hubs) where
The Glizzness could vend, normalized into Supabase and shown on a static map. Full detail in
`ProjectContext.md` (Vending Circuit section) and `DATA_MODEL.md`.

**Data pipeline (regenerate the normalized files from the master CSV):**
```powershell
python vending_circuit_etl.py        # VendingCircuit.csv -> data/markets.csv + data/events.csv
python vending_circuit_geocode.py    # fills lat/lng + writes data/event_schedules.csv
python vending_circuit_gen_sql.py    # data/*.csv -> supabase_vending_data.sql (idempotent reload)
python vending_circuit_gen_md.py     # data/events.csv -> VendingCircuit.md (human view)
# (run in this order; ETL clears lat/lng, geocode refills it)
```

**Adding events (e.g. the Missouri county sweep):** append rows to `VendingCircuit.csv` (set
`county`, an estimated `distance_mi`, `month`, `typical_dates`, `status`, `last_verified`); if an
event is in a new town, add that town to `CITY_HUB` in `vending_circuit_etl.py` and to the `C`
centroid table in `vending_circuit_geocode.py`. Then run the four commands above and reload the DB.

**Reload the database (Supabase SQL Editor):**
1. Run `supabase_vending_schema.sql` (drops + recreates `vending_*` tables, gate view, RLS, the
   anon grant, and the `last_verified` column).
2. Run `supabase_vending_data.sql` (idempotent: `truncate … restart identity cascade` then inserts
   17 markets / 127 events / 127 schedules).
3. Validate: `select count(*) from vending_published_events;`  → expect **124**.

`supabase_vending_data.sql` is **idempotent** — re-run it alone anytime to refresh the data (no
need to re-run the schema unless table structure changed). Regenerate it after editing data with
`python vending_circuit_gen_sql.py`.

**Keep the data fresh (manual — no scheduler needed):**
```powershell
python freshness_report.py     # offline punch-list: what needs verifying / re-dating
```
~Once a year (Jan-Mar, when next-year dates publish): trigger a re-date research pass on the
existing events, set their per-row last_verified date in VendingCircuit.csv, then:
```powershell
python vending_circuit_etl.py
python vending_circuit_geocode.py
python vending_circuit_gen_sql.py
python vending_circuit_gen_md.py
# then re-run supabase_vending_data.sql in the SQL editor
```

**View the map:**
```powershell
# open vending-map/index.html in a browser, or serve the folder:
python -m http.server 8000   # then http://localhost:8000/vending-map/
```
The Supabase anon key is in `vending-map/config.js` (public-safe — RLS limits it to `vending_*`).
Deploy by hosting the `vending-map/` folder on GitHub Pages / Netlify. See `vending-map/README.md`.
