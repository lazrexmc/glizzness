# Audit Log

This file is the durable audit trail for this repository. Future LLMs and engineers
should read it before making meaningful recommendations or code changes.

## How This File Works

- Treat this document as append-only audit history. Do not delete prior audits.
- Add new audits newest-last, using the template below.
- When code or operations change in response to an audit, add a follow-up entry under
  "Post-Audit Changes" with the date, changed files, and which findings were addressed.
- When re-auditing, explicitly compare current code against previous findings and mark
  each as: `Open`, `Mitigated`, `Fixed`, `Accepted Risk`, or `Obsolete`.
- Cite concrete file paths and line numbers. Avoid vague claims.
- If line numbers drift, cite the current line numbers and note that the prior audit line
  numbers were from an older revision.
- Do not paste secrets, tokens, private keys, raw financial CSV contents, or database dumps
  into this file. Refer to their paths and Git tracking status only.
- For financial findings, prefer exact cents and minimal reproducible examples.
- For security findings, distinguish between "committed to Git", "present locally but ignored",
  and "public by design".
- If a future LLM changes code after reading this audit, it should add a short
  "Post-Audit Changes" entry before ending the work session.

## Audit Entry Template

```markdown
## Audit YYYY-MM-DD - Short Title

### Scope

What was reviewed and why.

### Findings Status From Prior Audits

| Prior Finding | Status | Evidence |
| --- | --- | --- |
| Example | Open / Fixed / Mitigated / Accepted Risk / Obsolete | file:line |

### Severity-Ranked Findings

#### Critical

1. Finding title
   - Evidence: file:line
   - Impact:
   - Trigger / proof:
   - Recommendation:

#### High

#### Medium

#### Low

### Top Fixes Before Production

### Prioritized Test Plan

### Sign-Off Position

### Post-Audit Changes

- YYYY-MM-DD: No changes made during audit.
```

---

## Audit 2026-06-18 - Pre-Merge Repository Review

### Scope

Rigorous pre-merge audit of the repository as a two-part system:

1. Python financial-accounting automation for The Glizzness, LLC: Square to Wave
   journal-entry pipeline, Square/Wave sync into local SQLite and Supabase, loan-payment
   and tax-correction posters, Streamlit dashboard, reconciliation scripts, and valuation.
2. Vending Circuit sub-project: researched event dataset, ETL/geocode/SQL generation,
   Supabase vending tables, public anon-key Leaflet map.

Reviewed dimensions: security/secrets, financial correctness, vending data integrity,
general correctness, maintainability, docs drift, and operational risk.

No code changes were made during the audit.

### Severity-Ranked Findings

#### Critical

1. Dashboard/Supabase Wave posting path can post rows explicitly marked `error`.
   - Evidence: `sync.py:612` selects `journal_entries` with
     `.in_("status", ["staged", "error"])`; `build_wave_entries()` sets unbalanced rows
     to `"error"` at `sync.py:548`.
   - Impact: unbalanced or previously failed journal entries can be sent to Wave as real
     accounting transactions.
   - Trigger / proof: any payout where build computes `abs(total_dr - total_cr) > 1`
     becomes `status = "error"`, but dashboard "Post to Wave" still selects it.
   - Recommendation: post only `status = "staged"`; require explicit repair/rebuild for
     error rows.

2. Streamlit dashboard fails open if `APP_PASSWORD` is missing.
   - Evidence: `dashboard.py:29` only enforces the password gate if `APP_PASSWORD` has a
     value.
   - Impact: a misconfigured Streamlit deployment exposes dashboard actions backed by the
     Supabase service-role key and Wave/Square posting functions.
   - Recommendation: fail closed in deployed/non-local environments; require configured
     auth; add rate limiting or real identity provider auth.

#### High

3. Wave posting is not fully partial-run safe.
   - Evidence: Wave API call happens before DB status update at `sync.py:666`; DB status
     is updated after success at `sync.py:680`.
   - Impact: if the process dies after Wave accepts the transaction but before DB update,
     rerun relies on Wave duplicate `externalId` behavior. The duplicate path marks the row
     posted but does not persist `wave_entry_id` at `sync.py:690`.
   - Recommendation: persist `externalId` and a durable `posting` state before the API
     call; reconcile duplicate responses by external id; store the Wave transaction id when
     available.

4. Loan posting has the same `error`-row posting bug and uses floating-point money.
   - Evidence: `sync.py:767` selects loan rows with `.in_("status", ["staged", "error"])`;
     Supabase loan schema uses `DOUBLE PRECISION` at `supabase_schema.sql:130`;
     CLI loan schema uses `REAL` at `post_loan_payments.py:74`.
   - Impact: failed/unbalanced loan rows can be posted; penny drift is possible in loan
     totals and reports.
   - Recommendation: post only staged rows; store loan amounts as integer cents or Decimal;
     reject invalid money cells.

5. Missing order data can silently misclassify tax and discounts while staying balanced.
   - Evidence: build path falls back to empty order/payment maps at `sync.py:510` and then
     uses zero tax/discount at `sync.py:514`.
   - Impact: taxable sales can be recorded as revenue instead of tax liability with no
     imbalance to catch it.
   - Trigger / proof: payment amount 1080 cents, fee 30, payout 1050, missing order. Entry
     balances as DR clearing 1050 + DR fees 30 = CR sales 1080, but tax is not separated.
   - Recommendation: make missing orders/refund detail a hard build error for affected
     payments; reconcile against payout entry and order totals.

6. Supabase anon key is read-only for writes, but it can read all base `vending_*` tables,
   not only the published view.
   - Evidence: `supabase_vending_schema.sql:119` creates `select using (true)` policies on
     base vending tables; `vending-map/app.js:280` fetches `vending_events` directly.
   - Verification performed with committed anon key:
     - `GET /rest/v1/payouts?select=payout_id&limit=1` returned `[]` under RLS.
     - `POST /rest/v1/payouts` returned RLS error `42501`.
     - `GET /rest/v1/vending_events?select=id&limit=1` returned a row.
     - `POST /rest/v1/vending_events` returned RLS error `42501`.
   - Impact: hidden/excluded/unpublished vending rows and contact fields are public if they
     exist in base tables.
   - Recommendation: if only published rows should be public, grant anon select only on
     `vending_published_events` and make the map read that view.

#### Medium

7. Refund accounting is too coarse.
   - Evidence: refunds are recorded as `returns += abs(e_gross)` at `sync.py:526` and
     `post_to_wave.py:248`.
   - Impact: refunded tax/tips can be classified as sales returns instead of reversing tax
     liability or tips.
   - Trigger / proof: refund of a $10 item plus $0.80 tax records $10.80 as returns unless
     refund detail is split.
   - Recommendation: fetch refund/order breakdown and split sales, tax, tip, and fee
     effects explicitly.

8. Build/rebuild of journal entries is not atomic.
   - Evidence: row upsert happens at `sync.py:550`, then existing line items are deleted at
     `sync.py:565`, then new lines inserted at `sync.py:578`.
   - Impact: crash or API failure between steps can leave staged entries with no lines or
     stale metadata.
   - Recommendation: perform the rebuild in a transaction/RPC, or write a versioned set of
     lines then promote atomically.

9. Vending event IDs are unstable across refreshes.
   - Evidence: IDs are assigned by current deduped row order at
     `vending_circuit_etl.py:244`; SQL data load truncates/reinserts at
     `vending_circuit_gen_sql.py:38`.
   - Impact: any external references, URLs, analytics, or notes keyed by numeric event id
     can silently point to different events after reorder/add/delete.
   - Recommendation: use a stable slug/id from normalized name + city + state, or store a
     durable id in `VendingCircuit.csv`.

10. Vending classifiers are brittle substring rules.
    - Evidence: `verif()`, `event_type()`, and `food_friendly()` live at
      `vending_circuit_etl.py:156`.
    - Impact: small wording changes in notes/status can flip map color, verification
      badge, or event type.
    - Example: wording such as "not explicitly food trucks" and "food trucks are not
      allowed" depends on substring ordering and may not capture the intended negative.
    - Recommendation: move audited classification columns into source CSV or add tests for
      known tricky phrases.

11. Wave CSV and loan import paths use floats and silently coerce parse failures to zero.
    - Evidence: `sync_wave.py:184`, `sync.py:1017`, and `post_loan_payments.py:124`.
    - Impact: malformed CSV money cells can become `$0.00`; floating-point reports can
      drift.
    - Recommendation: use Decimal/cents parsing and fail loudly on invalid values.

#### Low

12. Git secret hygiene is mostly correct, but sensitive ignored files are present locally.
    - Evidence: `.gitignore` excludes DBs, `run_daily.ps1`, generic CSVs, and
      `.streamlit/secrets.toml`; `git ls-files` showed no financial DB/CSV/secrets tracked.
      Local ignored files observed: `glizzness.db`, `glizzness_reconciliation.db`,
      Wave transaction CSVs, `Weenie Wagon Transactions 6.9.26.csv`, `run_daily.ps1`, and
      `.streamlit/secrets.toml`.
    - Impact: Git is not currently leaking these files, but accidental upload outside Git
      remains a risk.
    - Recommendation: add pre-commit secret scanning and avoid putting real Wave account IDs
      in docs where practical.

13. Vending map uses `innerHTML`, but reviewed paths escape event fields.
    - Evidence: `vending-map/app.js:137` and `vending-map/app.js:194`; fields are passed
      through `esc()` at `vending-map/app.js:157`.
    - Impact: current XSS risk is controlled, but future edits can bypass escaping.
    - Recommendation: add a regression test with payloads like `<img src=x onerror=alert(1)>`.

14. Documentation drift exists.
    - Evidence: current CSV counts measured during audit were 31 markets / 380 events /
      380 schedules. `ProjectContext.md:473` still says generated SQL has 345 events and
      345 schedules; `ProjectContext.md:481` says `vending_published_events` has 342 rows;
      `supabase_vending_schema.sql:142` validation comments expect 345/342.
    - Recommendation: update docs after generated data refreshes and include a quick count
      command in the workflow.

### Security And Secrets Notes

- The committed Supabase anon key in `vending-map/config.js` and embedded copy in
  `vending-map/embed.html` is public by design.
- Accounting table RLS shape in `supabase_schema.sql` has RLS enabled with no policies.
  Anon REST reads returned empty rows and writes were blocked by RLS during audit.
- Vending tables are intentionally public-read in the committed schema. Writes were blocked
  by RLS during audit.
- No tracked DB, financial CSV, `.env`, `run_daily.ps1`, or `.streamlit/secrets.toml` was
  found via `git ls-files`.
- Local ignored sensitive files were present and should not be printed or committed.

### Top 5 Fixes Before Production

1. Stop posting `error` rows in Square and loan posting paths.
2. Add durable idempotency state around Wave calls: `staged -> posting -> posted/error`,
   with external id persisted before the API call.
3. Convert all financial storage/posting paths to integer cents or Decimal; reject invalid
   parses.
4. Make missing payment/order/refund detail a hard build error rather than zero-filled
   accounting.
5. Lock down dashboard auth fail-closed and add backup/restore strategy for `glizzness.db`
   and Supabase data.

### Prioritized Test Plan

1. Golden accounting tests with fixture Square payout JSON covering charge, tip, tax,
   discount, processing fee, refund, and deposit fee. Assert exact debit/credit lines in
   cents.
2. Idempotency tests for Wave success followed by DB-update failure, duplicate external id
   on rerun, and concurrent two-post simulation.
3. Error gating tests proving unbalanced/error entries cannot be selected for posting.
4. Missing-data tests proving missing order/payment/refund detail produces build error.
5. Loan tests for principal + interest cents math, interest-success/principal-failure
   recovery, and duplicate rerun.
6. Vending golden ETL tests proving stable IDs, expected market IDs, classifiers, geocodes,
   and SQL escaping for names such as `Huff 'n Puff`.
7. Security tests using the anon key to prove intended read-only/public scope and blocked
   accounting writes.
8. Dashboard smoke tests proving missing `APP_PASSWORD` fails closed in deployed mode.

### Docs Versus Reality

- `SETUP.md` was broadly aligned with current vending count expectations in the later
  vending section: 31 markets / 380 events / 380 schedules / 377 published.
- `DATA_MODEL.md` has current headline totals in later sections, but older checklist lines
  still mention 17 markets / 127 events / 124 published.
- `ProjectContext.md` has stale generated SQL/live Supabase counts in the vending section.
- `supabase_vending_schema.sql` validation comments are stale.

### Operational Risk

- `run_daily.ps1` exists locally and is ignored by Git. It runs `sync_square.py`,
  `post_to_wave.py --build $today`, then `post_to_wave.py --post $today`.
- The local script aborts on non-zero exit codes, but there is no durable distributed lock,
  no CI, no formal DB migration runner, and no backup/restore strategy documented for
  `glizzness.db`.
- Blast radius of a 2am failure depends on failure point. Before Wave post, likely a missed
  or staged entry. After Wave success but before local/Supabase state update, reruns rely on
  external-id duplicate behavior and may leave ambiguous local state.

### Sign-Off Position

I would not sign off on this running unattended against real money yet. The code has useful
idempotency intentions and sensible accounting structure, but the current dashboard posting
path can post rows explicitly marked `error`, loan/Wave-import money paths use floats, and
partial Wave-success failures can leave local state ambiguous. For real bank and tax data,
that is not an acceptable unattended risk profile.

### Post-Audit Changes

- 2026-06-18: Audit file created. No production code changed.
- 2026-06-18 (Claude review): Reviewed the audit and verified its concrete claims against
  current code. Spot-checks confirmed:
  - Finding 1 (Critical): CONFIRMED — `sync.py:553` sets `status="error"` when unbalanced;
    `sync.py:615` posting query selects `["staged","error"]`. (Partial mitigation: Wave's API
    rejects unbalanced DR/CR, so an `error` row likely fails at the API rather than corrupting
    books — but relying on the upstream provider is fragile. Agree it should post staged-only.)
  - Finding 2 (Critical): CONFIRMED — `dashboard.py:29` `if APP_PASSWORD:` skips the gate when
    the secret is absent (fails open). Real risk only in a deployed/non-local context.
  - Finding 6 (High): CONFIRMED design tradeoff — `supabase_vending_schema.sql` grants anon
    `select using (true)` on base tables and `vending-map/app.js` fetches `vending_events`
    directly so the defunct/excluded map toggle works. Practical impact LOW for this dataset:
    the exposed rows are public event listings and vendor-coordinator contacts already published
    on the festivals' own sites; no financial/PII exposure. Documented as Accepted Risk in
    ProjectContext.md. (To close fully: grant anon on `vending_published_events` only and drop the
    client-side defunct toggle.)
  - Finding 14 (Low — doc drift): FIXED. Updated DATA_MODEL.md (top-of-file 403 rows; gate view
    400; current-totals callout), SETUP.md (403/403/400), ProjectContext.md (headline + data-file
    + live-data counts), and the `supabase_vending_schema.sql` validation comments (expect 403 /
    403 / 400). Note: counts moved again after this audit was written — an interior gap-fill batch
    2 added +23 events (380 -> 403 total / 400 published) in the same session.
  - Findings 3-5, 7-13 (financial-pipeline + vending-pipeline hardening): NOT changed here —
    they require substantive accounting-code edits and belong in a dedicated remediation pass, not
    this docs/data session. They are accurate and should be prioritized per the Top-5 list. The
    unstable-vending-id (#9) and brittle-classifier (#10) items are already acknowledged in
    DATA_MODEL.md as known design risks.
  - Files changed this session beyond docs: VendingCircuit.csv + data/ + supabase_vending_data.sql
    (the +23 gap-fill events), add_gap_events.py, vending_circuit_etl.py, vending_circuit_geocode.py.
    No accounting-pipeline code touched.
