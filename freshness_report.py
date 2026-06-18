"""Vending Circuit - freshness report (Tier 1).
Run anytime on your PC:  python freshness_report.py
No network, no dependencies. Reads data/events.csv and prints a punch-list of
what likely needs a refresh, so you know when to trigger a re-date research pass.
"""
import csv, re, datetime, sys, os

EVENTS = os.path.join("data", "events.csv")
STALE_DAYS = 365          # "not verified in over a year"
today = datetime.date.today()

def parse_date(s):
    try: return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception: return None

def past_year_in(text):
    # only recent past years (last few cycles) - skips founding years like "since 2014"
    yrs = [int(y) for y in re.findall(r"\b(20\d{2})\b", text or "")]
    past = [y for y in yrs if today.year - 4 <= y < today.year]
    return max(past) if past else None

if not os.path.exists(EVENTS):
    sys.exit(f"Can't find {EVENTS} - run from the project root.")

rows = list(csv.DictReader(open(EVENTS, encoding="utf-8")))
published = [r for r in rows if r["verification_status"] in ("verified", "partial")
            and r["food_truck_friendly"] != "excluded"]

needs_conf  = [r for r in published if r["needs_confirmation"] == "true"]
partial     = [r for r in published if r["verification_status"] == "partial"]
past_dates  = [(r, past_year_in(r["typical_dates"]) or past_year_in(r["notes"]))
               for r in published]
past_dates  = [(r, y) for r, y in past_dates if y]
stale = []
for r in published:
    lv = parse_date(r.get("last_verified", ""))
    if lv and (today - lv).days > STALE_DAYS:
        stale.append((r, (today - lv).days))

def line(r): return f"  - {r['name']}  ({r['city']}, {r['state']})  [{r['month']}]"

print(f"\n=== Vending Circuit freshness report - {today.isoformat()} ===")
print(f"{len(published)} published events ({len(rows)} total in data/events.csv)\n")

print(f"[1] needs_confirmation - verify before relying  ({len(needs_conf)})")
print("\n".join(line(r) for r in needs_conf) or "  (none)")

print(f"\n[2] verification_status = partial - soft dates/size  ({len(partial)})")
print("\n".join(line(r) for r in partial) or "  (none)")

print(f"\n[3] date string references a PAST year  ({len(past_dates)})")
print("\n".join(f"{line(r)}  -> mentions {y}" for r, y in past_dates) or "  (none)")

print(f"\n[4] not research-verified in over {STALE_DAYS} days  ({len(stale)})")
print("\n".join(f"{line(r)}  -> {d} days" for r, d in sorted(stale, key=lambda x:-x[1])) or "  (none)")

flagged = {id(r) for r in needs_conf} | {id(r) for r in partial} \
          | {id(r) for r, _ in past_dates} | {id(r) for r, _ in stale}
print(f"\n--- {len(flagged)} distinct events flagged for attention ---")
print("Tip: most fairs/festivals publish next-year dates Jan-Mar. When this list grows")
print('(or each winter), trigger a re-date research pass, regenerate, and re-run the load SQL.\n')
