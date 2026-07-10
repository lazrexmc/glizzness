#!/usr/bin/env python
r"""sync_calendar.py — mirror the Glizzness Google Calendar into Supabase, SANITIZED.

Reads the business Google Calendar (read-only, via a service account) and writes a
PUBLIC-SAFE copy into Supabase `cart_schedule`, which the website's "Where We Vend"
page reads. The browser never touches Google — only the sanitized Supabase rows.

PRIVACY MODEL (opt-in public):
  * An event is PUBLIC only if its calendar color is "Basil"/green (colorId 10).
    Public rows keep the event title (venue) + location.
  * EVERY OTHER event becomes a "Booked — Unavailable" time block with NO title and
    NO location — private catering details never leave Google.
  Opt-in means a forgotten event stays private (shows "Unavailable"), never leaks.

SETUP: see CALENDAR_SETUP.md — create a Google service account, share the calendar
read-only with it, run supabase_schedule_schema.sql, set the env vars below.

ENV VARS:
  GOOGLE_SA_KEYFILE     path to the service-account JSON key (gitignored)
  GOOGLE_CALENDAR_ID    the calendar id (often the Google account email, or a
                        "...@group.calendar.google.com" id)
  SUPABASE_URL          https://<project>.supabase.co
  SUPABASE_SERVICE_KEY  service-role key (bypasses RLS to write cart_schedule)

INSTALL (one-time):  pip install google-api-python-client google-auth requests

USAGE:
  python sync_calendar.py             # sync the next 180 days
  python sync_calendar.py --dry-run   # show what WOULD sync; write nothing
  python sync_calendar.py --days 365  # widen the window
"""
import argparse
import datetime as dt
import os
import sys

PUBLIC_COLOR_ID = "10"   # Google "Basil" (green) = public. Change if you pick another color.
WINDOW_DAYS = 180


def _env(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"[error] missing env var {name} (see CALENDAR_SETUP.md)")
    return v


def fetch_events(days):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        _env("GOOGLE_SA_KEYFILE"),
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    cal_id = _env("GOOGLE_CALENDAR_ID")

    now = dt.datetime.now(dt.timezone.utc)
    time_min = now.isoformat()
    time_max = (now + dt.timedelta(days=days)).isoformat()

    events, page = [], None
    while True:
        resp = svc.events().list(
            calendarId=cal_id, timeMin=time_min, timeMax=time_max,
            singleEvents=True, orderBy="startTime", maxResults=2500, pageToken=page,
        ).execute()
        events.extend(resp.get("items", []))
        page = resp.get("nextPageToken")
        if not page:
            break
    return events


def to_row(ev):
    """Map a Google event -> a sanitized cart_schedule row (or None to skip)."""
    if ev.get("status") == "cancelled":
        return None
    start, end = ev.get("start", {}), ev.get("end", {})
    all_day = "date" in start
    if all_day:
        # store all-day events at noon UTC so the calendar date never rolls over on display
        starts_at = start["date"] + "T12:00:00Z"
        ends_at = (end.get("date") or start["date"]) + "T12:00:00Z"
    else:
        starts_at = start.get("dateTime")
        ends_at = end.get("dateTime")
    if not starts_at:
        return None

    is_public = ev.get("colorId") == PUBLIC_COLOR_ID
    return {
        "gcal_event_id": ev["id"],
        "starts_at": starts_at,
        "ends_at": ends_at,
        "all_day": all_day,
        "is_public": is_public,
        "title": (ev.get("summary") or "The Glizzness cart") if is_public else None,
        "location": (ev.get("location") or None) if is_public else None,
    }


def push(rows, dry):
    import requests

    U, K = _env("SUPABASE_URL"), _env("SUPABASE_SERVICE_KEY")
    today = dt.date.today().isoformat()
    H = {"apikey": K, "Authorization": "Bearer " + K, "Content-Type": "application/json"}

    if dry:
        print(f"[dry-run] would replace rows with starts_at >= {today} using {len(rows)} events")
        return

    # Replace the managed window: delete future rows, then insert the fresh set.
    # Idempotent — cleanly handles cancellations, moves, and re-colors on every run.
    d = requests.delete(f"{U}/rest/v1/cart_schedule?starts_at=gte.{today}", headers=H)
    d.raise_for_status()
    if rows:
        ins = requests.post(
            f"{U}/rest/v1/cart_schedule",
            headers={**H, "Prefer": "return=minimal"}, json=rows,
        )
        ins.raise_for_status()
    print(f"synced {len(rows)} event(s) to cart_schedule")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show what would sync, write nothing")
    ap.add_argument("--days", type=int, default=WINDOW_DAYS, help="how many days ahead to sync")
    a = ap.parse_args()

    events = fetch_events(a.days)
    rows = [r for r in (to_row(e) for e in events) if r]
    pub = sum(1 for r in rows if r["is_public"])
    print(f"fetched {len(events)} event(s) -> {len(rows)} row(s): {pub} public, {len(rows) - pub} unavailable")
    for r in rows[:12]:
        label = r["title"] if r["is_public"] else "Booked - Unavailable"
        print(f"  {r['starts_at'][:16]}  {'PUB' if r['is_public'] else '---'}  {label}")
    if len(rows) > 12:
        print(f"  ... (+{len(rows) - 12} more)")
    push(rows, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
