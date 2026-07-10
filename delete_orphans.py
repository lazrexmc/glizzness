"""One-off cleanup: delete duplicate/orphan Square catalog items by ID.

Duplicates got created when push_menu.py's create ran twice without a fresh pull.
These IDs are the extra copies NOT referenced by menu.json (the keepers stay).

DRY-RUN by default; --apply needs SQUARE_TOKEN with ITEMS_WRITE.
Safe to delete this file once run.

    python delete_orphans.py
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python delete_orphans.py --apply
"""
import os, sys
import requests

SQUARE_BASE = "https://connect.squareup.com/v2"
HEADERS = {"Authorization": f"Bearer {os.environ.get('SQUARE_TOKEN','')}",
           "Square-Version": "2025-01-23"}

ORPHANS = {
    "YZPEVVVPOGK667IDYOS4NYYD": "Potato Salad (duplicate)",
    "MWQFXLHYMBVL62LLDISTA6SM": "Cole Slaw (duplicate)",
}


def main():
    apply = "--apply" in sys.argv
    print(f"mode: {'APPLY (deletes from Square)' if apply else 'DRY RUN'}\n")
    for iid, label in ORPHANS.items():
        print(f"  {'DELETE' if apply else 'would delete'}: {label}  [{iid}]")
    if not apply:
        print("\nDRY RUN — nothing deleted. Set $env:SQUARE_TOKEN and re-run with --apply.")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN.")
    ok, fail = 0, []
    for iid, label in ORPHANS.items():
        r = requests.delete(f"{SQUARE_BASE}/catalog/object/{iid}", headers=HEADERS)
        if r.ok: ok += 1
        else: fail.append((label, r.text[:160]))
    print(f"\ndeleted {ok}/{len(ORPHANS)}")
    for l, d in fail:
        print(f"  FAILED {l}: {d}")
    print("Re-run pull_catalog.py to confirm the duplicates are gone.")


if __name__ == "__main__":
    main()
