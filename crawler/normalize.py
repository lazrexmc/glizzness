"""Signal Net — the normalized Signal + the source-agnostic filter/hash helpers.

Adapters produce Signal objects; run.py filters + dedups them; store.py writes them.
Nothing here knows about a specific source or the database."""
import hashlib
import html as _html
import re
from dataclasses import dataclass, asdict
from typing import Optional

from .config import AREA_TERMS, EVENT_TERMS

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def clean(s: Optional[str]) -> str:
    """Strip HTML, unescape entities, collapse whitespace."""
    if not s:
        return ""
    s = _TAG.sub(" ", s)
    s = _html.unescape(s)
    return _WS.sub(" ", s).strip()


def make_hash(source: str, external: str) -> str:
    """Stable idempotency key for a find (so the same item never re-inserts)."""
    return hashlib.sha1(("%s|%s" % (source, external or "")).encode("utf-8")).hexdigest()


def looks_like_event(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in EVENT_TERMS)


def looks_local(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in AREA_TERMS)


@dataclass
class Signal:
    source: str
    dedup_hash: str
    title: str
    url: Optional[str] = None
    starts_text: Optional[str] = None
    event_date: Optional[str] = None      # ISO 'YYYY-MM-DD' string, or None
    location_text: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    raw: Optional[dict] = None

    def text_blob(self) -> str:
        return " ".join(filter(None, [self.title, self.description, self.location_text, self.city]))

    def to_row(self) -> dict:
        """DB row: drop None so table defaults apply."""
        return {k: v for k, v in asdict(self).items() if v is not None}
