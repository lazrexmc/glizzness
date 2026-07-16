"""Signal Net orchestrator.

  python -m crawler.run --dry-run          # fetch + filter, print, NO db writes
  python -m crawler.run                     # fetch + filter + write new finds to Supabase
  python -m crawler.run --source rss:missourian   # run a single source

Each source is fetched by its adapter (one job: source -> normalized Signals). This module is
the source-agnostic core: filter to event-like + local, dedup within the batch, then write.
A failing source is recorded and skipped — it never kills the run."""
import argparse
import sys

from . import config, store
from .normalize import looks_like_event, looks_local
from .sources import SOURCES
from .adapters import rss, reddit, venue_watch, tribe

# make unicode titles safe to print on a Windows cp1252 console
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ADAPTERS = {"rss": rss, "reddit": reddit, "venue": venue_watch, "tribe": tribe}


def keep(sig, src):
    """An item survives if it's event-like AND local. A source flagged is_event_feed skips the
    event check; a source flagged local skips the area check (it's inherently local)."""
    blob = sig.text_blob()
    is_event = src.get("is_event_feed") or looks_like_event(blob)
    is_local = src.get("local") or looks_local(blob)
    return is_event and is_local


def main():
    ap = argparse.ArgumentParser(description="Glizzness Signal Net crawler")
    ap.add_argument("--dry-run", action="store_true", help="print finds, do not write to the DB")
    ap.add_argument("--source", help="run only the source with this id")
    args = ap.parse_args()

    srcs = [s for s in SOURCES
            if s.get("enabled", True) and (not args.source or s["id"] == args.source)]

    by_hash = {}
    per_source = []
    for src in srcs:
        adapter = ADAPTERS.get(src["type"])
        if not adapter:
            per_source.append((src["id"], "no-adapter", 0))
            continue
        try:
            items = adapter.fetch(src)
        except Exception as ex:  # a dead source must never kill the run
            per_source.append((src["id"], "ERROR %s" % type(ex).__name__, 0))
            continue
        kept = [s for s in items if keep(s, src)]
        for s in kept:
            by_hash[s.dedup_hash] = s
        per_source.append((src["id"], "ok", len(kept)))

    rows = [s.to_row() for s in by_hash.values()]

    print("\n=== Signal Net run (%d sources) ===" % len(srcs))
    for sid, status, n in per_source:
        print("  %-30s %-14s %3d" % (sid, status, n))
    print("  candidates after filter + dedup: %d" % len(rows))

    if args.dry_run:
        print("\n--- DRY RUN — no DB writes ---")
        for s in list(by_hash.values())[:60]:
            print("  [%s] %s | %s" % (s.source, s.title[:80], (s.url or "")[:70]))
        return

    inserted = store.insert_signals(rows)
    print("  NEW inserted to event_signals: %d" % len(inserted))


if __name__ == "__main__":
    main()
