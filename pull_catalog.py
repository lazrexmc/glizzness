"""READ-ONLY Square Catalog export + cleanup triage.

Pulls the entire Square catalog (items, variations, categories, modifier lists,
taxes, discounts) to catalog_export.json and prints a summary that flags likely
junk to clean up. Makes NO changes to Square — only HTTP GETs.

Because DoorDash reads Square's catalog, whatever we later clean in Square
propagates to DoorDash.

Setup (PowerShell), then run:
    $env:SQUARE_TOKEN = "your_square_access_token"   # needs ITEMS_READ scope
    python pull_catalog.py
"""
import os, sys, json, collections
import requests

SQUARE_TOKEN = os.environ.get("SQUARE_TOKEN", "")
SQUARE_BASE  = "https://connect.squareup.com/v2"
HEADERS = {
    "Authorization": f"Bearer {SQUARE_TOKEN}",
    "Square-Version": "2025-01-23",
}
OUT = "catalog_export.json"
TYPES = "ITEM,ITEM_VARIATION,CATEGORY,MODIFIER_LIST,MODIFIER,TAX,DISCOUNT,IMAGE"


def list_catalog():
    """Page through GET /catalog/list for all object types (read-only)."""
    if not SQUARE_TOKEN:
        print("[error] SQUARE_TOKEN env var not set. In PowerShell:\n"
              '    $env:SQUARE_TOKEN = "your_square_access_token"')
        sys.exit(1)
    objects, cursor = [], None
    while True:
        params = {"types": TYPES}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{SQUARE_BASE}/catalog/list", headers=HEADERS, params=params)
        if not r.ok:
            print(f"  [http {r.status_code}] {r.text[:300]}")
            r.raise_for_status()
        data = r.json()
        objects.extend(data.get("objects", []))
        cursor = data.get("cursor")
        print(f"  ...pulled {len(objects)} objects")
        if not cursor:
            break
    return objects


def money(v):
    m = (v or {}).get("price_money") or {}
    a = m.get("amount")
    return f"${a/100:,.2f}" if isinstance(a, int) else "(no price)"


def item_categories(item_data, cat_names):
    ids = []
    if item_data.get("category_id"):
        ids.append(item_data["category_id"])
    for c in item_data.get("categories", []) or []:
        if c.get("id"):
            ids.append(c["id"])
    if item_data.get("reporting_category", {}).get("id"):
        ids.append(item_data["reporting_category"]["id"])
    ids = list(dict.fromkeys(ids))
    return [cat_names.get(i, i) for i in ids]


def main():
    print("Pulling Square catalog (read-only)...")
    objs = list_catalog()
    json.dump(objs, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nSaved full catalog -> {OUT} ({len(objs)} objects). This is your backup.\n")

    by_type = collections.Counter(o["type"] for o in objs)
    items = [o for o in objs if o["type"] == "ITEM"]
    cats  = [o for o in objs if o["type"] == "CATEGORY"]
    mods  = [o for o in objs if o["type"] == "MODIFIER_LIST"]
    cat_names = {c["id"]: c.get("category_data", {}).get("name", "?") for c in cats}

    print("== CATALOG SUMMARY ==")
    for t, n in by_type.most_common():
        print(f"  {t:15} {n}")
    print(f"\n  {len(cats)} categories, {len(mods)} modifier lists")

    # ---- description coverage ----
    # description_html is the CUSTOMER-FACING field (Square Online + DoorDash show it). The legacy
    # `description` field is deprecated and is NOT shown to customers.
    def _nm(o):     return o.get("item_data", {}).get("name") or o["id"]
    def _html(o):   return (o.get("item_data", {}).get("description_html") or "").strip()
    def _legacy(o): return (o.get("item_data", {}).get("description") or "").strip()
    n_html  = sum(1 for o in items if _html(o))
    blanked = sorted(_nm(o) for o in items if _legacy(o) and not _html(o))
    no_desc = sorted(_nm(o) for o in items if not _html(o) and not _legacy(o))
    print("\n== DESCRIPTION COVERAGE ==")
    print(f"  customer-facing (description_html, shown on Square Online & DoorDash): {n_html}/{len(items)}")
    if blanked:
        print(f"  WARNING: {len(blanked)} item(s) have a legacy description but a BLANK description_html")
        print( "           -> these render blank on DoorDash; re-run:  python push_menu.py --apply")
        for x in blanked[:40]:
            print(f"     - {x}")
    if no_desc:
        print(f"  {len(no_desc)} item(s) have no description at all:")
        for x in no_desc[:40]:
            print(f"     - {x}")

    # ---- triage flags ----
    name_counts = collections.Counter(
        (o.get("item_data", {}).get("name") or "").strip().lower() for o in items)
    dup_names = {n: c for n, c in name_counts.items() if n and c > 1}

    uncategorized, blankish, zero_price, no_location = [], [], [], []
    JUNK = ("test", "asdf", "qwe", "temp", "delete", "xxx", "copy", "untitled")
    for o in items:
        d = o.get("item_data", {})
        name = (d.get("name") or "").strip()
        cats_for = item_categories(d, cat_names)
        if not cats_for:
            uncategorized.append(name or o["id"])
        low = name.lower()
        if (not name) or low in JUNK or any(low.startswith(j) for j in JUNK) or name.isdigit():
            blankish.append(name or "(blank)")
        vars_ = d.get("variations", []) or []
        if vars_ and all((v.get("item_variation_data", {}).get("price_money", {}).get("amount") in (None, 0))
                         for v in vars_):
            zero_price.append(name or o["id"])
        if not o.get("present_at_all_locations", True) and not o.get("present_at_location_ids"):
            no_location.append(name or o["id"])

    def show(label, lst, cap=40):
        print(f"\n  {label}: {len(lst)}")
        for x in lst[:cap]:
            print(f"     - {x}")
        if len(lst) > cap:
            print(f"     ...and {len(lst)-cap} more")

    print("\n== CLEANUP TRIAGE (candidates — nothing changed) ==")
    show("Duplicate item names", [f"{n}  (x{c})" for n, c in sorted(dup_names.items())])
    show("Blank / test-looking names", blankish)
    show("Items with NO category", uncategorized)
    show("Items priced $0 / no price", zero_price)
    show("Items not attached to any location", no_location)

    print("\n== ITEMS BY CATEGORY ==")
    grouped = collections.defaultdict(list)
    for o in items:
        d = o.get("item_data", {})
        cs = item_categories(d, cat_names) or ["(uncategorized)"]
        price = money((d.get("variations") or [{}])[0].get("item_variation_data", {}))
        grouped[cs[0]].append(f"{(d.get('name') or '?')}  {price}  [{len(d.get('variations', []))} var]")
    for cat in sorted(grouped):
        print(f"\n  # {cat}  ({len(grouped[cat])})")
        for line in sorted(grouped[cat]):
            print(f"     {line}")

    print(f"\nDone. Review {OUT} + the flags above, then we build the cleanup plan.")


if __name__ == "__main__":
    main()
