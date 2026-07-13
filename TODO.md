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

- [ ] **Unify everything under `glizzness.com` (one web address)** — consolidate the three properties so
  there's a single front door. *(Backlog — do AFTER the Cloudflare domain switch and the niche research
  runs; not urgent.)*
  - **Festival / vending map** (`vending-map/`, currently `festivals.glizzness.com` on Netlify) — wire it
    into the main site: embed `vending-map/embed.html` into the `site/events.html` placeholder ("Live map —
    coming soon"), or host it at a clean path like `glizzness.com/festivals`. **Clean up first:** Phase-6
    polish (event-type filter, defunct toggle, mobile), and confirm the prospecting map is meant to be
    public (organizer contacts are visible — already accepted as public). Decide: keep the Netlify
    subdomain vs. move the map into Cloudflare Pages as a subpath of the main site.
  - **Accounting dashboard** (`glizzness.streamlit.app`) — internal, password-protected admin tool.
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
