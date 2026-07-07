"""Backfill Square item descriptions (which flow to DoorDash).

Sets item_data.description for items that are missing one, from a reviewed map below.
DRY-RUN by default; --apply writes to Square (needs SQUARE_TOKEN with ITEMS_WRITE),
object-by-object + resilient. Items NOT in the map (and still blank) are listed as
"STILL NEEDS TEXT" so Trint can supply the specialty ones.

    python catalog_desc.py            # dry run - shows proposed descriptions
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python catalog_desc.py --apply
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

# Proposed descriptions. Sourced from menu.html, item variation names, and your own
# modifier text. EDIT ANY OF THESE before --apply. (Specialty items I couldn't source
# are intentionally left out -> they show as "STILL NEEDS TEXT".)
DESCRIPTIONS = {
    # --- from menu.html ---
    "Jackfruit": "Jackfruit, seasoned and roasted to perfection, served on our bun.",
    "Street Corn": "Traditional Mexican street food - roasted, seasoned corn off the cob, piled on a bed of tortilla chips.",
    "Nachos": "Build-your-own nachos - tortilla chips piled high, covered in queso, then finish with your choice of cold toppings from the side bar.",
    "Water": "Bottled water.",
    # --- from your own item/modifier data ---
    "Link": "A cheddar cheese-filled pork frank (jalapeno & cheddar option available).",
    "Nacho Dawg": "A Glizzy topped with nacho cheese, our salsa blend, and crumbled cheese chips.",
    # --- reasonable drafts (CONFIRM wording) ---
    "Glizzy Classic": "Our classic 1/4 lb all-beef Glizzy, topped with your favorites.",
    "Chicken Teriyaki": "Grilled teriyaki chicken - served as a single or 2 sticks.",
    "Sloppy Joe": "A classic sloppy joe piled on a bun.",
    "Half Pound Smoked Apple Brat": "A half-pound smoked apple brat from Patchwork Family Farms - like fall on a bun.",
    "Turkey Link": "A smoked turkey sausage link.",
    "Mac N' Cheese": "Creamy mac & cheese.",
    "Grill Cheese": "A classic grilled cheese.",
    # --- safe generics (drinks / snacks / merch) ---
    "Dasani": "Bottled Dasani water.",
    "Iced Coffee": "Cold, refreshing iced coffee.",
    "Fries": "Hot, crispy fries.",
    "Slim Jim": "A Slim Jim meat snack stick.",
    "Strawberry Uncrustable": "A Strawberry Uncrustable - crustless PB&J sandwich.",
    "Keychain": "A Glizzness keychain - take a piece of the cart home.",
}


def main():
    apply = "--apply" in sys.argv
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found - run pull_catalog.py first.")
    objs = json.load(open(EXPORT, encoding="utf-8"))
    items = [o for o in objs if o["type"] == "ITEM"]
    by_name = {(o["item_data"].get("name") or "").strip(): o for o in items}

    print("=== BACKFILL ITEM DESCRIPTIONS (-> DoorDash) ===")
    print(f"mode: {'APPLY (writes to Square)' if apply else 'DRY RUN (no changes)'}\n")

    to_set = []   # (obj, name, desc)
    for name, desc in DESCRIPTIONS.items():
        o = by_name.get(name)
        if not o:
            print(f"[warn] item not found, skipping: {name}"); continue
        to_set.append((o, name, desc))

    print(f"WILL SET description on {len(to_set)} items:")
    for _, name, desc in to_set:
        print(f"   - {name}: {desc}")

    have = [o["item_data"]["name"] for o in items if (o["item_data"].get("description") or "").strip()]
    still = [o["item_data"].get("name") for o in items
             if not (o["item_data"].get("description") or "").strip()
             and (o["item_data"].get("name") or "").strip() not in DESCRIPTIONS]
    print(f"\nALREADY HAVE a description ({len(have)}): {', '.join(sorted(have))}")
    print(f"\nSTILL NEEDS TEXT ({len(still)}) - Trint, what's in these? (I won't guess ingredients):")
    for n in sorted(still): print(f"   - {n}")

    if not apply:
        print("\nDRY RUN - nothing changed. Edit DESCRIPTIONS above, then re-run with --apply.")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")

    shutil.copy(EXPORT, "catalog_backup_before_desc.json")
    print("\nBacked up -> catalog_backup_before_desc.json\nApplying object-by-object...\n")
    ok, fail = 0, []
    for o, name, desc in to_set:
        obj = json.loads(json.dumps(o))
        obj["item_data"]["description"] = desc
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                          json={"idempotency_key": str(uuid.uuid4()), "object": obj})
        if r.ok: ok += 1
        else: fail.append((name, r.text[:160]))
    print(f"descriptions set on {ok}/{len(to_set)} items")
    if fail:
        print(f"\nCOULD NOT ({len(fail)}):")
        for name, detail in fail: print(f"   - {name}: {detail}")
    print("\nDONE. Re-run pull_catalog.py to confirm; descriptions sync to DoorDash shortly.")


if __name__ == "__main__":
    main()
