# Archive — 2026-07-13

Retired per the `FOLDER_AUDIT_2026-07-13.md` correction plan (batches B + D), approved by the owner.
**Nothing is deleted — everything here is reversible.** Tracked files were moved with `git mv`
(history preserved); restore any with `git mv archive/2026-07-13/<path> <original-path>`.

## Batch B — superseded web pages (replaced by `site/`)

| Archived file | Why | Replaced by |
|---|---|---|
| `menu.html` | Old hand-maintained menu (duplicate source of truth; had invented ingredients + "Hoggin' Dog") | `site/our-menu.html` (generated from `menu.json`) |
| `catering.html` | Old catering page; carried banned "chef/culinary" copy | `site/catering.html` |
| `catering/index.html`, `catering/config.js`, `catering/netlify.toml` | Standalone Netlify catering microsite (deploy never completed) | `site/catering.html` (on Cloudflare Pages) |
| `catering-hot-dogs-50.html` | Earlier predecessor of the catering page (was untracked) | `site/catering.html` |

**Kept in `catering/`:** `MARKETING.md` (B2B kit — de-credentialed in this pass) and `README.md`
(Netlify base-dir + auto-reply notes), both still referenced by `GO_LIVE.md`.
**Kept at root:** `netlify.toml` — it still serves the **live vending map** at festivals.glizzness.com
(publishes `vending-map/`), so it is NOT legacy.

## Batch D — dormant SQLite accounting pipeline (replaced by the Streamlit/Supabase app)

Posting to Wave now happens only through `glizzness.streamlit.app` → `dashboard.py` → `sync.py` →
Supabase. The old local SQLite pipeline was dormant (owner posts only via the Streamlit app).

| Archived file | Why |
|---|---|
| `sync_square.py`, `post_to_wave.py`, `post_loan_payments.py` | The SQLite build/post pipeline driven by `run_daily.ps1` |
| `valuation.py` | Read the frozen `glizzness.db`; reported stale figures |
| `reconcile.py` | Obsolete v1 prototype (separate DB, no Wave anchor) — latent double-post hazard if run |
| `migrate_to_supabase.py` | One-time SQLite→Supabase migration, already done 2026-06-17 |
| `debug_date.py`, `reset_entry.py`, `reset_errors.py`, `check_variances.py`, `introspect_wave.py` | Dev/one-off tools that only touched the frozen SQLite DB |

Also removed (not archived — dead code inside a live file): `build_loan_entries()` and the batch
`post_loan_payments()` in `sync.py` (no callers; `post_single_loan_payment()` — the one the dashboard
uses — was kept).

**Kept (the live path):** `sync.py`, `dashboard.py`, `db.py`, `money.py`, `auth.py`,
`tests/test_accounting.py` (15 tests still pass), and `post_sams_correction.py` (annual Sam's-tax
correction; its hardcoded Wave account IDs were made env-overridable in this pass).

> ⚠️ **OWNER ACTION:** disable the `run_daily.ps1` Windows Task Scheduler job if it still exists —
> it drove the now-archived SQLite pipeline. (Kept apart from the live path only by Wave's
> `externalId` dedup; retiring the scripts means the scheduled task would now error.)
