# Replication Playbook — building this system for someone else

*How to rebuild the Glizzness ops platform for a different small business. The hot dogs are incidental.*

**Who this is for:** the person building it (you, six months from now, for a different client).
**What's valuable here:** not the code — the **decisions and the traps**. The code is easy to retype;
the traps cost real days. Read §7 and §8 before you write anything.

**Companion docs:** `SYSTEM_PLAIN_ENGLISH.md` (hand to the client), `REBUILD.md` (Glizzness-specific
disaster recovery), `OPS_PLATFORM.md` (how the parts interlock).

---

## 1. The pattern in one sentence

> **Find opportunities automatically → let a human decide in ten seconds → keep a public face honest and
> current → let the boring parts run themselves.**

Everything below is scaffolding for that sentence.

## 2. Fit test — is this right for this client?

**Good fit** (most of these true):
- They **move around** or chase one-off opportunities (food truck, band, landscaper, market vendor,
  photographer, mobile detailer, contractor).
- Customers regularly ask **"where/when are you?"**
- **1–3 people**, all trusted. No real need for permission tiers.
- The owner is **too busy doing the work** to also operate software.
- They're paying (or refusing to pay) for a **pile of disconnected SaaS**.
- There is **one boring recurring chore** eating hours a week. That's your beachhead.

**Bad fit — walk away or scope differently:**
- Needs **real multi-user roles/permissions** (this pattern assumes everyone logged in is trusted).
- **Compliance-heavy** (HIPAA, PCI-in-scope, regulated records).
- **High volume** that blows past free tiers (this is a small-business pattern).
- Needs **offline-first** or a real mobile app.
- The client wants to **buy a product**, not commission a build. Different conversation — be honest early.

## 3. The stack (and why) — target: **$0/month**

| Layer | Choice | Why |
|---|---|---|
| Web host | **Cloudflare Pages** | Free, deploys on `git push`, no build step, custom domain + SSL free |
| Database + API | **Supabase (Postgres)** | Free tier; **PostgREST gives you a REST API for free**; RLS *is* the security model |
| Auth | **Supabase Auth** | Free; hand-create the 1–3 users, no signup flow to build |
| Scheduled jobs | **GitHub Actions cron** | Free (2,000 min/mo private); **the server you don't run** |
| Email alerts | **Make.com** (or similar) free tier | DB webhook → formatted email; no mail server |
| Internal dashboard | **Streamlit Community Cloud** | Free Python dashboard when you need one |
| Frontend | **Plain HTML/CSS/JS** | No framework, no build, no `node_modules`, nothing to rot |

**Real cost: a domain (~$20/yr).** That's it. Don't undersell this — it's the single most persuasive
fact in the pitch, and it's true.

**Deliberate omissions:** no framework, no bundler, no Docker, no server, no LLM in the running loop.
Every one of those is a thing that breaks at 2am for a client who can't fix it.

## 4. The reusable shapes

These are the actual IP. Steal all of them.

### 4.1 Public site + private tools in ONE deploy
Gated pages live in the same repo/host as the public site. They're simply **not in the nav** and are
protected by the database. No second project, no second deploy, no reverse proxy.

### 4.2 The three RLS patterns — get these right or you leak
Supabase **default-grants table access to `anon`** on new public-schema tables. RLS is what stops it.
Pick one per table, deliberately:

| Need | Recipe |
|---|---|
| **Public read** (schedule, map) | `grant select to anon` + `for select using (true)` |
| **Write-only intake** (lead form) | `grant insert to anon` + insert policy, **and NO select policy** → the public can submit but never read back |
| **Private** (internal tools, money, PII) | policy `for all to authenticated using (true)` **+ `revoke all on <tables> from anon;`** |

> **That REVOKE is the whole ballgame.** Without it, the *only* thing between the public key and your
> client's data is the absence of a policy — one `disable row level security` during a late-night fix and
> it's wide open. With it, anon gets `42501 permission denied` even if RLS is off. **Verify it by
> testing** (see §8.7).

### 4.3 The scheduled worker (GitHub Actions)
```yaml
on:
  schedule: [{ cron: "0 */4 * * *" }]
  workflow_dispatch: {}
jobs:
  run:
    steps:
      - name: Check setup          # ← guard FIRST, before checkout/install
        id: cfg
        env: { KEY: "${{ secrets.SOME_KEY }}" }
        run: |
          if [ -z "$KEY" ]; then
            echo "configured=false" >> "$GITHUB_OUTPUT"
            echo "::notice::Not configured yet - skipping (not a failure)."
          else echo "configured=true" >> "$GITHUB_OUTPUT"; fi
      - uses: actions/checkout@v5
        if: steps.cfg.outputs.configured == 'true'
      # ... every later step carries the same `if:`
```
**Why the guard:** you will commit the workflow before the client sets the secrets. Without this it fails
on every cron tick and **emails them a failure every 4 hours** — which is exactly how you teach a client
to ignore alerts. It also auto-activates the moment the secret appears: nothing to remember.

Secrets that a job needs but a browser must never see (service keys, API JSON) go in **repo secrets**,
never the repo.

### 4.4 The crawler = a curated source-poller (NOT "crawl the web")
Nobody crawls the whole web. Set that expectation on the first call — the value is *never forgetting to
check*, not omniscience.

```
crawler/
  run.py          # orchestrate: fetch -> filter -> dedup -> write; --dry-run
  sources.py      # the source list = DATA, not logic. Adding one = a config line.
  normalize.py    # one record shape + the filters + the hash
  store.py        # the ONLY thing that talks to the DB
  adapters/       # one small module per source TYPE, each: source -> [records]
```
- **Adapters are per *type*, not per site.** Find the repeating platform and you get many sources for
  one adapter. Goldmines: WordPress **"The Events Calendar"** (`/wp-json/tribe/events/v1/events` — no
  key, real dates), **BLOX/TownNews** news (`/search/?f=rss&t=article...`), WordPress `/event/feed/`,
  **LiveWhale** university calendars (`/live/json/events`), Squarespace (`?format=json`).
- **Dedup with a hash column**: `dedup_hash = sha1(source + external_id)`, **unique**, insert with
  on-conflict-do-nothing. The same item can never resurface — including after a dismissal.
- **Per-source try/except.** One dead source must never kill the run.
- **Filter conservatively-ish** and let the human dismiss. False positives cost a tap; misses cost money.
- **No LLM in the loop.** Plain HTTP to structured feeds is free, fast, and has no rate limiter to trip.
  (We learned this the hard way: LLM-driven mass search thrashed and got rate-limited.)

### 4.5 The triage gate ← the most transferable idea here
**Never dump machine output into a curated surface.**

```
crawler → [staging feed] → human: Keep / Dismiss → [clean board] → action
```
The operator sees **100%** of what the machine found; the clean board only ever gets human-approved
items. Same shape applies to promoting anything onto a **public** surface: a public-facing directory
needs a validation gate (coordinates, category, verified status), so a machine literally *can't* fill it
correctly — the human promote step isn't bureaucracy, it's what keeps the asset worth money.

### 4.6 Single source of truth → generated outputs
One file (e.g. `menu.json`) → a script renders the website *and* pushes to the POS. Decide it in one
place, in version control, where it can be diffed and rolled back. Never hand-edit the generated output.

### 4.7 The sanitized public mirror (opt-in)
Client keeps using the tool they already know (Google Calendar). A job copies a **public-safe subset** to
the DB; the site reads only that.
**Make privacy opt-IN:** an item is public only if explicitly marked so; everything else becomes an
anonymous *"Booked — Unavailable"* block. Forgetting = stays private. Never build it the other way.

## 5. Build order (and why this order)

1. **Database first.** Everything reads it. Get RLS right now, not later.
2. **The public site.** It's the front door *and* it proves the deploy pipeline end-to-end.
3. **Their single most annoying recurring chore.** ← *This is the beachhead, not the coolest feature.*
   Trust is bought here. Nothing else you build matters if this doesn't land.
4. **The gated internal tool** (auth + the human's daily surface).
5. **Discovery/crawler** — the compounding piece; it gets better as sources accrue.
6. **The analytics "brain" LAST.** It needs history that only exists after 1–5 are running.

> Getting seduced into building #6 first is the classic failure. Without history it's a guess with extra
> steps.

## 6. What changes per client vs. what's identical

**Identical (copy it):** the stack; the 3 RLS patterns; the Actions cron + guard; the deploy;
`adapters/` architecture; the dedup-hash trick; the triage-gate shape; the auth wiring + self-hosted JS;
the "generated from a source of truth" pipeline; the doc set.

**Swap per client:** the source list; the card's fields (what *this* operator needs to decide); the
intake form; branding; the accounting integration; the public surface.

**Rethink from scratch, every time — the part that actually matters:**
> **Who is the human, and what are they bad at?**
> For Glizzness the operator reads better through visual layout than dense text. That single fact drove
> the entire card design: one card at a time, icon-led, one fact per line, three huge buttons. If we'd
> shipped a spreadsheet he simply would not have used it, and the whole system would be worthless.
>
> Ask this on day one. It is not an accessibility footnote; it is the product spec.

## 7. The decisions that matter (with the reasoning)

1. **Run scheduled jobs in the cloud, never the client's PC.** A local scheduler only runs when their
   machine is awake — which means it **dies exactly while they're out doing the work**, which is exactly
   when the public schedule has to be right. This one is non-negotiable and it's counterintuitive to
   clients ("but my PC is always on"). It isn't.
2. **Human gate before any curated/public surface.** See §4.5.
3. **No LLM in a running loop** if structured feeds will do. Cost, rate limits, and nondeterminism for
   nothing.
4. **Self-host small JS deps.** A CDN outage or an ad-blocker shouldn't be able to blank the client's
   tool. One 200KB vendored file removes an entire failure class.
5. **Free tiers are a feature, not a compromise** — but respect the ceiling. Do the arithmetic: hourly
   cron × 2 min ≈ 1,400 min/mo against a 2,000 min free cap. Two-hourly is usually plenty.
6. **Audit before the first login, not after.** Cheaper, and nothing to retrofit.
7. **Document like you'll be hit by a bus** — a runbook per subsystem, one master handoff, and a
   from-nothing recovery doc. On a solo build this *is* the team.

## 8. The traps (each of these cost us real time)

1. **Never schedule a cron before it can succeed.** → §4.3's guard. We spammed the owner's inbox for a
   full night with 4-hourly failures.
2. **Windows scripts must be PURE ASCII.** PowerShell 5.1 reads `.ps1` as **cp1252**. A UTF-8 em-dash
   (`E2 80 94`) becomes `â€"` — and that trailing `0x94` is a **curly quote `”` that PowerShell treats as
   a string terminator.** A string closes early, every later quote flips in/out of string context, and it
   detonates far away with nonsense (`The term 'exit' is not recognized`). **A parser check does NOT
   catch it** — `[Parser]::ParseFile()` passed while the script failed at runtime. Test with
   `grep -nP "[^\x00-\x7F]" file.ps1`. Same family: Python printing `→` dies on a cp1252 console — use
   `sys.stdout.reconfigure(encoding="utf-8")`.
3. **PostgREST bulk insert requires UNIFORM KEYS.** Every object needs the same key set or you get a bare
   `400 Bad Request`. Don't "helpfully" omit empty fields — send `null`.
4. **Surface the HTTP error BODY.** `urllib` throws it away — and that body is exactly where PostgREST
   explains itself. We turned a self-explaining error into an undiagnosable stack trace. Always capture
   and print it.
5. **`--dry-run` does not test the write.** We validated 10 live sources and still shipped a broken
   insert, because dry-run skipped the last inch. Exercise the write path against a real (or scratch) DB.
6. **"Built" ≠ "live."** Repo code is not a working product. **The owner running it is the only proof.**
   Say "built, untested by you" until they've logged in — anything else is a lie you'll get caught in.
7. **Verify security, don't assert it.** Actually hit the private tables with the *public* key and
   confirm `401/42501`. If you get `200 []`, your REVOKE is missing and only RLS is holding the door.
8. **Confirm source identity.** `r/CoMo` is **Como, Italy** — not Columbia, Missouri. We caught it only
   because a live test returned Italian post titles. Test every source against real output before trusting it.
9. **Reddit:** `.json` is 403-blocked but `.rss` works. (It *did* work from a GitHub runner despite the
   datacenter-IP reputation — test rather than assume, in both directions.)
10. **Re-running a seed won't fix corrected data.** `on conflict do nothing` means an edited CSV row is a
    no-op if the id exists. Fix the source *and* run an UPDATE.

## 9. Rough effort

| Phase | Effort |
|---|---|
| Discovery (fit, the human, the beachhead chore) | a conversation or two |
| DB + public site + deploy | 1–2 days |
| The beachhead automation | 1–3 days |
| Gated tool + auth + a card/triage board | 2–4 days |
| Crawler (framework + ~10 verified sources) | 2–3 days — *most of it is verifying feeds actually work* |
| Audit + fixes | 1 day |
| Docs | ongoing, ~15% of total |

Budget more for **verifying sources** than for writing the crawler. The code is a day; confirming which
feeds are real, current, and machine-readable is the work.

## 10. The meta-lessons

- **The beachhead is a boring chore, not a cool feature.** Kill their worst weekly annoyance first.
- **Design for the specific human.** The generic user does not exist and will not log in.
- **Free tiers + no framework = a system that still runs untouched in three years.** Every dependency is
  a future outage you've pre-ordered.
- **Docs are the deliverable.** A solo build with no docs is a hostage situation — for you *and* them.
- **Let the client break it.** Every real bug here surfaced the moment the owner ran it himself. Your
  testing has a blind spot shaped exactly like your assumptions.
