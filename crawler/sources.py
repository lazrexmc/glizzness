"""Signal Net — the curated source list (DATA, not logic). Grows over time.

Each source is a dict:
  id            stable unique id, e.g. "tribe:coopers", "rss:vox", "reddit:columbiamo"
  type          "tribe" | "rss" | "reddit" | "venue"
  enabled       default True; set False to pause a source without deleting it
  local         True if the source is inherently local (skips the area-keyword check)
  is_event_feed True if EVERY item is already an event (skips the event-keyword check)
  + adapter-specific keys:
      tribe/rss/venue: url          reddit: subreddit (or just use rss on the .rss url)
  + optional: city, venue

All URLs below were fetched + verified live 2026-07-16 (research pass in SIGNAL_NET.md). They need a
real User-Agent (set in config.py) but NO API key. To add a source, drop in one line and test with
`python -m crawler.run --source <id> --dry-run`.
"""

SOURCES = [
    # ---- Tribe (WordPress "The Events Calendar") REST API — no key, REAL event dates ----
    # Cooper's Landing = the most vending-relevant venue (riverside, hosts food vendors). 157 events.
    {"id": "tribe:coopers", "type": "tribe",
     "url": "https://cooperslandingmo.com/wp-json/tribe/events/v1/events?per_page=50",
     "local": True, "is_event_feed": True, "venue": "Cooper's Landing", "city": "Columbia"},
    {"id": "tribe:stephens", "type": "tribe",
     "url": "https://www.stephens.edu/wp-json/tribe/events/v1/events?per_page=50",
     "local": True, "is_event_feed": True, "venue": "Stephens College", "city": "Columbia"},
    # Bur Oak explicitly allows food trucks; API is live but empty today — fills when they post events.
    {"id": "tribe:buroak", "type": "tribe",
     "url": "https://buroakbeer.com/wp-json/tribe/events/v1/events?per_page=50",
     "local": True, "is_event_feed": True, "venue": "Bur Oak Brewing", "city": "Columbia"},

    # ---- Venue event RSS (WordPress `event` post type) — all-events feeds ----
    {"id": "rss:bluenote", "type": "rss", "url": "https://www.thebluenote.com/event/feed/",
     "local": True, "is_event_feed": True, "venue": "The Blue Note", "city": "Columbia"},
    {"id": "rss:rosemusichall", "type": "rss", "url": "https://www.rosemusichall.com/event/feed/",
     "local": True, "is_event_feed": True, "venue": "Rose Music Hall", "city": "Columbia"},

    # ---- Mizzou LiveWhale calendar (512 events; campus + public). is_event_feed OFF so the
    # event-keyword filter trims lectures/meetings down to the vending-relevant public events. ----
    {"id": "rss:mizzou", "type": "rss", "url": "https://calendar.missouri.edu/live/rss/events",
     "local": True, "is_event_feed": False, "city": "Columbia"},

    # ---- Local news (BLOX/TownNews) — inherently local; event filter keeps the event-ish headlines ----
    {"id": "rss:komu", "type": "rss",
     "url": "https://www.komu.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc&k%5B%5D=%23topstory",
     "local": True, "is_event_feed": False, "city": "Columbia"},
    {"id": "rss:missourian", "type": "rss",
     "url": "https://www.columbiamissourian.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc&k%5B%5D=%23topstory",
     "local": True, "is_event_feed": False, "city": "Columbia"},
    {"id": "rss:vox", "type": "rss",
     "url": "https://www.voxmagazine.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc&c%5B%5D=arts/music",
     "local": True, "is_event_feed": False, "city": "Columbia"},

    # ---- Reddit — via .rss (the .json is 403-blocked). r/CoMo is Como ITALY; the MO sub is columbiamo.
    # Reddit hard-blocks datacenter IPs, so this may 403 on the GitHub runner (handled gracefully). ----
    {"id": "reddit:columbiamo", "type": "rss", "url": "https://www.reddit.com/r/columbiamo/.rss",
     "local": True, "is_event_feed": False, "city": "Columbia"},
]

# Verified-but-not-yet-added (need a key or are currently stale) — see SIGNAL_NET.md roadmap:
#   Ticketmaster Discovery (free key) -> Blue Note + Rose real show dates
#   Bandsintown (app_id) / Songkick (key) -> Eastside Tavern dive/punk shows
#   The District (discoverthedistrict.com/events?format=json) -> works but stale since 2025; poll later
#   City of Columbia / Visit Columbia CVB -> Cloudflare-blocked feeds; likely need page-scraping
