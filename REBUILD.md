# REBUILD.md — Disaster Recovery (rebuild The Glizzness from nothing)

> **"If something terrible happens."** This is the from-nothing runbook. It assumes the **GitHub repo**
> and the **`..\PrivateData\` folder** survived and *everything else is gone* — the Supabase project, the
> hosted sites, the machine, every login. Each subsystem has a deeper doc (linked in §8); this file is the
> **order to do things in**, the **account + secret map**, and the **cross-cutting traps**.
>
> This file is committed to a **private** GitHub repo (made private 2026-07-13) — it still contains **no secret values**, only where each
> secret lives and how to regenerate it. Keep it that way.
>
> Last updated: **2026-07-13**.

---

## What the system is (one paragraph)

The Glizzness runs on **one GitHub repo + one Supabase Postgres project + a few free hosts**. Five
subsystems: (1) the **public website** in `site/` on Cloudflare Pages; (2) the **menu pipeline**
`menu.json → gen_menu.py → site/our-menu.html` and `menu.json → push_menu.py → Square → DoorDash`;
(3) the **Where We Vend calendar** (Google Calendar → `sync_calendar.py` → Supabase → events page);
(4) the **festival map** (`vending_*` tables → Leaflet map at festivals.glizzness.com); (5) the
**accounting** (Square → Supabase → Wave, via a Streamlit dashboard). Every browser file uses **one public
`anon` Supabase key**; every server script uses **one secret `service_role` key**. Row-Level Security (RLS)
is what makes the anon key safe.

---

## 0 · Premise & survivors

- **Assume GONE:** the Supabase project, all hosted sites (Cloudflare Pages / Streamlit Cloud / legacy
  Netlify), the working machine, every service login, and every **gitignored** local file —
  `.streamlit/secrets.toml`, `glizzness.db`, `run_daily.ps1`, `catalog_export.json`, `past_cart_events.csv`.
- **Assume SURVIVES:** the GitHub repo `github.com/lazrexmc/glizzness` **and** the **`..\PrivateData\`**
  folder — a *sibling* of the repo (in the parent `James Jason Trinton Johnson\` dir) that holds the Google
  service-account JSON key, tax-portal logins, Etsy backup codes, etc.
- **The master key:** control of the shared mailbox **glizzness@gmail.com** and phone **314-266-8636** —
  they drive password-reset + 2FA for nearly every account below. **Recover the mailbox first.**

---

## 1 · Restore the workspace

```powershell
git clone https://github.com/lazrexmc/glizzness.git
# Place the recovered PrivateData folder as a SIBLING of the repo, so "..\PrivateData\" resolves:
#   ...\James Jason Trinton Johnson\Glizzness\    <- the repo
#   ...\James Jason Trinton Johnson\PrivateData\  <- secrets, OUTSIDE the repo
pip install requests supabase streamlit pandas google-api-python-client google-auth
```

`..\PrivateData\` being a **sibling** (not inside the repo) is load-bearing — scripts reference it that way,
and it keeps secrets out of git.

---

## 2 · Accounts to regain

| Account | What it's for | Recover via |
|---|---|---|
| **GitHub** (`lazrexmc/glizzness`) | source of truth; triggers Cloudflare + Streamlit deploys | github.com login (**private** repo — clone/pull/push all need a PAT/SSH key) |
| **Supabase** | the Postgres DB behind everything | supabase.com login → recreate project if gone |
| **Cloudflare** | Pages hosting for `site/` (and the migrated map) | dash.cloudflare.com |
| **GoDaddy** | domain **registrar only** for glizzness.com (DNS) | godaddy.com — touched only for the custom-domain step |
| **Google Cloud + Calendar** | service account + Calendar API feeding the events page | console.cloud.google.com + calendar.google.com (glizzness@gmail.com) |
| **Square** | POS; menu/catalog + accounting source | squareup.com + developer.squareup.com (Production token) |
| **Wave** | accounting destination ledger | waveapps.com |
| **DoorDash** | storefront `store/38788821` — a read-only mirror of Square | merchant portal |
| **Streamlit Community Cloud** | hosts the accounting `dashboard.py` | share.streamlit.io |
| **Netlify** *(legacy)* | old host of the map/catering — **being retired for Cloudflare**; don't rebuild | — |
| **Etsy**, **MyTax Missouri** | merch channel; sales-tax portal | logins/codes in `..\PrivateData\` |

---

## 3 · Secret & credential map

**Two Supabase keys, never swap them.** `anon` is public and lives in browser files; `service_role` is a
master key that bypasses RLS and must never appear in any tracked/browser file.

| Secret | Public? | Lives in | How to get / regenerate |
|---|---|---|---|
| `SUPABASE_ANON_KEY` | **public** | `site/assets/config.js`, `catering/config.js`, `vending-map/config.js` (committed) | Supabase → Project Settings → API → `anon public` |
| `SUPABASE_URL` | public | hardcoded in `db.py` (~line 8); the three `config.js`; env for `sync_calendar.py` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | **SECRET** | `.streamlit/secrets.toml` (gitignored) + Streamlit Cloud Secrets + shell env | Supabase → Project Settings → API → `service_role` |
| `SQUARE_TOKEN` | **SECRET** | shell `$env` (Lance's machine), `.streamlit/secrets.toml`, Streamlit Cloud, `run_daily.ps1` | Square Developer Dashboard → your app → **Production** Access Token (needs `ITEMS_READ`+`ITEMS_WRITE`) |
| `WAVE_TOKEN` | **SECRET** | `.streamlit/secrets.toml`, Streamlit Cloud, `run_daily.ps1` | Wave → Settings → Developer → Manage API tokens (full access) |
| `WAVE_BUSINESS_ID` | env-specific | same as above | Wave → Settings → Business (copy from URL) |
| `WAVE_*_ID` (11 account IDs) | env-specific | same as above | run `python sync_wave.py --sync-accounts`, then map each account **name** → id (names in `SETUP.md §3`) |
| `APP_PASSWORD` | **SECRET** | `.streamlit/secrets.toml` + Streamlit Cloud | operator-chosen (Lance + James). Unset ⇒ dashboard fails closed |
| `GOOGLE_SA_KEYFILE` | **SECRET** | `..\PrivateData\gcal-service-account.json` (outside repo); path via `$env` | Google Cloud → IAM → Service Accounts → Keys → Add key → JSON |
| `GOOGLE_CALENDAR_ID` | not secret | shell `$env` | Google Calendar → Settings and sharing → Integrate calendar → Calendar ID (glizzness@gmail.com) |
| GitHub push PAT/SSH | **SECRET** | OS credential manager / SSH agent | GitHub → Settings → Developer settings |

**Where secret *values* are NOT:** never in tracked files. `.gitignore` blocks `.streamlit/secrets.toml`,
`*service-account*.json`, `gcal-*.json`, `run_daily.ps1`, `.claude/`, `*.db`, and `*.csv` (except the
allow-listed `VendingCircuit.csv` / `data/*.csv`). The Supabase `service_role` key also historically sits in
agent memory under `.claude/` — that's exactly why `.claude/` is gitignored. On a real DR the project is
recreated, so **treat every old key as burned and regenerate.**

---

## 4 · Rebuild order (the critical path)

Everything reads Supabase, so build it first. Do these **in order**:

1. **Supabase** — create the project, run the schema SQL → **§5.1**
2. **Rewire the project ref** everywhere if the new Supabase URL differs from the old → **§5.1 (⚠)**
3. **Secret stores** — rebuild `.streamlit/secrets.toml` + paste into Streamlit Cloud + set shell env → **§3**
4. **Website** — deploy `site/` to Cloudflare Pages → **§5.2**
5. **Calendar** — Google service account + `sync_calendar.py` → **§5.3**
6. **Menu → Square → DoorDash** — `pull_catalog.py` → `gen_menu.py` → `push_menu.py` → **§5.4**
7. **Accounting** — deploy the Streamlit dashboard, re-sync from Square/Wave → **§5.5**
8. **Festival map** — load `vending_*` (442 events incl. 27 research prospects), deploy the map → **§5.6**
9. **Custom domain** — point glizzness.com at Pages (last, careful about email/MX) → **§5.7**

---

## 5 · Per-subsystem rebuild

### 5.1 Supabase (the foundation) — detail: `GO_LIVE.md §1`, `SETUP.md`, `DATA_MODEL.md`
1. Create a new project at supabase.com (region ~US Central). Store the DB password in `..\PrivateData\`.
2. Project Settings → API → copy **Project URL**, **anon** key, **service_role** key.
3. SQL Editor → run each schema **once, in this order** (the first four are non-destructive
   `CREATE TABLE IF NOT EXISTS`; only vending is order-sensitive):
   1. `supabase_schema.sql` (12 accounting tables; RLS **on, no policies** = service_role only)
   2. `supabase_catering_schema.sql` (`catering_leads`; anon **INSERT-only**)
   3. `supabase_contacts_schema.sql` (`contacts`; private)
   4. `supabase_schedule_schema.sql` (`cart_schedule`; anon **read-only**)
   5. `supabase_vending_schema.sql` (**DROPs+recreates** `vending_*`, the publish-gate view, RLS + SELECT policies)
   6. `supabase_vending_data.sql` (idempotent load: 31 markets / **442 events** = 415 circuit + 27 research
      prospects / 442 schedules — run **after** #5)
4. **⚠ Rewire the project ref** if the new URL differs from `ikhcbncnaojrndilmnnd`: update `db.py` (~line 8)
   and all three `config.js` (`SUPABASE_URL` + `SUPABASE_ANON_KEY`). The keys are
   JWTs bound to the project ref — old keys won't work on a new project, and the app silently talks to a dead
   project if you miss one. (The one-time `migrate_to_supabase.py` that also baked in the ref is **archived** —
   see `archive/2026-07-13/` — so it's no longer part of the rewire.)
5. Verify: in the SQL Editor, `select count(*) from vending_events;` → 442, `from vending_published_events;`
   → ~430. With the **anon** key, a fetch of `payouts` or `contacts` must return **nothing** (RLS working).

### 5.2 Website (Cloudflare Pages) — detail: `site/README.md`, `GO_LIVE.md §2`
1. Confirm `site/` has all pages + `_redirects` + `assets/`. There is **no build step** — no package.json, no
   wrangler.
2. Refresh `site/assets/config.js` if Supabase was rebuilt (new URL + anon key). Commit + push.
3. Cloudflare → **Workers & Pages → Create → Pages tab → Connect to Git** → repo `lazrexmc/glizzness`,
   branch `master`. **Framework preset = None · Build command = (empty) · Build output directory = `site`.**
   Save & Deploy → lands on `*.pages.dev`. **⚠ Use Pages + Connect-to-Git, NOT the Workers/`wrangler` flow**
   (the account UI funnels you to Workers — that's the wrong path for a static site).
4. Every push to `master` auto-redeploys. Verify on `*.pages.dev` before any DNS change (§5.7).

### 5.3 Where We Vend calendar — detail: `CALENDAR_SETUP.md`, `GO_LIVE.md §3`
1. `supabase_schedule_schema.sql` already run in §5.1.
2. Google Cloud → **enable Google Calendar API** → IAM → Service Accounts → create → **Keys → Add key →
   JSON** → save to `..\PrivateData\gcal-service-account.json`. Copy the SA email.
3. Google Calendar → Settings and sharing → **Share with specific people** → add the SA email → **"See all
   event details"**. Copy the **Calendar ID** (glizzness@gmail.com) from "Integrate calendar".
4. Set `$env:GOOGLE_SA_KEYFILE`, `$env:GOOGLE_CALENDAR_ID`, `$env:SUPABASE_URL`, `$env:SUPABASE_SERVICE_KEY`,
   then `python sync_calendar.py --dry-run` → `python sync_calendar.py`.
5. **Public trigger = event Visibility "Public"** (open event → Edit → "Default visibility" → Public). Not a
   color. Everything else renders "Booked — Unavailable".
6. **Automate it:** a small gitignored `.ps1` that sets the 4 env vars + runs the sync, registered in Windows
   Task Scheduler every 1–2h. Env vars don't persist, so the scheduled script must set them itself.

### 5.4 Menu pipeline (site + Square + DoorDash) — detail: `MENU_PIPELINE.md`, `GO_LIVE.md §4`
1. `SQUARE_TOKEN` = Production token (`ITEMS_READ`+`ITEMS_WRITE`) in **Lance's** PowerShell only.
2. If the Square catalog is gone: create the 6 categories (Glizzy, Not-a-Glizzy, Vegetarian, Sides, Drinks,
   Cart Only) + an enabled **7.975% "Sales Tax"** first (`push_menu.py` maps by category name + reads the tax id).
3. `python pull_catalog.py` → writes `catalog_export.json` (**required** by every catalog/push script; it's
   gitignored so it's absent after a clone).
4. Website leg (no token): `python gen_menu.py` (dry run → "No data problems found") → `python gen_menu.py
   --write` → commit → Cloudflare redeploys.
5. Square leg: `python push_menu.py` (dry run — review update/create/delete) → **Lance** runs
   `python push_menu.py --apply`.
6. **⚠ description_html:** Square Online + DoorDash display `description_html`, **not** the deprecated
   `description` field. `push_menu.py` sets both; if `description_html` is ever dropped, every customer-facing
   description goes blank (this was a real bug — fixed 2026-07-12). Verify with `pull_catalog.py`'s
   DESCRIPTION COVERAGE report and by checking the DoorDash store isn't blank.
7. Add-ons/tax only if changed: run order is `catalog_modifiers.py --apply` → `pull_catalog.py` →
   `push_menu.py` (re-pull between `--apply` steps). In the DoorDash portal, **exclude "Cart Only"**.

### 5.5 Accounting (Square → Wave via Streamlit) — detail: `ProjectContext.md`, `SETUP.md`
1. `supabase_schema.sql` already run (§5.1) — the 12 accounting tables, RLS-on-no-policies.
2. Ensure the **Wave chart of accounts** exists, then derive the 11 `WAVE_*_ID` values with
   `python sync_wave.py --sync-accounts` and map by account name.
3. Build `.streamlit/secrets.toml` (gitignored) with `APP_PASSWORD`, `SUPABASE_SERVICE_KEY`, `SQUARE_TOKEN`,
   `WAVE_TOKEN`, `WAVE_BUSINESS_ID`, and all 11 `WAVE_*_ID`.
4. Deploy: share.streamlit.io → New app → repo `lazrexmc/glizzness`, branch `master`, main file
   `dashboard.py`. **Paste the same secrets** into App Settings → Secrets (Streamlit Cloud does **not** read
   the repo file). Auto-redeploys on push (~60s).
5. Repopulate: in the dashboard, **Sync Square → Build Entries → Post to Wave** (closed-year floor =
   2025-01-01). Re-import pre-2025 history via **Import Wave CSV**.
6. **⚠ This is a Python server** — it runs on Streamlit Cloud, **not** Cloudflare Pages/Workers. Don't
   confuse it with the static site.
7. **⚠ Fix on rebuild:** the current secrets had `WAVE_SALES_RETURNS_ID` == `WAVE_DISCOUNTS_ID` (should be two
   distinct Wave accounts) — re-derive both cleanly.

### 5.6 Festival map — festivals.glizzness.com — detail: `vending-map/README.md`, `DATA_MODEL.md`
1. `vending_*` tables + data loaded in §5.1 (steps 3.5 + 3.6). Re-verify counts (31 markets / 442 events / ~430 published).
2. Set `vending-map/config.js` (`SUPABASE_URL` + `SUPABASE_ANON_KEY`). It reads the **raw** `vending_events`
   tables (client-side publish filter + an **event-type filter**), so those SELECT policies are load-bearing.
3. To regenerate data from the master CSV: `python vending_circuit_etl.py` → `vending_circuit_geocode.py` →
   `vending_circuit_gen_sql.py` → `vending_circuit_gen_md.py`, then re-run the vending SQL. (`geocode` is a
   built-in city→lat/lng dict, **not** an API — a brand-new city must be added to it or the event is dropped.)
   The **27 research prospects** (ids 500+, curated in `VENDING_PROSPECTS.md` from a 7-run deep-research sweep)
   come from a **separate loader**: `python build_prospects.py` writes `data/prospects.csv` +
   `data/prospect_schedules.csv`, and `vending_circuit_gen_sql.py` **folds them into**
   `supabase_vending_data.sql` automatically. Their new `event_type`s (mtb_gravel, sports_tournament, rodeo,
   car_show, air_show, dirt_track, winery, moto_rally) were added to the `event_type` CHECK enum in
   `supabase_vending_schema.sql` — extend that enum first if you add another type or the data load fails.
4. Host: a **separate** Cloudflare Pages project (same repo), **Build output directory = `vending-map`**.
   Then add the `festivals` subdomain (CNAME → the Pages target). **Not** Netlify (retired; `netlify.toml`
   is obsolete — see `ARCHIVE_REVIEW.md`).

### 5.7 Custom domain (glizzness.com) — detail: `GO_LIVE.md §2 step 4`
1. Verify on `*.pages.dev` first.
2. Cloudflare Pages project → Custom domains → add `glizzness.com` (+ `www`). Cloudflare shows the DNS target.
3. At **GoDaddy** (registrar only) update the DNS record. **⚠ Preserve existing MX/email records** — do not
   blanket-replace the zone, or email to glizzness@gmail.com / the domain breaks. This is the only step that
   touches GoDaddy. *(Still PENDING as of 2026-07-12 — site lives at glizzness.pages.dev.)*

---

## 6 · Cross-cutting traps (read before you start)

- **Cloudflare Pages ≠ Workers.** The CF UI pushes you to Workers/`wrangler`. For static sites use **Pages →
  Connect to Git**, output dir `site` (or `vending-map`). Wrong path = failed/blank deploy.
- **Hardcoded Supabase ref.** `SUPABASE_URL` is baked into `db.py` (not read from env there; the one-time
  `migrate_to_supabase.py` that also carried it is now archived). A rebuilt project has a new ref — update
  `db.py` + all three `config.js` or everything silently points at a dead DB.
- **RLS = on, no policies** for the 12 accounting tables + `contacts`. That's intentional: only `service_role`
  reads them. If you "helpfully" add a permissive policy you leak financials/PII; if you forget `ENABLE` the
  anon key exposes them.
- **anon vs service_role.** anon is safe in the browser *only* because RLS limits it (INSERT `catering_leads`,
  read `cart_schedule` + `vending_*`). service_role bypasses RLS — never in a `config.js`/tracked file.
- **`description_html`** is what Square Online + DoorDash show (not legacy `description`). `push_menu.py` must
  set it. `catalog_desc.py` only sets the legacy field — don't rely on it for the storefront.
- **`catalog_export.json` is gitignored** — absent after a clone. Run `pull_catalog.py` before any catalog/push
  script or they exit "not found".
- **Streamlit Cloud secrets are separate storage** — pasting into `.streamlit/secrets.toml` does nothing for
  the hosted app; paste the same block into share.streamlit.io → App → Settings → Secrets too.
- **Wave account IDs are `base64(account_id;business_id)`** — tied to the specific Wave business. Recreate the
  business → all 11 change → re-derive with `sync_wave.py --sync-accounts`.
- **Google SA is two-part:** the JSON key alone isn't enough — you must also (a) enable the Calendar API and
  (b) share the calendar read-only with the SA email.
- **`..\PrivateData\` is a sibling** of the repo, not inside it. Restore it there.
- **Netlify base-directory trap** (only if you ever use Netlify again): the root `netlify.toml` pins every
  build to `vending-map`; a second site must set **Base directory** in the UI, not just the publish dir.
- **Gitignored files never come back from git:** `run_daily.ps1` (live tokens), `glizzness.db`,
  `.streamlit/secrets.toml`, Wave transaction CSVs. Rebuild secrets from dashboards; rebuild data by re-syncing.
- **Vending schema is destructive:** `supabase_vending_schema.sql` DROPs the `vending_*` tables — re-running it
  wipes the data (reload via the data file). The `one_time` cadence CHECK must exist before the data inserts.
- **Vending `event_type` is a fixed allow-list:** the `event_type` CHECK in `supabase_vending_schema.sql`
  enumerates every valid type (music_fest, … + the 8 prospect types mtb_gravel, sports_tournament, rodeo,
  car_show, air_show, dirt_track, winery, moto_rally). A CSV row with a type not in it fails the **whole**
  data load — extend the CHECK before adding a new type.

---

## 7 · End-to-end verification

- [ ] Supabase SQL Editor: `vending_events`=442, `vending_published_events`≈430, `catering_leads` returns a number.
- [ ] anon key is **blocked** on `payouts`/`contacts`; **allowed** on `cart_schedule`/`vending_events`.
- [ ] `python -c "import db; db.get_client().table('payouts').select('payout_id').limit(1).execute()"` runs (service key OK).
- [ ] Website: every page on `*.pages.dev` loads; catering form submits a row into `catering_leads`; Where We Vend renders.
- [ ] Calendar: `sync_calendar.py --dry-run` prints "fetched N → M rows"; a Public event shows venue+location on the events page.
- [ ] Menu: `gen_menu.py` → "No data problems"; after `push_menu.py --apply`, Square + DoorDash descriptions are **not blank**.
- [ ] Accounting: `glizzness.streamlit.app` shows the password gate; the four status cards load; a Post to Wave doesn't duplicate.
- [ ] Festival map: the map's `*.pages.dev` loads clustered dots.
- [ ] `git ls-files | grep -Ei 'secrets.toml|service-account|run_daily'` returns **nothing** (no secret committed).

---

## 8 · Detailed docs (don't restate — link)

| Subsystem | Deep-dive doc |
|---|---|
| Bringing it all online (master checklist) | `GO_LIVE.md` |
| Supabase schema / data model | `DATA_MODEL.md`, `GO_LIVE.md §1` |
| Website | `site/README.md`, `GO_LIVE.md §2` |
| Where We Vend calendar | `CALENDAR_SETUP.md`, `GO_LIVE.md §3` |
| Menu pipeline | `MENU_PIPELINE.md`, `GO_LIVE.md §4` |
| Catering lead pipeline | `CATERING_LEADS.md` |
| Accounting (Square→Wave) | `ProjectContext.md`, `SETUP.md` |
| Festival map | `vending-map/README.md`, `DATA_MODEL.md` |
| Vending prospects (7-run deep-research sweep, ids 500+) | `VENDING_PROSPECTS.md` (curated) → `build_prospects.py` → `data/prospects.csv` |
| Event-history export (future demand baseline) | `pull_past_events.py` → gitignored `past_cart_events.csv` (analysis feeder, **not** a DR step) |
| What's safe to archive | `ARCHIVE_REVIEW.md` |
| Latest full-repo audit + what got archived | `FOLDER_AUDIT_2026-07-13.md` + `archive/2026-07-13/ARCHIVE_MANIFEST.md` |
