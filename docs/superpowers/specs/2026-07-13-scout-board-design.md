# Scout Board — design spec (v1, "the full loop")

**Date:** 2026-07-13
**Status:** approved shape; pending spec review → implementation plan.
**Related:** `TODO.md` (Scout board + admin hub items), `CATERING_LEADS.md` (the Make→Gmail pattern
this reuses), the memory `project-admin-hub-scout`, and the Midwest Event Finder
(`site/festivals/`) that the seed data was pulled off of.

---

## 1. Purpose

Turn the 27 curated research "prospects" (from the 7-run deep-research sweep) into **booked gigs**.
Give **Trint** — the owner/cook, who reads better through clear visual layout than dense text — a
dead-simple, phone-first way to triage each prospect **✅ Yes / 🤔 Maybe / ❌ No** and ask a question;
give **Lance** a desk to answer those questions, fill in missing event details, and work the Yeses.
It is **private** (never in the public site nav) and lives behind a real login.

This is the first tool to live behind the planned **admin hub**, so v1 builds a minimal hub too.

## 2. Constraints & principles

- **Build for Trint (hard accessibility constraint):** big, visual, icon-led, low-reading-burden —
  one fact per line, few words, unknowns stated plainly ("not yet known"), never a wall of text.
- **Mobile-first / one-handed:** Trint uses it on a phone; huge tap targets.
- **Private, real lock:** server-enforced auth (Supabase), not client-side theater. Unlinked from
  public nav; reached by bookmark.
- **Reuse the existing stack:** static pages on Cloudflare Pages + Supabase + Make→Gmail, same
  patterns as the catering lead pipeline. No new vendors, no framework.
- **YAGNI:** see Non-goals (§11).

## 3. Access & auth

- **Supabase Auth (email + password).** Two accounts: Trint and Lance. Created once by Lance in the
  Supabase dashboard (no public sign-up).
- The three Scout tables (§5) have **Row-Level Security ON** with policies granting full access **only
  to the `authenticated` role** (`to authenticated using (true) with check (true)`); **no `anon`
  policy**, so a logged-out visitor with the public anon key can read/write nothing. This is the real
  wall — the login gate isn't cosmetic, the database itself refuses anonymous access.
- The gated pages use **supabase-js** (from a CDN, like Leaflet is today) for the login session +
  data calls. The public site/finder keep their existing raw-`fetch` approach — unchanged.
- Both users can do everything (Trint's page and Lance's desk are just different screens, not
  permission tiers). Fine for two trusted people; revisit only if a third user with limited rights
  ever appears.

## 4. Pages (all gated, none in public nav)

| Path | Who | Purpose |
|---|---|---|
| `hub/` | Lance + Trint | Admin launcher: a login screen, then big tiles → **Scout Board**, **My Desk**, **Wave Dashboard** (opens `glizzness.streamlit.app` in a new tab). |
| `scout/` | Trint (mostly) | The card board — triage prospects. |
| `hub/desk` (or `hub/desk.html`) | Lance | The review desk — answer questions, enrich events, mark booked. |

A single Supabase session covers all three (log in once at the hub). A logout control on each.

## 5. Data — three Supabase tables

All `bigint`/`timestamptz`/`text` unless noted; RLS as in §3.

### `event_prospects` — the events
Seeded once from `data/prospects.csv`, then **edited in-app by Lance**. One row per prospect.

| Column | Source (prospects.csv) / notes |
|---|---|
| `id` (pk) | `id` (500+) |
| `name`, `event_type`, `city`, `state`, `county` | direct |
| `distance_mi` (int) | `distance_from_columbia_mi` |
| `drive_time_min` (int) | **computed** at seed: `round(distance_mi / 50 * 60)` (rough estimate) |
| `date_text` | `typical_dates` |
| `month` (int, nullable) | `month` |
| `crowd_text`, `crowd_estimate` (int, nullable) | `attendance_text`, `attendance_estimate` |
| `fee_text` | `food_vendor_fee` (often blank → shows "not yet known") |
| `application_method` | `application_method` |
| `application_deadline` (text, nullable) | **not in source** → null; Lance fills from the desk |
| `food_policy` (text: `open`/`competing`/`unknown`) | derived from `food_truck_friendly`: `explicit_yes`/`concession_friendly`→`open`, `unconfirmed`→`unknown` |
| `notes` | `notes` |
| `source_url` | `homepage_url` or `primary_source_url` |
| `lat`, `lng` (float) | direct |
| `booked` (bool, default false), `booked_at` (nullable) | Lance sets from the desk |
| `created_at`, `updated_at` | defaults |

**Seed:** a small script (e.g. `scout_seed_gen_sql.py`) reads `data/prospects.csv`, derives
`drive_time_min` + `food_policy`, and emits `insert ... on conflict (id) do nothing` (so re-running is
safe and never clobbers Lance's in-app edits). **Excluded prospects are left out** — rows with
`food_truck_friendly = 'excluded'` / `verification_status = 'excluded'` (the ~4 known no-gos, e.g.
Double X Speedway which sells its own dogs) are **not** seeded, since Trint's board is "respectable
events only." Result: ~23 cards. Lance runs the generated SQL in the Supabase editor (same as the
vending load).

### `prospect_decisions` — Trint's call
| Column | Notes |
|---|---|
| `id` (pk) | |
| `prospect_id` (fk → event_prospects, **unique**) | one current decision per prospect (upsert on re-tap) |
| `decision` (text: `yes`/`maybe`/`no`) | |
| `decided_by` (text) | the logged-in user's email |
| `decided_at` | default now |

### `prospect_thread` — the Q&A
| Column | Notes |
|---|---|
| `id` (pk) | |
| `prospect_id` (fk → event_prospects) | |
| `author` (text: `trint`/`lance`, or the email) | who wrote it |
| `body` (text) | the question or the answer |
| `created_at` | default now |

Trint's question and Lance's answer are both rows here; the card and desk render the thread
newest-last. Keeps decisions clean and lets the conversation grow.

## 6. Trint's card board (`scout/`)

Full-screen, **one big card at a time**, grouped by date (and it **must show multiple events on the
same day** — unlike the public "Where We Vend" list). Big type, icons, one fact per line:

```
┌─────────────────────────────────┐
│  🏁  CALLAWAY RACEWAY            │
│      Fulton · dirt track         │
│                                  │
│  📍  26 mi    ·    ~30 min       │
│  📅  Weekly race nights          │
│  👥  Grandstand crowd            │
│  💵  Fee — not yet known         │
│  🌭  Food — needs checking       │
│                                  │
│  [ ✅ YES ]  [ 🤔 MAYBE ]  [ ❌ NO ] │
│                                  │
│  ❓ Ask a question…              │
│  💬 Lance: "Called — they're in, │
│      $40, apply by Aug 1."       │
│                                  │
│  1 of 23              ▸ next     │
└─────────────────────────────────┘
```

- **Decision:** tapping ✅/🤔/❌ **upserts** `prospect_decisions` and advances to the next card. The
  current decision is shown if he comes back.
- **Ask:** the "❓ Ask a question…" field inserts a `prospect_thread` row (`author = trint`). Any of
  Lance's answers render on the card (💬).
- **Unknowns show plainly** ("not yet known" / "needs checking") — never hidden, never verbose.
- **Food policy** renders as a plain line: `open` → "🌭 Food OK", `unknown` → "🌭 Food — needs
  checking".
- **Filter:** an "undecided only" toggle (prospects with no `prospect_decisions` row) so he grinds
  the pile down; default shows undecided first.

## 7. Lance's review desk (`hub/desk`)

A compact list/table of all prospects with Trint's decision + latest question. Lance can:
- **Answer** a question → inserts `prospect_thread` (`author = lance`); it appears on Trint's card.
- **Edit** a prospect → updates `event_prospects` (fill fee, deadline, crowd, food policy, notes).
  This is how the "needs checking" gaps get filled.
- **Mark booked** → sets `event_prospects.booked = true`, `booked_at = now`.
- **Sort/filter by decision** (Yes / Maybe / No / undecided) so the Yeses are easy to work.

## 8. Alerts (Make → Gmail, reuse the catering pipeline)

Supabase Database Webhook(s) → a Make scenario → Gmail to `glizzness@gmail.com`, same shape as
`CATERING_LEADS.md`:
- On **insert to `prospect_thread` where `author = trint`** (Trint asked a question).
- On **insert to `prospect_decisions` where `decision in ('yes','maybe')`** (worth acting on).
- A **"no" never alerts** — no spam. (Filter in Make: `decision` Contains `yes`/`maybe`, or a
  separate webhook per event, mirroring the catering `email Contains @` filter trick.)

## 9. Admin hub launcher (`hub/`)

The gated front door: a Supabase login form, then big tiles → **Scout Board** (`scout/`), **My Desk**
(`hub/desk`), **Wave Dashboard** (external link to `glizzness.streamlit.app`, new tab). **Streamlit
stays where it lives** — the hub only links to it (no reverse-proxy; a Streamlit custom domain would
need a fussy Cloudflare websocket proxy for little gain on an already-password-protected tool). Not
linked from the public site nav.

## 10. Build order (once the spec is approved → see the implementation plan)

1. Supabase: create the 3 tables + RLS policies; create the Trint + Lance auth users.
2. Seed loader (`scout_seed_gen_sql.py`) → run the generated SQL to load ~23 prospects.
3. Shared auth/login + supabase-js wiring (`hub/` login).
4. Trint's card board (`scout/`).
5. Lance's desk (`hub/desk`).
6. Make→Gmail alert (webhook + scenario, per `CATERING_LEADS.md`).
7. Hub launcher tiles.
8. Deploy (rides the Cloudflare Pages deploy), confirm the gate blocks logged-out access, send Trint
   the link.

## 11. Non-goals (v1 YAGNI)

- No user roles/permissions beyond "logged in" (both users can do everything).
- No push/SMS notifications — email only.
- No native app — mobile web.
- Trint does **not** edit event details (only decides + asks); only Lance enriches.
- No analytics/reporting, no calendar sync, no auto-application. (Booked events flowing to the
  Where-We-Vend calendar is a *later* idea, not v1.)
- The excluded no-go prospects are not shown at all.

## 12. Open flags / risks

- **Drive time is an estimate** (`distance ÷ ~50 mph`), fine for triage, not routing.
- **Seed data is thin** — fee/deadline/crowd are often blank, so early cards show many "needs
  checking" lines and Trint's first pass will generate questions. That's the loop working, but set
  the expectation. Lance filling gaps from the desk is core, not optional.
- **supabase-js from CDN** is a new client dependency on the gated pages (the public site doesn't use
  it). Acceptable — it's the clean way to manage the auth session; if CDN/CSP is ever a concern we can
  self-host the one file.
- **Auth reset/lockout:** if a password is lost, Lance resets it in the Supabase dashboard. Document
  this in the runbook.
