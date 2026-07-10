# Menu Pipeline — `menu.json` is the source of truth

> **The repo is the source. Square is downstream.**
> Decide the menu here, in code review, where it can be diffed and rolled back.
> Nothing reaches customers until someone runs a command.

```
menu.json  ──> gen_menu.py --write  ──> site/our-menu.html      (the website)
           └─> push_menu.py --apply ──> Square ──> DoorDash  *** NOT BUILT YET ***
```

## Files

| File | Role |
|---|---|
| `menu.json` | **Source of truth.** Every item + variation, with its Square ID. Committed. |
| `gen_menu.py` | Renders `menu.json` → the block between `MENU:START` / `MENU:END` in `site/our-menu.html`. Stdlib only, **no Square token.** |
| `push_menu.py` | *(to build)* Pushes `menu.json` → Square (which feeds DoorDash). |
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

1. **Descriptions still needed from Trint:** `Something Fowl` ($7), `Taco` ($4 / Double $7).
   *Never invent ingredients.* `Burger` and `Boujee Burger` also lack descriptions but are Cart Only.
2. **`Turkey Link` — REMOVED (2026-07-10).** The $0.75 was a typo; the owner chose to retire the item
   entirely (not reprice). Marked `"retired": true` in `menu.json` — **still live in Square** → delete
   in the Dashboard or via `push_menu.py`. Same for `Special Brat` + `Glizzy Classic`.
3. **Build `push_menu.py`.** Read `menu.json`, take the current `version` for each object from a fresh
   `catalog_export.json`, and POST object-by-object to `/v2/catalog/object`
   (Square's `batch-upsert` is atomic — one bad object aborts everything). DRY-RUN by default;
   `--apply` requires `SQUARE_TOKEN`; back up the export first. Mirror `catalog_desc.py`.
   Honour `"retired": true` (delete/archive). **Lance runs every `--apply` himself** — the Square
   token lives in his shell, not the agent's.

## Decisions already baked in

- Use **"Dog"** spellings (`Chili Dog`, `Hog' N' Dog`). Reversed 2026-07-10 by owner (was "Dawg"); the item is **Hog' N' Dog** — never "Hoggin'", "Hawg'n'Dawg", or any other form.
- `Walking Chips` → **`Walking Nachos`**.
- **`Special Brat` retired.**
- Duplicate consolidated to one **`Glizzy`** (retired `Glizzy Classic`).
- **Two distinct nachos:** `Nachos` = tortilla chips piled in a serving boat; `Walking Nachos` = a bag
  of chips we pour it all into. Separate items, separate descriptions.
- **2026-07-10 Square sync:** Square was hand-edited to the current item set, then `menu.json` reconciled
  to the fresh `catalog_export.json` — added `Tamal(es)`; removed 6 items no longer in Square (Smoked Pork
  Sausage Link, Grill Cheese, Pork Chop Special, Slim Jim, Fries, Iced Coffee).
- Pricing story: **"A Glizzy is $5 — premium dogs start at just $2 more."**
  (Glizzy $5; Chili Dog / Hog' N' Dog $7 base; Brat $8 and Pulled Pork $9 stack above.)
- Customer-visible typos fixed: `Glossy Classic`→`Glizzy Classic`, `Chilly`→`Chili`,
  `Pull Pork`→`Pulled Pork` (4 items).
