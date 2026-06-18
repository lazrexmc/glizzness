# Vending Circuit — Data Model & Normalization Spec (LOCKED)

> **Task 1 deliverable.** This is the contract the ETL/geocode/load phases build against.
> Source of truth today: `VendingCircuit.csv` (127 rows, flat). Target: a normalized
> relational model in Supabase Postgres feeding a two-tier map UI.

---

## 1. Publish scope (DECISION)

The throttled `Unverified-ratelimited` candidates were all replaced by clean, adversarially
verified passes, so there is no "unverified candidate" tier left to badge. Locked policy:

| Bucket | Rule | UI behavior |
|---|---|---|
| **Publish** | `verification_status IN (verified, partial)` AND `food_truck_friendly <> excluded` AND `lat/lng` present | Shown on map — this IS the `vending_published_events` gate view (124 rows) |
| **Flagged subset** | published rows where `needs_confirmation = true` (this includes every `partial` row) | Shown with a "verify before relying" badge |
| **Hide by default** | `verification_status IN (defunct, excluded)` | Kept in DB for the record; filtered out of default map view, reachable via a toggle |
| **Quarantine (not published)** | missing `lat/lng` or `market_id` | Excluded by the gate view until fixed |

> Note: `partial` (e.g. Illinois State Fair, SeptemberFest Omaha — dates/size soft) is published
> *with* the verify badge, not hidden. The implemented gate view is the single source of truth for
> what's live; the table above documents it.

Rationale: everything we have is food-truck-relevant and fact-checked; the only things worth
hiding are the dead (Roots N Blues) and the closed-to-trucks (Bartlett, Vala's). Caveated
events are still useful leads, so we publish them with a flag rather than dropping them.

---

## 2. Relational schema (LOCKED)

### `markets` — top-tier map hubs (~17 rows)
| column | type | notes |
|---|---|---|
| id | serial PK | |
| name | text | e.g. "Kansas City Metro" |
| anchor_city | text | e.g. "Kansas City" |
| state | text | primary state |
| center_lat / center_lng | double | map centroid for the hub pin |
| default_zoom | int | zoom level when this hub is selected |
| distance_from_columbia_mi | int | driving miles, anchor city |
| summary | text | one-line cluster description |

### `events` — one row per real event/venue  (AS IMPLEMENTED — matches `data/events.csv` + `supabase_vending_schema.sql`)
| column | type | notes |
|---|---|---|
| id | int PK | |
| market_id | int FK → markets | **required to publish** |
| name | text | |
| city / state | text | |
| event_type | enum (text+CHECK) | see §3 |
| cadence | enum (text+CHECK) | see §3 |
| is_recurring_venue | bool | true for taprooms/markets/food-truck courts |
| food_truck_friendly | enum (text+CHECK) | see §3 |
| trip_type | enum (text+CHECK) | see §3 (recomputed from distance in ETL) |
| verification_status | enum (text+CHECK) | see §3 |
| needs_confirmation | bool | true when a caveat applies (dates/app/year) |
| distance_from_columbia_mi | int | |
| month | text | convenience; normalized dates live in `event_schedules` |
| typical_dates | text | verbatim display string |
| attendance_estimate | int | nullable (parsed from attendance_text) |
| attendance_text | text | original string ("~300,000", "5,000-8,000/month") |
| food_vendor_fee | text | mostly "Not researched" (fees deferred) |
| application_method | text | free text (form / email / PDF / portal) |
| contact_name / contact_email / contact_phone | text | split from the source `contact` field |
| homepage_url | text | nullable — **drives the conditional UI link** |
| primary_source_url | text | provenance |
| **lat / lng** | double | **required to publish** (geocoded — Task 3); city-level + ring offset (approximate, not exact addresses) |
| notes | text | caveats, fit warnings |
| last_verified | date | when the row was last research-verified; powers `freshness_report.py` |

> Deferred / not yet implemented (add later if needed): `venue_name`, `address` (we geocode at
> city level, so these are unused for now), `application_url` (folded into `application_method` /
> `homepage_url`), and `created_at`/`updated_at` timestamps.

### `event_schedules` — normalizes the messy date field (1 event → many)
| column | type | notes |
|---|---|---|
| id | serial PK | |
| event_id | int FK → events | |
| month | int | 1–12 (nullable for pure-recurring) |
| start_date / end_date | date | nullable (year-specific instances) |
| recurrence_text | text | "first Friday", "2nd Friday Apr–Sep", "last Friday Mar–Oct" |
| display_text | text | human string kept verbatim from CSV `typical_dates` |
| year_specific | bool | |

### `sources` — provenance / trust
| column | type | notes |
|---|---|---|
| id | serial PK | |
| event_id | int FK → events | |
| url | text | |
| quality | text | primary / secondary / blog |

### `fees` — STUBBED (defined, left empty for now)
event_id FK · fee_type · amount · unit · notes. Fees were intentionally deferred; the few
captured incidentally (e.g., Nashville Oktoberfest ~$2,000, John C. Fremont $550, Branson $400,
Washington County Fair $300) live in `events.notes` / `food_vendor_fee` until a fee pass runs.

---

## 3. Controlled vocabularies (LOCKED enums)

**event_type:** `state_fair` · `county_fair` · `festival` · `food_truck_rally` · `farmers_market` ·
`oktoberfest` · `craft_fair` · `art_fair` · `music_fest` · `bbq_fest` · `balloon_fest` ·
`holiday_market` · `cultural_fest` · `venue` · `booking_platform`

**cadence:** `annual` · `multi_week` · `monthly` · `weekly` · `recurring` (intermittent) · `year_round`

**food_truck_friendly:** `explicit_yes` · `concession_friendly` · `unconfirmed` · `excluded`

**trip_type:** `hometown` (≤15 mi) · `day_trip` (≤150 mi) · `overnight` (>150 mi)
→ **recompute from geocoded distance in ETL** (fixes legacy artifacts like Illinois State Fair
@140 mi currently tagged overnight).

**verification_status:** `verified` · `partial` · `defunct` · `excluded`

---

## 4. Status normalization map (current CSV `status` → new fields)

| current `status` string | verification_status | needs_confirmation | food_truck_friendly |
|---|---|---|---|
| Verified | verified | false | concession_friendly |
| Verified-regional | verified | false | (derive from notes) |
| Verified - food trucks / food-truck friendly / food vendors / seeks food vendors | verified | false | explicit_yes |
| Verified - vending unconfirmed | verified | true | unconfirmed |
| Verified - eligibility caveat | verified | true | concession_friendly |
| Verified - confirm running / confirm 2026 / confirm app method | verified | true | (derive) |
| Verified - 2026 passed | verified | true | (derive) |
| Verified location | verified | true | unconfirmed |
| Partial - verify dates | partial | true | (derive) |
| Medium confidence | partial | true | (derive) |
| Plan for 2027 | verified | true | explicit_yes |
| DEFUNCT - do not pursue | defunct | — | excluded |
| Excluded | excluded | — | excluded |

`food_truck_friendly` for `Verified-regional` rows is derived from the `notes` text in ETL
(e.g. "explicitly food-truck", "food trucks" → `explicit_yes`; "concession", "food vendors" →
`concession_friendly`; "weak fit", "doubtful", "NOT taking" → `unconfirmed`/`excluded`).

---

## 5. Market hubs (LOCKED — ~17 hubs)

A research pass ≠ a market. These geographic hubs are the map's top tier; each event maps to one.

| # | Hub | Anchor | States covered | ~mi from COMO |
|---|---|---|---|---|
| 1 | Columbia / Mid-Missouri | Columbia, MO | MO | 0 |
| 2 | Kansas City Metro | Kansas City, MO | MO, KS | 125 |
| 3 | St. Louis Metro (incl. Metro East) | St. Louis, MO | MO, IL | 125 |
| 4 | Springfield / Ozarks | Springfield, MO | MO | 165 |
| 5 | Central Illinois | Springfield, IL | IL | 140 |
| 6 | Des Moines | Des Moines, IA | IA | 200 |
| 7 | Quad Cities | Davenport, IA | IA, IL | 270 |
| 8 | Cedar Rapids / Iowa City | Cedar Rapids, IA | IA | 255 |
| 9 | Omaha Metro | Omaha, NE | NE, IA | 340 |
| 10 | Lincoln Area | Lincoln, NE | NE | 330 |
| 11 | Wichita / S-Central Kansas | Wichita, KS | KS | 280 |
| 12 | Central Kansas | Junction City, KS | KS | 150 |
| 13 | Tulsa Metro | Tulsa, OK | OK | 346 |
| 14 | NW Arkansas | Bentonville, AR | AR | 250 |
| 15 | Central Arkansas | Little Rock, AR | AR | 376 |
| 16 | Memphis | Memphis, TN | TN, MS | 290 |
| 17 | Nashville | Nashville, TN | TN | 431 |

Assignment is by city → hub (handled in Task 2). Sedalia (MO State Fair), Hannibal, Hermann,
Jeff City, Boonville, Moberly, Marshfield all roll up to **Mid-Missouri** or **Springfield/Ozarks**
by proximity; Council Bluffs IA rolls up to **Omaha**; Moline IL to **Quad Cities**; Fort Smith AR
to **NW Arkansas**.

---

## 6. Ready-for-next-phase checklist
- [x] Publish scope decided
- [x] Relational schema locked
- [x] Enums locked
- [x] Status→fields map defined
- [x] Market hubs enumerated
- [x] (Task 2) Consolidate + assign `market_id` + normalize enums → `data/markets.csv`, `data/events.csv` via `vending_circuit_etl.py` (127 events, 0 dupes, 0 unmapped)
- [x] (Task 3) Geocode lat/lng (city-level + jitter) + parse schedules → `data/event_schedules.csv` via `vending_circuit_geocode.py` (127/127 geocoded)
- [x] (Task 4) Load to Supabase — schema + data run in SQL editor; validation gate confirmed (17 markets / 127 events / 127 schedules / 124 published)
- [x] (Task 5) Two-tier Leaflet map (`vending-map/`) — data path verified via anon key
- [ ] (Task 6) Filters, defunct-toggle, marker clustering, mobile polish

---

## 7. Data freshness (manual, no scheduler)

The dataset is a point-in-time snapshot; what rots is mostly **dates** (events are annual —
the event persists, the date shifts each year). Kept fresh by hand, no services:

- **Tier 1 — `freshness_report.py`** (local, instant, offline): prints a punch-list —
  `needs_confirmation` rows, `partial` rows, date strings mentioning a recent past year, and
  rows whose `last_verified` is >365 days old. Run it anytime to see what needs attention.
- **Tier 2 — annual re-date pass** (Jan–Mar, when next-year dates publish): re-research the
  *existing* events, bump `LAST_VERIFIED` in `vending_circuit_etl.py`, regenerate, reload.
- **Tier 3 — periodic re-discovery** (every 1–2 yrs): full new/dead-event hunt.

**Reload is idempotent:** `supabase_vending_data.sql` does `truncate … restart identity cascade`
then inserts, so re-running it (after `supabase_vending_schema.sql` exists) fully refreshes the
data — handles added/removed events, no PK conflicts, no hand-patching.

> Note on positional ids: event `id` is row-order, not a stable natural key, so refreshes use
> truncate+insert (whole-table replace) rather than per-row upsert. If stable cross-refresh ids
> are ever needed (e.g., external references to an event), switch `id` to a name+city slug first.
