"""Signal Net — the only unit that writes to Supabase.

Uses the service_role key (bypasses RLS) via the PostgREST endpoint. Inserts with
on_conflict=dedup_hash + resolution=ignore-duplicates, so re-runs never create duplicates and
the returned representation contains ONLY the newly-inserted rows (→ an accurate 'new' count)."""
import json
import urllib.request

from . import config

_ENDPOINT = "/rest/v1/event_signals?on_conflict=dedup_hash"


def _headers():
    key = config.SUPABASE_SERVICE_KEY
    return {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Prefer": "return=representation,resolution=ignore-duplicates",
    }


def insert_signals(rows):
    """POST a batch of signal rows. Returns the list of rows that were actually inserted
    (conflicts on dedup_hash are ignored and NOT returned)."""
    if not rows:
        return []
    if not config.SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_KEY is not set — cannot write to Supabase.")
    data = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(
        config.SUPABASE_URL + _ENDPOINT, data=data, headers=_headers(), method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body.strip() else []
