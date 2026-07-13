#!/usr/bin/env python
r"""pull_past_events.py — one-time export of PAST Google Calendar events to a local CSV.

Companion to sync_calendar.py: SAME auth (service account, read-only), but it pulls the
HISTORY (timeMin in the past -> now) and dumps the RAW, UN-sanitized events to a local CSV,
so we can later match them against Square sales to build a per-event demand baseline
(see TODO.md "Event sales history -> demand baseline").

The output CSV is INTERNAL (may contain client names / locations) and is GITIGNORED (*.csv) —
do NOT commit it. Accuracy of old entries is unknown; this just preserves them for later.

ENV VARS (same ones sync_calendar.py already uses):
  GOOGLE_SA_KEYFILE   path to the service-account JSON key
  GOOGLE_CALENDAR_ID  the calendar id (usually the Google account email, e.g. glizzness@gmail.com)

INSTALL (one-time, already done for sync_calendar.py):
  pip install google-api-python-client google-auth

USAGE:
  python pull_past_events.py                    # everything since 2020-01-01 through now
  python pull_past_events.py --since 2022-01-01 # narrower window
  python pull_past_events.py --out events.csv   # custom output file (keep it a *.csv so it stays gitignored)
"""
import argparse
import csv
import datetime as dt
import os
import sys

OUT_DEFAULT = "past_cart_events.csv"   # gitignored via *.csv — stays local


def _env(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"[error] missing env var {name} — set the same vars sync_calendar.py uses "
                 f"(GOOGLE_SA_KEYFILE, GOOGLE_CALENDAR_ID); see CALENDAR_SETUP.md")
    return v


def fetch_past(since_iso):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        _env("GOOGLE_SA_KEYFILE"),
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    cal_id = _env("GOOGLE_CALENDAR_ID")

    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    events, page = [], None
    while True:
        resp = svc.events().list(
            calendarId=cal_id, timeMin=since_iso, timeMax=now_iso,
            singleEvents=True, orderBy="startTime", maxResults=2500, pageToken=page,
        ).execute()
        events.extend(resp.get("items", []))
        page = resp.get("nextPageToken")
        if not page:
            break
    return events


def flatten(ev):
    """Full raw-ish row: keep title/location/description (internal file), plus times + metadata."""
    start, end = ev.get("start", {}), ev.get("end", {})
    clean = lambda s: (s or "").replace("\r", " ").replace("\n", " ").strip()
    return {
        "event_id": ev.get("id", ""),
        "status": ev.get("status", ""),
        "visibility": ev.get("visibility", "default"),
        "all_day": "date" in start,
        "start": start.get("dateTime") or start.get("date") or "",
        "end": end.get("dateTime") or end.get("date") or "",
        "summary": clean(ev.get("summary")),
        "location": clean(ev.get("location")),
        "description": clean(ev.get("description")),
        "created": ev.get("created", ""),
        "updated": ev.get("updated", ""),
    }


COLS = ["event_id", "status", "visibility", "all_day", "start", "end",
        "summary", "location", "description", "created", "updated"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2020-01-01", help="earliest date to pull (YYYY-MM-DD)")
    ap.add_argument("--out", default=OUT_DEFAULT, help="output CSV path (keep it *.csv = gitignored)")
    a = ap.parse_args()

    since_iso = a.since + "T00:00:00Z"
    events = fetch_past(since_iso)
    rows = [flatten(e) for e in events if e.get("status") != "cancelled"]

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    pub = sum(1 for r in rows if r["visibility"] == "public")
    print(f"pulled {len(events)} event(s) since {a.since}  ->  wrote {len(rows)} row(s) to {a.out} "
          f"({pub} public, {len(rows) - pub} private/default)")
    for r in rows[:15]:
        print(f"  {r['start'][:16]:16}  {r['visibility']:9}  {(r['summary'] or '(no title)')[:46]}")
    if len(rows) > 15:
        print(f"  ... (+{len(rows) - 15} more)")
    print("\nNOTE: this CSV is internal + gitignored (may contain client details). Do NOT commit it.")


if __name__ == "__main__":
    sys.exit(main())
