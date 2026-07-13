# Vending Circuit — Data Model & Normalization Spec (LOCKED)

> **Task 1 deliverable.** This is the contract the ETL/geocode/load phases build against.
> Source of truth today: `VendingCircuit.csv` (415 rows, flat). Target: a normalized
> relational model in Supabase Postgres feeding a clustered map UI.

---

## 1. Publish scope (DECISION)

The throttled `Unverified-ratelimited` candidates were all replaced by clean, adversarially
verified passes, so there is no "unverified candidate" tier left to badge. Locked policy:

| Bucket | Rule | UI behavior |
|---|---|---|
| **Publish** | `verification_status IN (verified, partial)` AND `food_truck_friendly <> excluded` AND `lat/lng` present | Shown on map — this IS the `vending_published_events` gate view (400 rows) |
| **Flagged subset** | published rows where `needs_confirmation = true` (this includes every `partial` row) | Shown with a "verify before relying" badge |
| **Hide by default** | `verification_status IN (defunct, excluded)` | Kept in DB for the record; filtered out of default map view, reachable via a toggle |
| **Quarantine (not published)** | missing `lat/lng` or `market_id` | Excluded by the gate view until fixed |

> Note: `partial` is published *with* the verify badge, not hidden. As of the 2026-06-18
> confirmation pass the `partial` tier is currently empty (Illinois State Fair & SeptemberFest
> Omaha were both upgraded to `verified` once dates were confirmed). The implemented gate view is
> the single source of truth for what's live; the table above documents it.

Rationale: everything we have is food-truck-relevant and fact-checked; the only things worth
hiding are the dead (Roots N Blues) and the closed-to-trucks (Bartlett, Vala's). Caveated
events are still useful leads, so we publish them with a flag rather than dropping them.

---

## 2. Relational schema (LOCKED)

### `markets` — geographic map hubs (31 rows)
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
| county | text | county/parish; stored per row in `VendingCircuit.csv`, powers the map's county filter (esp. the Missouri sweep) |
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
| last_verified | date | when the row was last research-verified; powers `freshness_report.py`. **Per-row** — stored in `VendingCircuit.csv` (one date per event), not a global constant, so a partial refresh can stamp only the rows it touched. The ETL falls back to `LAST_VERIFIED_DEFAULT` only for rows that leave it blank. |

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

### Prospects layer — the 7-run research overlay (`data/prospects.csv`)

A second, independently-maintained dataset of **27 niche vending "prospects"** mined from a 7-run
deep-research sweep (`VENDING_PROSPECTS.md`, 2026-07-13): mountain-bike/gravel races, sports
tournaments, rodeos, car/air shows, dirt tracks, wineries, and moto rallies. They load into the
**same** `vending_events` / `vending_event_schedules` tables and render on the same map, but live in
their own files so the vending-circuit ETL never touches them.

- **`build_prospects.py`** → generates **`data/prospects.csv`** (event rows, same schema as
  `data/events.csv`) + **`data/prospect_schedules.csv`**, from a curated `P` table of the research
  findings. Re-run (`python build_prospects.py`) after editing that table.
- **IDs start at 500** (circuit events top out at 415) so the two datasets never collide, and the ETL
  (`VendingCircuit.csv` → `data/events.csv`) can regenerate the circuit without clobbering prospects.
  Prospects are **not** produced by the ETL — they are a separate curated file.
- **Loading:** `vending_circuit_gen_sql.py` folds `data/prospects.csv` + `data/prospect_schedules.csv`
  into `supabase_vending_data.sql` right after the circuit rows, so one idempotent `truncate+insert`
  reload refreshes both. Combined load = **442 events / 442 schedules / 31 markets** (415 circuit + 27
  prospects), ~433 published (all but the `excluded` prospects).
- **New `event_type`s** added to the schema CHECK enum (see §3): `mtb_gravel`, `sports_tournament`,
  `rodeo`, `car_show`, `air_show`, `dirt_track`, `winery`, `moto_rally`. The map's event-type filter
  (`f-type`) surfaces them.
- **Food-access mapping** — the research's food-vendor verdicts map onto `food_truck_friendly`:
  `explicit_yes` = venue is open / welcomes carts (e.g. Rocheport Second Saturdays, Augusta
  festivals); `concession_friendly` = apply-to-vend / contracted booths; `unconfirmed` = policy
  unstated, must call before committing; `excluded` = closed or directly competing (e.g. Double X
  Speedway sells its own $1.50 hot dogs). `excluded` rows load but the publish gate hides them.

---

## 3. Controlled vocabularies (LOCKED enums)

**event_type:** `state_fair` · `county_fair` · `festival` · `food_truck_rally` · `farmers_market` ·
`oktoberfest` · `craft_fair` · `art_fair` · `music_fest` · `bbq_fest` · `balloon_fest` ·
`holiday_market` · `cultural_fest` · `venue` · `booking_platform`
→ **extended 2026-07-13** for the 7-run research prospects (see "Prospects layer" in §2):
`mtb_gravel` · `sports_tournament` · `rodeo` · `car_show` · `air_show` · `dirt_track` · `winery` ·
`moto_rally`.

**cadence:** `annual` · `multi_week` · `monthly` · `weekly` · `recurring` (intermittent) · `year_round` ·
`one_time` (single-date concerts/prospects)

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

## 5. Market hubs (31 hubs)

A research pass ≠ a market. These geographic hubs are the map's top tier; each event maps to one.
Hubs 18–26 were added in the 2026-06-18 statewide Missouri sweep: 18–21 southern/SE (Mark Twain
sector), 22–24 north + west-central ring, 25–26 Bootheel + Northwest. Hannibal moved from hub 1 to
hub 22 (Northeast Missouri). Hubs 27–31 were then added for the out-of-region corridor network
(Indianapolis, I-70 STL–Indy, I-74 QC–Indy, Louisville, Evansville/Tri-State).

> **Hub # is now display-agnostic.** Since the map switched to zoom-based marker clustering
> (location-based), the hub number only keeps the data sane / non-zero (`market_id = 0` is
> quarantined) — it no longer drives any map tier. New off-corridor towns (e.g. the 2026-06-18
> interior gap-fill across S. IL / S. IA / NE OK / N-NE AR / W. KY) are mapped to the **nearest
> existing hub** rather than spawning new hubs.

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
| 18 | Lake of the Ozarks | Osage Beach, MO | MO | 70 |
| 19 | Rolla / I-44 Corridor | Rolla, MO | MO | 100 |
| 20 | Southeast Missouri | Cape Girardeau, MO | MO | 205 |
| 21 | South-Central Ozarks | West Plains, MO | MO | 150 |
| 22 | Northeast Missouri | Hannibal, MO | MO | 105 |
| 23 | North-Central Missouri | Kirksville, MO | MO | 95 |
| 24 | West-Central Missouri | Warrensburg, MO | MO | 85 |
| 25 | Bootheel | Kennett, MO | MO | 250 |
| 26 | Northwest Missouri | St. Joseph, MO | MO | 150 |
| 27 | Indianapolis Metro | Indianapolis, IN | IN | 480 |
| 28 | I-70 Corridor (STL–Indy) | Effingham, IL | IL, IN | 200 |
| 29 | I-74 Corridor (QC–Indy) | Champaign, IL | IL, IN | 250 |
| 30 | Louisville Metro | Louisville, KY | KY, IN | 360 |
| 31 | Evansville / Tri-State | Evansville, IN | IN, IL, KY | 230 |

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
- [x] (Task 2) Consolidate + assign `market_id` + normalize enums → `data/markets.csv`, `data/events.csv` via `vending_circuit_etl.py` (415 events, 0 dupes, 0 unmapped)
- [x] (Task 3) Geocode lat/lng (city-level + jitter) + parse schedules → `data/event_schedules.csv` via `vending_circuit_geocode.py` (415/415 geocoded)
- [x] (Task 4) Load to Supabase — schema + data run in SQL editor; validation gate confirmed (31 markets / 415 events / 415 schedules / 410 published). **With the prospects overlay folded in (2026-07-13) the loaded totals are 442 events / 442 schedules / ~433 published** — see the Prospects layer in §2.
- [x] (Task 5) Leaflet map (`vending-map/`) — data path verified via anon key
- [x] (Task 6) Filters (month/fit/trip/**county**), defunct-toggle, mobile polish
- [x] (Map) **Zoom-based marker clustering** (Leaflet.markercluster) — replaced the two-tier
  hub→event→back model with colored dots that group/scatter by zoom (2026-06-18)
- [x] (Cleanup) Per-row `last_verified` + `county` column + `vending_circuit_gen_md.py` (regenerable human view)
- [~] (MO county sweep) Lightweight capture of plausibly-vendable events, county by county. New rows
  carry `status = "Verified - vending unconfirmed"` (verify badge); details deferred for backfill.
  - **Batch 1** — 14 central-MO counties (Boone, Callaway, Cole, Cooper, Howard, Randolph, Audrain,
    Moniteau, Morgan, Osage, Gasconade, Pettis, Saline, Montgomery) → +27 events.
  - **Batch 2** — southern/SE "Mark Twain" sector (~28 counties across hubs 18–21: Lake of the Ozarks,
    Rolla/I-44, Southeast MO, South-Central Ozarks) → +36 events.
  - **Batch 3** — north + west-central ring (~18 counties across hubs 22–24: Northeast MO, North-Central
    MO, West-Central MO) → +19 events.
  - **Batch 4** — rest of state: deep Bootheel (hub 25), far Northwest/St. Joseph (hub 26), and the SW
    corner (Carthage/Joplin into hub 4) → +16 events. **Total now 225 / 222 published, 26 hubs.**
    Missouri is broadly covered; remaining work is detail backfill + occasional infill.
  - **Indianapolis Metro (hub 27)** — added on request as an out-of-region major market: +15 events
    (Marion/Hamilton/Johnson/Hendricks/Hancock counties, IN). **Total now 240 / 237 published, 27 hubs.**
  - Density is now handled by zoom-based clustering (the old per-hub pin density watch-item is moot).
  - **Boone County nightlife / mass-gathering pass (2026-07-06, one adversarially-verified deep-research
    run):** +12 Columbia/Boone events targeting the gap categories — breweries/venues (Logboat, Bur Oak,
    Cooper's Landing = explicit_yes, kitchen-free truck hosts; Rose Music Hall/Rose Park = unconfirmed),
    Show-Me State Games + Mizzou football home games + First Fridays + Market at Serendipity
    (unconfirmed/concession), **2 `one_time` concerts** (Pixies 9/23/26, Modest Mouse 9/24/26), and 2
    `excluded` dead-ends (Broadway Brewery Taproom = own kitchen; Boone County Farmers Market =
    producer-only, no resale). **Total now 415 / 410 published, 31 hubs.**
  - **Data confirmation pass** (event by event, filling application_method/contact/homepage/fee +
    clearing the verify badge): **ALL Missouri hubs done** — Mid-MO 33/41, KC 13/13, St. Louis 11/11,
    Springfield 19/19, regional hubs 18-26 58/64. ~14 MO events left intentionally flagged (weak/uncertain
    fit, ticketed music fests, unpublished contacts). Backlog now 82 - remainder is mostly out-of-state
    corridor/Indy lightweight leads (not yet confirmed).
    NOTE: clearing the badge means changing `status` AND scrubbing the word "confirm"/"verify" from the
    row's notes — those substrings re-trigger needs_confirmation/unconfirmed in the ETL.
  - **Corridor network (hubs 28–31)** — added I-70 (STL–Indy), I-74 (QC–Indy), Louisville, and
    Evansville/Tri-State; corridor intermediates fold into the nearest hub. KC–Topeka–Wichita–Tulsa
    and I-40/I-49 events folded into existing hubs. Plus nearby-STL infill (Franklin/Warren,
    Jefferson, St. Charles counties) and 4-area fill (mid-MO, Lake of the Ozarks).
  - **Full confirmation pass (2026-06-18)** — every flagged lead across ALL 31 hubs researched
    event-by-event (dates + food-vendor application + contact); `needs_confirmation` 133 → 3 (only
    Walk Back in Time, Clarkton Purple Hull Pea, Deutsch Country Days left honestly flagged for
    unverifiable 2026 dates). Reproducible from `confirm_updates.py` (133 records).
  - **Interior gap-fill, batch 1 (2026-06-18)** — off-corridor counties inside the footprint:
    S. Illinois (+12), S. Iowa (+6), NE Oklahoma (+5), N/NE Arkansas (+6), West Kentucky (+6) =
    **+35 lightweight leads** via `add_gap_events.py`.
  - **Interior gap-fill, batch 2 (2026-06-18)** — final 4 regions: S. Indiana (+6), SE Nebraska (+6),
    SE Kansas (+5), West Tennessee (+6) = **+23 lightweight leads**. Interior gap-fill now complete
    (all 9 regions across the footprint).

> **Current totals:** the vending circuit is **415 events / 410 published / 31 hubs**; 0 unmapped,
> 0 missing coords; `needs_confirmation` = 61 (3 prior holds + 58 gap-fill leads). Adding the 7-run
> research overlay (**+27 prospects**, ids 500+ — see the Prospects layer in §2) the map/DB now load
> **442 events / 442 schedules / ~433 published**. The live default map count is lower because the
> date-aware "past events" and "music fests" toggles hide some rows by default (toggleable on).

---

## 7. Data freshness (manual, no scheduler)

The dataset is a point-in-time snapshot; what rots is mostly **dates** (events are annual —
the event persists, the date shifts each year). Kept fresh by hand, no services:

- **Tier 1 — `freshness_report.py`** (local, instant, offline): prints a punch-list —
  `needs_confirmation` rows, `partial` rows, date strings mentioning a recent past year, and
  rows whose `last_verified` is >365 days old. Run it anytime to see what needs attention.
- **Tier 2 — annual re-date pass** (Jan–Mar, when next-year dates publish): re-research the
  *existing* events, set their `last_verified` date in `VendingCircuit.csv` (per row), regenerate, reload.
- **Tier 3 — periodic re-discovery** (every 1–2 yrs): full new/dead-event hunt.

**Reload is idempotent:** `supabase_vending_data.sql` does `truncate … restart identity cascade`
then inserts, so re-running it (after `supabase_vending_schema.sql` exists) fully refreshes the
data — handles added/removed events, no PK conflicts, no hand-patching.

> Note on positional ids: event `id` is row-order, not a stable natural key, so refreshes use
> truncate+insert (whole-table replace) rather than per-row upsert. If stable cross-refresh ids
> are ever needed (e.g., external references to an event), switch `id` to a name+city slug first.
