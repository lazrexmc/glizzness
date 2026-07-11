# Menu Pipeline — `menu.json` is the source of truth

> **The repo is the source. Square is downstream.**
> Decide the menu here, in code review, where it can be diffed and rolled back.
> Nothing reaches customers until someone runs a command.

```
menu.json  ──> gen_menu.py --write  ──> site/our-menu.html      (the website)
           └─> push_menu.py --apply ──> Square ──> DoorDash  (built; dry-run default, --apply needs SQUARE_TOKEN)
```

## Files

| File | Role |
|---|---|
| `menu.json` | **Source of truth.** Every item + variation, with its Square ID. Committed. |
| `gen_menu.py` | Renders `menu.json` → the block between `MENU:START` / `MENU:END` in `site/our-menu.html`. Stdlib only, **no Square token.** |
| `push_menu.py` | **Built.** Syncs Square FROM `menu.json`: pushes name/description/category/variations, **creates** missing items (writes the new Square IDs back into `menu.json`), **deletes** `retired` ones. Matches by `square_id` (updates in place, never duplicates). Leaves tax + modifiers on existing items alone. DRY-RUN default; `--apply` needs `SQUARE_TOKEN`. |
| `pull_catalog.py` | Read-only Square export → `catalog_export.json`. Now only used to **seed/reconcile** `menu.json`, not to render. |

## Everyday use

```bash
# 1. edit menu.json (names, prices, descriptions, sections, visibility)
python gen_menu.py            # DRY RUN: prints the HTML + any data problems
python gen_menu.py --write    # rewrite site/our-menu.html
git commit -am "menu: ..."    # Cloudflare Pages redeploys
```

Never hand-edit `site/our-menu.html` between the markers — it gets overwritten.

## Fields

- `square_id` — on the item **and each variation**. This is what lets a push **update Square in place**
  instead of creating duplicates. Don't invent these; they come from `pull_catalog.py`.
- `"website": false` — hide from the site but keep selling it (Cart Only items, the generic "Sides" item).
- `"retired": true` — remove it from Square on the next push.

## Why build-time and not a live Square fetch

The Square Catalog API requires a **secret access token**, and Square exposes no anonymous catalog
endpoint. Putting the token in client-side JS would leak your production credentials to anyone who
views source. So the menu is baked at build time. It's also faster, SEO-friendly, and can't break
because Square is down.

## Guardrails

`gen_menu.py` will not quietly publish bad data. It reports:
- items with **no description** (they'd render as a bare name + price),
- items with **no price**,
- prices **under $1.00** (almost always a typo).

Fix them in `menu.json`, then regenerate.

## Open items

`menu.json` is clean — 25 items, all website items described, `gen_menu.py` dry-run reports **no data
problems**. (Something Fowl is now described; Taco/Turkey Link were removed.) The website menu is
**already shipped**; only the Square push remains:

1. **Website menu — done.** `site/our-menu.html` is already regenerated from `menu.json` and committed
   (verified byte-identical to a fresh `gen_menu.py` render — `--write` is a no-op). Re-run only after
   you edit `menu.json`.
2. **Push the menu to Square (→ DoorDash):** `python push_menu.py` (dry run). Current diff: **22 updates,
   0 creates, 0 deletes** — really just 5 description backfills (Sloppy Joe, Jackfruit, Chips, Water,
   Keychain). The `retired` items (Chicken Teriyaki, generic **Sides**, **Walking Nachos**) are already
   absent from Square, so the push deletes nothing. Then **Lance** runs `python push_menu.py --apply`
   with `SQUARE_TOKEN`.
   > **Walking Nachos** is intentionally **retired** (owner decision 2026-07-10) — off the site and
   > already gone from Square, so the push deletes nothing. `Nachos` (the boat) is the live nachos item.

## Decisions already baked in

- Use **"Dog"** spellings (`Chili Dog`, `Hog' N' Dog`). Reversed 2026-07-10 by owner (was "Dawg"); the item is **Hog' N' Dog** — never "Hoggin'", "Hawg'n'Dawg", or any other form.
- `Walking Chips` → **`Walking Nachos`**.
- **`Special Brat` retired.**
- Duplicate consolidated to one website **`Glizzy`**; the plain register button is **kept** as
  `Classic Glizzy` (`website:false`, **not** retired — a one-tap POS button, hidden from the site).
- **Nachos vs. Walking Nachos:** `Nachos` = tortilla chips piled in a serving boat — the live item
  (`website:true`). `Walking Nachos` (a bag we pour it into) was **retired 2026-07-10** (owner decision):
  `retired:true`, off the site, already removed from Square.
- **2026-07-10 Square sync:** Square was hand-edited to the current item set, then `menu.json` reconciled
  to the fresh `catalog_export.json` — added `Tamal(es)`; removed 6 items no longer in Square (Smoked Pork
  Sausage Link, Grill Cheese, Pork Chop Special, Slim Jim, Fries, Iced Coffee).
- Pricing story: **"A Glizzy is $5 — premium dogs start at just $2 more."**
  (Glizzy $5; Chili Dog / Hog' N' Dog $7 base; Brat $8 and Pulled Pork $9 stack above.)
- Customer-visible typos fixed: `Glossy Classic`→`Glizzy Classic`, `Chilly`→`Chili`,
  `Pull Pork`→`Pulled Pork` (4 items).
