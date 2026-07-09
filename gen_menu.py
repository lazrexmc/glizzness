#!/usr/bin/env python
r"""gen_menu.py — regenerate the website menu from the Square catalog.

Square is the single source of truth for the menu. This script reads the local
export produced by `pull_catalog.py` and rewrites the menu block inside
`site/menu.html` (between the MENU:START / MENU:END markers).

No Square token needed here — it only reads `catalog_export.json`. Refresh that
first if you want the latest:

    python pull_catalog.py            # needs SQUARE_TOKEN; writes catalog_export.json
    python gen_menu.py                # DRY RUN - prints the HTML + any data problems
    python gen_menu.py --write        # rewrites site/menu.html

Then commit and let Cloudflare Pages redeploy.

Design notes
------------
* Names, prices and descriptions come straight from Square. If a name reads badly
  on the website, fix it IN SQUARE — that fixes the POS and DoorDash too.
* Items in EXCLUDE_CATEGORIES / EXCLUDE_ITEMS never reach the website.
* Anything in Square that this script can't place (unmapped category, no price,
  no description) is reported loudly rather than quietly published.
"""
import argparse, html, json, os, re, sys

EXPORT = "catalog_export.json"
TARGET = os.path.join("site", "menu.html")
START = "<!-- MENU:START"
END = "<!-- MENU:END -->"

# Square category -> (website heading, blurb). Order here is the order on the page.
SECTIONS = [
    ("Glizzy",       "Glizzy",       "Our original take on the classic 1/4&nbsp;lb all-beef dog."),
    ("Not-a-Glizzy", "Not-a-Glizzy", "Awesome in their own right — just not quite a Glizzy."),
    ("Vegetarian",   "Vegetarian",   "Our meat-free picks."),
    ("Sides",        "Sides",        "Sides rotate and can sell out — just ask what we've got."),
    ("Drinks",       "Drinks",       "Gotta wash it down."),
]

# Never show on the website.
EXCLUDE_CATEGORIES = {"Cart Only"}          # in-person only (incl. merch)
EXCLUDE_ITEMS = {"Sides"}                   # a generic catch-all item, not a real dish

# Show a per-variation breakdown only when it's short and actually informative.
MAX_OPTS = 4
GENERIC_VARIATION_NAMES = {"", "regular", "plain"}

# A price below this is almost certainly a data-entry slip in Square.
SUSPICIOUS_UNDER_CENTS = 100


def money(cents):
    if cents is None:
        return "—"
    return f"${cents/100:.0f}" if cents % 100 == 0 else f"${cents/100:.2f}"


def price_label(variations):
    prices = [a for _, a in variations if a is not None]
    if not prices:
        return "—"
    lo, hi = min(prices), max(prices)
    return money(lo) if lo == hi else f"{money(lo)}–{money(hi)}"


def variation_note(variations):
    """'Options: Brat $8 · Pull Pork $9.' — only when short and non-generic."""
    priced = [(n or "", a) for n, a in variations if a is not None]
    if not (2 <= len(priced) <= MAX_OPTS):
        return ""
    if all(n.strip().lower() in GENERIC_VARIATION_NAMES for n, _ in priced):
        return ""
    return "Options: " + " · ".join(f"{html.escape(n)} {money(a)}" for n, a in priced) + "."


def load_items():
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found — run `python pull_catalog.py` first.")
    objs = json.load(open(EXPORT, encoding="utf-8"))
    cats = {o["id"]: o["category_data"]["name"] for o in objs if o["type"] == "CATEGORY"}

    items = []
    for o in objs:
        if o["type"] != "ITEM" or o.get("is_deleted"):
            continue
        d = o["item_data"]
        rc = (d.get("reporting_category") or {}).get("id")
        variations = [
            (v["item_variation_data"].get("name"),
             (v["item_variation_data"].get("price_money") or {}).get("amount"))
            for v in d.get("variations", [])
        ]
        items.append({
            "name": " ".join((d.get("name") or "").split()),
            # Square descriptions can contain hard line breaks; collapse to one line.
            "desc": " ".join((d.get("description") or "").split()),
            "category": cats.get(rc, ""),
            "variations": variations,
            "prices": [a for _, a in variations if a is not None],
        })
    return items


def render(items, warn):
    known = {c for c, _, _ in SECTIONS}
    out = []

    for cat, heading, blurb in SECTIONS:
        rows = [i for i in items if i["category"] == cat and i["name"] not in EXCLUDE_ITEMS]
        if not rows:
            warn.append(f"section '{heading}' has no items in Square — skipped")
            continue
        rows.sort(key=lambda i: (min(i["prices"]) if i["prices"] else 10**9, i["name"].lower()))

        out.append('        <div class="menu-sec">')
        out.append('          <div class="menu-sec__h">')
        out.append(f"            <h2>{heading}</h2>")
        out.append(f"            <p>{blurb}</p>")
        out.append("          </div>")
        out.append('          <div class="menu-list">')
        for i in rows:
            desc = html.escape(i["desc"])
            note = variation_note(i["variations"])
            if note:
                desc = f"{desc} {note}".strip()
            line = (f'            <div class="mi"><span class="mi__name">{html.escape(i["name"])}</span>'
                    f'<span class="mi__price">{price_label(i["variations"])}</span>')
            line += f'<p class="mi__desc">{desc}</p></div>' if desc else "</div>"
            out.append(line)
        out.append("          </div>")
        out.append("        </div>")
        out.append("")

    # --- data problems worth fixing in Square, not papering over here ---
    for i in items:
        if i["category"] in EXCLUDE_CATEGORIES or i["name"] in EXCLUDE_ITEMS:
            continue
        if i["category"] not in known:
            warn.append(f"UNMAPPED category {i['category']!r} for item {i['name']!r} — not shown")
            continue
        if not i["prices"]:
            warn.append(f"NO PRICE  {i['name']!r} — shows as '—'")
        elif min(i["prices"]) < SUSPICIOUS_UNDER_CENTS:
            warn.append(f"SUSPICIOUS PRICE {i['name']!r} = {money(min(i['prices']))} — typo in Square?")
        if not i["desc"]:
            warn.append(f"NO DESCRIPTION {i['name']!r} — will render name + price only")

    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help=f"rewrite the menu block in {TARGET}")
    args = ap.parse_args()

    items = load_items()
    warn = []
    block = render(items, warn)

    shown = sum(1 for i in items
                if i["category"] in {c for c, _, _ in SECTIONS} and i["name"] not in EXCLUDE_ITEMS)
    hidden = len(items) - shown

    print("=== GENERATE WEBSITE MENU FROM SQUARE ===")
    print(f"mode: {'WRITE' if args.write else 'DRY RUN (no changes)'}")
    print(f"items in Square: {len(items)}  ->  on website: {shown}   hidden: {hidden}\n")

    if not args.write:
        print(block)

    if warn:
        print(f"\n--- {len(warn)} THING(S) TO FIX IN SQUARE ---")
        for w in sorted(set(warn)):
            print("  -", w)
    else:
        print("\nNo data problems found.")

    if not args.write:
        print("\nDRY RUN — nothing written. Re-run with --write to update the site.")
        return 0

    src = open(TARGET, encoding="utf-8").read()
    s, e = src.find(START), src.find(END)
    if s == -1 or e == -1:
        sys.exit(f"[error] markers not found in {TARGET} (expected {START} ... {END})")
    head_end = src.find("-->", s) + 3          # keep the START comment intact
    new = src[:head_end] + "\n" + block + src[e:]
    if new == src:
        print(f"\n{TARGET} already up to date.")
        return 0
    open(TARGET, "w", encoding="utf-8", newline="\n").write(new)
    print(f"\nwrote {TARGET}. Review, commit, and Cloudflare Pages will redeploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
