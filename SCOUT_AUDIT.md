# Scout Board — deep code audit (2026-07-16)

**Scope:** the Scout Board v1 as shipped in commit that added `site/hub/`, `site/scout/`,
`site/assets/scout.{js,css}`, `supabase_scout_schema.sql`, `scout_seed_gen_sql.py`,
`supabase_scout_data.sql`.

**Method:** two independent senior-level reviews — one on the frontend (auth/XSS/logic), one on the
data layer (schema/RLS/seed pipeline) — cross-checked and synthesized, plus author cross-read. The
tool is **pre-deployment** (Lance hasn't run the SQL, created users, or pushed yet), so every fix
below can land before first real use.

**Overall verdict:** the build is **solid and shippable after a short fix pass**. No data-loss or
data-exposure bug exists *today* (RLS is correctly on; XSS escaping is thorough). The real issues are
(1) one genuine security bug — an open-redirect in the login gate, (2) a missing defense-in-depth
backstop on the database, and (3) a cluster of robustness/correctness gaps that will bite quietly
rather than loudly. Nothing here is a rewrite; it's ~2–3 hours of tightening.

Design tradeoffs that are **intentional, not bugs** (excluded from findings): the flat
"both users can do everything" trust model, and the public anon key in `config.js`.

---

## Findings, ranked

Severity: **P0** fix before deploy · **P1** fix now (cheap + real) · **P2** soon · **P3** nice-to-have.

| # | Sev | Area | Where | Problem | Fix |
|---|-----|------|-------|---------|-----|
| 1 | **P0** | Security | `site/hub/index.html:88` `safeNext()` | Open redirect. Guard only blocks `//host`, not `/\host`. Browsers normalize `\`→`/` for http(s), so `?next=/\evil.com` passes and `location.replace` sends a **logged-in** user off-site — a phishing primitive aimed straight at the two keyholders. | Replace hand-rolled check with `new URL(n, location.origin)` and compare `.origin`; return `pathname+search+hash` only on same origin. |
| 2 | **P0** | Security | `supabase_scout_schema.sql:83` | RLS-only, no grant backstop. Supabase default-grants `anon` table CRUD on new public tables; only the *absence of a policy* blocks it. If anyone ever `disable row level security` for a one-off fix and forgets to re-enable, the public key gets full read/write instantly. | Add `revoke all on event_prospects, prospect_decisions, prospect_thread from anon;` after the grant. Turns "RLS off = catastrophe" into "RLS off = still permission-denied." |
| 3 | **P1** | Correctness | `site/scout/index.html:60-61`, `site/hub/desk.html:65-66` | Silent error swallow. Only the `event_prospects` query checks `.error`; the `decisions` + `thread` queries don't. If either fails, `|| []` makes **every card show as undecided** (Trint re-triages settled events) / **every Q&A thread vanishes** — with no error shown. | Check `dRes.error`/`tRes.error` like `pRes.error`; surface a visible warning instead of proceeding on empty data. |
| 4 | **P1** | Correctness | `scout.js:56` + `site/scout/index.html:132,197`, `site/hub/desk.html:263` | Thread author is hardcoded `'trint'`/`'lance'` per page; the `authorTag(session)` helper that was written for exactly this is **never called** (and `who` at scout:132 is dead code). Both pages are reachable by both users from the hub, so if Lance asks from `/scout`, it's stored as Trint and the desk's "needs a reply" logic misclassifies it. | Call `Scout.authorTag(session)` at both insert sites; delete the dead `who` line. |
| 5 | **P1** | Data integrity | `site/hub/desk.html:158` (Add lead), `:259` (Answer) | No re-entrancy guard. `ask()` in scout correctly disables its button before `await`; these two don't. A double-click inserts **duplicate** lead rows / duplicate answer bubbles (no unique constraint stops it). | Disable the save button + set a pending label before `await`, re-enable on error — mirror `ask()`. |
| 6 | **P1** | Data integrity | `site/hub/desk.html:176` `v()` + `:222` editModal | Editing one field rewrites **all** fields via a full `.update(patch)`, and `v()` returns `""` (never `null`) — so every previously-`NULL` blank silently becomes `''`. Creates two "unset" representations; future `where … is null` reports (e.g. "how many have no fee yet") undercount. | `v()` → `el.value.trim() || null`; converge on NULL (the seed already emits NULL for blanks). |
| 7 | **P1** | Robustness / supply-chain | all three pages (unpkg `@2`, no SRI) + `scout.js:12` | If supabase-js fails to load (CDN outage, school/corp filter, ad-blocker), `Scout.client()` throws inside uncaught async IIFEs → **blank login page / infinite "Loading…"**, no message. And an unpinned, unhashed CDN script has full read/write to private data once a session exists. | Wrap the top-level IIFEs in try/catch → render a "failed to load, reload" message; pin an exact version + add an `integrity` SRI hash (or self-host the ~40 KB UMD file). |
| 8 | **P2** | Race | `site/scout/index.html:178` `decide()` | Decision buttons aren't disabled during the upsert; in "review all" (undecided-off) mode a fast double-tap reads the shared `idx` after `await` and **skips a card**. Harmless in the default undecided-only mode (idempotent `buildView`). | Disable the three dbtns during the call, or capture `idx` locally at click time. |
| 9 | **P2** | Process | `scout_seed_gen_sql.py` (no DB read) | Future seed batches pick ids by hand in the CSV. If the desk has already auto-assigned 527+ to inbound leads, the next batch reusing those ids is **silently skipped** by `on conflict do nothing` — the printed summary won't show the drop. (Current 500–526 batch is safe.) | Compute the next start id from `select max(id)` live, and/or `... do nothing returning id` + diff against kept ids and print skips. |
| 10 | **P2** | Correctness | `site/scout/index.html:180`, `site/hub/desk.html:193,199,233` | `decided_at`/`booked_at`/`updated_at` are stamped from the **browser clock**, defeating the columns' `default now()`. A device with a wrong clock/timezone writes wrong audit timestamps with no server correction. | Drop these from the client payloads; let Postgres defaults stamp them (keep client-supplied `decided_by`). |
| 11 | **P2** | Latent XSS | `site/hub/desk.html:85` `chip()` | The one `innerHTML` sink that doesn't run through `esc()`. Not exploitable today (all args are CHECK-constrained enums/literals), but becomes stored-XSS the day someone passes a free-text column (e.g. `event_type`). | Add `esc(text)` inside `chip()`. |
| 12 | **P3** | Product | `site/scout/index.html:73-79` buildView sort | Recurring weekly events (`month = null`) sort to the **bottom** (99) — so the closest, best local gigs (Callaway, Rocheport, Head's Blacktop) land behind dated far-away events, contradicting "nearest/soonest first." | Decide the intended order for undated recurring events (likely: interleave by distance, or a dedicated "recurring" group at top). |
| 13 | **P3** | Maintainability | `supabase_scout_schema.sql:52` | `updated_at` freshness depends on every write path remembering to set it — the next path added will silently skip it. | Add a `before update` trigger (or `moddatetime` extension) so it's guaranteed, then remove the client-set values (ties to #10). |
| 14 | **P3** | Data quality | `data/prospects.csv:24` (id 522) | American Royal: `city = "Kansas City KS"` but `state = "MO"` — contradictory. Harmless now (neither field is displayed), a landmine for any future state filter. **Note:** because of `on conflict do nothing`, fixing the CSV alone will **not** fix the DB — needs a manual `update … where id=522`. | Correct the CSV *and* run the one-row `update`; consider light validation in the seed script. |

---

## What's genuinely solid (so this is balanced)

- **XSS**: `esc()` is applied at essentially every `innerHTML` sink — thread bodies, names, meta,
  fact values, modal field values, error strings. Only the `chip()` gap (#11), and it's not
  currently reachable with user text.
- **RLS mechanism** is correctly applied and matches house convention (`contacts`, `payouts` use the
  same "RLS on, no policy = zero access"); the only gap is the missing explicit REVOKE (#2).
- **SQL escaping** in the generator is correct — `'`→`''` under Postgres defaults, verified against
  real apostrophe rows (`Head''s`, `Leprechaun''s`, `Lee''s Summit`).
- **Identity strategy** is exactly right: `by default as identity` on the seeded table vs `always` on
  the children; the `setval` bump correctly prevents the current seed from colliding with desk leads.
- **FK cascades**, the `unique(prospect_id)` backing the decision upsert, the non-null `booked`
  default backing `.eq('booked', false)`, and UTF-8/BOM handling are all correct.
- **The gate works**: `requireSession()` runs before any data fetch on both gated pages; smoke-tested
  logged-out `/scout` + `/hub/desk` bounce to login with 0 console errors.
- Column/value count in the generated INSERT matches (21/21); no positional drift.

---

## Game plan

**Phase A — before Lance deploys (P0 + P1). ✅ DONE 2026-07-16.** All seven landed + re-verified:
1. ✅ `safeNext()` → `new URL` origin check (#1). *Verified: `/\evil.com`, `//evil.com`, `https://evil.com` all blocked; legit paths pass.*
2. ✅ `revoke all … from anon` added to `supabase_scout_schema.sql` (#2).
3. ✅ Error-check the decisions/thread queries on both pages (#3).
4. ✅ `authorTag(session)` used at both insert sites; dead `who` removed (#4).
5. ✅ Re-entrancy guards on Add-lead + Answer (+ Edit, for good measure) (#5).
6. ✅ `v()` returns `null` for blanks (#6).
7. ✅ **supabase-js self-hosted** at `site/assets/vendor/supabase.js` (v2.110.6) — kills the
   CDN-outage failure mode at the root, stronger than pin+SRI; plus try/catch load-failure guards on
   all three page IIFEs (#7).

→ Re-ran the frontend smoke test (login renders, self-hosted supabase-js loads, gate redirects on
both pages, 0 console errors/warnings). Committed. **The tool is now hardened for first deploy.**

**Phase B — first week of use (P2).** Fix once it's live and you can see it behave:
8. Disable decision buttons during upsert (#8).
9. Seed-batch id safety: compute start id from live max / detect skips (#9).
10. Move timestamps to server defaults (#10) — pairs with the `updated_at` trigger in Phase C.
11. `esc()` inside `chip()` (#11).

**Phase C — polish (P3).**
12. Decide + implement the recurring-event sort order (#12) — this is a product call, not a bug fix.
13. `updated_at` trigger (#13).
14. Fix the American Royal row in CSV **and** DB (#14).

**Not doing (out of scope / accepted):** role tiers, optimistic locking for concurrent edits,
un-book/override from the desk, an in-app research button — all intentionally deferred per the spec.
