# The Signal Net — runbook

An always-on aggregator that polls curated local sources every 4 hours and drops fresh event
finds into a **Signals feed** Lance skims. What he keeps flows onto the **Scout Board** as a
prospect (→ enrich → send to Trint). It's the automated intake for the Scout pipeline.

- **Design spec:** `docs/superpowers/specs/2026-07-16-signal-net-design.md`
- **Live URL** (once deployed): `glizzness.com/hub/signals` (gated; 4th tile on the hub)

---

## What's in the repo

| Path | Role |
|---|---|
| `supabase_signals_schema.sql` | `event_signals` table + RLS (authenticated-only, anon revoked) + allows `event_prospects.source='signal'`. Run once. |
| `crawler/run.py` | Orchestrator: fetch → filter (event-like + local) → dedup → write. `--dry-run` prints without writing. |
| `crawler/sources.py` | The curated source list (data, not logic). Add a source = one line. |
| `crawler/adapters/` | `rss.py` (RSS/Atom — the workhorse), `reddit.py` (JSON, unused in v1), `venue_watch.py` (best-effort HTML). |
| `crawler/{config,normalize,store}.py` | Term lists + Supabase URL; the Signal type + filters; the Supabase writer. |
| `crawler/requirements.txt` | `feedparser`. |
| `.github/workflows/crawler.yml` | GitHub Actions: cron every 4h + manual "Run workflow". |
| `site/hub/signals.html` | The gated Signals feed (Keep / Dismiss / Restore / + Add a find). |

**Architecture:** GitHub Actions runs the crawler in the cloud on a timer → writes to Supabase
`event_signals` with the **service_role key** (a GitHub secret) → the gated web page reads/updates
it as an authenticated user. Crawler and UI share only the database. **No LLM anywhere** — plain
HTTP to RSS/APIs, so nothing to rate-limit and nothing to pay.

---

## ONE-TIME SETUP (Lance — credentialed steps)

### 1. Create the table
Supabase → **SQL Editor** → paste all of `supabase_signals_schema.sql` → **Run**. (Run
`supabase_scout_schema.sql` first if you haven't — this depends on `event_prospects` existing.)

### 2. Add the GitHub Actions secret
Repo **github.com/lazrexmc/glizzness** → **Settings → Secrets and variables → Actions → New
repository secret**:
- **Name:** `SUPABASE_SERVICE_KEY`
- **Secret:** your Supabase **service_role** key (Supabase → Project Settings → API Keys → the
  `service_role` / `secret` one — *not* the anon key).

### 3. Deploy + first run
- `git push` is done, so Cloudflare has the Signals page and GitHub has the workflow.
- If the repo's Actions are off: repo → **Actions** tab → enable workflows.
- Kick a first run by hand: **Actions → "Signal Net crawler" → Run workflow**. Watch the log —
  it prints each source, how many candidates, and how many NEW rows it wrote.
- Open **glizzness.com/hub/signals** → your first finds should be there.

After that it runs itself every 4 hours.

---

## DAILY USE
- Open **glizzness.com/hub/signals**. Newest first.
- **✅ Keep → Trint** creates a Scout prospect (researching) — then work it on the Desk (enrich →
  Ready → Trint). **❌ Dismiss** hides it forever (remembered; never re-shown).
- **+ Add a find** — paste a Facebook/Instagram show you spotted yourself; it joins the feed so
  everything funnels through one skim.
- Filter by source; "Show dismissed" to review/restore past calls.

---

## LIVE SOURCES (v1 — all verified 2026-07-16, no API key)

| Source | Type | Yield (first run) |
|---|---|---|
| **Cooper's Landing** (`tribe:coopers`) | Tribe API | ~50 — the most vending-relevant venue (riverside, food vendors, bands) |
| **Mizzou calendar** (`rss:mizzou`) | LiveWhale RSS | ~80 (event-filtered from 512 campus items) — catches the big-foot-traffic events |
| **Stephens College** (`tribe:stephens`) | Tribe API | ~23 |
| **The Blue Note** / **Rose Music Hall** (`rss:*`) | event RSS | ~10 each — ticketed shows |
| **Bur Oak Brewing** (`tribe:buroak`) | Tribe API | 0 today (allows food trucks; fills when they post) |
| **KOMU · Missourian · Vox** (`rss:*`) | BLOX news RSS | event-ish headlines only (low, but catches announcements) |
| **r/columbiamo** (`reddit:columbiamo`) | Reddit `.rss` | ~6 (may 403 on the CI runner; fine) |

First run ≈ **182 candidates**; after that it's incremental (dedup means each event appears once). Use
the **source filter** on the Signals feed to skim source-by-source. **Verified-but-not-added** (keys or
stale): Ticketmaster Discovery, Bandsintown/Songkick (→ Eastside Tavern dive/punk), The District, City
of Columbia / CVB (Cloudflare-blocked) — see the notes at the bottom of `crawler/sources.py`.

## MANAGING SOURCES

Add one in `crawler/sources.py` (then commit — the next scheduled run picks it up):
```python
{"id": "rss:visitcolumbia", "type": "rss",
 "url": "https://…/events/rss", "local": True, "is_event_feed": True},
```
- `local: True` → the source is inherently local (skip the area-keyword check).
- `is_event_feed: True` → every item is already an event (skip the event-keyword check) — use for
  dedicated event calendars; leave it off for general news/Reddit so the event filter trims noise.
- `enabled: False` → pause a source without deleting it.
- Test before committing: `python -m crawler.run --source <id> --dry-run`.

**Reddit caveat:** Reddit's `.json` is 403-blocked; we use its `.rss` (works locally). But Reddit
**hard-blocks datacenter IPs**, so `reddit:columbiamo` may 403 on the GitHub runner even though it
works on your PC — a dead source is handled gracefully (logged, skipped). If it stays blocked, a
free Reddit OAuth app is the fix (v1.1). The RSS/event-calendar feeds are the reliable backbone.

---

## LOCAL DEV
```
pip install -r crawler/requirements.txt
python -m crawler.run --dry-run          # see what it would find, no DB writes
python -m crawler.run                      # real run (needs SUPABASE_SERVICE_KEY in your env)
```

## CADENCE
Every 4 hours (`cron: "0 */4 * * *"` in the workflow). ~200–350 of the 2,000 free private-repo
Actions minutes/month. Change the cron to go faster/slower.

## GOTCHAS
- A failing source never kills the run (per-source try/except; it's logged and skipped).
- **Dedup** is by `dedup_hash` (unique) + insert-ignore, so the same item never reappears — even
  across runs. A dismissed item stays dismissed.
- The **service_role key** is a full-access DB password: only ever in the GitHub secret, never in
  the repo or any page. Repo is private.
- Signals page is `noindex` + covered by `robots.txt` Disallow `/hub`.

## ROADMAP (not in v1)
- **→ Event Finder** promotion (v1.1): promote an approved signal to the public map
  (`vending_events`) with a region/type pick + geocode. The public map is a *validated gate*, so
  this is a curated one-click promote, never an auto-publish. See spec §9.5.
- Auto-ranking of finds (float likely gigs, sink junk); a Make→Gmail "N new today" digest;
  free-keyed APIs (Ticketmaster Discovery, Bandsintown); LLM extraction on messy pages.
