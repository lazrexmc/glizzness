"""Venue-watch adapter — BEST-EFFORT generic HTML scrape for venues with no feed.

Fetches a page and pulls anchor links whose text looks event-like. Crude by nature (per-site
HTML varies), so expect some noise — Lance dismisses false positives and a Dismiss is remembered.
Prefer a real RSS/JSON feed for a venue whenever one exists; use this only when none does.

Source dict: {"id","type":"venue","url", optional "base","venue","city","local":True}."""
import re
import urllib.request

from .. import config
from ..normalize import Signal, make_hash, clean, looks_like_event

_ANCHOR = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)


def fetch(source):
    req = urllib.request.Request(source["url"], headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    base = source.get("base") or source["url"]
    out, seen = [], set()
    for href, inner in _ANCHOR.findall(html):
        text = clean(inner)
        if len(text) < 6 or not looks_like_event(text):
            continue
        link = href if href.startswith("http") else base.rstrip("/") + "/" + href.lstrip("/")
        if link in seen:
            continue
        seen.add(link)
        out.append(Signal(
            source=source["id"],
            dedup_hash=make_hash(source["id"], link),
            title=text[:300],
            url=link,
            location_text=source.get("venue"),
            city=source.get("city"),
            raw={"page": source["url"]},
        ))
    return out
