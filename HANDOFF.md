# HANDOFF.md — The Glizzness: full project onboarding (READ THIS FIRST)

You (a new engineer or LLM) just opened a big, multi-subsystem repo. This is the map. Read this top
to bottom, then dive into the linked deep-dive doc for whatever you're touching. **Do not guess — every
subsystem has a runbook.**

---

## 1. What this is

**The Glizzness LLC** — a Columbia, Missouri **hot-dog cart** (home of "the Glizzy," a ¼-lb all-beef dog).
- **Trint** (James Jason Trinton Johnson) — owner/operator/cook.
- **Lance McCarter** (`lazrexmc` / `lazrex`, lancemccarter1316@hotmail.com) — builds all the tech (this repo).
- GitHub: `github.com/lazrexmc/glizzness` — **PRIVATE** (made private 2026-07-13). Branch: `master`.
  Clone/pull/push need a PAT/SSH.

This repo holds **everything**: the public website, the menu→POS pipeline, catering lead capture, the
"where we vend" calendar, a food-truck-event prospecting map, the Square→Wave accounting automation, and
a pile of research/analysis tooling.

---

## 2. The subsystems (status + where to look)

| Subsystem | What it does | Status | Deep-dive doc | Key files |
|---|---|---|---|---|
| **Website** | The public `glizzness.com` site | ✅ **DEPLOYED** to Cloudflare Pages (glizzness.pages.dev); custom domain pending | `site/README.md`, `GO_LIVE.md §2` | `site/` (6 pages, `assets/site.css`, `site.js`, `config.js`) |
| **Menu pipeline** | `menu.json` is the source of truth → website + Square + DoorDash | ✅ SHIPPED & SYNCED (26 web / 28 Square) | **`MENU_PIPELINE.md`** | `menu.json`, `gen_menu.py`, `push_menu.py`, `pull_catalog.py`, `catalog_modifiers.py` |
| **Catering leads** | Booking form → DB → instant email alert | ✅ LIVE | **`CATERING_LEADS.md`** | `site/catering.html`, Supabase `catering_leads`, Make.com, Gmail |
| **Where We Vend calendar** | Google Calendar → sanitized Supabase → events page | ✅ ACTIVATED | `CALENDAR_SETUP.md` | `sync_calendar.py`, Supabase `cart_schedule`, `site/events.html` |
| **Festival / vending map** | 442-event food-truck prospecting map | ✅ LIVE on Netlify (festivals.glizzness.com) | `vending-map/README.md`, `DATA_MODEL.md` | `vending-map/`, Supabase `vending_*`, `data/*.csv`, `VendingCircuit.csv` |
| **Vending research + prospects** | 7-run deep-research → curated food-cart opportunities → onto the map | ✅ done; loads via SQL | **`VENDING_PROSPECTS.md`** | `build_prospects.py`, `data/prospects.csv`, `data/prospect_schedules.csv` |
| **Event history / demand baseline** | Past calendar events, for future "how many people" modeling | 🟡 captured, analysis pending | `TODO.md` (demand baseline) | `pull_past_events.py` → `past_cart_events.csv` (local, gitignored) |
| **Accounting (Square→Wave)** | Square payouts → GAAP journal entries → Wave | ✅ LIVE via Streamlit/Supabase | **`ProjectContext.md`**, `SETUP.md` | `dashboard.py`, `sync.py`, `db.py`, `money.py`, `auth.py`, `post_sams_correction.py` |
| **Freelance rate sheet** | Lance's own pricing collateral (not repo content) | ✅ published as a claude.ai Artifact | — | (scratchpad `rate-sheet.html`; do NOT commit to this repo) |

---

## 3. The single most important idea: `menu.json` is the bible

Decide the menu **in the repo**, in code review, where it can be diffed and rolled back. Nothing reaches a
customer until someone runs a command:
```
menu.json ──> gen_menu.py --write ──> site/our-menu.html + home teaser   (website)
          └─> push_menu.py --apply ──> Square ──> DoorDash                 (POS + delivery)
```
Never hand-edit the generated block in `site/our-menu.html`. **Lance runs `--apply` himself** (SQUARE_TOKEN
lives only in his shell). Gotcha: Square HTML-escapes `description_html`, so `push_menu.diff()` `html.unescape`s
before comparing — else apostrophe'd descriptions phantom-update on every push. Full detail: `MENU_PIPELINE.md`.

---

## 4. Runbooks index (which doc for what)

- **Bring it all online / activate** → `GO_LIVE.md`
- **Rebuild from nothing after a disaster** (accounts, secrets, order) → `REBUILD.md`
- **Menu → website + Square + DoorDash** → `MENU_PIPELINE.md`
- **Catering lead pipeline (Supabase→Make→Gmail)** → `CATERING_LEADS.md`
- **Where-We-Vend calendar** → `CALENDAR_SETUP.md`
- **Festival/vending map + data model** → `vending-map/README.md`, `DATA_MODEL.md`
- **Accounting (Square→Wave), business logic + gotchas** → `ProjectContext.md`, `SETUP.md`
- **Latest full-repo audit** → `FOLDER_AUDIT_2026-07-13.md` (+ `archive/2026-07-13/ARCHIVE_MANIFEST.md`)
- **What's safe to archive** → `ARCHIVE_REVIEW.md`
- **Open work / gameplans** → `TODO.md`

---

## 5. Secrets & accounts (values are NOT in git — see `REBUILD.md`)

Every browser file uses only the **public** Supabase `anon` key. Secrets (`service_role`, `SQUARE_TOKEN`,
`WAVE_TOKEN`, Google service-account JSON, Streamlit `APP_PASSWORD`) live only in gitignored files / the
operators' shells / the hosting dashboards. `.claude/` (agent memory, holds a service-role key) and
`..\PrivateData\` (PII) are **not tracked**. The full account + secret-location map is in `REBUILD.md`.

Hosting: **Cloudflare Pages** (website, output dir `site/`), **Netlify** (vending map, publish `vending-map/`),
**Streamlit Community Cloud** (accounting dashboard), **Supabase** (one project: accounting + `vending_*` +
`catering_leads` + `cart_schedule` + `contacts`), **Make.com** (catering email), **Square** (POS→DoorDash),
**Wave** (books), **GoDaddy** (domain registrar).

---

## 6. HARD RULES (do not violate — these are owner decisions)

- Spelling: always **"Dog"**, never "Dawg". The item is **"Hog' N' Dog"**.
- **Never invent menu ingredients/descriptions.** Never add operator-credentialing ("culinary-school chef").
  Never mention **the Elks** (dead deal). No "corporate" branding ("Catering & events", not "& corporate").
- **Imagery:** real photos only for anything depicting the product (cart/food); AI only for abstract
  backgrounds; never the cart manufacturer's marketing photo.
- **PII** (contacts, financials, client details, resumes) stays in `..\PrivateData\` (sibling of repo) or
  gitignored files — never committed. The repo is private now, but keep this discipline.
- **Commits/PRs: NO Co-Authored-By / attribution trailer** (also enforced in settings.local.json).
- **Lance runs every credentialed op himself** (`push_menu.py --apply`, Supabase loads, `pull_past_events.py`)
  — his tokens/keys never reach an agent's shell.
- **Work style:** stay on the explicit ask, no unsolicited tangents; be frank and disagree when warranted.

---

## 7. Open work (gameplans all live in `TODO.md`)

Near-term (owner): **custom domain** `glizzness.com` → Cloudflare (nameserver route; owner uses plain gmail
so no MX to preserve); **DoorDash go-live** + digital marketing push.

Backlog gameplans (each spec'd in `TODO.md`; **most say "evaluate Square-native first"**):
- **Trint's "Scout board"** — a phone-first yes/no/maybe triage feed over the vending prospects.
- **Inventory + reorder-point system** — common item master; purchase-SKU + recipe/BOM mapping; Wave IN /
  Square-Orders OUT.
- **Employee scheduling (takt-time)** — staff to demand at a fixed pace; add people, not speed.
- **Event-sales demand baseline** — match `past_cart_events.csv` to Square Orders (event capture done).
- **Unify subdomains** (festivals + streamlit) under glizzness.com; **food supplier**; map polish.

---

## 8. What happened in the big 2026-07-13 session (so history makes sense)

Menu overhaul + dynamic add-ons + brat rename + Square sync; `push_menu` phantom-diff fix; catering lead
pipeline built; a **5-cluster full-repo audit** (`FOLDER_AUDIT_2026-07-13.md`) → corrections applied, the
**repo made private**, legacy web pages + the dormant **SQLite accounting pipeline archived** to
`archive/2026-07-13/`, `run_daily.ps1` scheduler confirmed OFF; lots of site-copy fixes (See-Our-Menu button,
"three ways", de-corporate, catering rewords); a **7-run deep-research vending sweep** →
`VENDING_PROSPECTS.md` → **27 prospects mined onto the festival map** (442 events, new event-type filter);
**294 past calendar events captured** (`past_cart_events.csv`) for demand modeling; a freelance **rate sheet**
Artifact. See `git log` and `FOLDER_AUDIT_2026-07-13.md` for specifics.
