"""Fix Square item modifier (add-on) menus so they show on the POS.

For the items below: attach + ENABLE the "Add-Ons" list with unlimited selection
(clears the max_selected_modifiers=0 bug that made tapping the item do nothing),
and use ONLY "Add-Ons" — the Glizzy also keeps "Topping Addition". Replacing the
list array drops any Cheeses/Simple-adds that were on those items. Also renames two
typo'd modifiers.

DRY-RUN by default; --apply writes to Square (needs SQUARE_TOKEN with ITEMS_WRITE),
object-by-object + resilient, backs up first.

    python catalog_modifiers.py            # dry run
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python catalog_modifiers.py --apply
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

# item name (CURRENT Square name) -> modifier LIST names it should carry (enabled, unlimited)
ITEM_MODLISTS = {
    "Glizzy":                        ["Add-Ons", "Topping Addition"],
    "Pulled Pork":                   ["Add-Ons"],
    "Hog N' Dawg":                   ["Add-Ons"],
    "Nachos":                        ["Add-Ons"],
    "Walking Chips":                 ["Add-Ons"],
    "Apple Brat":                    ["Add-Ons"],
    "Jackfruit":                     ["Add-Ons"],
    "Something Fowl":                ["Add-Ons"],
    "Shredded Chicken":              ["Add-Ons"],
    "Half Pound Smoked Apple Brat":  ["Add-Ons"],
    "Street Corn":                   ["Add-Ons"],
    "Sloppy Joe":                    ["Add-Ons"],
    "All The Way":                   ["Add-Ons"],
}

# modifier name typo fixes: (prefix to match, replacement for that prefix)
MOD_RENAMES = [
    ("Hoggin' Dog", "Hog' N' Dog"),   # in "Topping Addition"
    ("Pull pork",   "Pulled Pork"),  # in "Simple adds"
]


def main():
    apply = "--apply" in sys.argv
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found - run pull_catalog.py first.")
    objs = json.load(open(EXPORT, encoding="utf-8"))
    items = {(o["item_data"].get("name") or "").strip(): o for o in objs if o["type"] == "ITEM"}
    mlists = {(o["modifier_list_data"].get("name") or "").strip(): o
              for o in objs if o["type"] == "MODIFIER_LIST"}
    mods = [o for o in objs if o["type"] == "MODIFIER"]
    ml_id = {name: o["id"] for name, o in mlists.items()}
    ml_name = {o["id"]: name for name, o in mlists.items()}

    print("=== FIX ITEM MODIFIER (ADD-ON) MENUS ===")
    print(f"mode: {'APPLY (writes to Square)' if apply else 'DRY RUN (no changes)'}\n")

    item_updates = []
    for name, want in ITEM_MODLISTS.items():
        o = items.get(name)
        if not o:
            print(f"[warn] item not found, skipping: {name}"); continue
        cur = [ml_name.get(m.get("modifier_list_id"), "?")
               for m in (o["item_data"].get("modifier_list_info") or [])]
        missing = [w for w in want if w not in ml_id]
        if missing:
            print(f"[warn] modifier list(s) not found: {missing}")
        item_updates.append((o, name, want, cur))

    print("ITEM ADD-ON MENUS (target = enabled, unlimited):")
    for o, name, want, cur in item_updates:
        note = "no change" if set(want) == set(cur) else f"was: {cur or 'NONE'}"
        print(f"   - {name:30} -> {want}   [{note}]")

    mod_updates = []
    for pref, repl in MOD_RENAMES:
        for m in mods:
            nm = m["modifier_data"].get("name", "")
            if nm.startswith(pref):
                mod_updates.append((m, nm, repl + nm[len(pref):]))
    print("\nMODIFIER RENAMES:")
    for _, old, new in mod_updates:
        print(f"   - {old[:46]!r}\n       -> {new[:46]!r}")
    if not mod_updates:
        print("   (none matched)")

    if not apply:
        print(f"\nDRY RUN - nothing changed. Would update {len(item_updates)} items "
              f"+ {len(mod_updates)} modifiers.")
        print("Set $env:SQUARE_TOKEN and re-run with --apply.")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")

    shutil.copy(EXPORT, "catalog_backup_before_modifiers.json")
    print("\nBacked up -> catalog_backup_before_modifiers.json\nApplying object-by-object...\n")
    ok, fail = 0, []
    for o, name, want, cur in item_updates:
        obj = json.loads(json.dumps(o))
        obj["item_data"]["modifier_list_info"] = [
            {"modifier_list_id": ml_id[w], "enabled": True} for w in want if w in ml_id
        ]
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                          json={"idempotency_key": str(uuid.uuid4()), "object": obj})
        if r.ok: ok += 1
        else: fail.append((name, r.text[:160]))
    for m, old, new in mod_updates:
        obj = json.loads(json.dumps(m))
        obj["modifier_data"]["name"] = new
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                          json={"idempotency_key": str(uuid.uuid4()), "object": obj})
        if r.ok: ok += 1
        else: fail.append((old[:30], r.text[:160]))
    total = len(item_updates) + len(mod_updates)
    print(f"updated {ok}/{total} objects")
    if fail:
        print(f"\nCOULD NOT ({len(fail)}):")
        for n, d in fail: print(f"   - {n}: {d}")
    print("\nDONE. Re-run pull_catalog.py to confirm; changes sync to DoorDash shortly.")


if __name__ == "__main__":
    main()
