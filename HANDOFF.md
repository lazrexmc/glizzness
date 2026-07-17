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
| **Website** | The public `glizzness.com` site | ✅ **LIVE** at `glizzness.com` + `www` (Cloudflare Pages; custom domain switched 2026-07-14) | `site/README.md`, `GO_LIVE.md §2` | `site/` (6 pages, `assets/site.css`, `site.js`, `config.js`) |
| **Menu pipeline** | `menu.json` is the source of truth → website + Square + DoorDash | ✅ SHIPPED & SYNCED (26 web / 28 Square) | **`MENU_PIPELINE.md`** | `menu.json`, `gen_menu.py`, `push_menu.py`, `pull_catalog.py`, `catalog_modifiers.py` |
| **Catering leads** | Booking form → DB → instant email alert | ✅ LIVE | **`CATERING_LEADS.md`** | `site/catering.html`, Supabase `catering_leads`, Make.com, Gmail |
| **Where We Vend calendar** | Google Calendar → sanitized Supabase → events page | ✅ **LIVE + SELF-UPDATING** (GitHub Actions every 2h; verified in cloud 2026-07-16). `/events` is trustworthy → **the "check the website" marketing CTA is SAFE.** `PrivateData\sync-calendar.ps1` = the manual "push it live NOW" button | **`CALENDAR_SETUP.md`** | `sync_calendar.py`, `.github/workflows/calendar.yml`, `requirements-calendar.txt`, Supabase `cart_schedule`, `site/events.html` |
| **Midwest Event Finder** | Public finder for Midwest events to vend at / attend (rebranded from the "vending circuit map"; private research picks excluded → they seed the Scout board) | ✅ LIVE at `glizzness.com/festivals` (ships with the Cloudflare Pages site) | `site/festivals/README.md`, `DATA_MODEL.md` | `site/festivals/`, Supabase `vending_*`, `data/*.csv`, `VendingCircuit.csv` |
| **Vending research + prospects** | 7-run deep-research → curated food-cart opportunities → onto the map | ✅ done; loads via SQL | **`VENDING_PROSPECTS.md`** | `build_prospects.py`, `data/prospects.csv`, `data/prospect_schedules.csv` |
| **Admin hub + Scout board** | Gated cockpit (`/hub`) → Trint's phone-first event-triage card board (`/scout`, Yes/Maybe/No + ask) + Lance's review desk (`/hub/desk`) | ✅ **LIVE 2026-07-16** — audited + Phase-A-hardened, deployed, Lance logged in and verified. 23 prospects seeded. **RLS verified live:** anon key gets `42501` on all private tables | **`SCOUT_BOARD.md`**, `SCOUT_AUDIT.md`, `docs/.../2026-07-13-scout-board-design.md` | `site/hub/`, `site/scout/`, `assets/scout.js`+`scout.css`, `assets/vendor/supabase.js`, `supabase_scout_schema.sql`, `scout_seed_gen_sql.py` |
| **Signal Net (events crawler)** | Always-on GitHub Actions aggregator polls 10 curated local sources every 4h → finds → Signals feed (`/hub/signals`); Keep = a Scout prospect | ✅ **LIVE 2026-07-16** — running in the cloud; first real run inserted **178 signals** from 10 sources (Cooper's Landing, Mizzou, Blue Note, Rose, Stephens, Bur Oak, KOMU/Missourian/Vox, r/columbiamo) | **`SIGNAL_NET.md`**, `docs/.../2026-07-16-signal-net-design.md` | `crawler/`, `.github/workflows/crawler.yml`, `supabase_signals_schema.sql`, `site/hub/signals.html` |
| **Post Cards** | Drafts 2 social posts (night-before + morning-of) per **public** stop + a weekly roundup; Lance approves → copies → pastes into Meta Business Suite. Fixes posts going out *as the cart arrives* | ✅ **LIVE 2026-07-16** (schema run). No cron/secret — copy is generated client-side from `cart_schedule` | **`POST_CARDS.md`** | `site/hub/posts.html`, `supabase_posts_schema.sql` |
| **Demand baseline (the "brain")** | 4 yrs of Square sales (15,407 orders → 639 sessions) → per-venue/per-type profiles: **crew + prep on Trint's cards** ("Crew: 1–2 · Prep: Glizzy ×18"). Headline: only 27% of sessions match the calendar; the orphan 73% carry 69% of revenue — so sales are the spine | ✅ **LIVE 2026-07-16** — schema + data run, owner verified 10 profiles | **`DEMAND_BASELINE.md`** | `demand_baseline.py`, `site/assets/demand.js`, `Sales/items-*.csv` + `past_cart_events.csv` (local, gitignored) |
| **Lunch-rush / worksite prospects** | 17 verified big-employer targets (VU ~2,800, Paris Rd 4-plant corridor run, I-70 night crews →2029…) seeded onto the Scout desk — the "post up on the curb" lane; the crawler can't find employers | ✅ **SEEDED 2026-07-16** — owner verified 17 rows on the Desk | `CorporateProspects.md` (the source research) | `supabase_lunch_prospects.sql` |
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

- **Explain this system to a NON-technical person** (client/prospect-facing, zero jargon) → **`SYSTEM_PLAIN_ENGLISH.md`**
- **Build this pattern again for a DIFFERENT business** (the reusable decisions + traps) → **`REPLICATION_PLAYBOOK.md`**
- **Bring it all online / activate** → `GO_LIVE.md`
- **Rebuild from nothing after a disaster** (accounts, secrets, order) → `REBUILD.md`
- **Menu → website + Square + DoorDash** → `MENU_PIPELINE.md`
- **Catering lead pipeline (Supabase→Make→Gmail)** → `CATERING_LEADS.md`
- **Where-We-Vend calendar** → `CALENDAR_SETUP.md`
- **Festival/vending map + data model** → `site/festivals/README.md`, `DATA_MODEL.md`
- **Admin hub + Scout board (Trint's triage + Lance's desk)** → `SCOUT_BOARD.md` (+ audit `SCOUT_AUDIT.md`)
- **Signal Net events crawler (GitHub Actions → Signals feed)** → `SIGNAL_NET.md`
- **Post Cards (social drafts for public stops → Business Suite)** → `POST_CARDS.md`
- **Demand baseline (sales → crew + prep on the cards)** → `DEMAND_BASELINE.md`
- **Accounting (Square→Wave), business logic + gotchas** → `ProjectContext.md`, `SETUP.md`
- **Latest full-repo audit** → `FOLDER_AUDIT_2026-07-13.md` (+ `archive/2026-07-13/ARCHIVE_MANIFEST.md`)
- **What's safe to archive** → `ARCHIVE_REVIEW.md`
- **Open work / gameplans** → `TODO.md`
- **How the backlog systems tie into ONE platform** (the chassis/spine, the loop, build order) → `OPS_PLATFORM.md`

---

## 5. Secrets & accounts (values are NOT in git — see `REBUILD.md`)

Every **public** browser file uses only the **public** Supabase `anon` key. Secrets (`service_role`,
`SQUARE_TOKEN`, `WAVE_TOKEN`, Google service-account JSON, Streamlit `APP_PASSWORD`, and the crawler's
`SUPABASE_SERVICE_KEY` **GitHub Actions secret**) live only in gitignored files / the operators' shells /
the hosting dashboards / GitHub repo secrets. `.claude/` (agent memory, holds a service-role key) and
`..\PrivateData\` (PII) are **not tracked**. The full account + secret-location map is in `REBUILD.md`.

The **gated admin pages** (`/hub`, `/scout`, `/hub/desk`, `/hub/signals`) instead use **Supabase Auth**
(email+password, two hand-created users: Trint + Lance) and load supabase-js from the **self-hosted**
`site/assets/vendor/supabase.js` — no CDN dependency. Their tables have RLS granting only the
`authenticated` role (anon revoked), so the public anon key can't touch them.

Hosting/infra: **Cloudflare Pages** (website **and** the festival map at `/festivals` **and** the gated
hub/scout/signals pages, one project, output dir `site/`), **GitHub Actions** (runs the Signal Net
crawler every 4h + the **calendar sync** every 2h — both skip cleanly until their secrets exist),
**Streamlit Community Cloud** (accounting dashboard), **Supabase** (one
project: accounting + `vending_*` + `catering_leads` + `cart_schedule` + `contacts` + the Scout tables
`event_prospects`/`prospect_decisions`/`prospect_thread` + the Signal Net `event_signals` +
`post_drafts` (Post Cards) + `demand_profiles` (demand baseline) + `app_allowed` (auth allowlist)),
**Make.com** (catering email), **Square** (POS→DoorDash), **Wave** (books), **GoDaddy** (domain
registrar). **Netlify is retired** — the vending map moved off it into `site/festivals/`.

---

## 6. HARD RULES (do not violate — these are owner decisions)

- Spelling: always **"Dog"**, never "Dawg". The item is **"Hog' N' Dog"**.
- **Food copy: say the OUTCOME, never the logistics.** Two failure modes, both banned:
  1. ❌ **NEVER claim we "cook on-site"** / "cook fresh on the spot." It's **false** (we're a licensed
     **mobile food establishment** — all food is prepared at the **commissary**; the cart reheats/holds hot,
     finishes to order, and serves) **and** it's a health-code red flag.
  2. ❌ **NEVER narrate the commissary/reheating either** — "prepared in our commissary kitchen," "held hot,"
     "reheated." It's true, but it reads as a **back-of-house disclosure** and it **sells against us**:
     nobody paying $650 for catering wants to read that their food was reheated.
  ✅ **Correct:** just don't mention where it's cooked. *"Made fresh and served hot," "hot off the cart,"
  "served hot and fresh to your crowd," "made to order"* (assembly at the cart IS accurate). Customers
  assume food is cooked somewhere; they only care that it arrives **hot, fresh, and made for them**.
  *(Same principle as: never write "everything comes separate" on a catering menu — that's just how catering
  works. Don't put the mechanics in the sales copy.)* Fixed site-wide 2026-07-14.
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

**🚀 LAUNCHED 2026-07-14:** site **LIVE at `glizzness.com` + `www`** (Cloudflare; nameservers moved off
GoDaddy, apex = proxied CNAME-flatten to `glizzness.pages.dev`), **old GoDaddy builder down**, **catering
pipeline verified end-to-end**. **DoorDash go-live + social/marketing rollout in progress.**
Marketing approach: schedule + cross-post FB/IG via **Meta Business Suite** (free — one post to both);
**Google Business Profile** already live for local discovery + reviews. **Imagery hard-rule reaffirmed
2026-07-14: real photos only, NEVER AI-generated food/cart** (the RTX-3080 / IBTP genai pipeline is for
abstract backgrounds only — an AI hot dog on a real food brand reads as fake and erodes trust).

**🚀 WENT LIVE 2026-07-16 — the whole private ops platform is running:**
- **Admin hub + Scout board** (`SCOUT_BOARD.md`) — gated cockpit + Trint's Yes/Maybe/No card board +
  Lance's review desk. Deep-audited + hardened (`SCOUT_AUDIT.md`); Lance logged in and verified.
- **The Signal Net** (`SIGNAL_NET.md`) — the crawler runs itself every 4h; **178 signals** from 10 live
  sources on the first real run.
- **Calendar auto-sync** (`CALENDAR_SETUP.md`) — every 2h in the cloud; `/events` self-updates.
- **The loop is closed:** crawler finds → Lance Keeps → enriches → **Ready → Trint** → Trint decides on
  his phone → Lance books. *(Demo gotcha: Trint's board looks empty until cards are marked Ready.)*

**Also LIVE (built + SQL run 2026-07-16, later the same day):** the **demand baseline** — the "brain."
`demand_baseline.py` → `demand_profiles` (10 rows) → crew + prep on the Scout cards; plus the
**17 lunch-rush/worksite prospects** seeded to the Desk, and **Post Cards** (`post_drafts` table run).
Owner verified counts (10 profiles / 17 prospects). See `DEMAND_BASELINE.md`.
**Still backlog:** scheduling (who works it), **inventory depletion/reorder** (gameplan session
pending — owner directive: design first, NO code yet), rush-curve peak staffing.

Backlog gameplans (each spec'd in `TODO.md`; **most say "evaluate Square-native first"**):
- **Signal Net → Event Finder promote (v1.1)** — one-click curated promote of an approved signal to the
  public map, plus auto-flagging detail updates (never auto-publish; the map is a validated gate).
- **Inventory + reorder-point system** — common item master; purchase-SKU + recipe/BOM mapping; Wave IN /
  Square-Orders OUT.
- **Employee scheduling (takt-time)** — staff to demand at a fixed pace; add people, not speed.
- **Event-sales demand baseline** — match `past_cart_events.csv` to Square Orders (event capture done).
- **Unify the streamlit dashboard** under glizzness.com (the festival map is already unified — now
  `site/festivals/`); **food supplier**; map polish.

---

## 8. What happened in the big 2026-07-13 session (so history makes sense)

Menu overhaul + dynamic add-ons + brat rename + Square sync; `push_menu` phantom-diff fix; catering lead
pipeline built; a **5-cluster full-repo audit** (`FOLDER_AUDIT_2026-07-13.md`) → corrections applied, the
**repo made private**, legacy web pages + the dormant **SQLite accounting pipeline archived** to
`archive/2026-07-13/`, `run_daily.ps1` scheduler confirmed OFF; lots of site-copy fixes (See-Our-Menu button,
"three ways", de-corporate, catering rewords); a **7-run deep-research vending sweep** →
`VENDING_PROSPECTS.md` → **27 prospects mined onto the map** (442 events). The map was then **rebranded to
the public "Midwest Event Finder"** — research picks pulled OFF it to seed the Scout board, fit/past/defunct
filters dropped, "trip type" → "Distance from Columbia", single gold markers;
**294 past calendar events captured** (`past_cart_events.csv`) for demand modeling; a freelance **rate sheet**
Artifact. See `git log` and `FOLDER_AUDIT_2026-07-13.md` for specifics.
