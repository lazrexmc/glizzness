# "Where We Vend" calendar — setup

The website's **Where We Vend** page shows an on-brand "Upcoming stops" list. It reads
a **sanitized mirror** of the business Google Calendar from Supabase (`cart_schedule`).
The browser never touches Google — only public-safe rows.

> **STATUS — ✅ ACTIVATED 2026-07-11:** schema run, service account + calendar share done, real sync run
> (events populate `cart_schedule`), `events.html` renders the collapsible list.
>
> **✅ AUTO-REFRESH IS ON (2026-07-16).** The sync runs on **GitHub Actions every 2h**
> (`.github/workflows/calendar.yml`) — verified in the cloud (`synced 45 event(s)`, 30 public). It keeps
> working while Lance's PC is off and he's out at the cart, which is exactly when it matters.
> **`glizzness.com/events` is now trustworthy → the "check the website" marketing CTA is SAFE to use.**
>
> **Two ways to sync, both valid:**
> 1. **Automatic** — every 2h, hands-off. Nothing to do.
> 2. **Right now** — `PrivateData\sync-calendar.ps1` (right-click → Run with PowerShell). Use when you
>    just changed the calendar and don't want to wait up to 2h. Add `-DryRun` from a terminal to preview.
>
> *(The old Windows Task Scheduler plan was rejected — a local job dies exactly while Trint is out
> vending. See §"Keep it fresh".)*

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

## Keep it fresh — automated via GitHub Actions (every 2h)

**`.github/workflows/calendar.yml` runs `sync_calendar.py` in the cloud every 2 hours** (+ a manual
"Run workflow" button). The sync is idempotent (delete-future + insert), so re-running is always safe.

> **Why Actions and not Windows Task Scheduler** (the old plan): Task Scheduler only fires when
> Lance's PC is on and awake — which means the schedule would go **stale exactly while he's out
> working the cart** and customers are checking `glizzness.com/events`. That's the one moment it has
> to be right. Actions runs regardless of any local machine.

**✅ These three secrets are SET (2026-07-16) and the workflow is running.** Listed for disaster
recovery — GitHub → repo **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `GOOGLE_SA_JSON` | the **entire contents** of the service-account JSON key file (open it in a text editor, copy all of it, paste) |
| `GOOGLE_CALENDAR_ID` | the Calendar ID from step 4 above (often `glizzness@gmail.com`) |
| `SUPABASE_SERVICE_KEY` | the Supabase **service_role** key (Project Settings → API). *Shared with the Signal Net crawler — set it once.* |

The workflow writes `GOOGLE_SA_JSON` to a temp file on the ephemeral runner and points
`GOOGLE_SA_KEYFILE` at it, so **`sync_calendar.py` needs no changes** and no key is ever committed.

**First run:** GitHub → **Actions** → "Calendar sync" → **Run workflow** → the log should print
`fetched N event(s) -> M row(s): X public, Y unavailable` then `synced M event(s) to cart_schedule`.
Then check `glizzness.com/events`.

**Cost:** ~720 Actions minutes/month (+ ~360 for the crawler) against the **2,000 free** private-repo
minutes. Comfortable. If you ever need to trim, widen the cron to `0 */4 * * *`.

## Security
- The service-account JSON key grants read access to the calendar — **never commit it.**
  Keep it in `..\PrivateData\` (or anywhere outside the repo). `.gitignore` also blocks
  `*service-account*.json` / `gcal-*.json` as a backstop.
- It **also** lives as the `GOOGLE_SA_JSON` **GitHub Actions secret** (encrypted at rest, masked in
  logs, private repo) so the cloud sync can run. That's a deliberate, accepted tradeoff: the key is
  **read-only and scoped to the calendar** (`calendar.readonly`, no project roles), so its blast
  radius is "someone could read the cart calendar" — not the DB, not the money. To revoke: Google
  Cloud → IAM → Service Accounts → Keys → delete the key, then add a fresh one to the secret.
- The site only ever reads the **sanitized** `cart_schedule` (anon key, read-only).
  Private event titles/locations are never stored there.
