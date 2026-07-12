#!/usr/bin/env python
r"""gen_menu.py — render the website menu from menu.json (the source of truth).

  menu.json  ──> gen_menu.py --write  ──> site/our-menu.html   (the website)
             └─> push_menu.py --apply ──> Square ──> DoorDash

Edit `menu.json`, never `site/our-menu.html` — the block between the MENU:START /
MENU:END markers is overwritten.

    python gen_menu.py            # DRY RUN - prints the HTML + any data problems
    python gen_menu.py --write    # rewrites site/our-menu.html

Stdlib only. No Square token involved: a Square token must never reach the
browser, so the menu is baked at build time, not fetched live.

Items with `"website": false` (e.g. Cart Only) never reach the site.
Rather than quietly publishing bad data, this reports it: missing descriptions,
missing prices, and suspiciously low prices.
"""
import argparse, html, json, os, sys

SOURCE = "menu.json"
TARGET = os.path.join("site", "our-menu.html")
START = "<!-- MENU:START"
END = "<!-- MENU:END -->"
HOME = os.path.join("site", "index.html")      # home-page "Cart favorites" teaser
TSTART = "<!-- TEASER:START"
TEND = "<!-- TEASER:END -->"

MAX_OPTS = 4                                   # show per-variation prices only when short
GENERIC_VARIATION_NAMES = {"", "regular", "plain"}
SUSPICIOUS_UNDER_CENTS = 100                   # below $1.00 is almost certainly a typo


def money(cents):
    if cents is None:
        return "—"
    return f"${cents/100:.0f}" if cents % 100 == 0 else f"${cents/100:.2f}"


def prices_of(item):
    return [v["price_cents"] for v in item.get("variations", []) if v.get("price_cents") is not None]


def price_label(item):
    p = prices_of(item)
    if not p:
        return "—"
    lo, hi = min(p), max(p)
    return money(lo) if lo == hi else f"{money(lo)}–{money(hi)}"


def variation_note(item):
    """'Options: Brat $8 · Pull Pork $9.' — only when short and non-generic."""
    priced = [(v.get("name") or "", v["price_cents"])
              for v in item.get("variations", []) if v.get("price_cents") is not None]
    if not (2 <= len(priced) <= MAX_OPTS):
        return ""
    if all(n.strip().lower() in GENERIC_VARIATION_NAMES for n, _ in priced):
        return ""
    return "Options: " + " · ".join(f"{html.escape(n)} <strong>{money(a)}</strong>" for n, a in priced) + "."


def mi_html(i, indent=12):
    """One <div class="mi"> line for an item — name + price + optional description."""
    pad = " " * indent
    desc = html.escape(" ".join((i.get("description") or "").split()))
    note = variation_note(i)
    if note:
        desc = f"{desc} {note}".strip()
    s = (f'{pad}<div class="mi"><span class="mi__name">{html.escape(i["name"])}</span>'
         f'<span class="mi__price">{price_label(i)}</span>')
    return s + (f'<p class="mi__desc">{desc}</p></div>' if desc else "</div>")


def render_teaser(doc):
    """Home-page 'Cart favorites' block: items flagged favorite:true (in menu.json order)."""
    favs = [i for i in doc["items"] if i.get("favorite") and i.get("website")]
    return "\n".join(mi_html(i, 10) for i in favs)


def replace_block(path, start, end, block):
    """Rewrite the text between the start/end markers in `path`. Returns True if it changed."""
    src = open(path, encoding="utf-8").read()
    s, e = src.find(start), src.find(end)
    if s == -1 or e == -1:
        sys.exit(f"[error] markers not found in {path} (expected {start} ... {end})")
    head_end = src.find("-->", s) + 3            # keep the START comment intact
    new = src[:head_end] + "\n" + block.rstrip("\n") + "\n" + src[e:]
    if new == src:
        return False
    open(path, "w", encoding="utf-8", newline="\n").write(new)
    return True


def load():
    if not os.path.exists(SOURCE):
        sys.exit(f"[error] {SOURCE} not found.")
    return json.load(open(SOURCE, encoding="utf-8"))


def render(doc, warn):
    out = []
    for sec in doc["sections"]:
        rows = [i for i in doc["items"] if i.get("website") and i.get("section") == sec["key"]]
        if not rows:
            continue
        # order follows menu.json (edit the "items" array to reorder within a section)

        out.append('        <div class="menu-sec">')
        out.append('          <div class="menu-sec__h">')
        out.append(f'            <h2>{sec["heading"]}</h2>')
        if (sec.get("blurb") or "").strip():
            out.append(f'            <p>{sec["blurb"]}</p>')
        out.append("          </div>")
        out.append('          <div class="menu-list">')
        for i in rows:
            out.append(mi_html(i, 12))
        out.append("          </div>")
        out.append("        </div>")
        out.append("")

    known = {s["key"] for s in doc["sections"]}
    for i in doc["items"]:
        if not i.get("website"):
            continue
        if i.get("section") not in known:
            warn.append(f"UNMAPPED section {i.get('section')!r} for {i['name']!r} — not shown")
            continue
        p = prices_of(i)
        if not p:
            warn.append(f"NO PRICE  {i['name']!r} — shows as '—'")
        elif min(p) < SUSPICIOUS_UNDER_CENTS:
            warn.append(f"SUSPICIOUS PRICE {i['name']!r} = {money(min(p))} — typo?")
        if not (i.get("description") or "").strip():
            warn.append(f"NO DESCRIPTION {i['name']!r} — renders name + price only")

    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help=f"rewrite the menu block in {TARGET}")
    args = ap.parse_args()

    doc = load()
    warn = []
    block = render(doc, warn)

    shown = sum(1 for i in doc["items"] if i.get("website"))
    print("=== RENDER WEBSITE MENU FROM menu.json ===")
    print(f"mode: {'WRITE' if args.write else 'DRY RUN (no changes)'}")
    print(f"items: {len(doc['items'])}  ->  on website: {shown}   hidden: {len(doc['items']) - shown}\n")

    if not args.write:
        print(block)

    if warn:
        print(f"\n--- {len(warn)} THING(S) STILL TO FIX in {SOURCE} ---")
        for w in sorted(set(warn)):
            print("  -", w)
    else:
        print("\nNo data problems found.")

    if not args.write:
        print("\nDRY RUN — nothing written. Re-run with --write to update the site.")
        return 0

    wrote_menu = replace_block(TARGET, START, END, block)
    print(f"\n{'wrote ' + TARGET if wrote_menu else TARGET + ' already up to date'}.")

    # The same menu.json feeds the home-page 'Cart favorites' teaser, so it can never drift.
    n_fav = sum(1 for i in doc["items"] if i.get("favorite") and i.get("website"))
    wrote_home = replace_block(HOME, TSTART, TEND, render_teaser(doc))
    print(f"{'wrote ' + HOME + f' teaser ({n_fav} favorites)' if wrote_home else HOME + ' teaser already up to date'}.")
    print("Review, commit, and Cloudflare Pages will redeploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
