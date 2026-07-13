# Full-Repo Audit — The Glizzness LLC · 2026-07-13

**Method:** feedback-only (read-only) pass by 5 parallel auditors, one per cluster —
accounting/Square→Wave, menu pipeline, website, vending-map/calendar/SQL, and repo-hygiene/PII.
No file was changed, no `--apply`/network/DB write was run, `.claude/` and `..\PrivateData\`
were never touched. Conditions = the "FULL-REPO AUDIT" prompt agreed earlier in-session.

> **This document is the report only. No corrections have been made.** A batched correction
> gameplan is at the end, awaiting your approval before anything is touched.

---

## Executive summary

**Verdict: the systems are healthy; the repo's *hygiene* is not.** The menu pipeline is
**INTACT** (verified, not trusted — see below), no secret is committed anywhere, the accounting
code's June criticals are fixed and its tests pass, and the calendar privacy sanitizer is correct.

**The one urgent problem is exposure, not breakage:** the GitHub repo is **public**, and two
files that self-label "private/internal" are committed to it with **real third-party PII**. That,
plus a `.gitignore` bug that unprotects your personal essays and financial spreadsheets, is the
only thing I'd act on regardless of Tuesday's launch. **None of the findings block the DoorDash
go-live or the domain switch** — they're privacy + cleanup.

**Single most important fix:** get `Contacts.md` + `CorporateProspects.md` out of the public repo
(make the repo private, or untrack+move+scrub history), and fix `.gitignore:30-31`.

---

## Pipeline verdict: ✅ INTACT (verified)

- `python gen_menu.py` (dry-run) → `33 entries → 26 website / 7 hidden`, **no data problems.**
- `python push_menu.py` (dry-run) → **28 update (all "already in sync"), 0 create, 0 delete** — every
  item matched by `square_id`, no orphans, no duplicates.
- **P0 sync check PASS:** a fresh render was byte-compared against the live files — `site/our-menu.html`
  (MENU block) and `site/index.html` (TEASER block) are **byte-identical** to `menu.json`. The live
  site is not lying about the menu.

**Other positive confirmations (no action needed):**
- **No committed secrets.** Only Supabase **anon** keys appear in browser configs (decoded `role:anon`,
  public by design). No `service_role`/`WAVE_TOKEN`/`SQUARE_TOKEN`/Google service-account key committed.
- **No repo bloat / no PII in the DB path.** `.claude/` and `..\PrivateData\` are **not tracked**;
  `glizzness.db` (133 MB) and all financial CSVs are gitignored and **never entered git history**.
- **Accounting:** `pytest tests/` → **15 passed**; June audit criticals (auth fail-open, error-row
  posting) confirmed **FIXED** in code.
- **Calendar:** `sync_calendar.py` only surfaces title/location when `visibility == "public"`; every
  other case → "Booked — Unavailable." No private-event leak path.
- **Imagery rules respected:** real photos for product (cart/food); AI only for abstract backgrounds.

---

## Findings by severity

### 🔴 P0 — Exposure (act now, independent of go-live)

| # | File | Issue | Why it matters | Fix |
|---|---|---|---|---|
| P0-1 | `Contacts.md` (tracked) | Real third-party PII in the **public** repo — named HR / wellness / PR contacts across ~10 orgs with **direct phones + personal emails**, plus internal outreach notes & status. Header line 3 self-labels it *"INTERNAL (private repo — has phones/emails)."* | Privacy exposure of non-consenting third parties + a competitor-readable map of the whole sales pipeline. The file's own header proves this state is unintended. | Untrack + move to `..\PrivateData\`, **or** make the repo private. If the exposure window matters, purge from history. |
| P0-2 | `CorporateProspects.md` (tracked) | Same class — named HR contact (email+phone, line 37) + **sensitive commentary on named third parties** (e.g. "Veterans United… post-2022 layoffs", "REPEAT CLIENT… invoices on file"). Self-labels *"NOT public"* (line 3). | Same privacy + competitive exposure; reputationally sensitive notes about named companies are public. | Same as P0-1. |

> The auditor rated P0-2 as P1, but it's the same "private file in a public repo" class as P0-1, so
> it's grouped here. Both are remediated by the same action.

### 🟠 P1 — High (cleanup that matters)

| # | File:line | Issue | Fix |
|---|---|---|---|
| P1-1 | `.gitignore:30-31` | **Inline-comment bug** breaks `*.docx` and `*.xlsx` — git treats the trailing `# comment` as part of the pattern, so **neither ignores anything.** `HelpingPeople/*.docx` (5 personal essays) + any `SamsTransactions*.xlsx` are untracked **and unignored** → one `git add .` from a public commit. Verified via `git check-ignore`. | Put `*.docx` and `*.xlsx` each on their own line; move `HelpingPeople/` to `..\PrivateData\`. |
| P1-2 | `menu.html` (root, tracked) | **Duplicate menu** not generated from `menu.json` — contradicts the single-source model. Has **invented ingredients** ("secret recipe cheese sauce", "crispy onions"), "Columbia's finest hot dog **restaurant**" overclaim, and name drift **"Hoggin' Dog"** (rule: "Hog' N' Dog"). Superseded by generated `site/our-menu.html`. | Archive / `git rm`. |
| P1-3 | `catering.html` (root, tracked) | Superseded catering page carrying **banned operator-credentialing** — "…in collaboration with **our chef**", "**chef-guided** experience" (lines 511, 520). Superseded by `site/catering.html`. | Archive / `git rm`. |
| P1-4 | `catering/` folder (tracked) | Standalone Netlify catering microsite, superseded by `site/catering.html`. `catering/index.html:243` = **"Trint is a culinary-school chef"** (worst offender); `catering/MARKETING.md` repeats "chef-built", "Trint's culinary degree" across a **copy-paste-into-public marketing kit**. | Archive / `git rm` the folder (confirm nothing still deploys from it first). |
| P1-5 | `catalog_modifiers.py:31,33` | Still-active script (owns Square Add-Ons) has **stale keys**: `"Hog N' Dawg"` (now "Hog' N' Dog") and `"Walking Chips"` (renamed→retired). A future `--apply` would silently attach **no** add-ons to those items. | Rename key to `"Hog' N' Dog"`; drop the dead `"Walking Chips"` entry. |
| P1-6 | `reconcile.py:39,315-376` | Obsolete v1 prototype (separate `glizzness_reconciliation.db`, posts to Wave with a different `externalId` scheme and **no anchor**). Not wired to any automation, but a **latent double-post hazard** if ever run. | Archive (per `ARCHIVE_REVIEW.md §2`). |
| P1-7 | `run_daily.ps1` + dual-ledger | Legacy **SQLite** path (`sync_square.py`→`post_to_wave.py`) still exists beside the live **Supabase** dashboard path. Shared `externalId` + Wave dedup prevent an actual double-post, but the two ledgers drift. | Confirm the Task Scheduler job is **off**; retire the SQLite pipeline. |
| P1-8 | `sync.py:721,770` | Dead code — `build_loan_entries` / batch `post_loan_payments` imported nowhere (only `post_single_loan_payment` is used). | Delete, or wire a batch button. |
| P1-9 | `SETUP.md:320` | Doc drift — instructs clicking a **"Post Loans" button that does not exist** (only "Log Loan" does). | Fix the doc, or add the button. |
| P1-10 | `valuation.py:19,55` | Reads the **dormant** `glizzness.db` and uses a bad status filter (`'built'` never exists; `'staged'` counts un-posted as revenue) → silently reports stale/wrong figures while `SETUP.md` presents it as current. | Repoint at Supabase (or document as stale) + align the filter. |
| P1-11 | `DATA_MODEL.md:208-210` | Stale Phase-4 checklist — "127 events / 17 markets / 124 published" vs actual **415 / 31 / 410** (§5 line 147 already says 31; the SQL file was updated but this wasn't). | Update to 31 / 415 / 415 / 410. |
| P1-12 | `ARCHIVE_REVIEW.md` | The 2026-07-10 archive plan was **never executed** — "Nothing here is archived yet" is still true; every candidate above is still tracked. | Execute the plan (below), or delete it. |
| P1-13 | `site/README.md:9,107,109` | Still says **"scaffold, not deployed"** and lists Cloudflare deploy + "retire old pages" as open TODOs, though the site is live at glizzness.pages.dev. | Refresh. |
| P1-14 | `add_gap_events.py` | Spent one-shot (the 2026-06-18 gap sweep, already merged into the 415-row CSV; idempotent, appends 0 now). Not part of the re-runnable pipeline. | Archive (keep only for provenance). |

### 🟡 P2 — Medium (polish / lower-risk exposure)

| # | File:line | Issue | Fix |
|---|---|---|---|
| P2-1 | `AUDIT_LOG.md` (tracked) | Publishes a security audit of a money system with **OPEN findings** (#3/#5/#7/#8) — a "here are the soft spots" gift on a public repo. No secrets in it (disciplined), but the trail belongs private. Also **missing the 2026-07-10 audit entry** its own rules require. | Move DR/audit trail private; add the missing entry. |
| P2-2 | `REBUILD.md` / `GO_LIVE.md` | No secret *values*, but together they publish the security architecture — Supabase project ref, "RLS-on/no-policies" tables, where `service_role` lives, and `REBUILD.md:36` names the mailbox/phone as **"the master key… drive password-reset + 2FA for nearly every account"** — a social-engineering roadmap. | Trim the secret-map/"master key" specifics or host DR docs privately. |
| P2-3 | vending map: `supabase_vending_schema.sql:103,119-126` + `vending-map/app.js:297` | The "published view = gate" is documented as an access boundary but is **cosmetic**: the base table is `select using (true)` and the client reads `vending_events?select=*`, so the public anon key exposes **organizer contact_email/phone (~80–100 events)**, some personal. | Read the *view* in the client + drop the base-table read policy (make the gate real), or soften the comment to "intentionally public." |
| P2-4 | `ProjectContext.md` (multiple) | Internally contradictory drift — calendar "✅ ACTIVATED" (640) vs "not activated" (645); website "not deployed" (32) though live; catering "IN PROGRESS" + webhook listed as *future* (575,580) though **built**; "25 items" (607). Also exposes owner legal name + incident history (low risk). | Refresh, or add "superseded — see MENU_PIPELINE.md / CATERING_LEADS.md" pointers. |
| P2-5 | `GO_LIVE.md:10,13,68,70,3` | Menu-count drift ("20-item" / "25 items" → real **26 website / 28 Square**) + "not yet live" banner contradicts its own "✅ DEPLOYED 2026-07-12." | Update counts; reconcile banner. |
| P2-6 | `post_sams_correction.py:28-29` | Hardcodes `SAMS_TAX_ID`/`COGS_ID` instead of env vars (every sibling reads `os.environ`). | Move to `WAVE_SAMS_TAX_ID`/`WAVE_COGS_ID`. |
| P2-7 | `SETUP.md:57,76-78` | Real Wave account IDs (base64) in the public repo — not secrets (useless without the token) but leak the Wave business UUID. | Replace with placeholders as SETUP does elsewhere. |
| P2-8 | `post_loan_payments.py:223` | `--review` prints anchor as "WITHDRAWAL" but `post_entry` posts "DEPOSIT" (the code is correct; the review text is wrong). | Fix line 223 to "DEPOSIT". |
| P2-9 | `supabase_schema.sql:91,171` + `migrate_to_supabase.py:23,73` | `wave_posts` orphan table — created + RLS'd + migrated but read/written by no current code. | Drop it or document why retained. |
| P2-10 | `supabase_vending_data.sql` (469 KB, tracked) | Fully generated artifact (regenerable via `gen_sql`); duplicates the CSVs and is a drift trap if CSVs change without re-running. In sync now. | Keep (REBUILD loads it) with a "re-run gen_sql after any data edit" rule, or gitignore + regenerate on demand. |
| P2-11 | `vending_circuit_etl.py:15` | Stale comment "17 market hubs" but the MARKETS list below is 31. | Change to 31. |
| P2-12 | `site/order.html:64` | Stale copy — lists "**walking nachos**" (retired/consolidated to "Nachos") on a live page. | Change to "nachos". |
| P2-13 | `flyer/leave-behind.html:201-205` | Invented "crispy onions" + name drift ("Apple Sausage Brat"/"Walking Nachos"/"Street-Corn Elote") vs `menu.json`. (Correctly uses "Hog' N' Dog".) | Align to `menu.json` names/ingredients. |

### ⚪ P3 — Cosmetic

- `.gitignore` — add explicit `.pytest_cache/` line (currently only ignored via pytest's auto-written file).
- `catering-hot-dogs-50.html` — untracked **and** unignored (`??`), slated for retirement; delete locally.
- Vending event count inconsistent across docs — 415 (`GO_LIVE`/`REBUILD`) vs 403 (`ProjectContext`/`AUDIT_LOG`); pick one.
- `REBUILD.md` §8 doc index omits `CATERING_LEADS.md` (now built, has its own runbook) — add it.
- `post_to_wave.py:474` — bare invocation runs `--introspect` (a network call) instead of printing help.
- `supabase_vending_schema.sql:147` — confusing "+ 4 excluded" wording (math is right).
- `post_loan_payments.py:28` — docstring says cutoff 2025-05-13; actual is `> 2025-05-12`.
- `menu.json` — 5 retired tombstones linger (already gone from Square; harmless/self-documenting).
- `catalog_*.py` one-shot cleanup tools (cleanup/pass2/desc/tax/modifier_locations/delete_orphans) + `debug_date.py`/`reset_*`/`introspect_wave.py`/`check_variances.py` — obsolete, still tracked; some carry stale "Dawg" spellings (harmless only because dead). Archive with the SQLite sweep.

---

## Proposed archive manifest (nothing moved yet — awaiting approval)

Reversible via `git mv … archive/2026-07-13/` (preserves history) — **or** `git rm` if you'd rather
they leave the public repo entirely. **Confirm nothing still deploys from `catering/` first.**

**Superseded web pages:** `menu.html`, `catering.html`, `catering/` (whole folder), `catering-hot-dogs-50.html` (local).
**Dormant SQLite accounting pipeline:** `reconcile.py`, `valuation.py`, `debug_date.py`, `reset_entry.py`, `reset_errors.py`, `check_variances.py`, `introspect_wave.py`, `migrate_to_supabase.py`, and (owner action) the `run_daily.ps1` Task Scheduler job.
**Spent one-shot data tools:** `add_gap_events.py`, `catalog_cleanup.py`, `catalog_pass2.py`, `catalog_desc.py`, `catalog_tax.py`, `catalog_modifier_locations.py`, `delete_orphans.py`.
**Keep (still used):** `pull_catalog.py`, `catalog_modifiers.py` (fix its stale keys first), `gen_menu.py`, `push_menu.py`, the four `vending_circuit_*` generators, `sync.py`/`dashboard.py`/`post_to_wave.py` (live), `supabase_vending_data.sql`.

---

## Correction gameplan (batched — pick what to green-light)

Ordered by priority. **Go-live impact: none of these block Tuesday's DoorDash open or the domain
switch.** Batch A is urgent on its own privacy merits; the rest is cleanup.

- **Batch A — Public-repo exposure (URGENT).** Fix `.gitignore:30-31`; get `Contacts.md` +
  `CorporateProspects.md` (and `HelpingPeople/`) out of the public repo. *Decision needed:* make the
  **whole repo private** (instant, also covers AUDIT_LOG/REBUILD/ProjectContext exposure, works fine
  with Cloudflare Pages + Netlify) — **or** keep it public and **scrub** (untrack + move to
  `..\PrivateData\` + history purge). Private is the faster, more complete fix.
- **Batch B — Retire superseded public files.** Archive `menu.html`, `catering.html`, `catering/`
  (removes the "culinary-school chef" violations + invented-ingredient menu from the public repo).
- **Batch C — Small safe code fixes.** `catalog_modifiers.py` stale keys (P1-5), `post_loan_payments.py:223`
  review text, `post_to_wave.py:474` no-arg help, `post_sams_correction.py` env vars.
- **Batch D — Retire dormant SQLite accounting pipeline.** Archive `reconcile.py`/`valuation.py`/one-offs,
  remove `sync.py` dead loan funcs, confirm `run_daily.ps1` job off. (Touches "how the books work" —
  do carefully; confirm Supabase/dashboard is the canonical path.)
- **Batch E — Doc-drift refresh.** `SETUP.md`, `GO_LIVE.md`, `ProjectContext.md`, `DATA_MODEL.md`,
  `REBUILD.md`, `AUDIT_LOG.md`, `site/README.md`, vending-count reconcile, `order.html`/`flyer` menu copy.
- **Batch F — Vending map access (decision).** Make the "published gate" real (read the view + drop the
  base-table read policy) or soften the schema comment. Affects third-party organizer PII visibility.

---

## Green-light checklist (awaiting your approval — nothing done until you say)

1. Batch A exposure fix — **and** the private-vs-scrub decision.
2. Batch B retire superseded pages (confirm `catering/` isn't still deploying).
3. Batch C code fixes.
4. Batch D SQLite-pipeline retirement (confirm canonical path).
5. Batch E doc refresh.
6. Batch F vending gate decision.

**Nothing above has been changed. Reply with which batches to proceed on, on your terms.**
