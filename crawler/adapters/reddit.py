"""Reddit adapter — no-key public JSON (r/CoMo, r/mizzou). Inherently local.

Source dict: {"id","type":"reddit","subreddit", optional "city","local":True}.
Reddit rate-limits anonymous JSON; a real User-Agent keeps it mostly happy. A 429/403 raises
and run.py records it per-source without killing the whole run."""
import json
import urllib.request

from .. import config
from ..normalize import Signal, make_hash, clean

_URL = "https://www.reddit.com/r/%s/new.json?limit=50"


def fetch(source):
    req = urllib.request.Request(
        _URL % source["subreddit"], headers={"User-Agent": config.USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for child in data.get("data", {}).get("children", []):
        p = child.get("data", {})
        title = clean(p.get("title", ""))
        if not title:
            continue
        permalink = "https://www.reddit.com" + p.get("permalink", "")
        selftext = clean(p.get("selftext", ""))[:600]
        external = p.get("id") or permalink
        out.append(Signal(
            source=source["id"],
            dedup_hash=make_hash(source["id"], external),
            title=title[:300],
            url=permalink,
            description=(selftext or None),
            city=source.get("city", "Columbia"),
            raw={"subreddit": source["subreddit"]},
        ))
    return out
