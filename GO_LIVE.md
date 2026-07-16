# GO_LIVE.md — Bringing The Glizzness online

> **The master activation checklist.** Most of this is now live — the **website is deployed**
> **🚀 LAUNCHED 2026-07-14** — the site is **LIVE at `glizzness.com` (+ www)**, the old GoDaddy builder is
> unpublished, and the catering pipeline is **verified end-to-end** (owner alert + customer auto-reply).
> **DoorDash go-live + the social/marketing rollout are underway.** (This runbook is now mostly historical;
> work top-to-bottom only if rebuilding.)
> **Rebuilding from nothing after a disaster? See `REBUILD.md`.**
> Last updated: 2026-07-13.

## What's already built (so you know the state)
- **Website** — unified `site/` (Home, Menu, Order, **Catering & events**, Where We Vend, 404; "corporate" branding was dropped site-wide, and the home page now leads with Order / See-Our-Menu / Book buttons + a "three ways to get your Glizzy" section). **✅ LIVE** at `glizzness.com` + `www` (Cloudflare Pages; custom domain switched 2026-07-14).
- **Catering booking** — `site/catering.html` → Supabase `catering_leads` → **lead-notification pipeline LIVE** (Supabase Database Webhook → Make.com → Gmail; see `CATERING_LEADS.md`). The old standalone `catering/` page was **archived 2026-07-13**.
- **Vending map** — `site/festivals/` (Leaflet), now **part of the main Cloudflare Pages site** — reachable at **`glizzness.com/festivals`** (`glizzness.pages.dev/festivals` until the custom domain switches). **Netlify is retired** (it used to host this at `festivals.glizzness.com`). Now **442 events** = 415 vending-circuit + **27 new research "prospects"** (7-run deep-research sweep — `VENDING_PROSPECTS.md`), with a **multi-select event-type filter** (every niche an on/off checkbox) plus a **⭐ Research picks** toggle on the map. Reload steps in §1.
- **Menu source of truth** — `menu.json` → `gen_menu.py` renders `site/our-menu.html` + the home teaser (byte-identical, verified); `push_menu.py` (menu.json → Square → DoorDash) is built and **synced**. `menu.json` = **26 website items / 28 live in Square**, all described (see `MENU_PIPELINE.md`).
- **Where We Vend calendar** — `sync_calendar.py` + `cart_schedule` table + the `site/events.html` "Upcoming stops" list (collapsible: next 3 + "Show all"). **✅ ACTIVATED 2026-07-11** — schema run, real sync done, page renders. Remaining: automate the sync (§7 Task Scheduler); it becomes publicly visible when the site deploys (§2).

---

## 1. Supabase — run the SQL (once each)
Supabase SQL editor → run these. Project: `https://ikhcbncnaojrndilmnnd.supabase.co`.

| File | What it creates | Notes |
|---|---|---|
| `supabase_schema.sql` | accounting tables | already live (don't rerun casually) |
| `supabase_catering_schema.sql` | `catering_leads` | needed for the booking form to save leads |
| `supabase_vending_schema.sql` **then** `supabase_vending_data.sql` | vending map tables + **442 events** (415 circuit + 27 prospects) | schema FIRST (has the `one_time` CHECK + the extended `event_type` enum), then data. Reload = idempotent truncate+insert |
| `supabase_contacts_schema.sql` | `contacts` (B2B) | only if you use the contacts pipeline |
| `supabase_schedule_schema.sql` | `cart_schedule` | the Where We Vend calendar (§3) |
| `supabase_scout_schema.sql` | `event_prospects` / `prospect_decisions` / `prospect_thread` | **Scout board** (§8). Then `python scout_seed_gen_sql.py` → run `supabase_scout_data.sql` to seed 23 prospects |
| `supabase_signals_schema.sql` | `event_signals` (+ allows `event_prospects.source='signal'`) | **Signal Net** (§8). Run *after* the scout schema |

**Verify:** after the vending reload, expect **442 events / ~430 published**. After catering,
`select count(*) from catering_leads;` returns a number (0 is fine).

**Reload the vending data** (after editing the circuit *or* the research prospects): regenerate with
`python build_prospects.py` (writes `data/prospects.csv` + `data/prospect_schedules.csv`) →
`python vending_circuit_gen_sql.py` (folds the prospects into `supabase_vending_data.sql`) → re-run
`supabase_vending_data.sql` in the SQL editor (idempotent truncate+insert). Full detail: `REBUILD.md §5.6`.

## 2. Website — deploy `site/` to Cloudflare Pages
> **✅ DEPLOYED 2026-07-12** — live at **`glizzness.pages.dev`**, verified (home, menu from `menu.json`,
> live Where-We-Vend calendar + collapse, `_redirects` clean URLs, social/DoorDash wired). Deployed via
> **Cloudflare Pages → Connect to Git** (output dir `site`; the Workers/`wrangler` flow was the wrong path).
> **✅ Custom domain DONE (2026-07-14):** `glizzness.com` + `www` live on Cloudflare — nameservers moved off GoDaddy; apex is a proxied CNAME-flattened record to `glizzness.pages.dev`. Gmail unaffected.

GoDaddy stays the **registrar only**; the site is hosted on **Cloudflare Pages**. Full notes: `site/README.md`.

1. **Push** the repo to GitHub (remote already set: `github.com/lazrexmc/glizzness` — now a **private** repo, so clone/pull/push need a PAT or SSH key).
2. **Cloudflare Pages → Create project → Connect to Git** → pick the repo.
   - Framework preset: **None** · Build command: **(empty)** · **Build output directory: `site`**.
3. First deploy lands on `*.pages.dev`. **Verify there before any DNS change** — click every page, submit a test catering lead, check the Call/Text/DoorDash buttons and the top nav "Book the Cart" CTA (should be dark text on gold).
4. **Then** (separate, deliberate) point the domain: add `glizzness.com` (and `www`) as a custom domain in CF Pages, and update the DNS record at **GoDaddy**. *This is the only step that touches GoDaddy.*
5. `site/_redirects` handles friendly aliases (`/book`, `/delivery`, …). `/festivals` is **not** a redirect — it serves the festival map directly from `site/festivals/`.

## 3. "Where We Vend" calendar — ✅ ACTIVATED 2026-07-11
**Done:** schema run, Google service account created + calendar shared read-only, real sync run (47 events
flow into `cart_schedule`), and `events.html` renders the collapsible "Upcoming stops" list. **Public
trigger = event Visibility "Public"** (not color). **Remaining:** automate the sync on a timer (§7); note it
only becomes *publicly* visible once the site is deployed (§2). Steps below kept for reference / re-running.
Full detail: **`CALENDAR_SETUP.md`**. Short version:
1. Run `supabase_schedule_schema.sql` (done in §1 if you ran it).
2. **Google service account:** Cloud Console → enable **Google Calendar API** → create a
   service account → create a **JSON key** → save it OUTSIDE the repo (e.g. `..\PrivateData\gcal-service-account.json`).
3. **Share the calendar read-only** with the service-account email (Calendar → Settings and
   sharing → "See all event details"). Grab the **Calendar ID**.
4. `pip install google-api-python-client google-auth requests`
5. Set env vars (`GOOGLE_SA_KEYFILE`, `GOOGLE_CALENDAR_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`),
   then `python sync_calendar.py --dry-run` → then `python sync_calendar.py`.
6. **Schedule it** (Task Scheduler, every 1–2h) so the site stays current.
7. **Trint marks public dates:** open the event → Edit → set **Visibility = "Public"** → it shows
   publicly (venue + location). Default / Private / Confidential = shows only "Booked — Unavailable."
   Opt-in = never leaks.

## 4. Menu → Square → DoorDash
DoorDash pulls its menu **from Square**, so Square is the push target. `menu.json` is the source of truth. Full flow: `MENU_PIPELINE.md`.
1. **Website menu — already done.** `site/our-menu.html` was regenerated from `menu.json` and committed;
   it renders the full **26 website items** (verified byte-identical to a fresh `gen_menu.py` render). Only
   re-run `python gen_menu.py --write` if you edit `menu.json` again.
2. **Push to Square (→ DoorDash):** `python push_menu.py` (dry run). The menu is currently **SYNCED** —
   the latest dry-run shows **28 update (all "already in sync"), 0 create, 0 delete** (every item matched by
   `square_id`, no orphans). So after a clean `pull_catalog.py` there's nothing to apply; only re-run
   `python push_menu.py --apply` (as **Lance**, with `SQUARE_TOKEN`) after you actually edit `menu.json`.
   Add-ons live in `menu.json`'s "addons" block and render on the website via `gen_menu.py`, but are **not**
   pushed to Square — `catalog_modifiers.py` owns Square's Add-Ons. If you change add-ons, run order is
   `catalog_modifiers.py --apply` → `pull_catalog.py` → `push_menu.py`.
3. **DoorDash portal:** confirm the storefront `https://www.doordash.com/store/38788821` resolves
   and shows "The Glizzness"; **exclude the "Cart Only" category** from DoorDash.

## 5. Retire the old / fragmented web
Once `site/` is live and verified:
- Delete/redirect the **GoDaddy builder homepage** — *still open* (do it during the domain switch, §2 step 4).
- ✅ **DONE (2026-07-13):** the **root `menu.html` / `catering.html`**, **`catering-hot-dogs-50.html`**, and
  the **standalone `catering/` folder** were archived to `archive/2026-07-13/` (superseded by `site/`; see
  `archive/2026-07-13/ARCHIVE_MANIFEST.md`).
- ✅ **DONE (2026-07-13):** the **vending map** was migrated off Netlify into the main Cloudflare Pages site —
  it now lives at `site/festivals/` and serves at `glizzness.com/festivals` (Netlify retired; the old root
  `netlify.toml` was archived to `archive/2026-07-13/`). `site/events.html` links to it.

## 6. Social & contact (already wired)
`site/assets/config.js` already has Facebook + Instagram URLs, phone `314-266-8636`, email
`glizzness@gmail.com`, DoorDash store `38788821`. Verify the links after deploy.

## 7. Post-launch
- **Schedules:** the **calendar sync** (§3, Task Scheduler every 1–2h) is the only automation to stand up.
  Accounting is **manual** now — post via the Streamlit dashboard (`glizzness.streamlit.app` → `dashboard.py`
  → `sync.py` → Supabase → Wave); the old `run_daily.ps1` local-SQLite scheduler was **retired 2026-07-13**
  (confirmed off; see `archive/2026-07-13/ARCHIVE_MANIFEST.md`).
- **Marketing push:** `catering/MARKETING.md` (social + B2B outreach kit); `CorporateProspects.md` + `Contacts.md` for the corporate lane.
- **Time-sensitive:** Show-Me State Games (call Jessie Sida 573-884-2946); Mizzou FY27 vending renewal (Casey Forbis / EHS).

## 8. Admin hub + Scout board + Signal Net — bring online (BUILT 2026-07-16, not yet deployed)
Gated private tools at `glizzness.com/hub` (login), `/scout` (Trint's triage), `/hub/desk` (Lance's
review), `/hub/signals` (crawler finds). Full detail: **`SCOUT_BOARD.md`** + **`SIGNAL_NET.md`**.
1. **Tables:** run `supabase_scout_schema.sql`, then `supabase_signals_schema.sql` (§1).
2. **Auth users:** Supabase → Authentication → Users → **Add user** ×2 (Trint + Lance, Auto-Confirm).
   Use emails starting `trint`/`lance` so the Q&A labels itself.
3. **Seed the board:** `python scout_seed_gen_sql.py` → run the generated `supabase_scout_data.sql`.
4. **Crawler secret:** repo → Settings → Secrets and variables → Actions → **New repository secret**
   `SUPABASE_SERVICE_KEY` = the Supabase **service_role** key.
5. **Deploy** rides the normal Cloudflare Pages push. Then GitHub → **Actions** → enable, and run
   **"Signal Net crawler" → Run workflow** once to seed the Signals feed.
6. **Verify:** open `/scout` logged-out → it bounces to `/hub` login (the gate works). Log in → the
   tiles, board, desk, and signals pages load. First crawler finds appear on `/hub/signals`.

---

## Quick smoke test (after deploy)
- [ ] Every page loads; nav "Book the Cart" CTA is **dark-on-gold** (readable) on all pages.
- [ ] Menu page: grill hero shows grates/flames (not just the black base).
- [ ] Catering: 8 packages in the 2-column base│upgrade layout; no price "bounce".
- [ ] Catering booking form submits → a row lands in `catering_leads`.
- [ ] Call / Text / Email buttons open the dialer / SMS / email pre-filled.
- [ ] DoorDash button points to the live store.
- [ ] Where We Vend: "Upcoming stops" renders (public dates + "Booked — Unavailable"), or the graceful "coming soon" fallback if the sync hasn't run.
