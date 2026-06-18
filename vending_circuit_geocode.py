"""Phase 3: geocode (city-level from knowledge) + parse schedules.
Fills lat/lng in data/events.csv and writes data/event_schedules.csv.
"""
import csv, os, re

EV = "data/events.csv"
OUT_SCHED = "data/event_schedules.csv"

# ---- city centroids (lat, lng) ----
C = {
 ("Columbia","MO"):(38.9517,-92.3341),("Boonville","MO"):(38.9739,-92.7430),
 ("Hartsburg","MO"):(38.7039,-92.3088),
 ("Jefferson City","MO"):(38.5767,-92.1735),("Moberly","MO"):(39.4184,-92.4382),
 ("Hermann","MO"):(38.7036,-91.4374),("Sedalia","MO"):(38.7045,-93.2283),
 ("Hannibal","MO"):(39.7084,-91.3585),("Kansas City","MO"):(39.0997,-94.5786),
 ("Independence","MO"):(39.0911,-94.4155),("Lee's Summit","MO"):(38.9108,-94.3822),
 ("Parkville","MO"):(39.1950,-94.6822),("Blue Springs","MO"):(39.0169,-94.2816),
 ("St. Louis","MO"):(38.6270,-90.1994),("St. Charles","MO"):(38.7881,-90.4974),
 ("O'Fallon","MO"):(38.8106,-90.6998),("Wentzville","MO"):(38.8114,-90.8529),
 ("Dardenne Prairie","MO"):(38.7595,-90.7307),("Springfield","MO"):(37.2090,-93.2923),
 ("Ozark","MO"):(37.0211,-93.2060),("Republic","MO"):(37.1198,-93.4799),
 ("Branson","MO"):(36.6437,-93.2185),("Joplin","MO"):(37.0842,-94.5133),
 ("Carthage","MO"):(37.1764,-94.3102),("Marshfield","MO"):(37.3389,-92.9074),
 ("Lebanon","MO"):(37.6806,-92.6638),
 ("Lenexa","KS"):(38.9536,-94.7336),("Wichita","KS"):(37.6872,-97.3301),
 ("Hutchinson","KS"):(38.0608,-97.9298),("Salina","KS"):(38.8403,-97.6114),
 ("Derby","KS"):(37.5450,-97.2689),("Junction City","KS"):(39.0286,-96.8314),
 ("Edwardsville","IL"):(38.8114,-89.9532),("Belleville","IL"):(38.5200,-89.9840),
 ("Collinsville","IL"):(38.6703,-89.9846),("Highland","IL"):(38.7392,-89.6712),
 ("Springfield","IL"):(39.7817,-89.6501),("Moline","IL"):(41.5067,-90.5151),
 ("Omaha","NE"):(41.2565,-95.9345),("Waterloo","NE"):(41.2742,-96.2861),
 ("Bellevue","NE"):(41.1370,-95.9145),("Fremont","NE"):(41.4333,-96.4981),
 ("Lincoln","NE"):(40.8136,-96.7026),
 ("Wilber","NE"):(40.4806,-96.9628),("Papillion","NE"):(41.1544,-96.0422),
 ("Gretna","NE"):(41.1411,-96.2392),("Grand Island","NE"):(40.9264,-98.3420),
 ("Des Moines","IA"):(41.5868,-93.6250),("Cedar Rapids","IA"):(41.9779,-91.6656),
 ("Anamosa","IA"):(42.1083,-91.2849),("Iowa City","IA"):(41.6611,-91.5302),
 ("Davenport","IA"):(41.5236,-90.5776),("Bettendorf","IA"):(41.5556,-90.4951),
 ("Council Bluffs","IA"):(41.2619,-95.8608),
 ("Tulsa","OK"):(36.1540,-95.9928),("Broken Arrow","OK"):(36.0526,-95.7908),
 ("Owasso","OK"):(36.2695,-95.8547),("Bixby","OK"):(35.9420,-95.8833),
 ("Bartlesville","OK"):(36.7473,-95.9808),
 ("Rogers","AR"):(36.3320,-94.1185),("Bentonville","AR"):(36.3729,-94.2088),
 ("Springdale","AR"):(36.1867,-94.1288),("Canehill","AR"):(35.9081,-94.4022),
 ("Prairie Grove","AR"):(35.9759,-94.3169),("Conway","AR"):(35.0887,-92.4421),
 ("North Little Rock","AR"):(34.7695,-92.2671),("Little Rock","AR"):(34.7465,-92.2896),
 ("Fort Smith","AR"):(35.3859,-94.3985),
 ("Memphis","TN"):(35.1495,-90.0490),("Germantown","TN"):(35.0867,-89.8101),
 ("Collierville","TN"):(35.0420,-89.6645),("Bartlett","TN"):(35.2045,-89.8740),
 ("Hendersonville","TN"):(36.3048,-86.6200),("Nashville","TN"):(36.1627,-86.7816),
 ("Franklin","TN"):(35.9251,-86.8689),("Gallatin","TN"):(36.3884,-86.4467),
 ("Murfreesboro","TN"):(35.8456,-86.3903),
}
# fix the two sentinel typos defensively
C[("Hartsburg","MO")] = (38.7039,-92.3088)
C[("Canehill","AR")] = (35.9081,-94.4022)

MONTHS = {m:i for i,m in enumerate(
 ["January","February","March","April","May","June","July","August",
  "September","October","November","December"], start=1)}
ABBR = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
SEASON = {"spring":4,"summer":7,"fall":10,"winter":12}

def start_month(month_str):
    s = month_str.lower()
    for name,num in MONTHS.items():
        if name.lower() in s: return num
    for ab,num in ABBR.items():
        if re.search(r'\b'+ab, s): return num
    for se,num in SEASON.items():
        if se in s: return num
    return ""  # year-round / TBD

def recurrence_text(cadence, dates, month):
    if cadence in ("weekly","monthly","year_round","multi_week","recurring"):
        return dates or month
    return ""

def year_specific(dates):
    # a concrete day range like "Aug 13-23" or "Sep 4-7" or "Jun 11"
    return "true" if re.search(r'[A-Za-z]{3,}\.?\s*\d{1,2}', dates) and not re.search(r'(weekly|monthly|1st|2nd|3rd|last|every)', dates.lower()) else "false"

rows = list(csv.DictReader(open(EV, encoding="utf-8")))

# group indices per city for jitter
from collections import defaultdict
bycity = defaultdict(list)
for r in rows:
    bycity[(r["city"], r["state"])].append(r)

missing = []
for (city,state), group in bycity.items():
    coord = C.get((city,state))
    if not coord:
        missing.append(f"{city}, {state}")
        continue
    lat0, lng0 = coord
    n = len(group)
    for idx, r in enumerate(group):
        # deterministic ring offset so same-city events don't perfectly overlap (~250-400m)
        if n == 1:
            r["lat"], r["lng"] = f"{lat0:.5f}", f"{lng0:.5f}"
        else:
            import math
            ang = (2*math.pi*idx)/n
            dlat = 0.0035*math.cos(ang)
            dlng = 0.0035*math.sin(ang)
            r["lat"], r["lng"] = f"{lat0+dlat:.5f}", f"{lng0+dlng:.5f}"

# write events back
cols = list(rows[0].keys())
with open(EV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)

# build schedules
sched = []
sid = 0
for r in rows:
    sid += 1
    sm = start_month(r["month"])
    sched.append({
        "id": sid,
        "event_id": r["id"],
        "month": sm,
        "display_text": r["typical_dates"] or r["month"],
        "recurrence_text": recurrence_text(r["cadence"], r["typical_dates"], r["month"]),
        "year_specific": year_specific(r["typical_dates"]),
    })
with open(OUT_SCHED, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id","event_id","month","display_text","recurrence_text","year_specific"])
    w.writeheader()
    for s in sched: w.writerow(s)

# report
geocoded = sum(1 for r in rows if r["lat"])
print("events:", len(rows), "| geocoded:", geocoded, "| missing coords:", len(missing))
for m in missing: print("   MISSING:", m)
print("schedules written:", len(sched))
from collections import Counter
print("schedule month set:", sum(1 for s in sched if s["month"]!=""), "of", len(sched), "(rest year-round/TBD/seasonal)")
print("year_specific true:", sum(1 for s in sched if s["year_specific"]=="true"))
