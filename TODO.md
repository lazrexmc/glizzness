# The Glizzness — TODO / Backlog

Running list of open action items. Add dated entries; check them off or delete when done.
(For the full go-live sequence see `GO_LIVE.md`; for strategy see the north-star spec.)

> **The six backlog systems — Finder · Scout · demand baseline · staffing · inventory · scheduling — are
> ONE integrated platform, not six features.** How they tie together (the shared spine, the loop, the
> build order, the open integration decisions) lives in **`OPS_PLATFORM.md`**. Read that first.

---

# 🔥 OWNER ACTION LIST — work top to bottom *(2026-07-14)*

*Cash is tight ($120). Everything below is ordered by "what puts money in the account soonest."
The engineering backlog is BELOW this and is **parked** until revenue is stable.*

## 🟣 0. ⚠️ NOT LIVE YET — ASK CLAUDE TO WALK YOU THROUGH IT *(added 2026-07-16)*

> **Status check, honestly stated:** the **Scout board** + **Signal Net** are **CODE IN THE REPO ONLY**.
> Lance has **not opened any of it, has not created a login, has not run a single SQL file, has not set
> the GitHub secret, has never seen the hub.** Nothing is live to him. Do not describe these as "live"
> or "ready" — they are *built and untested by the owner.*

- [ ] **Say to Claude: "walk me through the Scout board + Signal Net setup."** He guides it **one step at
      a time**, waits for you at each step, and verifies before moving on. Do NOT just hand over a runbook.
      The rough shape (all owner-credentialed, ~30–40 min total):
  1. Supabase SQL editor → run `supabase_scout_schema.sql`, then `supabase_signals_schema.sql`.
  2. Supabase → Authentication → **create 2 users** (Trint + Lance) → *this is your hub login.*
  3. `python scout_seed_gen_sql.py` → run the generated `supabase_scout_data.sql` (23 prospects).
  4. GitHub → repo Settings → Secrets → Actions → add **`SUPABASE_SERVICE_KEY`** (the Supabase
     service_role key).
  5. GitHub → Actions → enable → **Run workflow** ("Signal Net crawler") → seeds the Signals feed.
  6. Open **glizzness.com/hub** → log in → check Signals / Scout Board / Desk actually work.
- [ ] Then decide the **v1.1 "→ Event Finder" promote** (spec §9.5) once you've actually used the feed.

## 🔴 1. CASH THIS WEEK — calls & emails

- [ ] **Show-Me State Games — CALL TODAY.** Jessie Sida **573-884-2946** (main 573-882-2101).
      Food-vendor slot, **Jul 17–19 and Jul 24–26**. High foot traffic. Fastest cash on this page.
- [ ] **Venues — weekend cart nights** (open all summer, don't care that MU is out):
  - Bur Oak Brewing — **events@buroakbeer.com** (*explicitly allows food trucks*)
  - Cooper's Landing — **573-657-1299** / info@cooperslandingmo.com (*hosts vendors most weekends*)
  - Logboat — logboatbrewing.com/contact (**was 38% of all past gigs — the anchor account**)
  - Rose Music Hall / The Blue Note — 573-874-1944 / booking@thebluenote.com
- [ ] **Corporate lunch outreach** (offices are FULLY STAFFED in July — this lane is MU-independent):
  - **Veterans United** — 573-876-2600 — ⚠️ **REPEAT CLIENT, reconnect, don't cold-pitch.** Prior invoice
    on file: **$1,376.68**. Pull the old events contact.
  - **MBS** — Mark Nistendirk, HR — humanresources@mbsbooks.com
  - **Boone County** — Angela Wehmeyer, HR Dir — hr@boonemo.gov — 573-886-4395 *(verified)*
  - **Boone Health** — Jenny Workman — Jenny.Workman@boone.health
  - **CPS** — Laina Fullum — lunch@cpsk12.org
  - **City of Columbia** — HR@CoMo.gov
  - EquipmentShare · Watlow (573-474-9402) · Central Bank · MidwayUSA · Eurofins · Schneider
  - **Pitch two options:** (a) *sponsored appreciation lunch* — they prepay (GUARANTEED cash), or
    (b) *zero cost to them* — you park, they announce it internally, employees buy their own.
    **Never "park and pray."**
- [ ] **🟠 NEW VEIN — apartment-complex property managers.** The Domain + Elements **already bought**
      (pool parties). Property managers are STAFF with event budgets, Columbia is packed with complexes,
      and they're prepping **August move-in / resident events** right now. Nobody is working this lane.

- [ ] **★★ PHARMA REP LUNCHES — the premium recurring vein (owner, 2026-07-14).** Pharma sales reps buy
  catered lunches for medical offices/clinics to get physician face-time: **big budgets, price-insensitive,
  RECURRING** (same offices on a weekly/monthly rotation). Maps PERFECTLY onto the **drop-off trays** (Desk
  Job / Roll Call) — it's a deliver-to-the-clinic product, no cart. Difficult, demanding buyers, but deep
  pockets; **reliability > price.**
  - **Access — do NOT cold-chase field reps.** Get where they already book: **list on ezCater** (dominant
    office/catering marketplace reps search + it gives them the expense/compliance receipt). Also get on
    **medical-office "approved caterer" lists** (office managers keep a shortlist reps pull from).
  - **Rep-proof the product:** individually packed, **name-labeled**, on-time-to-the-minute delivery — it's
    the rep's face in front of the doctor. That's what wins and keeps them.
  - **Next:** (a) list on ezCater (+ verify best-fit platforms); (b) pull a Columbia medical-clinic list to
    target for the caterer list. *(Claude can research both — paced search.)*
  - ✅ **RESEARCH DONE 2026-07-15 → see [PharmaLunch.md](PharmaLunch.md)**: platforms (ezCater primary —
    free listing, **15% + 2.75%** per order; CaterCow + Cater Nation secondary), the ezCater signup steps
    (+price the menu +15–20% to absorb the cut), the Columbia target clinics/clusters (Nifong Plaza, Keene
    corridor, Broadway Bluffs, Berrywood endocrine; Boone Clinic, University Physicians Specialty Clinic,
    Cosmopolitan Diabetes/Endo, Cayce Derm), and the rep-proof operational bar. **Owner action: create the
    free ezCater account (~30 min, needs LLC/EIN/commissary addr).**

## 🔴 2. BEFORE THE SOCIAL CAMPAIGN POSTS

- [ ] **Facebook Sharing Debugger — RE-SCRAPE.** developers.facebook.com/tools/debug/ → paste
      `https://glizzness.com` → **"Scrape Again."** Repeat for `/catering` and `/order`.
      ⚠️ **Facebook caches old link previews. Skip this and your launch post shows NO IMAGE** even though
      the og:image fix is already live.
- [ ] **Update IG + FB bio link → `glizzness.com`** (links aren't clickable in IG captions — the bio link
      is the only clickable one, so IG CTAs must say "link in bio").
- [ ] **Schedule the launch posts in Meta Business Suite** (free; cross-posts FB + IG in one action).

## 🔴 3. GOOGLE BUSINESS PROFILE — free catering leads

- [ ] **Add "Caterer" as a category.** ⚠️ Food/restaurant categories require a visitable address —
      **fix by switching the profile to a SERVICE-AREA BUSINESS** (caterers travel to the customer, so
      Google allows it with no address).
- [ ] **Set service area = Columbia / Boone County; hide the address.**
      ⛔ **NEVER fake an address** (commissary, home, mailbox) — that's a fast track to **suspension**, and
      you'd lose the reviews/history you already have.
- [ ] **Website field → `glizzness.com`** (verify it's not the old GoDaddy site). Add the **order link**
      (DoorDash) and the **appointment/quote link** (`glizzness.com/catering`).
- [ ] **Paste the new 710-char business description** (leads with "caterer" — it's the money search).
- [ ] **Add real photos** (loaded Glizzy, the cart). GBP heavily rewards fresh photos.
- [ ] **Post the relaunch to GBP** — links **are** clickable there (unlike Instagram).
- [ ] **Push reviews** — biggest local ranking + trust factor. QR at the cart; ask regulars.
- [ ] Turn on attributes: **delivery, takeout, catering.**

## 🟠 4. CATERING MENU EXPANSION

- [ ] **Review the preview: `glizzness.com/tempcatering.html`** (unlinked, noindex, live page untouched).
      Pulled Pork $650/50 ($13) · Pulled Chicken $650/50 ($13) · Pork & Chicken $700/50 ($14) ·
      Sandwich Tray $250/25 ($10) · Roll-Up Tray $250/25 ($10) · nacho copy updated · 25-guest minimum ·
      **no deposit language** (held per owner).
- [ ] **Approve or adjust prices/names** → then merge into live `catering.html` + delete the preview.
- [ ] Decide on the **deposit requirement** (held off for now).

## 🟡 5. SEED FOR AUGUST — Mizzou (the fall calendar gets set in JULY)

*Students are gone, but the STAFF who book catering are at their desks planning fall. Wait until August
and the vendors are already chosen.*

- [ ] **Mizzou Residence Life** (your $4,000 account — a DEPARTMENT, not students)
- [ ] **Campus Activities** · **MU Athletics** (welcome-back)
- [ ] **Office of Fraternity & Sorority Life — get on the APPROVED-CATERER LIST.** This is the master key:
      stop chasing rotating chapter treasurers; make the chapters find *you*, every year.
- [ ] **`mugreekweekoperations@missouri.edu`** (a ROLE email — survives officer turnover)
- [ ] **MU vending agreement FY27 renewal** (Casey Forbis, Finance & Business Services) + **MU EHS food
      permit** (573-882-7018 / muehssanitarian@missouri.edu) — both needed before fall.

## 🟢 6. QUICK TECH (dashboard actions — 5 min each)

- [ ] **Cloudflare → Rules → Redirect Rules:** `www.glizzness.com/*` → `https://glizzness.com/$1` (301).
- [ ] **Google Search Console** — add glizzness.com, submit `https://glizzness.com/sitemap.xml`.
- [ ] **DoorDash op-must:** Trint **sets the tablet address EVERY time the cart opens** — forget once and
      drivers roll to last night's spot.

## 🔵 7. MONEY / OPS DISCIPLINE

- [ ] **Enforce a 50% deposit** on catering bookings — that's cash in hand *before* you buy food. The
      fastest, cheapest money available and it needs nobody's permission.
- [ ] **STOP volume-discounting.** Realized prices on big gigs have been **$3.50–$6/guest** (MU Athletics
      $3.50, MSA $4.40, Business Week $4.50) against a **$7 list price and $22 premium**. Those are the
      longest days and the most food. That leak costs more than any menu change.
- [ ] **Square Capital / Loans** — check the Square dashboard. They underwrite on your **processing
      history** (~$186K through them); often instant, no credit pull. Likely faster than a bank.
- [ ] **Callaway Bank line of credit** — bring **Square sales reports + P&L + the Weenie Wagon loan
      payment history**. Ask for a **specific, self-liquidating amount** ("$X to fulfill $Y in booked
      catering"). ⛔ **Do NOT mention the overdraft history as leverage — to an underwriter it's a red
      flag, not loyalty.** Borrow to *fulfill booked work*, never to cover a slow week.

---

## Open

- [ ] **★★ Catering menu expansion — "not everyone wants to eat wieners"** *(added 2026-07-14 — ACTIVE,
  revenue-critical)* Widen the catering menu so a mixed crowd can actually be fed. New items:
  - **Pulled Pork** — pan of pulled pork + buns + BBQ sauce + sandwich pickles, served as a station.
  - **Southern BBQ Pulled Chicken** — same format as the pork.
  - **Nachos** (already on the catering menu) — now plain, or topped with pulled pork or pulled chicken.
  - **Deli sandwiches** — ham / turkey / chicken on Hawaiian rolls (or standard rolls), Sam's-sourced.
  - **Roll-ups** — same deli meats, rolled instead of sandwiched.
  - **Sides** — potato salad / coleslaw / chips (already on the menu).
  - **COPY RULE (owner):** never write it as "everything comes separate" — a pan + buns + fixings IS how
    catering works; it's implied, never announced. Standard catering phrasing only.
  - **STRATEGIC:** the deli sandwich / roll-up tray is a **cold drop-off product — no cart, no cooking, low
    food cost, high margin.** That's exactly the "boxed-lunch drop-off" the corporate lane
    (`CorporateProspects.md`) calls for, and the cheapest catering product to fulfill when cash is tight.
    Two lanes now: **hot BBQ bars** (on-site/cart) and **cold trays** (drop-off, no cart).
  - **BLOCKED ON:** owner pricing (per-guest + tray prices). Then build the package cards into
    `site/catering.html` (8 existing packages, $7–$22/guest range) and update the catering menu.

- [ ] **★ Private admin hub (login-gated) — TOP PRIORITY** — one page at `glizzness.com` (NOT in public
  nav), behind a real user/pass gate, that is Trint's + Lance's cockpit: it houses the **Scout board**
  (below) and **links out to** the **Streamlit Wave dashboard** (`glizzness.streamlit.app`). Goal:
  "everything reachable from the Glizzness domain" without moving Streamlit itself.
  - **The Streamlit dashboard is fine where it lives.** It's internal + password-protected already, so a
    pretty URL buys little, and a Streamlit custom domain needs a fussy Cloudflare proxy for its
    websockets. The hub just **links** to it — no reverse-proxy. (Supersedes the old "streamlit subdomain"
    sub-task.)
  - **Security (frank):** this gate fronts financial (Wave) + prospecting data, so it must be a REAL auth
    wall, not client-side theater — the Scout board writes to Supabase, so it needs proper RLS + a
    server-checked passcode, not a hidden `<div>`. Eggs-in-one-basket is accepted, but the basket has to
    actually lock.
  - **Build:** an `admin/` (or `hub/`) folder, unlinked from nav; passcode gate; tiles → Scout board + Wave
    dashboard (+ future tools). *(added 2026-07-13)*

- [ ] **Online ordering — Square Online + DoorDash: what's actually viable for a roaming cart?**
  *(added 2026-07-13)* Owner wants to allow online order / pickup / delivery. The blocker: a cart has **no
  fixed pickup address**, and Square Online's delivery/pickup wants a set store location. DoorDash lets us
  operate as a store (we're live on the DoorDash **Marketplace**, store 38788821) — but that's DoorDash's
  OWN storefront, not Square's.
  - **The hoped-for hack — "use Square Online ordering, let DoorDash do the delivery" — probably does NOT
    dodge the address problem.** Square Online's on-demand delivery *is* powered by **DoorDash Drive**, so
    the courier can be DoorDash — but the **pickup/origin address still lives in Square** (a fixed store
    location), so a daily-moving cart can't set a dynamic origin. Changing the courier doesn't change
    *where* they pick up. **VERIFY** — Square's mobile/dynamic-address support changes; confirm before
    ruling it out (web research or Square support).
  - **What likely DOES work + is worth it: order-ahead PICKUP at the cart.** No delivery, no address
    problem (pickup = walk to the cart window), and it **cuts the line at busy lunch/late-night rushes** —
    directly helping the demand-surge/staffing pain. Needs the cart's live location surfaced (ties to
    Where-We-Vend).
  - **Delivery is already handled by the DoorDash Marketplace — and it IS the roaming-cart answer.**
    DoorDash's merchant **tablet lets you update the pickup address**, so when Trint opens the cart at a
    new spot for the night he sets that address and drivers come to the current location. **Square can't do
    this** (fixed store address) — which is exactly why DoorDash, not Square Online, is the online/delivery
    channel for a moving cart. Duplicating it through Square adds little.
    - **Operational must:** the address is only right if Trint **sets it every time the cart opens** —
      forget once and drivers roll to last night's spot. Checklist item, and a clean candidate to tie to
      **Where-We-Vend** so the night's location is set in one place.
  - **Next step:** verify Square's current mobile-pickup capability + the Square↔DoorDash Drive setup, then
    decide: (a) Square Online order-ahead pickup, (b) lean on DoorDash Marketplace for delivery, (c) both.

- [ ] **Find Trint a verified food supplier that will deliver to us** — a distributor/wholesaler
  willing to deliver despite (a) currently **low volume** and (b) **no fixed home / commercial
  address** (cart + Flyover commissary, no brick-and-mortar). Most big distributors (Sysco, US Foods)
  require order minimums and a business delivery address, so the task is finding one that works at our
  scale — e.g. Restaurant Depot / cash-and-carry, a regional/local distributor, or a supplier that
  delivers to the commissary. *(added 2026-07-10)*

- [ ] **Catering / "Book the cart" booking backend** — partially built; see `CATERING_LEADS.md` for the
  live pipeline. Form (`catering.html#book`) INSERTs a row into Supabase `catering_leads`.
  - **(a) Notification — ✅ DONE (2026-07-13).** Supabase Database Webhook on `catering_leads` INSERT →
    Make.com scenario → Gmail sends a formatted alert to glizzness@gmail.com. (Runbook: `CATERING_LEADS.md`.)
  - **(b) Triage / status** — *still open.* Track a lead new → contacted → booked → done (a status column +
    a simple admin view, or just work them in the Supabase table).
  - **(c) Calendar** — *still open.* Should a *confirmed* booking become a Google Calendar event? (would then
    flow to Where-We-Vend via `sync_calendar.py` if marked Public). Decide manual vs. automatic.
  - **(d) Auto-reply — ✅ LIVE (2026-07-13).** A 2nd Gmail module in the same Make scenario, **filtered on
    `record.email` Contains `@`** (email is optional on the form), emails the customer a confirmation.
    Copy + steps in `CATERING_LEADS.md` ("Auto-reply to the customer"). Verified end-to-end — a passing
    run shows **3 operations** in the Make log (webhook + owner-notify + auto-reply).
  - **(e) Where leads live day-to-day** — *still open.* The operator's actual working view of the pipeline.
  *(added 2026-07-12; notification shipped 2026-07-13)*

- [ ] **Add niche event sources + event-type sorting to the vending map** — high-value niches food carts
  can hit that aren't in the general festival lists. **Deep-research in progress (2026-07-13):** a 7-run
  serial sweep covering (1) MTB/gravel/cycling [lokievents, bikereg], (2) sports tournaments
  [tournamentlinks], (3) rodeos/car-shows/BBQ/air-shows/hot-air-balloons, (4) dirt-track racing,
  (5) wineries + MO wine trail, (6) motorcycle rallies/poker runs, (7) surrounding-county fairs + parish
  festivals. (Serial, not parallel — parallel trips the web-search rate limiter.) Then: mine the results
  into the vending-circuit dataset + add a **category / event-type filter** to the map so we can sort by
  type. *(added 2026-07-12; research expanded 2026-07-13)*

- [ ] **Unify everything under `glizzness.com` (one web address)** — consolidate the properties so
  there's a single front door. *(Backlog — the festival-map half is **DONE**; only the Streamlit
  dashboard subdomain remains.)*
  - **Midwest Event Finder (was the "festival / vending map") — ✅ DONE + REBRANDED (2026-07-13).** Moved
    from Netlify into **`site/festivals/`** (still the `/festivals` URL — folder/URL rename deferred since
    it needs redirects), and **rebranded from "The Glizzness Vending Circuit" into the public "Midwest
    Event Finder"**: a tool to find events to vend at OR attend, not "our circuit." Private research picks
    pulled off it (→ Scout board); Past/defunct/fit filters removed; "trip type" → "Distance from
    Columbia"; single gold markers. **North-star (future): monetize it** — organizers pay to be featured /
    kept 100% current (a paid Midwest event directory). `site/events.html` links to it (new tab).
  - **Accounting dashboard** (`glizzness.streamlit.app`) — see the **admin hub** item at the top of this
    list: the decision is to **leave Streamlit where it lives** and just link to it from the gated hub (no
    custom-domain proxy). This sub-task is folded into that item.
  - Prereq: `glizzness.com` live on Cloudflare — ✅ **DONE 2026-07-14** (domain switched; site + www live, SSL enabled).
  *(added 2026-07-13)*

- [~] **Trint's event-triage app ("Scout board") — ✅ BUILT 2026-07-16 → runbook [SCOUT_BOARD.md](SCOUT_BOARD.md).**
  Code is in the repo (schema `supabase_scout_schema.sql`, seed `scout_seed_gen_sql.py` → 23 cards,
  pages `site/hub/` + `site/scout/`, auth `site/assets/scout.js`). Gate smoke-tested (logged-out
  `/scout` bounces to login; 0 console errors). **REMAINING — Lance's credentialed setup** (in the
  runbook): (1) run the schema SQL, (2) create the Trint + Lance auth users, (3) run the seed SQL,
  (4) `git push` deploys it, (5) then the ongoing CLI loop = enrich `researching` cards with Claude →
  **Ready → Trint**. Make→Gmail alerts are optional phase-2. *Original design below for reference.*

- [~] **The Signal Net — always-on events crawler → ✅ v1 BUILT 2026-07-16 → runbook [SIGNAL_NET.md](SIGNAL_NET.md).**
  GitHub Actions polls curated local sources every 4h → writes finds to Supabase `event_signals` →
  Lance skims the gated **Signals feed** (`/hub/signals`, 4th hub tile) → **Keep** (→ Scout prospect)
  / **Dismiss**. Code: `crawler/` (run.py + rss/reddit/venue adapters, tested — r/columbiamo pulls
  real events), `.github/workflows/crawler.yml`, `supabase_signals_schema.sql`, `site/hub/signals.html`.
  Spec: `docs/.../2026-07-16-signal-net-design.md`. **REMAINING — Lance:** (1) run the schema SQL,
  (2) set the `SUPABASE_SERVICE_KEY` GitHub Actions secret, (3) enable + manually trigger the workflow,
  (4) skim `/hub/signals`. **v1.1 fast-follow (Lance asked):** a **"→ Event Finder"** promote action —
  push an approved signal to the PUBLIC map (`vending_events`) with a region/type pick + geocode
  (curated, never auto-publish, because the map is a validated public gate) + auto-flag updates to
  existing events. See spec §9.5. Also later: auto-ranking, Make→Gmail digest, free-keyed APIs.

- [ ] **Trint's event-triage app ("Scout board") — yes / no / maybe on prospect events** — the 7-run
  vending research (`VENDING_PROSPECTS.md`) produces far too many events for Trint to sort out via the map.
  Build him a dead-simple, phone-first decision tool. *(Backlog — build after the 7 research runs are
  compiled; not urgent.)*

  **Concept:** a private, mobile-first **board of cards** (NOT the map, and it lives behind the admin hub
  above) — one big card per respectable event with **✅ Yes / 🤔 Maybe / ❌ No** buttons and an **"❓ Ask a
  question"** field. **Design for Trint specifically:** he reads better through clear visual layout than
  dense text, so each card is **big, visual, low-reading-burden** — icon-led facts he can grasp at a
  glance: **distance, drive time, vending/application fee, application deadline/window, crowd size, date**.
  This is a hard design constraint, not a nice-to-have. Grouped by date, and — unlike the public "Where We
  Vend" list — it **must show multiple events on the same day**. Trint taps through; his answers +
  questions land where Lance can act on them (Lance researches the questions, books the Yeses).

  **Seed data is ready:** the 27 curated research picks were just pulled OFF the public Midwest Event
  Finder (ids ≥ 500) precisely so they can become this board — they're Trint's picks, not the public's.

  **Reuse the existing stack (same patterns as the catering form + Where We Vend):**
  - **Data:** new Supabase tables — `event_prospects` (id, name, event_type, city, venue, lat/lng,
    start/end date, crowd_estimate, food_policy [unknown/open/closed/competing], drive_time, distance,
    description, source_url, `answer`) + `prospect_decisions` (prospect_id, decision enum yes/no/maybe,
    question text, decided_by, created_at). RLS like `catering_leads`: anon INSERT/UPSERT, no public SELECT
    of anything sensitive; Lance reads via service_role / the Streamlit dashboard.
  - **Seed:** ETL the curated `VENDING_PROSPECTS.md` rows → `event_prospects` (a `gen_sql`-style loader,
    same approach as the vending circuit).
  - **Frontend:** a standalone mobile page (e.g. `scout.html` or a `scout/` folder), **unlinked from public
    nav**, light passcode. Card feed grouped by date; huge tap targets; a decision saves instantly to
    Supabase and marks the card; "undecided only" filter. Each card expands to full detail + source link +
    Lance's answer to any question Trint asked.
  - **Lance's side:** a "Prospect decisions" view (Streamlit dashboard page or a Supabase view) showing all
    yes/maybe/no + questions; optional **Make.com webhook → Gmail alert** on a new decision/question (reuse
    the `CATERING_LEADS.md` pipeline). Loop: Trint triages → Lance books the Yeses / researches the
    questions & Maybes → answers flow back onto the card.

  **Build sequence:** (1) finish + curate the 7-run research in `VENDING_PROSPECTS.md`; (2) schema migration
  for the two tables; (3) ETL prospects → Supabase; (4) build the mobile card-feed page (date-grouped,
  multi-event-per-day, Yes/No/Maybe + Ask, Supabase-wired); (5) decisions view for Lance + optional
  Make→Gmail alert; (6) deploy privately, send Trint the link; (7) run the triage loop.

  **Principles:** mobile-first / one-handed / huge buttons · zero-friction (private link + passcode, no real
  login) · internal-only (never in public nav) · **multiple events per day is a hard requirement**.
  *(added 2026-07-13)*

- [ ] **Inventory + reorder-point system** — track stock IN (purchases) vs OUT (sales) so we always know
  on-hand and when to reorder. *(Backlog — meaty; build incrementally.)*

  **⚑ EVALUATE FIRST — Square-native vs custom (both options stay open):** Square is the home POS and has
  **built-in inventory** (item-level stock counts, low-stock alerts, vendor management, and — in Square for
  Retail — purchase orders + COGS), drivable from VS Code via the **Square Inventory + Catalog API**, exactly
  like `push_menu.py` / `pull_catalog.py` already do. **Likely gap:** Square tracks stock of *sellable* items,
  not the raw-ingredient **BOM depletion** described above (Chili Dog → dog + bun + chili) — so the recipe
  layer may still need custom logic (or a Square add-on) on top. **Plan:** spike the Square Inventory API
  first, use it for everything it covers, and build custom only for the recipe/ingredient math it can't do.

  **The core problem (owner's insight):** purchases, sales, and stock use THREE different vocabularies —
  Sam's/vendor receipt SKUs (what we BUY) ≠ Square POS menu items (what we SELL) ≠ raw inventory items
  (buns, dogs, brats, chili, cheese, chips, drinks, propane…). They must all map to one common **inventory
  item master** so "inventory IN" and "inventory OUT" reconcile despite coming from different sources.

  **Two mapping layers (the crux):**
  1. **Purchase SKU → inventory item** (+ units per pack). e.g. a Sam's "48-ct franks" case → 48 × `hot dog`.
  2. **POS menu item → inventory items consumed** = a recipe / bill-of-materials. e.g. `Chili Dog` = 1 dog +
     1 bun + ~4 oz chili + ~1 oz cheese. This is what lets Square SALES deplete raw stock.

  **Flow:**
  - **IN:** when processing a Sam's receipt in Wave (already coded to COGS), also log the items + qty into an
    inventory ledger (IN). Same manual path for **non-Sam's vendors** (vendor, date, item, qty, cost).
  - **OUT:** pull Square **item-level** sales (Square **Orders API** line items — richer than the payout /
    settlement data the accounting pipeline posts today) → deplete raw stock via the recipe map.
  - **On-hand = IN − OUT ± adjustments** (waste, physical-count corrections).
  - **Reorder point / par level** per item → flag "reorder X" when on-hand < par; ideally project days-of-
    supply from sales velocity → a generated shopping list.

  **Stack:** Supabase tables — `inventory_items` (master + unit + par/reorder point), `vendor_skus`
  (purchase SKU → inventory item + pack size), `inventory_purchases` (IN), `menu_recipes` (Square item →
  inventory items + qty), `inventory_ledger` (all movements), `physical_counts` (periodic reconciliation).
  Admin UI lives in the **Streamlit dashboard** (`dashboard.py`): log purchases, manage recipes, see on-hand
  + reorder alerts. Reuses the existing Supabase + dashboard stack.

  **Build sequence:** (1) define the inventory item master; (2) build the Sam's purchase catalog from
  receipts (SKU→item + pack size); (3) build recipes/BOM for each Square menu item; (4) Supabase schema;
  (5) dashboard pages to log purchases (Sam's + other vendors) + manage recipes; (6) Square item-level sales
  sync → depletion; (7) reorder-point logic + generated reorder list; (8) physical-count reconciliation.

  **Then automate** the manual build steps: Sam's receipt parsing (CSV/OCR → purchase lines), scheduled
  sales depletion, auto-generated reorder lists. *(added 2026-07-13)*

- [ ] **Employee scheduling + staffing-to-demand system** — make sure Trint (cook) is at every event with
  ENOUGH hands, and — the key philosophy — that the crew always works at the SAME sustainable pace: scale
  volume by adding PEOPLE, never by making anyone cook faster or harder. *(Backlog.)*

  **⚑ EVALUATE FIRST — Square-native vs custom (both options stay open):** Square has **Team Management +
  Square Shifts** (create/publish schedules, shift swaps, timecards), drivable from VS Code via the **Square
  Labor / Team API** — that likely covers the scheduling *mechanics* (rosters, shifts, staff notifications)
  out of the box. **Gap:** the staffing-to-demand / takt-time math (compute required headcount from an
  event's crowd estimate at a fixed per-person pace) is NOT something Square does — that logic layers on top
  of whichever scheduling backend we pick. **Plan:** spike Square Shifts/Labor API first; build custom only
  for the demand → headcount model.

- [ ] **Event sales history → demand baseline** — match PAST Google-Calendar events to Square sales to learn
  "how much did we actually sell at events like this," so the staffing-to-demand model above (and the Scout
  board) rank on real numbers instead of guesses. *(Backlog — feasibility confirmed; it's a data-analysis
  task, no new infra.)*

  **✅ Capture done (2026-07-13):** `pull_past_events.py` exported **294 past events** (Oct 2023 → now) to the
  local, gitignored `past_cart_events.csv` (raw, un-sanitized). Remaining work = the Square **Orders** match
  + per-event rollup (revenue / order count / items / peak hour).

  **Feasible? Yes — both sources are timestamped:**
  - **Events:** pull past entries from Google Calendar (Calendar API accepts past `timeMin`/`timeMax`) — each
    has date, time window, location. (`sync_calendar.py` keeps only *upcoming* stops in `cart_schedule`, but
    the Google Calendar itself still holds the history.)
  - **Sales:** pull Square sales with timestamps via the **Square Orders API** (richer than the payout data
    the accounting pipeline posts) — filter to **in-person POS** to exclude DoorDash/online = true on-site sales.
  - **Join:** bucket Square orders into each event by date/time-window overlap → per-event **revenue, order
    count, items sold, peak hour**. (Single cart = one Square location, so date/time is the only matcher.)

  **Caveats:** match quality depends on accurate event time windows; must exclude delivery orders; historical
  depth is limited by how far back events were actually logged in the calendar — but it **accumulates going
  forward**, so every logged event + its sales becomes a data point from now on.

  **Owner's refinement (2026-07-13) — the Google Calendar is NOT the complete event list; the SALES are
  the spine.** A huge recurring revenue stream — **school-year late-night (~10 PM) downtown Columbia, the
  bar crowd** — is mostly NOT on the calendar. So expect **many dates with sales and no event**, and the
  join must NOT be driven off the calendar (that would erase the highest-value trade). Flip it:
  - **Cluster the Square orders first** (date + time window) — that's ground truth.
  - **Attach a calendar event where one matches**; leftover clusters are **unlabeled sales days** to classify.
  - **Classify orphans by signature:** many small orders + late-night + school-year weekends = the
    **bar-district walk-up trade** (a first-class recurring "event type" with no calendar entry); a single
    large order at close = a **private party, client covered the whole tab** (batch/close-out billing, not
    walk-up — ties to the `service_mode` split above); steady daytime = a regular gig nobody logged.
  - **Transaction-shape tells (owner, 2026-07-13):** **catering = a large single ticket, usually an
    Invoice** (Channel `Invoice Sales` / big `Custom Amount`) — a booked job; a **single transaction with a
    huge line-item count** = a **private party where one person settled the whole tab at close**
    (walk-up-style ordering, one payer, batch service); **many small separate tickets** clustered in time =
    individual **walk-up** trade. Validate against `Sales/items-*.csv` (top tickets by item-count and by $).
  - **Hard limit — Square is ONE location, so it tells you WHEN, not WHERE.** Every in-person sale sits
    under the single cart location no matter where it parked, so downtown-vs-brewery can only come from the
    calendar (when present) or be inferred from the time/day fingerprint. Plan for a **human-in-the-loop
    labeling pass** on the orphans, not a clean auto-sort.

  **Why it matters:** empirical backbone for the employee-scheduling model above — turns "guess the crowd"
  into "at events like this we did $X / N orders → need M hands," and tells the Scout board which event
  *types* actually paid off (which to rebook). *(added 2026-07-13)*

  **The philosophy (owner's — and it's a real ops concept, "labor standard / takt time"):** set a target
  sustainable throughput per station (e.g. 1 cook comfortably makes ~X items/hr, 1 cashier ~Y orders/hr),
  then staff each event to meet its expected demand AT that rate — so a bigger crowd means MORE
  stations/people, not a faster or more stressed Trint. Consistent pressure, consistent pace, at any volume.

  **Owner's refinement (2026-07-13) — the staffing math is VENUE-AGNOSTIC: 1 order = 1 order.** Crew =
  expected orders/hr ÷ the sustainable per-person pace (+ buffer), full stop — a dirt track and a wedding
  with the same order rate need the same hands. So the staffing **engine is universal (build once, reuse
  everywhere)**; the venue only shapes the *demand estimate* (crowd × capture × items/order), and that is
  the ONLY thing the demand baseline learns from history (capture rate + items/order — the pace is a fixed
  labor standard). Upshot: even a never-worked venue gets a real crew number from an order estimate, not
  "no data" — history just sharpens the capture/items inputs.

  **Owner's refinement 2 (2026-07-13) — demand SHAPE matters, not just volume: staff to the demand
  *curve*, not the total.**
  - **Rolling / made-to-order** (guests order as they arrive — normal cart vending): steady-state
    throughput, crew = order-rate ÷ sustainable pace. A queue you keep pace with.
  - **Batch / all-at-once** (the whole headcount served at a fixed time — plated catering, a synchronized
    meal): a *produce-N-by-a-deadline* problem, not a queue — driven by total item count, per-item time,
    lead time, and prep-ahead/hold capacity. Usually wants a short SURGE of hands or a make-ahead assembly
    line, NOT the steady crew a rolling window needs.
  - These are two ends of a **demand-concentration spectrum**: flat curve (rolling) → peaks/rushes
    (intermission, halftime, parade lets out) → a single spike (everything at t=T). The real tradeoff is
    staffing to the **peak vs. the average** (over-staff = idle hands; under-staff = blown-out lines at
    the rush); all-at-once is just the extreme where peak = 100%.
  - So the model needs a per-event **service_mode** input (rolling vs. batch, or a rush profile) and the
    crew math **branches on it**. The demand baseline can read the actual rush-curve from Square order
    **timestamps** (not just daily totals) per event type → feeds peak staffing.

  **Components:**
  - **Staff roster** — people, roles/skills (cook / cashier / prep / runner), availability, contact.
  - **Events to staff** — pulled from the confirmed vending schedule (`cart_schedule` / Google Calendar) +
    confirmed catering bookings; each event carries a date/time, location, and expected crowd/volume.
  - **Labor standards** — the sustainable per-station throughput rates (the pace we protect).
  - **Demand → headcount** — estimate covers per event (crowd × capture% × items/order, or catering guest
    count) ÷ per-person standard rate → required crew (cook/cashier/runner counts) + a buffer.
  - **Assignment** — fill each event's required slots from available staff; flag **under-staffed** events and
    double-booked people.
  - **Staff view + notifications** — each person sees/accepts their shifts on mobile (same pattern as the
    Scout board / Where-We-Vend page); reminders.

  **Stack:** Supabase tables — `staff`, `staff_availability`, `staffing_standards` (throughput per role),
  `shift_assignments`, and a computed `staffing_requirements` per event (events × demand × standards). Lance
  builds/monitors in the Streamlit dashboard; staff use a mobile page. Integrates with the vending calendar +
  catering bookings + the crowd estimates in `VENDING_PROSPECTS.md`.

  **Build sequence:** (1) staff roster + availability; (2) define labor standards per station; (3) demand →
  headcount model per event; (4) assignment engine (fill slots, flag gaps/conflicts); (5) staff-facing shift
  view + Lance's scheduling view; (6) reminders; (7) later — auto-suggest staffing from event crowd
  estimates, plus time tracking / labor-cost.

  **Interlocks with the other backlog systems:** required headcount depends on event **crowd estimates**
  (the prospect research) and menu **throughput** (the inventory/recipe BOM) — build them so they can share
  data. *(added 2026-07-13)*
