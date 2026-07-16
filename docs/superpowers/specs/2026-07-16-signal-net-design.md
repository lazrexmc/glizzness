# The Signal Net — design spec (v1)

**Date:** 2026-07-16
**Status:** approved shape (Lance approved the design + all 3 forks; said "proceed" → building).
**Related:** the **Scout Board** (`SCOUT_BOARD.md`, `docs/.../2026-07-13-scout-board-design.md`) — this
is its automated intake. `CATERING_LEADS.md` (the Make→Gmail pattern, reused for alerts later).
The **Midwest Event Finder** (`site/festivals/`) and `data/prospects.csv` (the manual research picks).

---

## 1. Purpose

Lance keeps missing events The Glizzness could vend at — they're scattered across news, socials,
Reddit, venue pages, city calendars, ticketing sites. **The Signal Net** is an always-on aggregator
that never forgets to check a curated list of sources on a timer, pulls out anything event-like near
Columbia, and drops fresh finds into a **review feed Lance skims daily**. What he keeps flows onto the
**Scout Board** as a prospect (→ enrich → send to Trint). "I can't miss anymore."

**It is a conveyor belt into the Scout Board, not a separate island.** Same Supabase project, same
auth/RLS pattern, same predict→review→act loop.

## 2. The three decisions (settled with Lance)

1. **Where it runs:** **GitHub Actions cron** — cloud, always-on (runs when his PC is off/asleep/away),
   free (~200–350 of the 2,000 free private-repo minutes/month at a 4-hour cadence). The job writes
   finds to Supabase with the **service_role key**, stored as the GitHub Actions secret
   `SUPABASE_SERVICE_KEY` (never committed).
2. **The feed:** finds land in a **separate "Signals" feed** (`/hub/signals`), NOT on Trint's board.
   Lance skims: **Keep** (→ becomes a Scout prospect he can enrich + send to Trint) or **Dismiss**
   (marked dismissed, remembered, never shown again). He sees 100% of finds; only his keepers reach
   Trint. Trint's card board stays clean.
3. **Coverage:** **free & reliable core** — poll only sources that publish a feed/API (RSS/Atom, no-key
   JSON like Reddit, and later free-keyed APIs like Ticketmaster Discovery), plus a **watchlist of
   local venue pages**. **No LLM in the running job** (that sidesteps the web-search rate-limit thrash
   we hit before, and costs nothing). The Facebook/Instagram-only tiny shows — which no crawler reaches
   cleanly — are covered by a **manual "paste-a-link" add** on the Signals feed.

## 3. Architecture / data flow

```
~curated sources                GitHub Actions (cron: every 4h + manual dispatch)
 (RSS/Atom · Reddit JSON ·   ──►  crawler/run.py:
  venue pages · keyed APIs)         for each source: adapter.fetch() -> normalized items
                                    filter: event-like + Columbia-area
                                    dedup: skip hashes already in DB (unique dedup_hash)
                                    write NEW -> Supabase event_signals (service_role)
                                            │
                                    ┌───────▼──────────┐
                                    │  Signals feed    │  site/hub/signals.html (auth-gated)
                                    │  status = 'new'  │  ← Lance's fresh daily skim
                                    └───────┬──────────┘
                             ┌──────────────┴──────────────┐
                        ✅ Keep                         ❌ Dismiss
                 insert event_prospects              status='dismissed'
                 (source='signal', researching),      (remembered; never re-shown)
                 signal.status='kept',
                 promoted_prospect_id set
                        │
                 → Scout Board desk: enrich → Ready → Trint  (existing pipeline)
```

**Isolation of units:**
- Each **adapter** (rss, reddit, venue_watch, …) has one job: fetch a source → yield normalized
  `Signal` dicts. It knows nothing about the DB or other adapters.
- The **normalizer/filter/dedup** core is source-agnostic: it takes normalized items, drops
  non-local/non-event and already-seen ones, and returns the new ones.
- The **writer** is the only unit that talks to Supabase.
- The **web UI** only reads/updates `event_signals` + inserts `event_prospects` — it never runs the
  crawler. The crawler and the UI share only the database.

## 4. Data model — one new table

`event_signals` (Supabase; RLS authenticated-only + anon revoked, same as the Scout tables):

| Column | Notes |
|---|---|
| `id` bigint pk | identity |
| `source` text | stable source id, e.g. `reddit:CoMo`, `rss:missourian-arts`, `venue:rosemusichall`, `manual` |
| `dedup_hash` text **unique** | idempotency key = hash(source + external id/url). `on conflict do nothing` on insert so re-runs never duplicate. |
| `title` text not null | |
| `url` text | link to the source item (opens in new tab) |
| `starts_text` text | raw date/time text as published |
| `event_date` date | parsed when confidently possible, else null |
| `location_text` text | venue/place as published |
| `city` text | when derivable |
| `description` text | snippet |
| `image_url` text | optional |
| `raw` jsonb | the original item (debugging / later enrichment) |
| `status` text | `new` / `kept` / `dismissed` (default `new`); check-constrained |
| `promoted_prospect_id` bigint | fk → event_prospects(id), set on Keep (null default) |
| `found_at` timestamptz | default now() |
| `reviewed_at` timestamptz | set when kept/dismissed |

Indexes: `status`, `found_at desc`. No `event_prospects` schema change needed — Keep just inserts a
normal prospect with `source='signal'`. (The Scout schema's `source` check currently allows
`research`/`inbound`; **v1 adds `signal` to that check constraint** — a one-line migration.)

## 5. The crawler (`crawler/`)

```
crawler/
  run.py              # orchestrator: load sources -> fetch -> filter -> dedup -> write; --dry-run flag
  config.py           # SUPABASE_URL + reads SUPABASE_SERVICE_KEY from env; area keywords; cadence
  sources.py          # the curated source list (data, not logic) — grows over time
  normalize.py        # Signal dataclass + helpers (hashing, date parsing, event/area filters)
  store.py            # Supabase writer (REST, service_role) + fetch-existing-hashes / insert-ignore
  adapters/
    rss.py            # RSS/Atom via feedparser — covers most local sources
    reddit.py         # Reddit no-key JSON (r/CoMo, r/mizzou), keyword-filtered
    venue_watch.py    # fetch a venue page, extract event-ish links/blocks (best-effort, per-site)
    # later (need free keys, Lance adds as secrets): ticketmaster.py, eventbrite.py, bandsintown.py
  requirements.txt    # feedparser, requests
```

- **Filtering:** an item is kept if (a) its source is inherently local (r/CoMo, city calendar, local
  news) OR its text matches area terms (Columbia, CoMo, Boone County, nearby towns), AND (b) it looks
  event-like (has a date, or matches event terms: show, concert, festival, market, live, fest, tour,
  rally, fair, night…). Conservative filters are fine — Lance dismisses false positives, and a Dismiss
  is remembered.
- **Dedup:** `dedup_hash` unique + insert with `on conflict do nothing` → the same show never reappears.
- **No secrets in repo:** `SUPABASE_SERVICE_KEY` (and any future API keys) come from env, injected by
  GitHub Actions from repo secrets.
- **Politeness:** a descriptive User-Agent, sequential fetches, per-source try/except so one dead
  source never kills the run; `--dry-run` prints without writing.

## 6. GitHub Actions (`.github/workflows/crawler.yml`)

- `on: schedule: cron '0 */4 * * *'` (every 4h) + `workflow_dispatch` (manual "Run workflow" button).
- Steps: checkout → setup-python → `pip install -r crawler/requirements.txt` → `python -m crawler.run`
  with `SUPABASE_SERVICE_KEY` from `secrets.SUPABASE_SERVICE_KEY` (and `SUPABASE_URL` inline/public).
- Logs a summary (sources polled, items found, new inserted, errors) to the Actions run output.

## 7. The Signals feed (`site/hub/signals.html`)

Fourth tile on the hub. Auth-gated (reuses `assets/scout.js`). Reads `event_signals where status='new'`,
newest `found_at` first. Each card: **title**, source badge, when/where text, description snippet, a
**link out** (source, new tab), and two big buttons — **Keep** / **Dismiss**:
- **Keep** → `insert event_prospects` (`source='signal'`, `stage='researching'`, `name=title`,
  `date_text=starts_text`, `city`, `notes=description`, `source_url=url`) → set signal `status='kept'`,
  `promoted_prospect_id`, `reviewed_at`. Card leaves the feed. It's now on the Scout desk to enrich.
- **Dismiss** → `status='dismissed'`, `reviewed_at`. Card leaves the feed, never returns.
- **＋ Paste-a-link** box: manual add for a Facebook/Insta show Lance spotted — creates a
  `manual`-source signal (title + url + optional note) that he then Keeps like any other. Fills the FB hole.
- Filters: by source; a "show dismissed" toggle; a "N new" count badge.

Re-entrancy guards, `esc()` on all injected text, error-checked queries — same hardening standard as
the post-audit Scout pages.

## 8. Security

- `event_signals` RLS authenticated-only + `revoke all … from anon` (Scout-board pattern; the public
  anon key can't touch it).
- The crawler writes with **service_role** (bypasses RLS) — key lives only in the GitHub Actions
  secret, never in the repo or any page. Repo is private.
- Signals page is `noindex` + `robots.txt` Disallow (like `/hub`, `/scout`).

## 9. Build order

1. `supabase_signals_schema.sql` (table + RLS + revoke) **+** the one-line `event_prospects.source`
   check-constraint update to allow `'signal'`. *(Lance runs both.)*
2. Crawler framework: `normalize.py`, `store.py`, `config.py`, `sources.py`, `adapters/rss.py`,
   `adapters/reddit.py`, `run.py`, `requirements.txt`.
3. Seed `sources.py` with **verified** working feeds (research pass confirms real URLs first).
4. Test `python -m crawler.run --dry-run` against live feeds until it pulls real Columbia events.
5. `.github/workflows/crawler.yml`.
6. `site/hub/signals.html` + hub tile + `noindex`/robots.
7. Runbook `SIGNAL_NET.md`; deploy (git push) + Lance's credentialed steps.

## 10. Non-goals (v1 — YAGNI)

- **No LLM/AI** in the crawler (v2 could add targeted extraction on high-value messy pages).
- **No auto-ranking/scoring** of finds (v1.1, once there's real data to rank).
- **No paid event APIs** (revisit if free coverage proves thin).
- **No Facebook/Instagram scraping** (ToS + anti-scraping) → manual paste-add instead.
- **No geocoding/distance math** — show the location text; distance is a later nicety.
- **No auto-promote** — nothing reaches Trint without Lance's review.
- **No sources-config DB table** — the source list is a versioned config file for now.
- **No alerts** — Lance pulls the feed. A Make→Gmail "N new finds today" digest is an easy later add.

## 11. Risks / open flags

- **Feed availability:** many sites don't publish RSS, or moved it. The research pass verifies real URLs
  before seeding; the list starts with whatever genuinely works and grows. A thin start is expected.
- **Reddit rate-limits** unauthenticated JSON (HTTP 429). Mitigate with a real User-Agent + low
  frequency; if it becomes unreliable, a free Reddit app (script auth) is a small later add.
- **Venue-page scraping is brittle** (per-site HTML). Treat `venue_watch` as best-effort; prefer any
  venue that exposes a real feed. Failing a source must never break the run (per-source try/except).
- **Duplicate events across sources** (same festival from news + Ticketmaster) — v1 dedups within a
  source by hash; cross-source near-duplicate merging is a later nicety (Lance dismisses the dupe now).
