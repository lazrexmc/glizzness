"""Signal Net — the curated source list (DATA, not logic). Grows over time.

Each source is a dict:
  id            stable unique id, e.g. "reddit:CoMo", "rss:missourian-arts", "venue:rosemusichall"
  type          "reddit" | "rss" | "venue"
  enabled       default True; set False to pause a source without deleting it
  local         True if the source is inherently local (skips the area-keyword check)
  is_event_feed True if EVERY item is already an event (skips the event-keyword check)
  + adapter-specific keys:
      reddit: subreddit
      rss:    url
      venue:  url, base?, venue?
  + optional: city, venue

Verified working feeds get added here from the research pass (see SIGNAL_NET.md). Start small
with what genuinely works; add sources a line at a time.
"""

SOURCES = [
    # ---- Reddit — via the .rss endpoint (the .json is 403-blocked; .rss slips through).
    # NOTE: r/CoMo is Como, ITALY — the Columbia MO sub is r/columbiamo. Reddit hard-blocks
    # datacenter IPs, so this may 403 on the GitHub Actions runner even though it works locally;
    # a dead source is handled gracefully. If CI blocks it, a free Reddit OAuth app is the fix.
    {"id": "reddit:columbiamo", "type": "rss",
     "url": "https://www.reddit.com/r/columbiamo/.rss",
     "local": True, "is_event_feed": False, "city": "Columbia"},

    # ---- RSS / event feeds ----
    # Filled from the verified-feeds research pass. Format example:
    # {"id": "rss:missourian-arts", "type": "rss",
    #  "url": "https://www.columbiamissourian.com/.../rss", "local": True, "is_event_feed": False},
]
