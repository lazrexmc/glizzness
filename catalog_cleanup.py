"""Square Catalog cleanup — Pass 1 (declutter): delete junk + fix names.

DRY-RUN BY DEFAULT (reads catalog_export.json, calls Square for NOTHING, just prints
the plan). Use --apply to actually write to Square (needs SQUARE_TOKEN with ITEMS_WRITE).

Deleting catalog items does NOT affect historical sales/reporting — Square keeps the
item name on past transactions. Because DoorDash reads Square's catalog, this cleans both.

    python catalog_cleanup.py                 # dry run — shows exactly what would happen
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python catalog_cleanup.py --apply         # executes (after a fresh pull_catalog.py)
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

# ---- DECISIONS (from the 2026 cleanup review) ----
# Junk items to DELETE (broken topping-as-variation items + $0 abandoned items + catering clutter).
DELETE_ITEMS = [
    # broken "toppings-as-variations" junk
    "apple", "black", "snake", "double", "mush",
    # $0 / never-finished abandoned items
    "arkansauce", "Asian chicken", "blackened catfish", "cuban", "fireball",
    "Goofy Goober", "hot honey chicken", "meatball", "pineapple curry chicken",
    "pineapple teriyaki", "veggie", "veggies", "chicken salad", "Fettuccine",
    "Lasagna", "cheesecake", "philly", "Half B&Gs", "Biscuits And Gravy",
    # catering/event clutter (do manually / via the booking form instead)
    "Catering for 100", "On site setup", "On site service",
    "Deposit for on site service for event", "Food Truck Fest ~ 200",
]
# Placeholder / orphan modifier lists to DELETE (only if not referenced by any item).
DELETE_MODIFIER_LISTS = ["Bag of Chips Choice", "Fruit Choice", "Soda Choice", "Glizzies"]
# Name fixes (typos / abbreviations).
RENAME_ITEMS = {
    "Chkn Tryki": "Chicken Teriyaki",
    "Strwbry Uncrstble": "Strawberry Uncrustable",
    "Prk CHP SPECIAL": "Pork Chop Special",
    "MacN'Cheese": "Mac N' Cheese",
    "GlizzyClassic": "Glizzy Classic",
    "dasani": "Dasani",
}
DELETE_EMPTY_CATEGORIES = True   # remove categories no item references (dupes/empties)


def load():
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found — run pull_catalog.py first.")
    return json.load(open(EXPORT, encoding="utf-8"))


def index(objs):
    items = [o for o in objs if o["type"] == "ITEM"]
    mls   = [o for o in objs if o["type"] == "MODIFIER_LIST"]
    cats  = [o for o in objs if o["type"] == "CATEGORY"]
    by_item = {(o["item_data"].get("name") or "").strip(): o for o in items}
    by_ml   = {(o["modifier_list_data"].get("name") or "").strip(): o for o in mls}
    # category ids referenced by any item
    used_cat_ids = set()
    ml_refs = set()
    for o in items:
        d = o["item_data"]
        if d.get("category_id"): used_cat_ids.add(d["category_id"])
        for c in d.get("categories", []) or []:
            if c.get("id"): used_cat_ids.add(c["id"])
        if d.get("reporting_category", {}).get("id"):
            used_cat_ids.add(d["reporting_category"]["id"])
        for mi in d.get("modifier_list_info", []) or []:
            if mi.get("modifier_list_id"): ml_refs.add(mi["modifier_list_id"])
    return items, mls, cats, by_item, by_ml, used_cat_ids, ml_refs


def main():
    apply = "--apply" in sys.argv
    objs = load()
    items, mls, cats, by_item, by_ml, used_cat_ids, ml_refs = index(objs)

    del_ids, del_report = [], []
    # items
    for name in DELETE_ITEMS:
        o = by_item.get(name)
        if o:
            del_ids.append(o["id"]); del_report.append(f"ITEM   {name}")
        else:
            del_report.append(f"ITEM   {name}   [NOT FOUND - skipped]")
    # modifier lists (only if unreferenced)
    for name in DELETE_MODIFIER_LISTS:
        o = by_ml.get(name)
        if not o:
            del_report.append(f"MODLIST {name}   [NOT FOUND - skipped]"); continue
        if o["id"] in ml_refs:
            del_report.append(f"MODLIST {name}   [STILL REFERENCED - skipped, keeping]")
        else:
            del_ids.append(o["id"]); del_report.append(f"MODLIST {name}")
    # empty categories
    if DELETE_EMPTY_CATEGORIES:
        for c in cats:
            if c["id"] not in used_cat_ids:
                del_ids.append(c["id"])
                del_report.append(f"CATEGORY {c['category_data'].get('name','?')}   [empty]")

    # renames -> upsert objects (preserve version + full data)
    upserts, ren_report = [], []
    for old, new in RENAME_ITEMS.items():
        o = by_item.get(old)
        if not o:
            ren_report.append(f"{old!r} -> {new!r}   [NOT FOUND - skipped]"); continue
        obj = json.loads(json.dumps(o))       # deep copy
        obj["item_data"]["name"] = new
        upserts.append(obj); ren_report.append(f"{old!r} -> {new!r}")

    # ---- report ----
    print("=== SQUARE CATALOG CLEANUP - PASS 1 (declutter) ===")
    print(f"mode: {'APPLY (writes to Square)' if apply else 'DRY RUN (no changes)'}\n")
    print(f"DELETE {len(del_ids)} objects:")
    for r in del_report: print("   -", r)
    print(f"\nRENAME {len(upserts)} items:")
    for r in ren_report: print("   -", r)
    kept = len(items) - sum(1 for n in DELETE_ITEMS if n in by_item)
    print(f"\nResult: {len(items)} items -> ~{kept} items after deletes.")
    plan = {"delete_ids": del_ids, "delete_report": del_report,
            "rename_report": ren_report, "upsert_count": len(upserts)}
    json.dump(plan, open("catalog_cleanup_plan.json", "w"), indent=2)
    print("Wrote catalog_cleanup_plan.json")

    if not apply:
        print("\nDRY RUN complete - nothing changed. Re-run with --apply to execute.")
        return

    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")
    shutil.copy(EXPORT, "catalog_backup_before_cleanup.json")
    print("\nBacked up -> catalog_backup_before_cleanup.json")

    if del_ids:
        r = requests.post(f"{SQUARE_BASE}/catalog/batch-delete", headers=HEADERS,
                          json={"object_ids": del_ids})
        print("batch-delete:", r.status_code, r.text[:200])
        r.raise_for_status()
    if upserts:
        body = {"idempotency_key": str(uuid.uuid4()),
                "batches": [{"objects": upserts}]}
        r = requests.post(f"{SQUARE_BASE}/catalog/batch-upsert", headers=HEADERS, json=body)
        print("batch-upsert:", r.status_code, r.text[:200])
        r.raise_for_status()
    print("\nDONE. Re-run pull_catalog.py to see the cleaned catalog.")


if __name__ == "__main__":
    main()
