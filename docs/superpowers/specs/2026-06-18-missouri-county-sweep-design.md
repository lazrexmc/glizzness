# Missouri County Sweep — Design Spec

**Date:** 2026-06-18
**Project:** Vending Circuit (sub-project of Glizzness)
**Author:** Lance McCarter (with Claude)

## Background

The Vending Circuit is a researched list of food-truck-vendable events for The Glizzness,
normalized into Supabase (`vending_*` tables) and shown on a static Leaflet map
(`festivals.glizzness.com`). It currently holds **127 events (124 published)** across 17
geographic market hubs, built from 12 adversarially-verified deep-research passes.

The pipeline is: edit the flat master `VendingCircuit.csv` → `vending_circuit_etl.py`
(derives normalized fields → `data/events.csv`) → `vending_circuit_geocode.py` (city-level
lat/lng + `data/event_schedules.csv`) → `vending_circuit_gen_sql.py` (→ `supabase_vending_data.sql`)
→ re-run the SQL in Supabase (idempotent truncate+insert). The map reads the live tables via
the anon key.

This spec covers a **Missouri county-by-county coverage sweep** plus two small enabling
improvements. It is the next priority, replacing the previously-discussed fee research (dropped).

## Goals

1. **Per-row `last_verified`** — make event freshness honest per row.
2. **`county` field + county map filter** — capture Missouri county granularity while keeping
   the existing 17 market hubs.
3. **Mid-MO county sweep, batch 1** — lightweight capture of *all plausibly-vendable* fairs,
   carnivals, festivals, and parades in the 14 central-Missouri counties listed below, then a
   reassess gate before any statewide continuation.

## Non-goals / out of scope

- **Fee research** for the 112 "Not researched" events — explicitly dropped.
- **Caveat verification** for the existing 11 `needs_confirmation` events — deferred (not dropped).
- **Non-MO thin markets** (Central IL/KS, Lincoln, Central AR, Des Moines, Quad Cities) — deferred.
- **Missouri counties beyond batch 1** (the other ~100 counties + St. Louis City) — gated on the
  batch-1 reassess.
- **Deep per-event detail** on swept events — captured lightweight; user backfills the good ones later.

---

## Piece 1 — Per-row `last_verified`

**Problem:** `last_verified` is a single global constant (`LAST_VERIFIED = "2026-06-17"`) in
`vending_circuit_etl.py`. Every event gets the same date, so a partial refresh can't truthfully
stamp only the rows it touched, and `freshness_report.py`'s "stale > 365 days" check is meaningless.

**Change:**
- Add a `last_verified` column to **`VendingCircuit.csv`** (the master).
- Backfill all 127 existing rows with `2026-06-17` (their current effective value).
- In `vending_circuit_etl.py`: read `r.get("last_verified")` per row; fall back to a module
  default (today's pass date) when blank, so new rows without an explicit value still get stamped.
- Downstream is unchanged: `events.csv` already carries `last_verified`; `freshness_report.py`
  already reads it.

**Acceptance:** ETL run produces `data/events.csv` where existing rows keep `2026-06-17` and any
new/edited rows show their own date; `freshness_report.py` `[4]` section reflects per-row dates.

---

## Piece 2 — `county` field + county filter

Per the chosen structure: tag events with county, **keep the 17 hubs** (events still roll up to
the nearest existing MO hub).

**Data model:**
- Add a `county` column to **`VendingCircuit.csv`** (stored explicitly per row — the research pass
  already knows the county; we do not build a city→county derivation table).
- Backfill the existing 127 rows' counties via a one-time city→county map for the ~50 known cities
  (MO cities required; out-of-state may be left blank for now and backfilled opportunistically).
- `vending_circuit_etl.py`: pass `county` straight through to `data/events.csv`.
- `supabase_vending_schema.sql`: add `county text` to `vending_events` (schema re-run is a
  drop+recreate; safe with the idempotent data reload).
- `vending_circuit_gen_sql.py`: include `county` in the generated INSERTs.

**Map (`vending-map/`):**
- Drawer: show county in the location line (e.g., "Columbia, MO · Boone County").
- Filter bar: add a **County `<select>`**, default "Any county", populated only with counties that
  actually have events (stays short early on). Wire it into `FILT`/`passesFilter`/`applyFilters`
  exactly like the existing month/friendly/trip filters.
- Regenerate `embed.html` via `build_embed.py` after the map changes.

**Decision:** county filter is always present (default "Any county"), consistent with the other
filters — not conditionally shown.

**Acceptance:** map loads with a working County filter; selecting a county narrows Tier 1 hub
counts and Tier 2 pins; drawer shows county; `embed.html` regenerated.

---

## Piece 3 — Mid-MO county sweep, batch 1

**Counties (14):** Boone, Callaway, Cole, Cooper, Howard, Randolph, Audrain, Moniteau, Morgan,
Osage, Gasconade, Pettis, Saline, Montgomery.

**Method:** serial deep-research passes — **one county or a small county-group at a time** (the
logged rate-limiter rule; never fan out). Each pass adversarially verified for event existence and
date. Capture **all plausibly-vendable events**: fairs, carnivals (incl. church/parish picnics),
festivals, and parades *that have real vending*. Skip parade-only events with no vending and very
small gatherings.

**Lightweight capture — fields per event:**

| Field | Batch-1 capture |
|---|---|
| `event_name` | required |
| `city`, `state` | required |
| `county` | required (the sweep key) |
| `typical_dates` | required — the date string (drives `event_schedules` + month filter) |
| `month` | required — derived from the date |
| `distance_mi` | rough estimate from Columbia (these are close-in; the number only buckets trip-type) |
| `status` | `Verified - vending unconfirmed` (→ ETL: verified + needs_confirmation + food-fit unconfirmed) |
| `url` | captured when the research source provides one (provenance); else blank |
| `last_verified` | today's pass date |
| `food_vendor_fee` | `Not researched` |
| `application_method`, `contact`, `attendance`, `notes` | blank / `TBD` — user backfills later |

The `Verified - vending unconfirmed` status makes each swept event **publish on the map with the
amber "verify before relying" badge** — correct for an un-vetted lead. The user later upgrades the
status/details on the ones worth pursuing.

**New towns:** any city not already known needs a one-line addition to:
- `vending_circuit_etl.py` `CITY_HUB` (city → nearest MO hub id: 1 Mid-MO or 4 Springfield/Ozarks), and
- `vending_circuit_geocode.py` `C` (city → county-seat/city centroid lat/lng).
Missing either leaves the event unmapped (market_id=0) or ungeocoded (no pin) — both excluded by the
gate. The geocoder's ring-offset already de-overlaps same-city events.

**Fold + checkpoint (run after the batch):**
```
python vending_circuit_etl.py
python vending_circuit_geocode.py
python vending_circuit_gen_sql.py
# re-run supabase_vending_data.sql in the Supabase SQL editor
# regenerate VendingCircuit.md (human view) and embed.html
python freshness_report.py
# commit + push to master
```

**Reassess gate:** after batch 1, review yield (events found / effort / Mid-MO pin density) and
decide whether to continue to the rest of Missouri. Do **not** auto-continue statewide.

**Acceptance:** the 14 counties' vendable events are in `VendingCircuit.csv` (lightweight),
publish on the map under the correct hub + county with the verify badge, the County filter lists
the new counties, freshness report is clean, and the batch is committed + pushed.

---

## Data model change summary

| File | Change |
|---|---|
| `VendingCircuit.csv` | + `last_verified` column, + `county` column; backfill 127 rows; add batch-1 rows |
| `vending_circuit_etl.py` | per-row `last_verified`; pass `county` through; new `CITY_HUB` entries |
| `vending_circuit_geocode.py` | new `C` centroid entries for new towns |
| `vending_circuit_gen_sql.py` | include `county` in INSERTs |
| `supabase_vending_schema.sql` | + `county text` on `vending_events` |
| `vending-map/index.html`, `app.js` | County filter + drawer county line |
| `embed.html` | regenerated via `build_embed.py` |
| `DATA_MODEL.md` | document `county` column + per-row `last_verified` |

## Risks / watch-items

- **Mid-MO pin density:** capturing all events across 14 counties may push hub 1 (and 4) well past
  ~20 pins, breaking the assumption that justified skipping marker clustering. The county filter
  mitigates it; revisit clustering at the reassess gate if density is bad.
- **Distance estimates:** rough miles are fine for trip-type buckets; not represented as exact.
- **Positional event `id`:** still row-order (truncate+insert reload). Unchanged; acceptable.
- **Volume vs. lightweight detail:** by design, many new rows will be thin leads with the verify
  badge — expected, not a defect.

## Sequencing

Piece 1 → Piece 2 → Piece 3 (pieces 1–2 are prerequisites so swept rows get a real `last_verified`
and `county` cleanly). Pieces 1 and 2 can be implemented and committed together as a
"pipeline + schema upgrade" before the research begins.
