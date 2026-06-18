# Vending Circuit Map

A self-contained, static web map of food-truck-vendable events for The Glizzness, reading
live from Supabase. Two-tier, rendering-minimal: **market hubs → click a hub → its events →
click an event → detail drawer** (with the event's homepage link shown only when one exists).

No build step, no server, no framework. Plain HTML + Leaflet + vanilla JS.

## Files
| File | Purpose |
|---|---|
| `index.html` | Markup, styling, Leaflet + script includes |
| `app.js` | Map logic: load markets/events from Supabase, two-tier render, detail drawer |
| `config.js` | Supabase URL + **anon public** key (you fill the key) |

## Setup (one step)
1. Supabase dashboard → **Project Settings → API** → copy the **`anon` `public`** key.
2. Paste it into `config.js` as `SUPABASE_ANON_KEY`.

The anon key is **safe to expose** in a client app: the `vending_*` tables have public-read
RLS policies; the accounting tables have **no** policies and stay blocked. The map can only
read the vending data.

## Run locally
Just open `index.html` in a browser (double-click), or serve the folder:
```
python -m http.server 8000        # then visit http://localhost:8000/vending-map/
```

## Deploy (free options)
- **GitHub Pages:** enable Pages on the repo → the map is at `…/vending-map/`.
- **Netlify / Cloudflare Pages:** drag-drop the `vending-map/` folder, or connect the repo.

(For GitHub Pages the committed `config.js` must contain the real anon key — that's fine, it's
public-safe.)

## Data source
Reads two REST endpoints with the anon key:
- `vending_markets` — 17 hub pins (Tier 1)
- `vending_events` filtered to the publish gate (`verification_status in (verified,partial)`,
  `food_truck_friendly <> excluded`, `lat not null`) — ~124 events, rendered per-market (Tier 2)

Both fetched once on load (small payload); rendering is tiered so only one market's pins are on
the map at a time. To change what's published, edit the rows in Supabase (or re-run the ETL +
reload) — the map reflects it on refresh.

## Architecture notes
- **Tier 1** renders only the 17 market circle-markers (sized by event count).
- **Tier 2** clears the hub layer and renders just the selected market's event markers
  (colored by food-truck-friendliness), fit-bounds to them.
- **Tier 3** opens the side drawer with dates, size, distance/trip-type, application method,
  contact, fee (if known), notes, and a conditional **Event page** button.
- "← All markets" returns to Tier 1.

## Roadmap (Phase 6 — not yet built)
Filters (by month / food-truck-friendly / day-trip vs overnight), default-hide toggle for
defunct/excluded, marker clustering if the set grows, and mobile polish.
