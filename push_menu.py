"""push_menu.py — sync Square FROM menu.json (the source of truth / "the bible").

menu.json wins. For EVERY item it pushes name, description, category (from its
section), and each variation's name + price. It also:
  * CREATES items that are in menu.json but missing from Square (e.g. one deleted by
    accident), then writes the new Square IDs back into menu.json so it self-heals.
  * DELETES items marked "retired": true.
Matches items + variations by square_id, so updates happen in place — never duplicates.

Does NOT touch tax or modifier (add-on) settings on EXISTING items — those are
preserved from the current export (managed by catalog_modifiers.py). New items are
created taxed, at all locations, with no modifiers.

Run order when you also fixed modifiers: catalog_modifiers.py --apply -> pull_catalog.py
-> push_menu.py.

    python push_menu.py            # dry run — shows every change, writes nothing
    $env:SQUARE_TOKEN = "token_with_ITEMS_WRITE"
    python push_menu.py --apply
"""
import os, sys, json, uuid, shutil, copy
import requests

EXPORT = "catalog_export.json"
MENU = "menu.json"
SQUARE_BASE = "https://connect.squareup.com/v2"
HEADERS = {
    "Authorization": f"Bearer {os.environ.get('SQUARE_TOKEN','')}",
    "Square-Version": "2025-01-23",
    "Content-Type": "application/json",
}


def money(cents):
    return {"amount": int(cents), "currency": "USD"}


def build_update(sq, mi, cat_id):
    obj = copy.deepcopy(sq)
    d = obj["item_data"]
    d["name"] = mi["name"]
    d["description"] = mi.get("description", "") or ""
    d.pop("description_html", None)
    d.pop("description_plaintext", None)
    if cat_id:
        d["reporting_category"] = {"id": cat_id}
        d["categories"] = [{"id": cat_id}]
    mjv = {v["square_id"]: v for v in mi.get("variations", [])}
    for v in d.get("variations", []):
        mv = mjv.get(v["id"])
        if not mv:
            continue
        vd = v["item_variation_data"]
        vd["name"] = mv["name"]
        vd["pricing_type"] = "FIXED_PRICING"
        vd["price_money"] = money(mv["price_cents"])
    return obj


def build_create(mi, cat_id, tax_id):
    variations = [{
        "type": "ITEM_VARIATION",
        "id": "#" + v["square_id"],
        "present_at_all_locations": True,
        "item_variation_data": {
            "name": v["name"],
            "pricing_type": "FIXED_PRICING",
            "price_money": money(v["price_cents"]),
        },
    } for v in mi.get("variations", [])]
    item_data = {"name": mi["name"], "description": mi.get("description", "") or "",
                 "variations": variations}
    if tax_id:
        item_data["tax_ids"] = [tax_id]
    if cat_id:
        item_data["reporting_category"] = {"id": cat_id}
        item_data["categories"] = [{"id": cat_id}]
    return {"type": "ITEM", "id": "#" + mi["square_id"],
            "present_at_all_locations": True, "item_data": item_data}


def diff(sq, mi, cat_id, cat_name):
    ch = []
    cur = sq["item_data"]
    if (cur.get("name") or "") != mi["name"]:
        ch.append(f'name "{cur.get("name")}" -> "{mi["name"]}"')
    if (cur.get("description") or "") != (mi.get("description") or ""):
        ch.append("description")
    if cat_id and (cur.get("reporting_category") or {}).get("id") != cat_id:
        ch.append(f"category -> {cat_name}")
    mjv = {v["square_id"]: v for v in mi.get("variations", [])}
    for v in cur.get("variations", []):
        mv = mjv.get(v["id"])
        if not mv:
            continue
        vd = v["item_variation_data"]
        if vd.get("name") != mv["name"]:
            ch.append(f'var "{vd.get("name")}" -> "{mv["name"]}"')
        if (vd.get("price_money") or {}).get("amount") != mv["price_cents"]:
            ch.append(f'price {mv["name"]} -> ${mv["price_cents"]/100:.2f}')
    return ch


def main():
    apply = "--apply" in sys.argv
    for f in (EXPORT, MENU):
        if not os.path.exists(f):
            sys.exit(f"[error] {f} not found.")
    objs = json.load(open(EXPORT, encoding="utf-8"))
    menu = json.load(open(MENU, encoding="utf-8"))
    sq_by_id = {o["id"]: o for o in objs if o.get("type") == "ITEM"}
    sq_by_name = {}
    for o in objs:
        if o.get("type") == "ITEM":
            sq_by_name.setdefault((o["item_data"].get("name") or "").strip(), o)
    cat_by_name = {o["category_data"]["name"]: o["id"] for o in objs if o.get("type") == "CATEGORY"}
    sec_cat = {s["key"]: s["square_category"] for s in menu["sections"]}
    tax_id = next((o["id"] for o in objs if o.get("type") == "TAX"), None)

    print("=== PUSH menu.json -> Square (menu.json is the source of truth) ===")
    print(f"mode: {'APPLY (writes to Square)' if apply else 'DRY RUN (no changes)'}\n")

    updates, creates, deletes, adopted = [], [], [], False
    for mi in menu["items"]:
        sq = sq_by_id.get(mi["square_id"])
        cat_name = sec_cat.get(mi["section"])
        cat_id = cat_by_name.get(cat_name)
        if mi.get("retired"):
            if sq:
                deletes.append((mi["square_id"], mi["name"]))
            continue
        if not sq:
            # ID not found — but if an item with this NAME already exists in Square, adopt
            # its IDs instead of creating a duplicate (self-heals a stale/placeholder id).
            byname = sq_by_name.get(mi["name"].strip())
            if byname:
                mi["square_id"] = byname["id"]
                sqv = byname["item_data"].get("variations", [])
                for i, v in enumerate(mi.get("variations", [])):
                    if i < len(sqv):
                        v["square_id"] = sqv[i]["id"]
                adopted = True
                sq = byname
            else:
                creates.append((mi, cat_id, cat_name))
                continue
        updates.append((sq, mi, cat_id, cat_name, diff(sq, mi, cat_id, cat_name)))

    print(f"ITEMS TO SYNC (update): {len(updates)}")
    for sq, mi, cid, cname, ch in updates:
        print(f"   - {mi['name']:30}{'  |  ' + '; '.join(ch) if ch else '  |  already in sync'}")
    print(f"\nITEMS TO CREATE (missing from Square): {len(creates)}")
    for mi, cid, cname in creates:
        print(f"   - {mi['name']:30}  ({cname}, {len(mi.get('variations',[]))} var)")
    print(f"\nITEMS TO DELETE (retired): {len(deletes)}")
    for sid, name in deletes:
        print(f"   - {name}  [{sid}]")

    if not apply:
        print(f"\nDRY RUN — nothing changed. {len(updates)} update, {len(creates)} create, "
              f"{len(deletes)} delete.")
        print("Set $env:SQUARE_TOKEN and re-run with --apply.")
        return
    if not os.environ.get("SQUARE_TOKEN"):
        sys.exit("[error] --apply needs SQUARE_TOKEN (with ITEMS_WRITE) set.")

    shutil.copy(EXPORT, "catalog_backup_before_push.json")
    print("\nBacked up -> catalog_backup_before_push.json\nApplying object-by-object...\n")
    ok, fail, menu_changed = 0, [], False

    for sq, mi, cid, cname, ch in updates:
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                          json={"idempotency_key": str(uuid.uuid4()), "object": build_update(sq, mi, cid)})
        if r.ok: ok += 1
        else: fail.append((mi["name"], r.text[:160]))

    for mi, cid, cname in creates:
        temp_item = "#" + mi["square_id"]
        temp_vars = ["#" + v["square_id"] for v in mi.get("variations", [])]
        r = requests.post(f"{SQUARE_BASE}/catalog/object", headers=HEADERS,
                          json={"idempotency_key": str(uuid.uuid4()), "object": build_create(mi, cid, tax_id)})
        if not r.ok:
            fail.append((mi["name"] + " (create)", r.text[:160])); continue
        ok += 1
        mp = {m["client_object_id"]: m["object_id"] for m in r.json().get("id_mappings", [])}
        mi["square_id"] = mp.get(temp_item, mi["square_id"])
        for v, tv in zip(mi.get("variations", []), temp_vars):
            v["square_id"] = mp.get(tv, v["square_id"])
        menu_changed = True

    for sid, name in deletes:
        r = requests.delete(f"{SQUARE_BASE}/catalog/object/{sid}", headers=HEADERS)
        if r.ok: ok += 1
        else: fail.append((f"delete {name}", r.text[:160]))

    if menu_changed or adopted:
        json.dump(menu, open(MENU, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(MENU, "a", encoding="utf-8").write("\n")
        print("menu.json updated with corrected/created Square IDs.")

    print(f"pushed {ok}/{len(updates)+len(creates)+len(deletes)} objects")
    if fail:
        print(f"\nCOULD NOT ({len(fail)}):")
        for n, d in fail:
            print(f"   - {n}: {d}")
    print("\nDONE. Re-run pull_catalog.py to confirm; changes sync to DoorDash shortly.")


if __name__ == "__main__":
    main()
