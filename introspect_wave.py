#!/usr/bin/env python3
"""Introspect Wave GraphQL schema to find available fields on Business type."""
import os, json, requests

WAVE_TOKEN       = os.environ.get("WAVE_TOKEN", "")
WAVE_BUSINESS_ID = os.environ.get("WAVE_BUSINESS_ID", "")
WAVE_GQL = "https://gql.waveapps.com/graphql/public"
HEADERS  = {"Authorization": f"Bearer {WAVE_TOKEN}", "Content-Type": "application/json"}

def gql(query, variables=None):
    r = requests.post(WAVE_GQL, headers=HEADERS, json={"query": query, "variables": variables or {}})
    return r.json()

def print_type_fields(type_name):
    result = gql(f"""
    query {{
      __type(name: "{type_name}") {{
        name kind
        fields {{
          name
          type {{ name kind ofType {{ name kind ofType {{ name kind }} }} }}
          args {{ name type {{ name kind ofType {{ name kind }} }} }}
        }}
      }}
    }}
    """)
    t = (result.get("data") or {}).get("__type") or {}
    fields = t.get("fields") or []
    if not fields:
        print(f"  (no fields — type name may differ or introspection restricted)")
        return
    for f in fields:
        ft = f["type"]
        name = ft.get("name") or ft.get("kind", "")
        inner = (ft.get("ofType") or {})
        iname = inner.get("name") or inner.get("kind", "")
        print(f"  {f['name']:<35} {name or iname}")
        if f.get("args"):
            for a in f["args"]:
                at = a["type"]
                aname = at.get("name") or (at.get("ofType") or {}).get("name", at.get("kind",""))
                print(f"      arg: {a['name']}: {aname}")

# 1 — root Query type fields
print("=== Root Query fields ===")
print_type_fields("Query")

# 2 — Business type fields
print("\n=== Business type fields ===")
print_type_fields("Business")

# 3 — Transaction OBJECT fields
print("\n=== Transaction object fields ===")
print_type_fields("Transaction")

# 4 — all types with 'transaction' in name
print("\n=== Types with 'transaction' in name ===")
result2 = gql("query { __schema { types { name kind } } }")
types = (result2.get("data") or {}).get("__schema", {}).get("types", [])
for t in types:
    if "transaction" in t["name"].lower():
        print(f"  {t['kind']:<15} {t['name']}")

# 5 — try live query on business to see if any field works
print("\n=== Live business query (moneyTransactions attempt) ===")
live = gql("""
query ($id: ID!) {
  business(id: $id) {
    id
    name
  }
}
""", {"id": WAVE_BUSINESS_ID})
print(json.dumps(live, indent=2)[:600])
