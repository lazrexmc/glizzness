"""Square Catalog cleanup — Pass 1 (declutter): delete junk + fix names.

DRY-RUN BY DEFAULT (reads catalog_export.json, calls Square for NOTHING, just prints
the plan). Use --apply to actually write to Square (needs SQUARE_TOKEN with ITEMS_WRITE).

Applies changes OBJECT-BY-OBJECT (not one atomic batch) so a single object Square won't
let us touch can't abort the whole run — it deletes/renames everything it can and reports
exactly what it couldn't (with the real error). Deleting catalog items does NOT affect
historical sales/reporting. Because DoorDash reads Square's catalog, this cleans both.

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
DELETE_ITEMS = [
    "apple", "black", "snake", "double", "mush",
    "arkansauce", "Asian chicken", "blackened catfish", "cuban", "fireball",
    "Goofy Goober", "hot honey chicken", "meatball", "pineapple curry chicken",
    "pineapple teriyaki", "veggie", "veggies", "chicken salad", "Fettuccine",
    "Lasagna", "cheesecake", "philly", "Half B&Gs", "Biscuits And Gravy",
    "Catering for 100", "On site setup", "On site service",
    "Deposit for on site service for event", "Food Truck Fest ~ 200",
]
DELETE_MODIFIER_LISTS = ["Bag of Chips Choice", "Fruit Choice", "Soda Choice", "Glizzies"]
RENAME_ITEMS = {
    "Chkn Tryki": "Chicken Teriyaki",
    "Strwbry Uncrstble": "Strawberry Uncrustable",
    "Prk CHP SPECIAL": "Pork Chop Special",
    "MacN'Cheese": "Mac N' Cheese",
    "GlizzyClassic": "Glizzy Classic",
    "dasani": "Dasani",
}
DELETE_EMPTY_CATEGORIES = True


def load():
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found — run pull_catalog.py first.")
    return json.load(open(EXPORT, encoding="utf-8"))


def build_plan(objs):
    items = [o for o in objs if o["type"] == "ITEM"]
    mls   = [o for o in objs if o["type"] == "MODIFIER_LIST"]
    cats  = [o for o in objs if o["type"] == "CATEGORY"]
    by_item = {(o["item_data"].get("name") or "").strip(): o for o in items}
    by_ml   = {(o["modifier_list_data"].get("name") or "").strip(): o for o in mls}
    used_cat_ids, ml_refs = set(), set()
    for o in items:
        d = o["item_data"]
        if d.get("category_id"): used_cat_ids.add(d["category_id"])
        for c in d.get("categories", []) or []:
            if c.get("id"): used_cat_ids.add(c["id"])
        if d.get("reporting_category", {}).get("id"):
            used_cat_ids.add(d["reporting_category"]["id"])
        for mi in d.get("modifier_list_info", []) or []:
            if mi.get("modifier_list_id"): ml_refs.add(mi["modifier_list_id"])

    deletes, notes = [], []          # deletes: list of (id, label)
    for name in DELETE_ITEMS:
        o = by_item.get(name)
        if o: deletes.append((o["id"], f"ITEM  {name}"))
        else: notes.append(f"ITEM  {name}  [NOT FOUND - skipped]")
    for name in DELETE_MODIFIER_LISTS:
        o = by_ml.get(name)
        if not o: notes.append(f"MODLIST  {name}  [NOT FOUND - skipped]")
        elif o["id"] in ml_refs: notes.append(f"MODLIST  {name}  [STILL REFERENCED - keeping]")
        else: deletes.append((o["id"], f"MODLIST  {name}"))
    if DELETE_EMPTY_CATEGORIES:
        for c in cats:
            if c["id"] not in used_cat_ids:
                deletes.append((c["id"], f"CATEGORY  {c['category_data'].get('name','?')} [empty]"))

    renames = []                     # renames: list of (object, label)
    for old, new in RENAME_ITEMS.items():
        o = by_item.get(old)
        if not o: notes.append(f"RENAME  {old!r} -> {new!r}  [NOT FOUND - skipped]"); continue
        obj = json.loads(json.dumps(o))
        obj["item_data"]["name"] = new
        renames.append((obj, f"{old!r} -> {new!r}"))
    return deletes, renames, notes, len(items)


def main():
    apply = "--apply" in sys.argv
    objs = load()
    deletes, renames, notes, n_items = build_plan(objs)

    print("=== SQUARE CATALOG CLEANUP - PASS 1 (declutter) ===")
    print(f"mode: {'APPLY (writes to Square, object-by-object)' if apply else 'DRY RUN (no changes)'}\n")
    print(f"DELETE {len(deletes)} objects:")
    for _, label in deletes: print("   -", label)
    print(f"\nRENAME {len(renames)} items:")
    for _, label in renames: print("   -", label)
    if notes:
        print("\nskipped:")
        for nnote in notes: print("   -", nnote)
    print(f"\nResult: {n_items} items -> ~{n_items - sum(1 for l in deletes if l[1].startswith('ITEM'))} items after deletes.")

    if not apply:
        print("\nDRY RUN complete - nothing changed. Re-run with --apply to execute.")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")

    shutil.copy(EXPORT, "catalog_backup_before_cleanup.json")
    print("\nBacked up -> catalog_backup_before_cleanup.json")
    print("Applying object-by-object...\n")

    ok_del, fail_del = [], []
    for oid, label in deletes:
        r = requests.delete(f"{SQUARE_BASE}/catalog/object/{oid}", headers=HEADERS)
        if r.ok:
            ok_del.append(label)
        else:
            try: err = r.json().get("errors", [{}])[0]
            except Exception: err = {"detail": r.text[:160]}
            fail_del.append((label, err.get("code"), err.get("detail")))

    ok_ren, fail_ren = [], []
    for obj, label in renames:
        body = {"idempotency_key": str(uuid.uuid4()), "object": obj}
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS, json=body)
        if r.ok:
            ok_ren.append(label)
        else:
            try: err = r.json().get("errors", [{}])[0]
            except Exception: err = {"detail": r.text[:160]}
            fail_ren.append((label, err.get("code"), err.get("detail")))

    print(f"DELETED  {len(ok_del)}/{len(deletes)}   |   RENAMED  {len(ok_ren)}/{len(renames)}")
    if fail_del:
        print(f"\nCOULD NOT DELETE ({len(fail_del)}) — reason from Square:")
        for label, code, detail in fail_del:
            print(f"   - {label}\n        {code}: {detail}")
    if fail_ren:
        print(f"\nCOULD NOT RENAME ({len(fail_ren)}):")
        for label, code, detail in fail_ren:
            print(f"   - {label}\n        {code}: {detail}")
    print("\nDONE. Re-run pull_catalog.py to see the current catalog.")
    if fail_del or fail_ren:
        print("Send me the 'COULD NOT ...' lines above and I'll sort the remainder.")


if __name__ == "__main__":
    main()
