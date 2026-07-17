# Inventory Depletion — design spec (v1, "two-level ledger")

**Date:** 2026-07-16
**Status:** GAMEPLAN APPROVED-IN-SHAPE — owner directive: **design only, NO code yet.** This spec is
the blueprint to return to. Nothing below is built.
**Related:** `OPS_PLATFORM.md` (this is the "inventory" spoke), `DEMAND_BASELINE.md` (predicts
per-stop need — the demand side of every alert here), `TODO.md` (original inventory backlog item,
superseded by this), the Scout/Signals/Posts stack (patterns + gated-page language to reuse).

---

## 1. Purpose

Know **what's in the coolers right now**, **how much to stock before leaving for an event**
(owner: "based on previous events, their sales, how similar they are"), **what to prep** before
upcoming stops, and **when to buy raw goods** — with near-zero logging burden, because drifted
stock numbers are worse than none.

## 2. The decisions (all made 2026-07-16, with the owner)

| Decision | Choice | Why |
|---|---|---|
| Scope | **Two-level: raw goods (commissary) + prepped (coolers)** | Owner picked the full vision over prepped-only. Purchases stock raw; prep converts raw → cooler; sales deplete cooler |
| Sales OUT | **Square Orders API on a GitHub Actions cron (every 1–2h)** | Near-live stock. Eyes-open tradeoff: `SQUARE_TOKEN` becomes an Actions secret (can write catalog + read payments — biggest-blast-radius secret yet; comparable to `SUPABASE_SERVICE_KEY` already there) |
| Toppings | **EXCLUDED — made fresh daily** | No carryover ⇒ nothing to deplete. They become a printed **"daily fresh" checklist** on the load-out sheet; their produce is a par shopping list, not ledger rows |
| Bulk units | **Half/full hotel PANS** (chili, nacho cheese, pulled pork, pulled chicken, sloppy joe) | Catering-native; glanceable in a cooler. Each-items (dogs, brats, links, patties) count as **each** |
| Prep logging | **Big-button gated phone page ("Prep")**, logged by whoever cooked, ~10 seconds | The habit is the whole game; logging must be faster than skipping. Same Trint-design language as the Scout board (huge buttons, icon-led) |
| Shelf life | Prepped items good **48–96h** (temp maintained) | Prep is a **rolling buffer** covering multiple stops, not a daily from-scratch task — the math plans across stops |

## 3. The model

```
RAW (commissary)               PREPPED (coolers)               SOLD
cases of dogs, buns,   --prep batch logged-->   cooked dogs (each),   --Square sales,-->  gone
chips, drink cases,     (consumes raw,           pans of chili/pork      auto, every 1-2h
pork butts, fixings      creates prepped)        48-96h shelf life
   ▲                                                  ▲
   └── "bought 4 cases" quick-add                     └── COUNT button resets truth anytime
```

**Prep is the hinge:** one tap ("cooked 60 dogs") simultaneously **adds 60 to the cooler AND
subtracts 1.25 cases from raw**. One entry moves both ledgers — never double entry.

## 4. The four flows

1. **IN (raw):** quick-add on the Prep page — "bought 4 cases dogs, 6 bags buns." Manual v1.
   Sam's receipt parsing = later automation, explicitly NOT a v1 dependency.
2. **CONVERT (prep):** the big-button page. Tap item → tap quantity (+10/+30/+60 dogs;
   +½/+1 pan) → done. Logged at the commissary by whoever cooked.
3. **OUT (sales):** Actions cron polls Square Orders → sold items deplete prepped stock through
   the recipe map. **Reuses `demand_baseline.py`'s item ALIAS MAP** ("GlizzyClassic"/"Glizzy
   Classic"/"Glizzy" → one item) — that solved problem stays solved. Re-review with `--aliases`
   after any menu rename.
4. **DAILY FRESH:** toppings print as a checklist on the load-out sheet; never ledger rows.

## 5. The recipe maps (the crux — owner-editable DATA, not code)

- **Menu item → prepped units** (~25 rows): Glizzy = 1 dog + 1 bun · Chili Dog = 1 dog + 1 bun +
  ⅛ pan chili · Nachos = ⅛ pan cheese + chips · … Per-serving pan fractions start as OUR DRAFT
  and the owner corrects them; counts self-correct residual error over time.
- **Prep batch → raw units:** 1 batch "60 dogs" = 1.25 cases · 1 pan chili = its fixings.
  If per-ingredient fixings are too fussy, collapse to "1 chili kit" — granularity is the
  owner's call per item.

## 6. Read surfaces

- **Coolers view** (hub tile, may share the Prep page): on-hand per item + a
  **"covers your next N stops?"** line — the demand baseline already predicts each upcoming
  stop's need, so this is the owner's "how much to stock before we leave," live.
- **Load-out sheet per stop:** predicted need (venue history or analog, marked "(est.)") vs
  on-hand → "prep 20 more dogs before Friday" + the daily-fresh checklist + drinks/chips pars.
- **Raw reorder:** simple PAR levels v1 ("dogs below 2 cases → buy") — a Sam's run needs a floor,
  not demand math.

## 7. Drift is a design input, not a failure

Waste, spills, and forgotten logs WILL desync the ledger. Therefore:
- **COUNT button** — "actually 30 dogs left" hard-resets truth in one tap. Counts are king; the
  math only carries between counts. No guilt, no reconstruction.
- **WASTE button** — dumped pans logged in one tap (also feeds future waste analytics, not v1).

## 8. New moving parts (the full bill)

~4 ledger/stock tables + 2 recipe-map tables (authenticated-only + allowlist RLS, per the
2026-07-16 hardening pattern) · **one new cron** (Square OUT; `SQUARE_TOKEN` Actions secret,
skip-cleanly guard like the other workflows) · **one new gated page** (Prep/Coolers, Trint
language) · load-out additions to existing surfaces. No new vendors. No LLM.

## 9. Build order (when the owner says GO — not before)

1. **Item master + recipe maps** — data session with the owner, no code.
2. **Prepped ledger + Prep page** (+ Count/Waste) — the habit-forming core, works standalone.
3. **Square OUT cron** — live depletion.
4. **Raw level** — purchases quick-add + prep-consumes-raw + pars.
5. **Load-out sheet** — baseline prediction vs on-hand, + daily-fresh checklist.

Each phase is independently useful; stop after any of them and the system still earns its keep.

## 10. Honest risks

- **The prep-log habit is the whole game.** Mitigations: 10-second logging, counts-as-reset,
  and phase 2 ships alone so the habit is proven before the rest is built on it.
- **Recipe fractions start as guesses** — self-correcting via counts, but early alerts are soft.
- **Square item renames** drift the alias map — `--aliases` review after menu changes.
- **`SQUARE_TOKEN` in Actions** — accepted eyes-open; consider a scoped OAuth app later.

## 11. NOT in v1 (deliberate)

Food costing/COGS · waste analytics · supplier auto-ordering · propane · toppings/produce ledger
(daily-fresh checklist + par list instead) · Sam's receipt OCR/parsing · Square-native inventory
(evaluated: it tracks sellable-item counts, not BOM/ingredient depletion — custom is required for
the hinge, so custom it is).

## 12. Open details to settle at build time

Exact per-serving pan fractions (draft → owner corrects) · par levels per raw item · cron cadence
(1h vs 2h) · whether Prep + Coolers are one page or two · which raw fixings collapse into "kits."
