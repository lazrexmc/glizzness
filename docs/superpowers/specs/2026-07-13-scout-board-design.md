# Scout Board — design spec (v1, "the full loop")

**Date:** 2026-07-13
**Status:** approved shape; pending spec review → implementation plan.
**Related:** `TODO.md` (Scout board + admin hub items), `CATERING_LEADS.md` (the Make→Gmail pattern
this reuses), the memory `project-admin-hub-scout`, and the Midwest Event Finder
(`site/festivals/`) that the seed data was pulled off of.

---

## 1. Purpose

Turn the 27 curated research "prospects" (from the 7-run deep-research sweep) into **booked gigs**.
Prospects are **prescreened first** — a one-click **deep-research assist** drafts the missing details
(fee, deadline, crowd, food policy) and Lance confirms them, so Trint only ever sees vetted, complete
cards and decides on good info, not guesses.
Give **Trint** — the owner/cook, who reads better through clear visual layout than dense text — a
dead-simple, phone-first way to triage each prospect **✅ Yes / 🤔 Maybe / ❌ No** and ask a question;
give **Lance** a desk to answer those questions, fill in missing event details, work the Yeses, and
**manually add new leads** — the random email/call requests to vend somewhere — so every opportunity,
researched or inbound, flows through Trint's one triage process instead of a separate inbox.
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
| `id` (pk) | seed rows keep `id` (500+); desk-added leads get fresh ids (see seed note) |
| `source` (text, default `research`) | `research` for the 27 seed rows; `inbound` for desk-added email/call leads |
| `stage` (text: `researching`/`ready`, default `researching`) | prescreen gate: Trint's board shows **only `ready`**; Lance enriches `researching` rows, then marks them ready |
| `research_requested_at` (nullable) | set when Lance taps "🔎 Research this" — queues the row for the deep-research runner |
| `research_filled_at` (nullable) | set by the runner once it has written drafts; UI shows "researched — confirm me" until Lance vets |
| `research_summary` (text, nullable) | the runner's short findings + sources, for Lance to sanity-check |
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
safe and never clobbers Lance's in-app edits). `id` is `bigint generated by default as identity`; after
seeding the explicit 500+ ids the sequence is bumped above the seed range (`setval`) so **desk-added
leads (§7) get fresh, non-colliding ids** automatically. **Excluded prospects are left out** — rows with
`food_truck_friendly = 'excluded'` / `verification_status = 'excluded'` (the ~4 known no-gos, e.g.
Double X Speedway which sells its own dogs) are **not** seeded, since Trint's board is "respectable
events only." Result: ~23 cards, all seeded as `stage = researching` (Lance's initial prescreen
backlog). Lance runs the generated SQL in the Supabase editor (same as the vending load).

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

**Only prescreened cards appear here** (`stage = ready`) — Trint sees vetted, filled-in events, not raw
leads. Full-screen, **one big card at a time**, grouped by date (and it **must show multiple events on the
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
- **Any remaining unknowns show plainly** ("not yet known") — prescreening makes these rare, but a
  genuine TBD is shown, never hidden and never buried in text.
- **Food policy** renders as a plain line: `open` → "🌭 Food OK", `unknown` → "🌭 Food — needs
  checking".
- **Filter:** an "undecided only" toggle (prospects with no `prospect_decisions` row) so he grinds
  the pile down; default shows undecided first.

## 7. Lance's review desk (`hub/desk`)

A compact list/table of all prospects with Trint's decision + latest question. Lance can:
- **Add a lead** → a small form creates a new `event_prospects` row (name required; city / type / date /
  distance / fee / crowd / notes optional; `source = inbound`). It lands on Trint's board as
  **undecided**, so the random email/call requests to vend somewhere enter his natural triage — no
  separate inbox to babysit. (Distinct from `catering_leads`, which is customer *catering* bookings;
  these are *vending-opportunity* requests.)
- **Prescreen → mark ready** → work the `researching` queue (the ~23 seed + any inbound leads): fill the
  gaps (fee / deadline / crowd / food policy), then hit **"Ready → send to Trint"** (`stage = ready`).
  Only then does the card reach Trint's board. **This is the quality gate.**
- **🔎 Research this** → queues the prospect for the deep-research assist (sets `research_requested_at`);
  drafts come back for you to confirm (see the auto-fill note below).
- **Answer** a question → inserts `prospect_thread` (`author = lance`); it appears on Trint's card.
- **Edit** a prospect → updates `event_prospects` (fill fee, deadline, crowd, food policy, notes).
  This is how the "needs checking" gaps get filled.
- **Mark booked** → sets `event_prospects.booked = true`, `booked_at = now`.
- **Sort/filter by decision** (Yes / Maybe / No / undecided) so the Yeses are easy to work.

**Deep-research auto-fill (the 🔎 button).** A browser button can't *run* deep research — this is a static
site with no backend. So the honest design: the button **queues** the prospect; a **Claude-side runner**
(`scout_research.py`, which Lance runs from his Claude Code session — it has the deep-research tooling +
the service-role key) picks up queued rows, runs a deep-research pass per prospect (reusing the 7-run
sweep tooling), and **writes drafts back** to `event_prospects` (fee / deadline / crowd / food_policy /
source + `research_summary`), setting `research_filled_at`. Lance then **confirms** the drafts (flagged
"researched — confirm me", never auto-trusted) and marks the card ready. So "one click" = request now,
fields fill in when the runner next runs — hands-off, not instant.

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
5. Lance's desk (`hub/desk`) + the 🔎 "Research this" queue button.
6. Deep-research runner (`scout_research.py`, Claude-side) → drafts back to `event_prospects` for confirm.
7. Make→Gmail alert (webhook + scenario, per `CATERING_LEADS.md`).
8. Hub launcher tiles.
9. Deploy (rides the Cloudflare Pages deploy), confirm the gate blocks logged-out access, send Trint
   the link.

## 11. Non-goals (v1 YAGNI)

- The deep-research runner is **manual-trigger** in v1 (Lance runs `scout_research.py` from his session),
  not a scheduled/always-on service — a cron/auto-run is a later nicety. (The one-click auto-fill itself
  *is* in v1; only the "run it on a schedule without Lance" part is deferred.)
- No user roles/permissions beyond "logged in" (both users can do everything).
- No push/SMS notifications — email only.
- No native app — mobile web.
- Trint does **not** edit event details (only decides + asks); only Lance enriches.
- No analytics/reporting, no calendar sync, no auto-application. (Booked events flowing to the
  Where-We-Vend calendar is a *later* idea, not v1.)
- The excluded no-go prospects are not shown at all.

## 12. Open flags / risks

- **Drive time is an estimate** (`distance ÷ ~50 mph`), fine for triage, not routing.
- **The prescreen gate trades immediacy for quality:** the seed data is thin (fee/deadline/crowd often
  blank), and Trint only sees `ready` cards — so **his board starts empty until Lance vets the ~23**.
  Lance's upfront prescreen pass is the gating work; the payoff is Trint decides on good info, not
  guesses. The one-click deep-research auto-fill (§7) is what makes that prescreen pass fast.
- **"One-click deep research" is request-now, fill-later — not instant, and not from the browser.** A
  static site has no backend to run deep research, so the button queues the prospect and the Claude-side
  runner fills it in on its next run. Drafts are always **flagged for Lance's confirmation**, never
  auto-marked ready — deep research can be wrong, so a human vets before Trint sees it.
- **supabase-js from CDN** is a new client dependency on the gated pages (the public site doesn't use
  it). Acceptable — it's the clean way to manage the auth session; if CDN/CSP is ever a concern we can
  self-host the one file.
- **Auth reset/lockout:** if a password is lost, Lance resets it in the Supabase dashboard. Document
  this in the runbook.
