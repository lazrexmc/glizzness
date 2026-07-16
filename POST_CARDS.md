# Post Cards — runbook

Social post drafts, auto-written for every **public** stop on the calendar. Lance reviews, approves,
copies, and pastes into **Meta Business Suite** to schedule. Fixes the real problem: posts used to go
out *as the cart arrived*, so nobody saw them in time.

- **Live URL:** `glizzness.com/hub/posts` (gated; a hub tile)
- **Source of truth:** `cart_schedule` where `is_public = true` — i.e. the Google Calendar, via the
  auto-sync (`CALENDAR_SETUP.md`). **Private/catering gigs never enter this pipeline at all**, so a
  client's address can't leak into a post.
- **Marketing rationale:** the cadence + why lead time matters — see `TODO.md` (marketing section).

---

## ⚠️ Setup (Lance — one SQL file)

Supabase → SQL Editor → run **`supabase_posts_schema.sql`** (creates `post_drafts`; RLS
authenticated-only + anon revoked). That's it — no cron, no secret, no new moving parts.

## How it works

The page **generates the copy itself, in the browser**, every load:

1. Reads your public upcoming stops from `cart_schedule`.
2. For each stop it drafts **two posts**:
   - **📅 Night before** → schedule for **6:00 PM the day before**
   - **☀️ Morning of** → schedule for **10:00 AM that day**
3. Plus one **🗓️ Weekly roundup** per week ("Where to find us this week"), scheduled Sunday 6 PM.
4. Each card shows **when to schedule it**, the **FB text**, the **IG text**, and **which photo**.
5. **Approve / Edit / Skip.** Only the decision is stored — the drafts are regenerated each load.

A post whose send-time has already passed is never offered. Cards are grouped by week; the default
filter is **To review**, so you work the list to empty and close it.

### Why two text variants
- **Facebook** ends with `glizzness.com/events` — links work there.
- **Instagram** ends with *"link in bio"* — **IG captions are not clickable**, so a URL there is dead
  text. Keep your IG bio link pointed at `glizzness.com`.

### Copy rotation (why it isn't the same post every week)
Logboat hits ~3×/week. Identical copy every time trains followers to scroll past. So each card draws
from a pool of **8 night-before + 8 morning-of** phrasings, chosen by a **hash of the event id + touch**
— which means the copy is **varied across stops but stable for a given stop** (it won't reshuffle under
you on reload). Verified: 4 consecutive Logboat stops → 4 distinct night-before variants.

To add/adjust phrasings: edit the `NIGHT` / `MORNING` arrays at the top of the page script.

### Photos
`PHOTOS = ["glizzy.jpg", "cart-mizzou.jpg"]` — rotated per card. **Real photos only** (hard rule: never
AI imagery for product/cart). **This is the current bottleneck on post quality, not the copy** — only
two usable shots exist. When new real photos land in `site/assets/img/`, add the filenames to that one
array and every future card rotates through them.

---

## Daily/weekly use

1. Mark the stop **Visibility = Public** in Google Calendar (that's what makes it a customer-facing stop).
2. Wait for the sync (≤2h) — or run `PrivateData\sync-calendar.ps1` to push it live now.
3. Open **`glizzness.com/hub/posts`** → the new stop's cards appear.
4. **Approve** (or Edit if it's a special one) → hit **copy** on the FB or IG block.
5. In **Meta Business Suite**, paste, attach the photo shown, and schedule it for the **"Schedule for"**
   time on the card.
6. On arrival, post a **Story** by hand — that's the one post that *should* be live, and Stories can't
   be scheduled by any API anyway.

## Gotchas

- **`event_ref` is the `gcal_event_id`, NOT `cart_schedule.id`.** The calendar sync **deletes and
  reinserts every future row on every run**, so `cart_schedule.id` churns every 2 hours — keying off it
  would orphan every approval twice an hour. Google's event id is stable. (The weekly card uses a
  synthetic ref, `week:2026-W29`.)
- **Edit an event's time in Google Calendar** and its cards regenerate with the new send times — but an
  approval you already made still points at the old text/time. Hit **Undo** on the card and re-approve.
- Deleting an event in Google Calendar leaves its `post_drafts` row orphaned. Harmless (nothing reads
  it), but a cleanup is a future nicety.
- Nothing here posts anything. **It drafts; you schedule.** Deliberate — see the roadmap.

## Roadmap (deliberately NOT built)

**Auto-posting to Meta was considered and rejected for now.** It needs a Meta Developer App, **2–4 weeks
of App Review**, and Page/IG tokens that **expire (~60 days) and fail silently** — posts would just stop
one day with no error anywhere obvious. The manual paste costs ~10 min/week and cannot break.

**Revisit only once the weekly review is a proven habit.** The value here is *lead time*, and copy-paste
delivers that today; the API would only save the ten minutes. Build it for a habit you have, not one you
hope to have. (Note: Instagram **Stories** can't be scheduled via API regardless.)
