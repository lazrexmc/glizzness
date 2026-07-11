# "Where We Vend" calendar — setup

The website's **Where We Vend** page shows an on-brand "Upcoming stops" list. It reads
a **sanitized mirror** of the business Google Calendar from Supabase (`cart_schedule`).
The browser never touches Google — only public-safe rows.

```
Google Calendar (one business calendar)
   │  sync_calendar.py  (server-side, service account, read-only)
   │    • event Visibility = "Public"  → PUBLIC: keep title + location
   │    • everything else               → "Booked — Unavailable" (date/time only, no details)
   ▼
Supabase  cart_schedule  (public-read RLS; service_role writes)
   ▼
site/events.html  → "Upcoming stops"  (anon key, read-only)
```

## How Trint marks an event PUBLIC
In Google Calendar, open the event → click **Edit** (pencil) → change the
**"Default visibility"** dropdown to **"Public"** → save. (For a recurring series,
choose **"This event"** for a single stop, or **"All events"** for the whole series.)
That's it. Any other setting (Default / Private / Confidential) stays **private** and shows
only as "Booked — Unavailable" on the site. *Opt-in by design: forget to set it and it stays
private — it never leaks.* (To change which setting = public, edit `PUBLIC_VISIBILITY` in
`sync_calendar.py`.)

## One-time setup (Lance)

1. **Create the Supabase table** — run `supabase_schedule_schema.sql` in the Supabase SQL editor.

2. **Google Cloud service account** (so the sync can read the calendar headlessly):
   - Google Cloud Console → create/select a project → **APIs & Services → Enable APIs →
     enable "Google Calendar API".**
   - **IAM & Admin → Service Accounts → Create service account** (any name, e.g.
     `glizzness-calendar`). No project roles needed.
   - On that service account → **Keys → Add key → Create new key → JSON** → download it.
     Save it somewhere private (NOT in the repo), e.g. `..\PrivateData\gcal-service-account.json`.
   - Copy the service account's **email** (`...@...iam.gserviceaccount.com`).

3. **Share the calendar with the service account (read-only):**
   - Google Calendar → the Glizzness calendar → **Settings and sharing** →
     **Share with specific people** → add the service-account email →
     permission **"See all event details"** (read-only).

4. **Get the Calendar ID:** same Settings page → **Integrate calendar → Calendar ID**
   (often the account email, or a `...@group.calendar.google.com` id).

5. **Install deps (one-time):**
   ```
   pip install google-api-python-client google-auth requests
   ```

## Running the sync

Set the env vars, then run. PowerShell:
```powershell
$env:GOOGLE_SA_KEYFILE   = "C:\path\to\gcal-service-account.json"
$env:GOOGLE_CALENDAR_ID  = "glizzness@gmail.com"      # your Calendar ID
$env:SUPABASE_URL        = "https://ikhcbncnaojrndilmnnd.supabase.co"
$env:SUPABASE_SERVICE_KEY= "<service-role key>"

python sync_calendar.py --dry-run     # preview — writes nothing
python sync_calendar.py               # sync the next 180 days
```

## Keep it fresh (schedule it)
Run it on a timer so the site stays current — e.g. **Windows Task Scheduler** every
1–2 hours (mirror `run_daily.ps1`'s pattern), or any cron. The sync is idempotent
(delete-future + insert), so re-running is always safe.

## Security
- The service-account JSON key grants read access to the calendar — **never commit it.**
  Keep it in `..\PrivateData\` (or anywhere outside the repo). `.gitignore` also blocks
  `*service-account*.json` / `gcal-*.json` as a backstop.
- The site only ever reads the **sanitized** `cart_schedule` (anon key, read-only).
  Private event titles/locations are never stored there.
