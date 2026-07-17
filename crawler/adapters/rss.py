"""RSS/Atom adapter — covers most local sources (news, city/college/library calendars).

Source dict: {"id","type":"rss","url", optional "city","local","is_event_feed"}."""
import feedparser

from .. import config
from ..normalize import Signal, make_hash, clean


def fetch(source):
    d = feedparser.parse(source["url"], agent=config.USER_AGENT)
    # AUDIT FIX (high): feedparser never raises — a 403/404/DNS failure comes back as
    # bozo=1 / status>=400 with zero entries, which the run summary showed as "ok 0".
    # Surface real failures so a dead source reads ERROR, not "quiet day".
    status = getattr(d, "status", 200)
    if status >= 400:
        raise RuntimeError("HTTP %s from %s" % (status, source["url"]))
    if getattr(d, "bozo", 0) and not d.entries:
        raise RuntimeError("unparseable feed (%s): %s" % (
            type(getattr(d, "bozo_exception", None)).__name__, source["url"]))
    out = []
    for e in d.entries:
        title = clean(getattr(e, "title", "") or "")
        if not title:
            continue
        link = getattr(e, "link", "") or ""
        summary = clean(getattr(e, "summary", "") or getattr(e, "description", "") or "")
        external = getattr(e, "id", "") or link or title
        # Some event feeds (iCal-ish/Localist) expose a real start; generic RSS does not,
        # so we leave event_date/starts_text empty and let the description carry context.
        starts = clean(getattr(e, "published", "") or "") or None
        out.append(Signal(
            source=source["id"],
            dedup_hash=make_hash(source["id"], external),
            title=title[:300],
            url=link or None,
            starts_text=starts if source.get("is_event_feed") else None,
            location_text=source.get("venue"),
            city=source.get("city"),
            description=(summary[:600] or None),
            raw={"feed": source["url"]},
        ))
    return out
