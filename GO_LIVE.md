# GO_LIVE.md — Bringing The Glizzness online

> **The master activation checklist.** Everything below is **built in the repo but not
> yet live.** Work top-to-bottom — later steps assume earlier ones are done. Each step
> says exactly what to click/run. Deep-dive docs are linked where they exist.
> **Rebuilding from nothing after a disaster? See `REBUILD.md`.**
> Last updated: 2026-07-12.

## What's already built (so you know the state)
- **Website** — unified `site/` (Home, Menu, Order, Catering/Corporate, Where We Vend, 404). Browser-verified, **not deployed.**
- **Catering booking** — `catering/` standalone page **and** the newer `site/catering.html` (both POST to Supabase `catering_leads`). Keep the `site/` one; retire the standalone.
- **Vending map** — `vending-map/` (415 events), was on Netlify at `festivals.glizzness.com`.
- **Menu source of truth** — `menu.json` → `gen_menu.py` renders `site/our-menu.html` (**already regenerated & committed** — the site shows the full 20-item menu, verified byte-identical to a fresh render); `push_menu.py` (menu.json → Square → DoorDash) **is built.** `menu.json` is clean (25 items, all website items described). Only the Square push is left (§4).
- **Where We Vend calendar** — `sync_calendar.py` + `cart_schedule` table + the `site/events.html` "Upcoming stops" list (collapsible: next 3 + "Show all"). **✅ ACTIVATED 2026-07-11** — schema run, real sync done, page renders. Remaining: automate the sync (§7 Task Scheduler); it becomes publicly visible when the site deploys (§2).

---

## 1. Supabase — run the SQL (once each)
Supabase SQL editor → run these. Project: `https://ikhcbncnaojrndilmnnd.supabase.co`.

| File | What it creates | Notes |
|---|---|---|
| `supabase_schema.sql` | accounting tables | already live (don't rerun casually) |
| `supabase_catering_schema.sql` | `catering_leads` | needed for the booking form to save leads |
| `supabase_vending_schema.sql` **then** `supabase_vending_data.sql` | vending map tables + 415 events | schema FIRST (has the `one_time` CHECK), then data. Reload = idempotent truncate+insert |
| `supabase_contacts_schema.sql` | `contacts` (B2B) | only if you use the contacts pipeline |
| `supabase_schedule_schema.sql` | `cart_schedule` | **NEW** — the Where We Vend calendar (§3) |

**Verify:** after the vending reload, expect ~415 events / ~410 published. After catering,
`select count(*) from catering_leads;` returns a number (0 is fine).

## 2. Website — deploy `site/` to Cloudflare Pages
> **✅ DEPLOYED 2026-07-12** — live at **`glizzness.pages.dev`**, verified (home, menu from `menu.json`,
> live Where-We-Vend calendar + collapse, `_redirects` clean URLs, social/DoorDash wired). Deployed via
> **Cloudflare Pages → Connect to Git** (output dir `site`; the Workers/`wrangler` flow was the wrong path).
> **Remaining: custom domain** — point `glizzness.com` at Pages (step 4) once you're ready (careful: MX/email).

GoDaddy stays the **registrar only**; the site is hosted on **Cloudflare Pages**. Full notes: `site/README.md`.

1. **Push** the repo to GitHub (remote already set: `github.com/lazrexmc/glizzness`).
2. **Cloudflare Pages → Create project → Connect to Git** → pick the repo.
   - Framework preset: **None** · Build command: **(empty)** · **Build output directory: `site`**.
3. First deploy lands on `*.pages.dev`. **Verify there before any DNS change** — click every page, submit a test catering lead, check the Call/Text/DoorDash buttons and the top nav "Book Catering" (should be dark text on gold).
4. **Then** (separate, deliberate) point the domain: add `glizzness.com` (and `www`) as a custom domain in CF Pages, and update the DNS record at **GoDaddy**. *This is the only step that touches GoDaddy.*
5. `site/_redirects` handles friendly aliases (`/book`, `/delivery`, `/festivals`, …).

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
   it renders the full 20 website items (verified byte-identical to a fresh `gen_menu.py` render). Only
   re-run `python gen_menu.py --write` if you edit `menu.json` again.
2. **Push to Square (→ DoorDash):** `python push_menu.py` (dry run). As of this audit the diff is
   **22 updates, 0 creates, 0 deletes** — in practice just 5 description backfills (Sloppy Joe, Jackfruit,
   Chips, Water, Keychain). The three `retired` items (Chicken Teriyaki, the generic **Sides** item, and
   **Walking Nachos**) are **already gone from Square**, so nothing is deleted. Then **Lance** runs
   `python push_menu.py --apply` with `SQUARE_TOKEN`. If you changed add-ons, run order is
   `catalog_modifiers.py --apply` → `pull_catalog.py` → `push_menu.py`.
   > **Note:** Walking Nachos is intentionally **retired** (owner decision 2026-07-10) — off the site and
   > already gone from Square, so `--apply` deletes nothing. The live nachos item is `Nachos` (the boat).
3. **DoorDash portal:** confirm the storefront `https://www.doordash.com/store/38788821` resolves
   and shows "The Glizzness"; **exclude the "Cart Only" category** from DoorDash.

## 5. Retire the old / fragmented web
Once `site/` is live and verified:
- Delete/redirect the **GoDaddy builder homepage**.
- Retire the **root `menu.html` / `catering.html`**, **`catering-hot-dogs-50.html`**, and the
  **standalone `catering/` folder** (superseded by `site/`).
- Decide the **vending map**: migrate `vending-map/` to Cloudflare Pages (Netlify hit its cap),
  or keep it where it is and link from `site/events.html`.

## 6. Social & contact (already wired)
`site/assets/config.js` already has Facebook + Instagram URLs, phone `314-266-8636`, email
`glizzness@gmail.com`, DoorDash store `38788821`. Verify the links after deploy.

## 7. Post-launch
- **Schedules:** calendar sync (§3), and the Square→Wave accounting sync (`run_daily.ps1` via Task Scheduler).
- **Marketing push:** `catering/MARKETING.md` (social + B2B outreach kit); `CorporateProspects.md` + `Contacts.md` for the corporate lane.
- **Time-sensitive:** Show-Me State Games (call Jessie Sida 573-884-2946); Mizzou FY27 vending renewal (Casey Forbis / EHS).

---

## Quick smoke test (after deploy)
- [ ] Every page loads; nav "Book Catering" is **dark-on-gold** (readable) on all pages.
- [ ] Menu page: grill hero shows grates/flames (not just the black base).
- [ ] Catering: 8 packages in the 2-column base│upgrade layout; no price "bounce".
- [ ] Catering booking form submits → a row lands in `catering_leads`.
- [ ] Call / Text / Email buttons open the dialer / SMS / email pre-filled.
- [ ] DoorDash button points to the live store.
- [ ] Where We Vend: "Upcoming stops" renders (public dates + "Booked — Unavailable"), or the graceful "coming soon" fallback if the sync hasn't run.
