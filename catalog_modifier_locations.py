"""Make the add-on modifier lists show on the POS at ALL locations.

Root cause of "no add-ons on the handheld": the modifier lists are pinned to a single
location (e.g. LGDKWP1W9QGEA) while items are present at all locations, so at any other
location the list is filtered out and nothing shows. This sets the target lists AND
their modifiers to present_at_all_locations = True.

DRY-RUN by default; --apply writes to Square (needs SQUARE_TOKEN with ITEMS_WRITE),
object-by-object, backs up first.

    python catalog_modifier_locations.py            # dry run
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python catalog_modifier_locations.py --apply
"""
import os, sys, json, uuid, shutil, copy
import requests

EXPORT = "catalog_export.json"
SQUARE_BASE = "https://connect.squareup.com/v2"
HEADERS = {
    "Authorization": f"Bearer {os.environ.get('SQUARE_TOKEN','')}",
    "Square-Version": "2025-01-23",
    "Content-Type": "application/json",
}

# The lists we want available everywhere (Cheeses / Simple adds intentionally left out).
LISTS = ["Add-Ons", "Topping Addition"]


def make_all_locations(o):
    obj = copy.deepcopy(o)
    obj["present_at_all_locations"] = True
    obj.pop("present_at_location_ids", None)
    obj.pop("absent_at_location_ids", None)
    return obj


def main():
    apply = "--apply" in sys.argv
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found - run pull_catalog.py first.")
    objs = json.load(open(EXPORT, encoding="utf-8"))

    target_lists = [o for o in objs
                    if o.get("type") == "MODIFIER_LIST"
                    and (o["modifier_list_data"].get("name") or "").strip() in LISTS]
    target_ids = {o["id"] for o in target_lists}
    target_mods = [o for o in objs
                   if o.get("type") == "MODIFIER"
                   and o.get("modifier_data", {}).get("modifier_list_id") in target_ids]

    print("=== MAKE ADD-ON LISTS PRESENT AT ALL LOCATIONS ===")
    print(f"mode: {'APPLY (writes to Square)' if apply else 'DRY RUN (no changes)'}\n")

    to_update = []
    for o in target_lists + target_mods:
        already = o.get("present_at_all_locations") is True and not o.get("present_at_location_ids")
        if already:
            continue
        to_update.append(o)

    print(f"Lists: {[o['modifier_list_data'].get('name') for o in target_lists]}")
    print(f"Objects to set all-locations: {len(to_update)} "
          f"({len(target_lists)} list(s) + {len(target_mods)} modifier(s))\n")
    for o in to_update:
        if o["type"] == "MODIFIER_LIST":
            nm = o["modifier_list_data"].get("name")
        else:
            nm = (o["modifier_data"].get("name") or "")[:40]
        print(f"   - {o['type']:14} {nm}   at={o.get('present_at_location_ids')}")

    if not to_update:
        print("Nothing to change — already all-locations.")
        return
    if not apply:
        print("\nDRY RUN — nothing changed. Set $env:SQUARE_TOKEN and re-run with --apply.")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")

    shutil.copy(EXPORT, "catalog_backup_before_modloc.json")
    print("\nBacked up -> catalog_backup_before_modloc.json\nApplying object-by-object...\n")
    ok, fail = 0, []
    for o in to_update:
        obj = make_all_locations(o)
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                          json={"idempotency_key": str(uuid.uuid4()), "object": obj})
        if r.ok: ok += 1
        else: fail.append((o["id"], r.text[:160]))
    print(f"updated {ok}/{len(to_update)} objects")
    if fail:
        print(f"\nCOULD NOT ({len(fail)}):")
        for i, d in fail:
            print(f"   - {i}: {d}")
    print("\nDONE. Re-run pull_catalog.py to confirm; add-ons should now show on the handheld.")


if __name__ == "__main__":
    main()
