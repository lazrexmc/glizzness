"""Phase 2 ETL: consolidate -> dedupe -> assign markets -> normalize enums.
Reads VendingCircuit.csv (raw master), writes data/markets.csv and data/events.csv.
No geocoding / no schedule parsing here (Phase 3). No DB load (Phase 4).
"""
import csv, os, re

SRC = "VendingCircuit.csv"
OUTDIR = "data"
os.makedirs(OUTDIR, exist_ok=True)

# ---- 17 market hubs (from DATA_MODEL.md §5) ----
# (id, name, anchor_city, state, center_lat, center_lng, default_zoom, distance, summary)
MARKETS = [
    (1,  "Columbia / Mid-Missouri", "Columbia", "MO", 38.9517, -92.3341, 9, 0,   "Hometown + mid-MO towns within ~100 mi"),
    (2,  "Kansas City Metro", "Kansas City", "MO", 39.0997, -94.5786, 10, 125,   "KC MO+KS metro and suburbs"),
    (3,  "St. Louis Metro", "St. Louis", "MO", 38.6270, -90.1994, 10, 125,       "STL MO side + Illinois Metro East"),
    (4,  "Springfield / Ozarks", "Springfield", "MO", 37.2090, -93.2923, 9, 165, "SW Missouri Ozarks incl. Branson/Joplin"),
    (5,  "Central Illinois", "Springfield", "IL", 39.7817, -89.6501, 10, 140,    "Springfield IL / Illinois State Fair"),
    (6,  "Des Moines", "Des Moines", "IA", 41.5868, -93.6250, 10, 200,           "Des Moines metro"),
    (7,  "Quad Cities", "Davenport", "IA", 41.5236, -90.5776, 10, 270,           "Davenport/Bettendorf IA + Moline IL"),
    (8,  "Cedar Rapids / Iowa City", "Cedar Rapids", "IA", 41.9779, -91.6656, 9, 255, "CR + Iowa City corridor"),
    (9,  "Omaha Metro", "Omaha", "NE", 41.2565, -95.9345, 10, 340,              "Omaha NE + Council Bluffs IA"),
    (10, "Lincoln Area", "Lincoln", "NE", 40.8136, -96.7026, 9, 330,            "Lincoln + Wilber + Grand Island"),
    (11, "Wichita / S-Central Kansas", "Wichita", "KS", 37.6872, -97.3301, 9, 280, "Wichita, Hutchinson, Salina, Derby"),
    (12, "Central Kansas", "Junction City", "KS", 39.0286, -96.8314, 9, 150,    "Junction City / Manhattan corridor"),
    (13, "Tulsa Metro", "Tulsa", "OK", 36.1540, -95.9928, 10, 346,             "Tulsa + Broken Arrow/Owasso/Bixby/Bartlesville"),
    (14, "NW Arkansas", "Bentonville", "AR", 36.3729, -94.2088, 9, 250,         "Bentonville/Rogers/Springdale/Fayetteville + Fort Smith"),
    (15, "Central Arkansas", "Little Rock", "AR", 34.7465, -92.2896, 10, 376,   "Little Rock / North Little Rock / Conway"),
    (16, "Memphis", "Memphis", "TN", 35.1495, -90.0490, 10, 290,               "Memphis TN + suburbs + Southaven MS"),
    (17, "Nashville", "Nashville", "TN", 36.1627, -86.7816, 10, 431,           "Nashville + Franklin/Hendersonville/Gallatin/Murfreesboro"),
]

# ---- city -> market_id (keyed by (city_lower, state)) ----
CITY_HUB = {}
def reg(mid, state, *cities):
    for c in cities:
        CITY_HUB[(c.lower(), state)] = mid
reg(1,"MO","Columbia","Boonville","Hartsburg","Jefferson City","Moberly","Hermann","Sedalia","Hannibal","Mexico","Fulton","Rocheport","Ashland")
reg(2,"MO","Kansas City","Independence","Lee's Summit","Parkville","Blue Springs","Liberty","Gladstone")
reg(2,"KS","Lenexa","Overland Park","Leavenworth","Olathe","Shawnee","Kansas City")
reg(3,"MO","St. Louis","St. Charles","O'Fallon","Wentzville","Dardenne Prairie","Cottleville","Chesterfield","Kirkwood","Fenton","Maplewood","Washington")
reg(3,"IL","Edwardsville","Belleville","Collinsville","Highland","Granite City","Glen Carbon","Alton")
reg(4,"MO","Springfield","Ozark","Republic","Branson","Joplin","Carthage","Marshfield","Lebanon","Nixa","Bolivar")
reg(5,"IL","Springfield")
reg(6,"IA","Des Moines","West Des Moines","Ankeny","Urbandale","Ames")
reg(7,"IA","Davenport","Bettendorf")
reg(7,"IL","Moline","Rock Island","East Moline")
reg(8,"IA","Cedar Rapids","Anamosa","Iowa City")
reg(9,"NE","Omaha","Waterloo","Bellevue","Fremont","Papillion","Gretna","La Vista")
reg(9,"IA","Council Bluffs")
reg(10,"NE","Lincoln","Wilber","Grand Island")
reg(11,"KS","Wichita","Hutchinson","Salina","Derby","Andover","Newton")
reg(12,"KS","Junction City","Manhattan","Topeka")
reg(13,"OK","Tulsa","Broken Arrow","Owasso","Bixby","Bartlesville","Jenks","Sand Springs","Muskogee")
reg(14,"AR","Rogers","Bentonville","Springdale","Fayetteville","Canehill","Prairie Grove","Fort Smith","Bella Vista")
reg(15,"AR","Conway","North Little Rock","Little Rock","Hot Springs")
reg(16,"TN","Memphis","Germantown","Collierville","Bartlett")
reg(16,"MS","Southaven")
reg(17,"TN","Nashville","Franklin","Hendersonville","Gallatin","Murfreesboro")

def market_for(city, state):
    return CITY_HUB.get((city.strip().lower(), state.strip()), 0)

# ---- enum derivation ----
def trip_type(dist):
    try: d = int(dist)
    except: return "overnight"
    if d <= 15: return "hometown"
    if d <= 150: return "day_trip"
    return "overnight"

def verif(status):
    s = status.lower()
    if "defunct" in s: return ("defunct", False)
    if status == "Excluded": return ("excluded", False)
    if s.startswith("partial") or "medium confidence" in s: return ("partial", True)
    caveat = any(k in s for k in ("unconfirmed","confirm","verify","2026 passed","plan for 2027","location"))
    return ("verified", caveat)

def event_type(name, notes):
    t = (name + " " + notes).lower()
    n = name.lower()
    if "state fair" in n: return "state_fair"
    if "county fair" in n or (("fair" in n) and "food truck" not in n and "art" not in n and "craft" not in n): return "county_fair"
    if "food truck" in n or "feastival" in n or "food truck rally" in t or "food truck wednesday" in t or "food truck thursday" in t or "food truck friday" in t or "food truck frenzy" in n: return "food_truck_rally"
    if "farmers market" in n or "market days" in n or "night market" in n or "community market" in n: return "farmers_market"
    if "oktoberfest" in n or "schweizerfest" in n: return "oktoberfest"
    if "craft fair" in n: return "craft_fair"
    if "art" in n and ("fair" in n or "festival" in n): return "art_fair"
    if "bbq" in n or "ribfest" in n or "smoke on" in n or "blues & bbq" in n: return "bbq_fest"
    if "balloon" in n: return "balloon_fest"
    if "christmas" in n or "holiday market" in n or "living windows" in n or "dickens" in n: return "holiday_market"
    if any(k in n for k in ("brewing","brewery","winery","taproom","boardwalk","marketplace","trucks, taps","vineyard","hold fast","guthrie green")): return "venue"
    if any(k in n for k in ("cherry blossom","czech","latino","fiestas","italian","greek","heritage","cultural")): return "cultural_fest"
    if "music" in n: return "music_fest"
    return "festival"

VENUE_NAMES = ("hold fast","marketplace at 2500","t&t","boardwalk","marshall brewing","newbo","guthrie green","rose district farmers","crossroads first fridays")
def cadence_and_venue(name, month, dates, etype):
    m = (month + " " + dates).lower()
    n = name.lower()
    venue = etype == "venue" or any(v in n for v in VENUE_NAMES)
    if "year-round" in m or "year round" in m: cad = "year_round"
    elif "weekly" in m or re.search(r'\b(mon|tue|wed|thu|fri|sat|sun)\b', m) and ("every" in m or "weekly" in m or "11a-2p" in m or "4-8p" in m): cad = "weekly"
    elif "weekly" in dates.lower() or "(weekly)" in m: cad = "weekly"
    elif "monthly" in m or "(monthly)" in m or re.search(r'(1st|2nd|3rd|last)\s+(fri|thu|sat)', m): cad = "monthly"
    elif "twice yearly" in m or "weekends in" in m or "8 fridays" in m or "select frid" in m or "multi-week" in m or "& oct" in m or "weekends" in m: cad = "multi_week"
    elif "intermittent" in m or "recurring" in m: cad = "recurring"
    else: cad = "annual"
    if venue and cad == "annual": cad = "recurring"
    return cad, venue

def food_friendly(status, notes):
    s = (status + " " + notes).lower()
    if "defunct" in s or status == "Excluded" or "not taking" in s or "not viable" in s or "internal-only" in s or "internal food" in s: return "excluded"
    if any(k in s for k in ("food-truck showcase","food trucks are","food-truck-centric","food truck row","explicitly food","food trucks explicitly","hot dogs","20+ trucks","food truck plaza","dedicated food truck","food truck competition","food-truck-centered","food trucks 10","food-truck friendly","food trucks welcome","food truck fair","food-truck-focused","food trucks +","food truck/food-vendor","food trucks invited")): return "explicit_yes"
    if any(k in s for k in ("weak fit","doubtful","unconfirmed","not established","not explicitly","confirm","favors local","lower priority","invite-only","not a dedicated","at capacity","fills","full for 2026")): return "unconfirmed"
    return "concession_friendly"

EMAIL_RE = re.compile(r'[\w.\-+]+@[\w.\-]+\.\w+')
PHONE_RE = re.compile(r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}|\d{3}-[A-Z]{3,4}')
def split_contact(contact):
    email = EMAIL_RE.search(contact)
    phone = PHONE_RE.search(contact)
    email = email.group(0) if email else ""
    phone = phone.group(0) if phone else ""
    name = contact
    for x in (email, phone):
        if x: name = name.replace(x, "")
    name = name.strip(" /,-")
    # if leftover looks like a url or generic, drop as name
    if name and ("." in name and " " not in name): name = ""
    return name, email, phone

def parse_attendance(text):
    t = text.replace(",", "")
    m = re.search(r'\d{3,}', t)
    return int(m.group(0)) if m else ""

# ---- run ----
rows = list(csv.DictReader(open(SRC, encoding="utf-8")))

# dedupe by (name_lower, city_lower)
seen = {}
dupes = []
for r in rows:
    key = (r["event_name"].strip().lower(), r["city"].strip().lower())
    if key in seen:
        dupes.append(r["event_name"] + " / " + r["city"])
        continue
    seen[key] = r
deduped = list(seen.values())

events = []
unmapped = []
for i, r in enumerate(deduped, start=1):
    et = event_type(r["event_name"], r["notes"])
    cad, venue = cadence_and_venue(r["event_name"], r["month"], r["typical_dates"], et)
    vs, needs = verif(r["status"])
    mid = market_for(r["city"], r["state"])
    if mid == 0: unmapped.append(f'{r["event_name"]} ({r["city"]}, {r["state"]})')
    cname, cemail, cphone = split_contact(r["contact"])
    url = r["url"]
    homepage = url if url and "." in url else ""
    events.append({
        "id": i,
        "market_id": mid,
        "name": r["event_name"],
        "city": r["city"],
        "state": r["state"],
        "event_type": et,
        "cadence": cad,
        "is_recurring_venue": "true" if venue else "false",
        "food_truck_friendly": food_friendly(r["status"], r["notes"]),
        "trip_type": trip_type(r["distance_mi"]),
        "verification_status": vs,
        "needs_confirmation": "true" if needs else "false",
        "distance_from_columbia_mi": r["distance_mi"],
        "month": r["month"],
        "typical_dates": r["typical_dates"],          # kept for Phase 3 schedule parsing
        "attendance_estimate": parse_attendance(r["attendance"]),
        "attendance_text": r["attendance"],
        "food_vendor_fee": r["food_vendor_fee"],
        "application_method": r["application_method"],
        "contact_name": cname,
        "contact_email": cemail,
        "contact_phone": cphone,
        "homepage_url": homepage,
        "primary_source_url": url,
        "lat": "",   # Phase 3
        "lng": "",   # Phase 3
        "notes": r["notes"],
    })

# write markets.csv
with open(os.path.join(OUTDIR, "markets.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id","name","anchor_city","state","center_lat","center_lng","default_zoom","distance_from_columbia_mi","summary"])
    for m in MARKETS:
        w.writerow(m)

# write events.csv
cols = list(events[0].keys())
with open(os.path.join(OUTDIR, "events.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for e in events:
        w.writerow(e)

# report
from collections import Counter
print("input rows:", len(rows), "| deduped:", len(deduped), "| dupes removed:", len(dupes))
if dupes: print("  dup names:", dupes)
print("events written:", len(events))
print("unmapped to market (market_id=0):", len(unmapped))
for u in unmapped: print("   -", u)
print("market_id distribution:", dict(sorted(Counter(e["market_id"] for e in events).items())))
print("event_type:", dict(Counter(e["event_type"] for e in events)))
print("cadence:", dict(Counter(e["cadence"] for e in events)))
print("food_truck_friendly:", dict(Counter(e["food_truck_friendly"] for e in events)))
print("verification_status:", dict(Counter(e["verification_status"] for e in events)))
print("trip_type:", dict(Counter(e["trip_type"] for e in events)))
print("needs_confirmation true:", sum(1 for e in events if e["needs_confirmation"]=="true"))
print("recurring venues:", sum(1 for e in events if e["is_recurring_venue"]=="true"))
