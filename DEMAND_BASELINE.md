# Demand Baseline — runbook

The "brain" of the ops platform (`OPS_PLATFORM.md`): distills 4 years of Square sales
(**15,407 orders → 639 selling sessions**) into per-venue and per-session-type **demand profiles** —
orders/hr, crew needed, units sold, prep mix — and serves them to the Scout board so Trint's card
says **"Crew: 1–2 · Prep: Glizzy ×18"** on evidence instead of a guess.

- **Script:** `demand_baseline.py` (reads LOCAL gitignored exports; writes local outputs + optional SQL)
- **Profiles table:** Supabase `demand_profiles` (`supabase_demand_schema.sql`; RLS authenticated-only + anon revoked)
- **Consumers:** `site/assets/demand.js` → Trint's card (`/scout`) + Lance's desk (`/hub/desk`)
- *(Filenames: this runbook is `DEMAND_BASELINE.md`; the generated report is
  `demand_baseline_report.md` — distinct names because Windows is case-insensitive.)*

---

## The headline finding (why this is built the way it is)

**The Google Calendar is NOT the business.** Measured against the sales:

| | sessions | revenue |
|---|---:|---:|
| with a calendar event | 172 (27%) | ~$58k (31%) |
| **no calendar event (orphans)** | **467 (73%)** | **~$128k (69%)** |

So the pipeline clusters the **sales first** (ground truth), attaches a calendar event where one
matches, and auto-classifies the orphans by transaction signature (late-night bar trade / private
party one-payer / big tab settled at close / unlogged daytime gig). Joining off the calendar would
have modelled a third of the business. *(Owner's call, 2026-07-13 — the data proved it decisively.)*

## The numbers that matter

- **Labor standard (owner-set 2026-07-16): 1 person ≈ 15 orders/hr sustainable**, +15% buffer.
  `crew = ceil(orders_hr × 1.15 / 15)`. Philosophy: scale volume by adding PEOPLE, never pace.
- Orders/hr across all sessions: **median 9.5 · p90 19.8 · max 49** (a 5.2× median→peak spread —
  the whole argument for staffing to the profile, not the average).
- **Logboat** (74 sessions): 1 person, ~18 units, ~$123/night. **Mizzou** (10 sessions): p90 =
  48.9 ord/hr → **4 hands**, ~$311. Opposite businesses; staff them differently.
- **Daytime lunch trade is the single biggest session type** (252 sessions) — the evidence behind
  the lunch-rush prospect seed (`supabase_lunch_prospects.sql`).

## How estimates reach a card (the matching ladder)

Most evidence wins, and the card says which rung it used:
1. **Manual `suggested_crew`** on the prospect — Lance's override, always wins.
2. **Venue history** — prospect name contains a profiled venue key → *"from 74 past sessions here"*.
3. **Event-type analog** — e.g. `lunch_rush`/`festival` → daytime sessions; `dirt_track`/`winery` →
   evening; marked **"(est.)"**.
4. **Overall median** of all 639 sessions — weakest, also "(est.)".

A guess never masquerades as evidence: only rung 2 omits the "(est.)" marker. The desk shows the
full basis + typical gross; Trint's card keeps it short (his design constraint).

## Refresh cycle (Lance)

1. Drop fresh Square item exports into `Sales/` (`items-YYYY-...csv`).
2. `python demand_baseline.py --sql`
   → regenerates `demand_baseline_report.md`, `data/demand_profiles.json`,
   **`supabase_demand_data.sql`**.
3. Paste `supabase_demand_data.sql` into the Supabase SQL editor → Run. (Idempotent: wipes +
   reloads the whole table.) The cards update on next page load. No deploy needed.

**One-time setup:** run `supabase_demand_schema.sql` once *before* the first data load.

`python demand_baseline.py --aliases` shows how the 94 historical item names collapse to ~25 real
items (4 spellings of the Glizzy = 13,078 sold) and which money/service lines are excluded from
prep. **Review it after menu renames** — drift here silently corrupts prep math.

## Honest limits (documented in the script, repeated here on purpose)

- **No crowd data** → a true capture rate is NOT derivable. A never-worked venue gets an *informed
  analog*, not evidence.
- **No crew-size history** → the 15/hr pace is an owner-set standard, not learned. Change
  `PACE_PER_PERSON` in the script if the standard changes, then re-run + reload.
- **Square is one location** → it knows WHEN, never WHERE. Venue only comes from calendar matches;
  calendar titles drift ("Logboat"/"Log boat" split the anchor account until normalized), so
  `venue_of()` normalizes — extend `VENUE_KEYS` when a new regular venue appears.
- Session boundaries are a heuristic (>3h gap). A double-header day merges if the gap is short.

## Privacy

`demand_baseline_report.md`, `data/demand_profiles.json`, and the generated
`supabase_demand_data.sql` are **gitignored** (they carry revenue). The `demand_profiles` table is
authenticated-only with anon revoked — `gross_median` shows on the desk, never on a public surface.

## Roadmap
- Booked events auto-pull their venue profile into a "load-out sheet" per stop.
- Prep logging → depletion → reorder points (`TODO.md` inventory item) — deferred until the
  prep-logging habit is proven; drifted stock numbers are worse than none.
- Rush-curve (order timestamps within a session) → staff to the peak window, not the session mean.
