"""The Events Calendar ("Tribe") REST API adapter — no key, and it carries REAL event dates.

Many local WordPress venues expose it at `<site>/wp-json/tribe/events/v1/events?per_page=50`
(Cooper's Landing, Stephens College, Bur Oak…). Richer than their RSS: real `start_date` + venue.

Source dict: {"id","type":"tribe","url", optional "city","venue","local","is_event_feed"}."""
import json
import urllib.request

from .. import config
from ..normalize import Signal, make_hash, clean


def fetch(source):
    req = urllib.request.Request(source["url"], headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for e in data.get("events", []):
        title = clean(e.get("title", ""))
        if not title:
            continue
        start = (e.get("start_date") or "").strip()          # "2026-07-16 16:30:00"
        venue = ""
        v = e.get("venue")
        if isinstance(v, dict):
            venue = clean(v.get("venue") or "")
        external = str(e.get("id") or e.get("url") or title)
        out.append(Signal(
            source=source["id"],
            dedup_hash=make_hash(source["id"], external),
            title=title[:300],
            url=e.get("url"),
            starts_text=start or None,
            event_date=(start.split(" ")[0] if start else None),   # YYYY-MM-DD
            location_text=venue or source.get("venue"),
            city=source.get("city"),
            description=(clean(e.get("description", ""))[:600] or None),
            raw={"tribe": source["url"]},
        ))
    return out
