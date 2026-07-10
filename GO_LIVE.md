# GO_LIVE.md — Bringing The Glizzness online

> **The master activation checklist.** Everything below is **built in the repo but not
> yet live.** Work top-to-bottom — later steps assume earlier ones are done. Each step
> says exactly what to click/run. Deep-dive docs are linked where they exist.
> Last updated: 2026-07-10.

## What's already built (so you know the state)
- **Website** — unified `site/` (Home, Menu, Order, Catering/Corporate, Where We Vend, 404). Browser-verified, **not deployed.**
- **Catering booking** — `catering/` standalone page **and** the newer `site/catering.html` (both POST to Supabase `catering_leads`). Keep the `site/` one; retire the standalone.
- **Vending map** — `vending-map/` (415 events), was on Netlify at `festivals.glizzness.com`.
- **Menu source of truth** — `menu.json` → `gen_menu.py` renders `site/menu.html`. `push_menu.py` (menu.json → Square → DoorDash) **NOT built yet.**
- **Where We Vend calendar** — `sync_calendar.py` + `cart_schedule` table + the `site/events.html` "Upcoming stops" list. **NEW — needs activation (§3).**

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
GoDaddy stays the **registrar only**; the site is hosted on **Cloudflare Pages**. Full notes: `site/README.md`.

1. **Push** the repo to GitHub (remote already set: `github.com/lazrexmc/glizzness`).
2. **Cloudflare Pages → Create project → Connect to Git** → pick the repo.
   - Framework preset: **None** · Build command: **(empty)** · **Build output directory: `site`**.
3. First deploy lands on `*.pages.dev`. **Verify there before any DNS change** — click every page, submit a test catering lead, check the Call/Text/DoorDash buttons and the top nav "Book Catering" (should be dark text on gold).
4. **Then** (separate, deliberate) point the domain: add `glizzness.com` (and `www`) as a custom domain in CF Pages, and update the DNS record at **GoDaddy**. *This is the only step that touches GoDaddy.*
5. `site/_redirects` handles friendly aliases (`/book`, `/delivery`, `/festivals`, …).

## 3. "Where We Vend" calendar — activate
Full step-by-step: **`CALENDAR_SETUP.md`**. Short version:
1. Run `supabase_schedule_schema.sql` (done in §1 if you ran it).
2. **Google service account:** Cloud Console → enable **Google Calendar API** → create a
   service account → create a **JSON key** → save it OUTSIDE the repo (e.g. `..\PrivateData\gcal-service-account.json`).
3. **Share the calendar read-only** with the service-account email (Calendar → Settings and
   sharing → "See all event details"). Grab the **Calendar ID**.
4. `pip install google-api-python-client google-auth requests`
5. Set env vars (`GOOGLE_SA_KEYFILE`, `GOOGLE_CALENDAR_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`),
   then `python sync_calendar.py --dry-run` → then `python sync_calendar.py`.
6. **Schedule it** (Task Scheduler, every 1–2h) so the site stays current.
7. **Trint marks public dates:** color a calendar event **green/"Basil"** → it shows publicly
   (venue + location). Any other color = shows only "Booked — Unavailable." Opt-in = never leaks.

## 4. Menu → Square → DoorDash
DoorDash pulls its menu **from Square**, so Square is the push target. `menu.json` is the source of truth. Full flow: `MENU_PIPELINE.md`.
1. **Build `push_menu.py`** (not built) — `menu.json` → Square (object-by-object, needs each
   object's current `version` from a fresh `catalog_export.json`, DRY-RUN default, `--apply`
   needs `SQUARE_TOKEN`). Honour `"retired": true`. **Lance runs `--apply` himself.**
2. **Delete the retired items in Square** (Dashboard, or via the push): **Turkey Link, Special
   Brat, Glizzy Classic**.
3. **Still-needed descriptions** (from Trint): **Something Fowl** ($7), **Taco** ($4 / Double $7).
   *Never invent ingredients.*
4. Once `menu.json` is clean: `python gen_menu.py --write` → refreshes `site/menu.html`
   (this swaps the old curated teaser for the real ~30 items — only do it when descriptions are in).
5. **DoorDash portal:** confirm the storefront `https://www.doordash.com/store/38788821` resolves
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
