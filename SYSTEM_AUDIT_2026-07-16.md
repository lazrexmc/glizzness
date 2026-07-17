# Full-System Audit — 2026-07-16

**Scope:** every live subsystem — gated tools (hub/scout/signals/posts/desk + scout.js/demand.js),
public site (site.js, festivals map, catering form), crawler (Python + adapters), data layer (all
Supabase schemas/RLS/grants), ops scripts + CI (sync_calendar, demand_baseline, both workflows),
and documentation-vs-reality.

**Method:** 6 specialist auditors → 41 findings raised → **every finding adversarially verified by an
independent skeptic** → **37 confirmed, 4 refuted**. 47 agents (Fable 5), ~1.9M tokens.
*(Companion: `SCOUT_AUDIT.md` was the 2026-07-16 pre-deploy audit of the Scout board alone; its
Phase B/C items remain open and are not re-listed here.)*

**Verdict, honestly:** the platform is sound in its bones — the RLS pattern, the idempotent loads,
the escape discipline all held up. But the audit caught **2 criticals** that mattered enormously:
a security hole that undermined the entire private-data model (self-signup), and a UI bug that made
the newest tool act on the wrong data (Post Cards indexing). Both are exactly the class of bug that
one-developer + one-reviewer processes miss — the finder that raised the signup hole read *what the
schema didn't say*. Worth every token.

---

## PHASE A — criticals + confirmed highs (✅ ALL FIXED / delivered this same day)

| # | Sev | Where | Finding | Resolution |
|---|-----|-------|---------|------------|
| 1 | **CRIT** | `site/hub/posts.html` | Action buttons resolved `data-i` against the **unfiltered** array while cards were rendered from the **filtered** list — as soon as one card was decided, Approve/Copy/Edit/Undo all hit the WRONG card (wrong text pasted into Business Suite, wrong drafts deleted) | ✅ fixed — handler resolves against the rendered list (`shown`) |
| 2 | **CRIT** | all private tables | **Self-signup hole:** Supabase's `/auth/v1/signup` is ON by default and reachable with the published anon key; every private policy trusted ANY `authenticated` user → a stranger could self-register and read/write prospects, signals, drafts, and revenue profiles. Docs claimed "no public sign-up" — true only if a dashboard toggle was flipped, and nothing ensured it was | ✅ two-pronged: **(a) Lance disables the dashboard toggle** (Auth → Sign In/Providers), **(b) `supabase_hardening_2026-07-16.sql`** adds an `app_allowed` email allowlist checked by every private-table policy via a SECURITY DEFINER fn — we no longer depend on the toggle |
| 3 | HIGH | `site/festivals/app.js` + vending RLS | The public map fetched the **whole `vending_events` table**; the publish gate + prospect exclusion were client-side JS only. Anyone could curl `id=gte.500` with the anon key and read Trint's 27 private prospects (contacts, fees, notes) + defunct rows. The 07-13 "pull the picks off the map" was cosmetic | ✅ in the hardening SQL: the RLS policy **is** now the publish gate (`id<500` + verified/partial + not excluded + located); child tables follow via `exists` |
| 4 | HIGH | `crawler/run.py` | A run where EVERY source failed exited 0 and looked identical to a quiet day — the cron would stay green while the feed dried up forever | ✅ all-sources-failed now exits 1 (one dead source still doesn't kill a run) |
| 5 | HIGH | `crawler/adapters/rss.py` | `feedparser` never raises — 403/404/DNS came back as "ok 0", so 7 of 10 sources could never show ERROR | ✅ raises on HTTP ≥400 / unparseable-empty. **Immediately exposed that `rss:vox` has been silently broken since day one** (→ Phase B) |
| 6 | HIGH | `sync_calendar.py` | delete-future-then-plain-INSERT: an in-progress event that started before the cutoff survives the delete but is still returned by Google → unique-key 409 AFTER the delete → the public schedule left **empty** until a later run | ✅ insert → **upsert** on `gcal_event_id` |
| 7 | HIGH | `REBUILD.md` | The from-nothing rebuild path omitted everything added 2026-07-16 (post_drafts, demand_profiles, lunch seed) — a DR would silently rebuild without them | ✅ SQL run-order now lists steps 9–12 incl. the hardening file + signup-toggle step |

**Lance's two credentialed steps (the only outstanding Phase A items):**
1. Dashboard → Authentication → Sign In/Providers → **disable "Allow new users to sign up."**
2. Run **`supabase_hardening_2026-07-16.sql`**, then its step 5 (insert the two allowed emails).
   ⚠️ Until step 5 runs, the hub shows no data (allowlist starts empty — fail-closed on purpose).

## PHASE B — confirmed mediums (fix in the next working session)

| Where | Finding |
|-------|---------|
| `crawler/sources.py` | **`rss:vox` is broken** (unparseable response — likely bot-blocking feedparser's UA). Was invisible until fix #5; investigate or disable |
| `crawler/config.py` | `is_competitor()`/`EVENT_RESCUE` match bare substrings — word-boundary them (same class as the demand.js fix) |
| `crawler/run.py` | vendor-booked pairing: items with `event_date=None` bypass the taken-date drop; the "no food partner" note stamps even when zero competitors were recognized |
| `crawler/config.py` | `is_dead()` scans the whole blob — an event *mentioning* a past cancellation gets dropped (comeback events are exactly the signal we want) |
| `site/assets/demand.js` | `nameMatchesKey` anchors the start but not the END of the key — a key matching a longer word's prefix still reads as history |
| `site/hub/posts.html` | Edit-modal "Save & approve" closes unconditionally — a DB error destroys the edited copy; also: a **rescheduled stop stays "approved" with stale copy** (keyed on ref+touch only) |
| `site/hub/signals.html` | `picked` filter set keeps vanished sources (count drifts); `keep()` is a non-atomic 2-step (dup prospects possible on retry/2 devices); feed reads newest **500 across all statuses** — old untriaged "new" rows fall off once the table outgrows it (prune or filter server-side) |
| `demand_baseline.py` | no cross-file order dedup (overlapping Sales exports double-count); `attach()` buckets by exact date so the ±5h window never crosses midnight + multi-day all-day events only match day 1 |
| `site/catering.html` | form has no action + `novalidate` — with JS failed/off, submit GET-navigates with PII in the query string and the lead vanishes; email never validated anywhere |
| `supabase_catering_schema.sql` | grant tightening for `catering_leads`/`cart_schedule` — ✅ **already folded into the hardening SQL** (clean grant reset) |

## PHASE C — confirmed lows (backlog)

posts.html: failed-Skip button relabels to "Approve"; morning-of hardcodes 10 AM (a 9 AM stop gets announced after it starts). site.js: schedule fetch caps at 60 rows with private blocks counting against it; catering insert has no length caps/honeypot. sync_calendar: Google's all-day `end.date` is EXCLUSIVE → ends stored a day late. demand_baseline: unparseable rows dropped with zero accounting. rss.py: `pubDate` on event feeds is publish-date, not event-date (comment claims otherwise). Docs: HANDOFF §5 table list (✅ fixed), SIGNAL_NET tribe.py omission (✅ fixed), SCOUT_BOARD tile list (✅ fixed), REBUILD anon-key paths (✅ fixed).

## REFUTED (4) — raised, then killed by the skeptics; do not "fix"

| Claimed | Why it died |
|---------|-------------|
| `javascript:` URLs in signals hrefs | Code reading accurate, scenario doesn't hold for curated-feed URLs + the manual add is the owner |
| UTC date cutoff hides tonight's stop after 7pm | `starts_at=gte.<date>` compares against timestamptz midnight — evening stops still ≥ today's midnight |
| Festival list sorts by first-loaded schedule row | Requires multi-schedule events; the dataset has none (1:1) |
| `clean()` strip-then-unescape "resurrects" markup | That order is the standard correct HTML-to-text extraction; display layers all `esc()` |

## Feedback (the part you asked for)

1. **The adversarial layer is the whole game.** 41 raised → 4 killed. Without the skeptics we'd have
   "fixed" four non-bugs — including reordering `clean()` into something *worse*.
2. **The two criticals share a root:** both were *assumption* gaps, not code typos — "authenticated
   means one of us" and "the filtered list is the list." Reviews that only read diffs don't catch
   these; auditors reading *the system* did.
3. **Silent-failure hunting paid off instantly** — the vox feed has been dead the whole time and
   every prior run reported it as a quiet day. "Green" and "working" are different claims.
4. **Docs drift fast at this build pace.** Six of 37 findings were documentation contradictions,
   all from one day's work. The docs-truth auditor should run after every big build day.
5. **Pattern to keep:** every fix from this audit went through the same discipline as the code it
   fixes — word-boundary matchers got tests, the hardening SQL fails closed, the crawler
   distinguishes outage from quiet.
