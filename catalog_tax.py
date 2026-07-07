"""Ensure every Square item collects the 7.975% Sales Tax.

Square attaches taxes to items via item_data.tax_ids. This links the existing enabled
7.975% "Sales Tax" to EVERY item that's missing it. DRY-RUN by default; --apply writes
to Square (needs SQUARE_TOKEN with ITEMS_WRITE), object-by-object + resilient.

    python catalog_tax.py            # dry run - shows which items are missing tax
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python catalog_tax.py --apply
"""
import os, sys, json, uuid, shutil
import requests

EXPORT = "catalog_export.json"
RATE = "7.975"
SQUARE_BASE = "https://connect.squareup.com/v2"
HEADERS = {
    "Authorization": f"Bearer {os.environ.get('SQUARE_TOKEN','')}",
    "Square-Version": "2025-01-23",
    "Content-Type": "application/json",
}


def main():
    apply = "--apply" in sys.argv
    if not os.path.exists(EXPORT):
        sys.exit(f"[error] {EXPORT} not found - run pull_catalog.py first.")
    objs = json.load(open(EXPORT, encoding="utf-8"))

    taxes = [o for o in objs if o["type"] == "TAX"]
    match = [t for t in taxes if (t["tax_data"].get("percentage") == RATE and t["tax_data"].get("enabled"))]
    if not match:
        present = ", ".join(f"{t['tax_data'].get('name')}={t['tax_data'].get('percentage')}%" for t in taxes)
        sys.exit(f"[error] no enabled {RATE}% tax found. Taxes present: {present}")
    tax_id = match[0]["id"]
    print(f"=== APPLY {RATE}% SALES TAX TO ALL ITEMS ===")
    print(f"mode: {'APPLY (writes to Square)' if apply else 'DRY RUN (no changes)'}")
    print(f"tax: {match[0]['tax_data'].get('name')} ({RATE}%)  id={tax_id}\n")

    items = [o for o in objs if o["type"] == "ITEM"]
    need = [o for o in items if tax_id not in (o["item_data"].get("tax_ids") or [])]
    have = len(items) - len(need)
    print(f"items: {len(items)} total | already taxed: {have} | MISSING tax: {len(need)}")
    for o in need:
        print("   + add tax ->", o["item_data"].get("name"))

    if not apply:
        print("\nDRY RUN complete - nothing changed. Re-run with --apply to attach tax to all.")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")

    shutil.copy(EXPORT, "catalog_backup_before_tax.json")
    print("\nBacked up -> catalog_backup_before_tax.json\nApplying object-by-object...\n")
    ok, fail = 0, []
    for o in need:
        obj = json.loads(json.dumps(o))
        ids = obj["item_data"].get("tax_ids") or []
        if tax_id not in ids:
            ids.append(tax_id)
        obj["item_data"]["tax_ids"] = ids
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                          json={"idempotency_key": str(uuid.uuid4()), "object": obj})
        if r.ok: ok += 1
        else: fail.append((obj["item_data"].get("name"), r.text[:160]))
    print(f"tax applied to {ok}/{len(need)} items")
    if fail:
        print(f"\nCOULD NOT ({len(fail)}):")
        for name, detail in fail: print(f"   - {name}: {detail}")
    print("\nDONE. Re-run pull_catalog.py to confirm every item is taxed.")


if __name__ == "__main__":
    main()
