"""Square Catalog cleanup - Pass 2 (organize): sort items into clean sections.

DRY-RUN BY DEFAULT. --apply writes to Square (needs SQUARE_TOKEN with ITEMS_WRITE),
object-by-object + resilient (reports anything it can't touch). Run pull_catalog.py
FIRST so catalog_export.json has current versions.

What it does:
  - deletes 'Special' (unknown item; recreate on the fly if needed)
  - sets each item's PRIMARY section (reporting_category) to the right category so the
    DoorDash/POS menu shows real sections instead of one 'Food & Beverages' blob
  - creates a 'Cart Only' category for burgers + merch (you then exclude it on DoorDash)
  - deletes the emptied leftover categories (Food & Beverages, the duplicate Not-a-Glizzy)

    python catalog_pass2.py            # dry run
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python catalog_pass2.py --apply
"""
import os, sys, json, uuid, shutil
import requests

EXPORT = "catalog_export.json"
SQUARE_BASE = "https://connect.squareup.com/v2"
HEADERS = {
    "Authorization": f"Bearer {os.environ.get('SQUARE_TOKEN','')}",
    "Square-Version": "2025-01-23",
    "Content-Type": "application/json",
}

DELETE_ITEMS = ["Special"]
NEW_CATEGORIES = ["Cart Only"]            # created if missing (hidden from DoorDash in the portal)
KEEP_CATEGORIES = ["Glizzy", "Not-a-Glizzy", "Sides", "Drinks", "Vegetarian", "Cart Only"]
CAT_OF = {  # item name -> section
    # Glizzies (existing "Glizzy" category)
    "Glizzy": "Glizzy", "Glizzy Classic": "Glizzy", "All The Way": "Glizzy",
    "Something Fowl": "Glizzy", "Chili Dawg": "Glizzy", "Hog N' Dawg": "Glizzy",
    "Nacho Dawg": "Glizzy", "Special Brat": "Glizzy", "Apple Brat": "Glizzy",
    "Half Pound Smoked Apple Brat": "Glizzy", "Smoked Pork Sausage Link": "Glizzy",
    "Link": "Glizzy", "Turkey Link": "Glizzy",
    # Not-a-Glizzy
    "Pulled Pork": "Not-a-Glizzy", "Sloppy Joe": "Not-a-Glizzy", "Grill Cheese": "Not-a-Glizzy",
    "Chicken Teriyaki": "Not-a-Glizzy", "Shredded Chicken": "Not-a-Glizzy",
    "Pork Chop Special": "Not-a-Glizzy", "Taco": "Not-a-Glizzy",
    # Vegetarian
    "Jackfruit": "Vegetarian",
    # Sides
    "Fries": "Sides", "Chips": "Sides", "Walking Chips": "Sides", "Mac N' Cheese": "Sides",
    "Nachos": "Sides", "Street Corn": "Sides", "Sides": "Sides", "Slim Jim": "Sides",
    "Strawberry Uncrustable": "Sides",
    # Drinks
    "Beverage": "Drinks", "Water": "Drinks", "Dasani": "Drinks", "Iced Coffee": "Drinks",
    # Cart Only (hidden from DoorDash)
    "Burger": "Cart Only", "Boujee Burger": "Cart Only", "Keychain": "Cart Only",
}


def load():
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found - run pull_catalog.py first.")
    return json.load(open(EXPORT, encoding="utf-8"))


def main():
    apply = "--apply" in sys.argv
    objs = load()
    items = [o for o in objs if o["type"] == "ITEM"]
    cats  = [o for o in objs if o["type"] == "CATEGORY"]
    by_item = {(o["item_data"].get("name") or "").strip(): o for o in items}
    cat_id_by_name, cat_name_by_id = {}, {}
    for c in cats:
        nm = c["category_data"].get("name", "?")
        cat_name_by_id[c["id"]] = nm
        cat_id_by_name.setdefault(nm, c["id"])   # first wins = canonical (handles dup names)

    print("=== SQUARE CATALOG CLEANUP - PASS 2 (organize) ===")
    print(f"mode: {'APPLY (writes to Square)' if apply else 'DRY RUN (no changes)'}\n")

    missing = [n for n in CAT_OF.values() if n not in cat_id_by_name and n not in NEW_CATEGORIES]
    if missing:
        print("[warn] target categories not found + not marked new:", set(missing))
    to_create = [n for n in NEW_CATEGORIES if n not in cat_id_by_name]
    print(f"CREATE categories: {to_create or 'none'}")

    print(f"\nDELETE items: {DELETE_ITEMS}")
    for n in DELETE_ITEMS:
        if n not in by_item: print(f"   - {n}  [NOT FOUND - skipped]")

    print("\nMOVE each item to its section (primary/reporting category):")
    from collections import defaultdict
    grouped = defaultdict(list)
    for name, o in by_item.items():
        if name in DELETE_ITEMS: continue
        target = CAT_OF.get(name)
        if not target:
            grouped["(UNASSIGNED - left as-is)"].append(name); continue
        grouped[target].append(name)
    for sec in ["Glizzy", "Not-a-Glizzy", "Vegetarian", "Sides", "Drinks", "Cart Only", "(UNASSIGNED - left as-is)"]:
        if grouped.get(sec):
            tag = " (hidden from DoorDash)" if sec == "Cart Only" else ""
            print(f"   # {sec}{tag}  ({len(grouped[sec])}): {', '.join(sorted(grouped[sec]))}")

    keep_ids = {cat_id_by_name[n] for n in KEEP_CATEGORIES if n in cat_id_by_name}
    del_cats = [(c["id"], cat_name_by_id[c["id"]]) for c in cats if c["id"] not in keep_ids]
    print(f"\nDELETE leftover/duplicate categories after reassign: "
          f"{[n for _, n in del_cats] or 'none'}")

    if not apply:
        print("\nDRY RUN complete - nothing changed. Re-run with --apply to execute.")
        print("NOTE: 'Cart Only' is hidden from DoorDash in the DoorDash portal (not via API).")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")

    shutil.copy(EXPORT, "catalog_backup_before_pass2.json")
    print("\nBacked up -> catalog_backup_before_pass2.json\nApplying object-by-object...\n")

    def post(obj):
        return requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                             json={"idempotency_key": str(uuid.uuid4()), "object": obj})

    # 1) create new categories, capture real ids
    for nm in to_create:
        r = post({"type": "CATEGORY", "id": "#new_" + nm.replace(" ", "_"),
                  "category_data": {"name": nm}})
        if r.ok:
            cat_id_by_name[nm] = r.json()["catalog_object"]["id"]
            print(f"created category {nm} -> {cat_id_by_name[nm]}")
        else:
            print(f"[FAIL] create category {nm}: {r.status_code} {r.text[:160]}");
    # 2) delete items
    ok, fail = 0, []
    for n in DELETE_ITEMS:
        o = by_item.get(n)
        if not o: continue
        r = requests.delete(f"{SQUARE_BASE}/catalog/object/{o['id']}", headers=HEADERS)
        if r.ok: ok += 1
        else: fail.append((f"delete {n}", r.text[:160]))
    # 3) reassign items
    moved = 0
    for name, o in by_item.items():
        if name in DELETE_ITEMS or name not in CAT_OF: continue
        cid = cat_id_by_name.get(CAT_OF[name])
        if not cid: fail.append((f"move {name}", "target category id missing")); continue
        obj = json.loads(json.dumps(o))
        obj["item_data"]["reporting_category"] = {"id": cid}
        obj["item_data"]["categories"] = [{"id": cid}]
        r = post(obj)
        if r.ok: moved += 1
        else: fail.append((f"move {name}", r.text[:160]))
    # 4) delete leftover categories
    delcat_ok = 0
    for cid, nm in del_cats:
        r = requests.delete(f"{SQUARE_BASE}/catalog/object/{cid}", headers=HEADERS)
        if r.ok: delcat_ok += 1
        else: fail.append((f"delete category {nm}", r.text[:120]))

    print(f"\nitems deleted {ok}/{len(DELETE_ITEMS)} | items moved {moved} | categories removed {delcat_ok}/{len(del_cats)}")
    if fail:
        print(f"\nCOULD NOT ({len(fail)}):")
        for label, detail in fail: print(f"   - {label}: {detail}")
    print("\nDONE. Re-run pull_catalog.py to confirm. Then in the DoorDash portal, exclude the")
    print("'Cart Only' category so burgers + keychain don't show for delivery.")


if __name__ == "__main__":
    main()
