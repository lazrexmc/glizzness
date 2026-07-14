# OPS_PLATFORM.md — the integrated operations platform ("one vehicle, six spokes")

**Date:** 2026-07-13 · **Status:** architecture blueprint (design phase; parts spec'd/scoped separately).

This is the **connective tissue** the rest of the docs don't have. Each part is scoped on its own
(`docs/superpowers/specs/2026-07-13-scout-board-design.md` for the Scout board; `TODO.md` for the rest).
**This doc is the chassis** — how the six parts share data and tie into one working system.

> Owner's framing (2026-07-13): *"all of these items are a wheel to the same vehicle… if we stop, it
> stops."* The whole point is that these are **not six features** — they're one machine. Build them so
> they share a spine, or you build something you have to rip out. See [[feedback-work-style]].

---

## The six parts

1. **Midwest Event Finder** — *discover* events worth vending at (public map; `site/festivals/`).
2. **Scout board** — *triage* which discovered/inbound events to actually pursue (private; spec'd).
3. **Demand baseline** — *learn* expected demand per event-type from sales history (the brain).
4. **Staffing model** — *crew* needed per event (venue-agnostic; orders/hr ÷ sustainable pace).
5. **Inventory + reorder** — *stock* needed per event (recipes × expected items).
6. **Scheduling** — *who works* each event (fill the crew count from staff availability).

(+ the **Square → Wave accounting** automation — already live — is the money spine and a key data source.)

---

## The chassis: one shared spine

Everything bolts to **two core entities**:

- **`events`** — every gig, from *all* sources: a Finder pick, a Scout "yes," a proven-recurring (the
  late-night bar trade, Logboat), a catering booking, even an **orphan sales-day the data reveals**. One
  row = *when · where · type · crowd estimate · `service_mode`*. **Five of the six parts read this.**
- **`orders`** — the Square sales (`Sales/items-*.csv`, timestamped to the second, with transaction IDs).
  The **ground truth** of what actually happened, and the **feedback signal** that makes the system learn.

## The brain: the demand baseline

The one part that **joins `events` + `orders`** and learns a **demand profile per event-type**:
expected orders, the **rush curve** (from order timestamps), capture rate, items/order, and `service_mode`.
**Without it, staffing and inventory are just guessing.** It's the flywheel; Square sales are the odometer.

---

## How the six bolt on (inputs → outputs)

| Part | Reads | Writes |
|---|---|---|
| **Finder** | `vending_events` | surfaces opportunities to the Scout board |
| **Scout board** | Finder prospects + inbound leads | **committed events** → the spine (a "yes") |
| **Demand baseline** | `events` + `orders` (Sales) | **demand profiles** per event-type |
| **Staffing** | an event + its demand profile | **crew count** → Scout card + the schedule |
| **Inventory** | events + demand profile + **recipes/BOM** | **buy/reorder list** |
| **Scheduling** | events + crew count + staff availability | **the roster** (who works what) |

## The loop — predict → do → measure → improve

```
   Finder ─discover→ Scout ─decide→ [event lands on the spine]
                                          │
                            Demand baseline predicts orders + shape
                                          │
                     ┌────────────────────┼────────────────────┐
                  Staffing             Inventory            Scheduling
                 (how many)           (what to buy)          (who works)
                                          │
                               cart works the event
                                          │
                   Square sales ──feed back──► the baseline gets smarter
```

Every event worked makes the next prediction sharper. That feedback loop is what makes it a *platform*
and not six disconnected tools.

---

## Two populations of events (they enter through different doors)

- **Proven-recurring** — the late-night bar trade, Logboat, Mizzou games. Already known to pay, so they
  **skip the Scout board** and go straight to staffing/inventory/scheduling.
- **New / unproven prospects** — dirt tracks, wineries, inbound requests. These need the **Finder → Scout**
  path *before* they ever need staffing.

Both land on the same `events` spine; they just enter from different doors.

---

## What already exists (map the current pieces to the spine)

| Current system / data | Role in the platform |
|---|---|
| `vending_events` / `vending_event_schedules` (Supabase) | Finder discovery layer |
| `event_prospects` / `prospect_decisions` / `prospect_thread` (planned — Scout spec) | Scout triage + committed events |
| `cart_schedule` (Supabase, from Google Calendar) | the *committed schedule* (where the cart WILL be) |
| `catering_leads` (Supabase) | catering bookings — one source of committed events |
| `Sales/items-*.csv` (local, gitignored) | the `orders` ground truth (feeds the baseline) |
| Square → Wave (Streamlit/Supabase) | the money spine + a data source |

---

## The little things to tie together (honest inventory of open decisions)

This is the part that "sucks" — the connective decisions nobody's made yet. Naming them IS the work:

1. **The events-spine decision.** Unify every event source into ONE `events` table, or keep them separate
   and build a **canonical "committed gigs" view** that joins them? *Lean:* a canonical committed-events
   view/table that the baseline + staffing + inventory read, kept **distinct** from the discovery
   (`vending_events`) and triage (`event_prospects`) tables — those have different lifecycles. Don't force
   one mega-table. **This is the first real decision; five parts depend on it.**
2. **`service_mode`** enum (`rolling` / `batch` / `mixed`) — where it's set, and how the baseline infers it
   from transaction shape (few-items-big-invoice = catering/batch; many-items-one-ticket = private tab).
3. **Demand-profile storage** — where the baseline's learned outputs live (a `demand_profiles` table keyed
   by event-type: expected orders, rush curve, capture %, items/order).
4. **How proven-recurring events enter** (they skip Scout) — a way to mark/auto-generate them onto the spine.
5. **Event identity across systems** — one canonical key that ties a Finder id ↔ a Scout id ↔ a calendar
   entry ↔ an inferred orphan sales-day, so nothing double-counts.
6. **Orphan sales-day classification** — turning Sales clusters with no calendar match into `events` (the
   late-night bar trade, private parties). Human-in-the-loop labeling; Square is *when*, not *where*.
7. **Menu recipes / BOM** — the item→ingredients map that inventory depletion needs.
8. **The labor standard** — the sustainable per-person pace (config input for staffing).

---

## Critical path (build order that respects the dependencies)

1. **Decide the events spine** (#1 above) — five parts read it, so it's first.
2. **Demand baseline** — **now buildable**: its two inputs are `events` + the Square sales, and the sales
   are in hand (`Sales/items-*.csv`). This is the first real unlock and the brain everything else needs.
3. **Staffing / Inventory / Scheduling** — become *trustworthy* only once the baseline exists (before that
   they guess). Build after.
4. **Scout board** — the front door (already spec'd). Can build in parallel; it writes committed events to
   the spine and shows the staffing model's crew estimate on each card.

---

## Pointers

- Scout board design: `docs/superpowers/specs/2026-07-13-scout-board-design.md`
- Every part's own scope + the owner's model refinements: `TODO.md` (staffing item has the venue-agnostic +
  demand-shape + transaction-shape notes; demand-baseline item has the sales-are-the-spine notes)
- The sales data + review: `Sales/items-*.csv` (gitignored), reviewed 2026-07-13
- Data model / existing schema: `DATA_MODEL.md`
- Memory: [[project-admin-hub-scout]], [[project-vending-circuit]], [[project-event-history]]
