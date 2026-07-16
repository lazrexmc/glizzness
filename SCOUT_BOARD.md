# Scout Board — runbook

Trint's phone-first event-triage tool + Lance's review desk, behind a login gate. Turns the
27 curated research picks (and any inbound vend requests) into booked gigs.

- **Design spec:** `docs/superpowers/specs/2026-07-13-scout-board-design.md`
- **Pattern reused:** `CATERING_LEADS.md` (the Supabase + Make→Gmail pipeline)
- **Live URLs** (once deployed): `glizzness.com/hub` · `glizzness.com/scout` · `glizzness.com/hub/desk`
  — none are in the public nav; reach them by bookmark.

---

## What got built (in the repo)

| File | Role |
|---|---|
| `supabase_scout_schema.sql` | The 3 tables + RLS (authenticated-only). Run once. |
| `scout_seed_gen_sql.py` | Reads `data/prospects.csv` → emits `supabase_scout_data.sql` (23 cards; 4 no-gos excluded). |
| `supabase_scout_data.sql` | Generated seed INSERTs. Run once, after the schema. |
| `site/assets/scout.js` | Shared supabase-js auth (login session, gate/redirect, helpers). |
| `site/assets/scout.css` | Scout styling (reuses the brand tokens from `site.css`). |
| `site/hub/index.html` | Login gate + tiles (Scout Board · My Desk · Wave Dashboard). |
| `site/scout/index.html` | Trint's card board. |
| `site/hub/desk.html` | Lance's review desk. |

**Architecture:** static pages on Cloudflare Pages + Supabase, same stack as the catering form.
The public site uses raw `fetch` + the anon key; the **gated** Scout pages use **supabase-js** for a
real login session. Three tables have RLS with **only** an `authenticated` policy — logged out, the
public anon key (already in `assets/config.js`) can read/write **nothing** here. The login is the wall.

---

## ONE-TIME SETUP (Lance — these need the Supabase dashboard / your credentials)

### 1. Create the tables
Supabase → **SQL Editor** → paste all of `supabase_scout_schema.sql` → **Run**. (Safe alongside the
accounting / vending / catering / cart_schedule tables.)

### 2. Create the two login users
Supabase → **Authentication → Users → Add user** (do this twice; there is no public sign-up):
- Trint — his email + a password you set. ✅ tick **Auto Confirm User**.
- Lance — your email + a password. ✅ **Auto Confirm User**.

> The app tags thread messages by the email local-part: an address starting `trint`/`james`/`jason`
> shows as Trint; `lance`/`laz` shows as Lance. Pick emails that start that way and the Q&A labels
> itself correctly. (Cosmetic only — any email can log in and use everything.)

### 3. Seed the 23 prospects
```
python scout_seed_gen_sql.py
```
Then Supabase → **SQL Editor** → paste `supabase_scout_data.sql` → **Run**. Re-running is safe
(`on conflict (id) do nothing` — it never clobbers edits you've made in the app).

### 4. Deploy
`git push` — Cloudflare Pages auto-builds `site/`. The three pages go live at `/hub`, `/scout`,
`/hub/desk`.

### 5. Smoke-test the gate (proves it's a real wall, not theater)
- Open `glizzness.com/scout` **logged out** → it must bounce you to `/hub`.
- Log in at `/hub` → you land on the tiles; **Scout Board** and **My Desk** now open.
- Bonus: while logged out, in the browser console, a `fetch` to `…/rest/v1/event_prospects` with the
  anon key returns `[]`/permission-denied — the data is inaccessible without a session.

---

## DAILY USE

**Trint** → bookmark `glizzness.com/scout`.
- One big card at a time, newest/soonest first. Tap **✅ Yes / 🤔 Maybe / ❌ No** — it saves and jumps
  to the next card. Type a question in **❓ Ask** and it goes to Lance; his answers show on the card.
- "Undecided only" is on by default so he grinds the pile down; uncheck it to review past calls.

**Lance** → `glizzness.com/hub/desk`.
- **Filters:** All / Researching / Ready / Undecided / Yes / Maybe / No / Booked.
- **+ Add lead** — a random email/call vend request. Lands as `inbound` + `researching`.
- **Ready → Trint** — after you've filled the gaps (fee, deadline, crowd, food policy), this flips
  `stage = ready` and the card appears on Trint's board. **This is the quality gate — Trint only ever
  sees `ready` cards.**
- **Edit** — fill in the blanks (this is how "not yet known" becomes real info).
- **Answer** — reply to Trint's question (or leave a note); it lands on his card.
- **Mark booked** — closes it out (drops off Trint's board).

---

## BUILDING CARDS WITH CLAUDE (the CLI loop — no in-app research button by design)

The seed cards are thin (fee/deadline/crowd often blank). To make Trint's board useful, cards get
enriched **here in the Claude Code CLI**, then approved:

1. Ask Claude to research a prospect (deadline, fee, crowd, food policy, contact). *Paced/serial —
   parallel web-search trips the rate limiter.*
2. Claude drafts the fields + a short `research_note` with sources; Lance reviews/tweaks.
3. Approve → either (a) you edit the row on the **desk** and hit **Ready → Trint**, or (b) Claude
   writes it straight in as `stage = ready` via a small loader (same idea as the vending load).

Inbound leads added from the desk start as `researching` and enrich the same way.

---

## ALERTS (phase 2 — optional, mirrors `CATERING_LEADS.md`)

Get a Gmail ping when Trint acts, so you don't have to poll the desk. Supabase **Database Webhooks**
→ a Make scenario → Gmail to `glizzness@gmail.com`:
- On insert to `prospect_thread` where `author = 'trint'` (he asked a question).
- On insert to `prospect_decisions` where `decision in ('yes','maybe')` (worth acting on).
- **A "no" never alerts** (no spam). Use the same Make filter trick as the catering auto-reply
  (`decision` Contains `yes`/`maybe`).

Not required for v1 — the desk shows everything. Add it when checking the desk gets old.

---

## MAINTENANCE / GOTCHAS

- **Lost password:** Supabase → Authentication → Users → the user → reset/set a new password.
- **ids:** seed rows keep their 500-range ids; the seed script bumps the identity sequence so
  desk-added leads get fresh, non-colliding ids automatically.
- **Re-seeding is safe** (`on conflict do nothing`) — it won't overwrite in-app edits, and excluded
  no-gos (Double X, Lucas Oil, Serenity Valley, Air Show) are never seeded.
- **supabase-js** loads from unpkg (like Leaflet on the map). If a CSP is ever added to the site,
  allow-list `unpkg.com` + the Supabase project origin, or self-host the one file.
- **Not indexed:** each gated page carries `noindex`, and `robots.txt` disallows `/hub` + `/scout`
  (the RLS wall is the real protection; this just keeps them out of search).
