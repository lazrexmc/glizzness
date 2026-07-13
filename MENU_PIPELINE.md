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

## Add-ons (toppings)

The add-on / toppings card on the menu page is **also generated from `menu.json`** — the top-level
`"addons"` block (`heading`, `blurb`, and `items[]` of `{name, price_cents, website, square_id}`).
`gen_menu.py` renders it as a compact list **right after the Sides section** (`render_addons`). Set an
add-on's `"website": false` to hide it from the site.

> **Caveat — add-ons don't push to Square.** `push_menu.py` only manages items, not modifiers. Square's
> **Add-Ons** modifier list is edited separately (`catalog_modifiers.py` / the dashboard). The `menu.json`
> `addons` block currently **mirrors** the live Square list exactly (same 9, same prices, same IDs), but
> changing an add-on price here updates the **website only** — update Square too, or the two drift.
> (Future option: teach `catalog_modifiers.py` to read add-ons from `menu.json` so it's one source.)

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

## Current state (2026-07-13)

Menu is **shipped and fully synced.** `menu.json` = **33 entries → 26 on the website, 7 hidden**
(Classic Glizzy + Keychain are `website:false` POS/cart buttons; five are `retired` tombstones —
Chicken Teriyaki, the generic Sides item, Walking Nachos, Pulled Pork Roll, Nacho Glizzy). `gen_menu.py`
dry-run reports **no data problems**.

- **Website — done.** `site/our-menu.html` *and* the home-page teaser both regenerate from `menu.json`
  (`gen_menu.py --write`). Re-run only after editing `menu.json`; Cloudflare Pages redeploys on commit.
- **Square — synced.** `pull_catalog.py` confirms **28 live items** (the 26 website items + the 2 hidden
  POS buttons), every one `[1 var]`, **descriptions 28/28**. Website ↔ `menu.json` ↔ Square ↔ DoorDash are
  in lockstep. Re-sync after a menu change: `pull_catalog.py` → `push_menu.py` (dry-run) → **Lance** runs
  `push_menu.py --apply` with `SQUARE_TOKEN`.

**Menu shape (2026-07-12/13 overhaul):** uniform single price per item (no more multi-price "Options:"
display); pricing story = **"A Glizzy is $5 — premium dogs start at just $2 more."** Sections: Glizzy,
Not-a-Glizzy (sandwiches), Small Plates (Nachos / Chili Nachos / Pulled Pork Nachos / Tamale / Street
Corn), Vegetarian, Sides, Drinks. Chili items are **chili + cheese, no crispy onions** (owner removed).
Nachos are individual items — the Square Item **Option** set was deleted so variation names are writable.

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
- **2026-07-12/13 menu overhaul:** uniform single-price items (dropped the multi-price "Options:"
  display); new **Small Plates** section; **Pulled Pork Roll** and **Nacho Glizzy** retired; chili items
  lost the crispy onions (chili + cheese only); **add-ons moved into `menu.json`** (`addons` block,
  rendered after Sides — see the Add-ons section above).
