# ARCHIVE_REVIEW.md — staging list for possible archival

> **Nothing here is archived yet.** This is a review list. When you decide an item can go,
> follow **"How to archive"** at the bottom. Add new candidates here as you find them.
>
> Last reviewed: **2026-07-10** full-repo audit (branch `audit-2026-07-10`).
> Rule of thumb: **archive, don't delete** (reversible). **PII/financial never goes to `archive/`** —
> it's committed — send it to `..\PrivateData\` instead.

---

## 1. Legacy website (superseded by `site/`)
The unified site in `site/` replaces the old fragmented pages. These are candidates:

| Candidate | Why | Superseded by |
|---|---|---|
| root `menu.html` | old menu snapshot ("Cheesy Glizzy", per-item add-on pricing) | `site/our-menu.html` (generated from `menu.json`) |
| root `catering.html` | subset of the new page; also carries banned "culinary-school chef" copy | `site/catering.html` |
| `catering/index.html`, `catering/config.js` | duplicate booking flow (both write to Supabase `catering_leads`) | `site/catering.html` (superset: adds workplace lane, clean copy) |
| root `netlify.toml`, `catering/netlify.toml` | Netlify was dropped for Cloudflare Pages | — (Cloudflare needs no toml) |
| `catering-hot-dogs-50.html` *(untracked)* | earlier predecessor of the catering menu; broken local banner | `site/catering.html` |

**KEEP (do not archive):**
- `catering/MARKETING.md` — the B2B outreach kit (still referenced by `GO_LIVE.md`). ⚠️ Rewrite its
  "lean on Trint's culinary degree" / "culinary-school chef" hooks before reusing — violates the
  no-credentialing rule.
- `catering/README.md` — documents the Netlify base-directory gotcha + lead auto-reply idea (reference).
- **`vending-map/`** — **NOT obsolete.** It's the 415-event festival prospecting map (the `vending_*`
  tables), a *different product* from the "Where We Vend" cart calendar (`site/events.html`). It's just
  currently homeless (Netlify dropped) — move it to Cloudflare Pages or link it from `events.html`.

## 2. Legacy accounting — the SQLite pipeline (superseded)
**Confirmed 2026-07-10:** posting to Wave and Wave-CSV upload now happen only through the Streamlit app
(`glizzness.streamlit.app` → `dashboard.py` → Supabase). The old local **SQLite** pipeline is dormant.

- ⚠️ **Operational first:** if `run_daily.ps1` is still a Windows Task Scheduler job, **disable it** so
  nothing double-posts to Wave (the two ledgers are only kept apart by Wave's `externalId` dedup).
- Candidates once that's confirmed off:
  `sync_square.py`, `post_to_wave.py`, `post_loan_payments.py`, `valuation.py`, `reconcile.py`
  (obsolete v1 prototype), `debug_date.py`, `reset_entry.py`, `reset_errors.py`, `check_variances.py`,
  `introspect_wave.py` (dev tool; duplicated by `post_to_wave.py --introspect`),
  `migrate_to_supabase.py` (one-time migration, already done).
  Data (already gitignored): `glizzness.db`, `glizzness_reconciliation.db`.
- **KEEP (the live path):** `sync.py`, `db.py`, `money.py`, `auth.py`, `dashboard.py`,
  `tests/test_accounting.py`. Also keep `post_sams_correction.py` (annual Sam's-tax correction) — but
  fix its hardcoded Wave account IDs first.

## 3. Menu — vestigial `retired` tombstones
`menu.json` still lists three `retired:true` items that are **already gone from Square** (so the push
deletes nothing): **Chicken Teriyaki**, the generic **Sides** item, and **Walking Nachos**
(retired 2026-07-10). Harmless, but you can prune them from `menu.json` once you're sure they'll never
be re-created.

## 4. Misc / low priority
- `chatlog.txt` *(untracked, gitignored)* — legacy catering-menu chat log; superseded by `CHATLOG.md`.
- `build_resume.py` — Trint's resume generator; moved to `..\PrivateData\` with the resumes (2026-07-10).
- Dated/locked specs — **keep for reference, don't archive**, just know the counts are historical:
  `docs/superpowers/specs/2026-06-18-missouri-county-sweep-design.md` (sweep complete; 127→415 events),
  `DATA_MODEL.md` (127-event/403-row snapshot).

---

## How to archive (when ready)
1. Make a dated folder: `archive/YYYY-MM-DD/` (use the day you archive).
2. **Tracked** file → preserve history: `git mv <file> archive/YYYY-MM-DD/<file>`.
3. **Untracked** file → just move it: `mv <file> archive/YYYY-MM-DD/`.
4. **PII/financial → `..\PrivateData\`, never `archive/`** (archive is committed).
5. Log it in `archive/YYYY-MM-DD/ARCHIVE_MANIFEST.md`: what, why, where it came from, how to restore
   (`git mv` back).
6. Update any doc that pointed at the moved file (e.g. `GO_LIVE.md` §5 lists the legacy web pages).
7. Commit: `git commit -m "archive: retire <items> (superseded by <replacement>)"`.

**Never hard-delete.** Archiving is reversible; deletion isn't.
