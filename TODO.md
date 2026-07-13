# The Glizzness — TODO / Backlog

Running list of open action items. Add dated entries; check them off or delete when done.
(For the full go-live sequence see `GO_LIVE.md`; for strategy see the north-star spec.)

## Open

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
  - **(d) Auto-reply** — *still open.* Send the customer a "thanks, we'll be in touch" confirmation on submit.
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
  - **Festival / vending map — ✅ DONE (2026-07-13).** Moved from `vending-map/` (a standalone
    `festivals.glizzness.com` site on Netlify) into **`site/festivals/`**, so it now ships with the main
    Cloudflare Pages site and serves at **`glizzness.com/festivals`** (`glizzness.pages.dev/festivals`
    until the custom domain switches). **Netlify is retired** (root `netlify.toml` archived to
    `archive/2026-07-13/`). `site/events.html` links to it. Ships with the event-type filter + 442 events.
  - **Accounting dashboard** (`glizzness.streamlit.app`) — *still open* — internal, password-protected admin tool.
    Optionally reachable at a memorable subdomain (e.g. `admin.glizzness.com`) via CNAME/Cloudflare — note
    Streamlit Community Cloud has limited custom-domain support (may need a Cloudflare proxy/Worker; watch
    the websocket). Keep it OUT of the public nav. Lowest priority of the three.
  - Prereq: `glizzness.com` must be live on Cloudflare first (domain-switch task / `GO_LIVE.md §2`).
  *(added 2026-07-13)*

- [ ] **Trint's event-triage app ("Scout board") — yes / no / maybe on prospect events** — the 7-run
  vending research (`VENDING_PROSPECTS.md`) produces far too many events for Trint to sort out via the map.
  Build him a dead-simple, phone-first decision tool. *(Backlog — build after the 7 research runs are
  compiled; not urgent.)*

  **Concept:** a private, mobile-first **card feed** (NOT the map) — one card per prospect event with big
  **✅ Yes / 🤔 Maybe / ❌ No** buttons and an **"❓ Ask a question"** field. Grouped by date, and — unlike the
  public "Where We Vend" list — it **must show multiple events on the same day**. Trint taps through; his
  answers + questions land where Lance can act on them (Lance researches the questions, books the Yeses).

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

  **Why it matters:** empirical backbone for the employee-scheduling model above — turns "guess the crowd"
  into "at events like this we did $X / N orders → need M hands," and tells the Scout board which event
  *types* actually paid off (which to rebook). *(added 2026-07-13)*

  **The philosophy (owner's — and it's a real ops concept, "labor standard / takt time"):** set a target
  sustainable throughput per station (e.g. 1 cook comfortably makes ~X items/hr, 1 cashier ~Y orders/hr),
  then staff each event to meet its expected demand AT that rate — so a bigger crowd means MORE
  stations/people, not a faster or more stressed Trint. Consistent pressure, consistent pace, at any volume.

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
