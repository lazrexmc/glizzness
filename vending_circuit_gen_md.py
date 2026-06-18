"""Generate VendingCircuit.md (human-readable view) from data/events.csv.
Run after vending_circuit_etl.py + vending_circuit_geocode.py so it reflects the
normalized data. Grouped by trip type, sorted by distance then name. The CSV stays
the authoritative master; this markdown is a generated, in-sync view.
"""
import csv, os

EV = os.path.join("data", "events.csv")
OUT = "VendingCircuit.md"

rows = list(csv.DictReader(open(EV, encoding="utf-8")))

def published(r):
    return (r["verification_status"] in ("verified", "partial")
            and r["food_truck_friendly"] != "excluded")

pub = [r for r in rows if published(r)]
hidden = [r for r in rows if not published(r)]

def dist(r):
    try: return int(r["distance_from_columbia_mi"])
    except (ValueError, TypeError): return 9999

def contact_link(r):
    if r["homepage_url"]: return r["homepage_url"]
    parts = [r["contact_name"], r["contact_email"], r["contact_phone"]]
    return " / ".join(p for p in parts if p) or "—"

def flag(r):
    return " ⚠️" if r["needs_confirmation"] == "true" else ""

def table(group):
    out = ["| Event | Location | County | Dist | Month | Typical dates | Size | Contact / link |",
           "|---|---|---|---|---|---|---|---|"]
    for r in sorted(group, key=lambda r: (dist(r), r["name"])):
        loc = f'{r["city"]}, {r["state"]}'
        county = r["county"] or "—"
        size = r["attendance_text"] or "—"
        out.append(f'| {r["name"]}{flag(r)} | {loc} | {county} | {r["distance_from_columbia_mi"]} '
                   f'| {r["month"]} | {r["typical_dates"] or "—"} | {size} | {contact_link(r)} |')
    return "\n".join(out)

home = [r for r in pub if r["trip_type"] == "hometown"]
day  = [r for r in pub if r["trip_type"] == "day_trip"]
night = [r for r in pub if r["trip_type"] == "overnight"]

lines = [
 "# 🌭 The Glizzness — Festival & Fair Vending Circuit",
 "",
 f"**Master list — {len(rows)} events** within ~480 mi of Columbia, MO. Built from adversarially-verified "
 "research passes (foundational + regional + an ongoing Missouri county-by-county sweep).",
 "",
 "> **`VendingCircuit.csv` is the authoritative, database-ready master.** This markdown is a generated, "
 "human-readable view — regenerate with `python vending_circuit_gen_md.py`. Distances are approximate "
 "**driving miles** from Columbia. ⚠️ = `needs_confirmation` (verify dates/fit before relying).",
 ">",
 f"> **Live versions:** normalized into Supabase (`vending_*` tables, {len(pub)} published) and visualized "
 "by a static map in `vending-map/` (filters incl. county). Normalization spec: `DATA_MODEL.md`.",
 ">",
 "> Regenerate data: `python vending_circuit_etl.py && python vending_circuit_geocode.py && "
 "python vending_circuit_gen_sql.py && python vending_circuit_gen_md.py`.",
 "",
 "**Legend:** 🏠 hometown (~0 mi) · 🚗 day trip (≤150 mi) · 🏨 overnight (>150 mi).",
 "",
 "## Counts",
 "",
 f"- 🏠 Hometown / mid-MO: **{len(home)}**",
 f"- 🚗 Day trips (≤150 mi): **{len(day)}**",
 f"- 🏨 Overnight (>150 mi): **{len(night)}**",
 f"- ❌ Defunct / excluded (hidden): **{len(hidden)}**",
 "",
 "---",
 "",
 f"## 🏠 Hometown & mid-Missouri (~0 mi)  ({len(home)})",
 "",
 table(home),
 "",
 f"## 🚗 Day trips (≤150 mi)  ({len(day)})",
 "",
 table(day),
 "",
 f"## 🏨 Overnight (>150 mi)  ({len(night)})",
 "",
 table(night),
 "",
 f"## ❌ Defunct / excluded (hidden from the map by default)  ({len(hidden)})",
 "",
 table(hidden),
 "",
]
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print(f"wrote {OUT}: {len(rows)} events ({len(pub)} published) — "
      f"home {len(home)} / day {len(day)} / overnight {len(night)} / hidden {len(hidden)}")
