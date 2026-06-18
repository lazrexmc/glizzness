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
 # Mid-MO county sweep batch 1
 ("Centralia","MO"):(39.2103,-92.1382),("Ashland","MO"):(38.7728,-92.2563),
 ("Sturgeon","MO"):(39.2353,-92.2799),("Fulton","MO"):(38.8467,-91.9479),
 ("Auxvasse","MO"):(39.0145,-91.8957),("Kingdom City","MO"):(38.9540,-91.9343),
 ("Fayette","MO"):(39.1456,-92.6843),("New Franklin","MO"):(39.0153,-92.7374),
 ("Higbee","MO"):(39.3070,-92.5174),("Huntsville","MO"):(39.4359,-92.5454),
 ("Mexico","MO"):(39.1698,-91.8829),("California","MO"):(38.6278,-92.5663),
 ("Versailles","MO"):(38.4314,-92.8413),("Linn","MO"):(38.4869,-91.8482),
 ("Owensville","MO"):(38.3450,-91.5010),("Marshall","MO"):(39.1234,-93.1968),
 ("Montgomery City","MO"):(38.9776,-91.5052),
 # Southern/SE Missouri sweep (batch 2)
 ("Eldon","MO"):(38.3486,-92.5824),("Camdenton","MO"):(38.0083,-92.7446),
 ("Laurie","MO"):(38.1989,-92.8330),("Osage Beach","MO"):(38.1300,-92.6568),
 ("Rolla","MO"):(37.9514,-91.7713),("St. James","MO"):(38.0003,-91.6135),
 ("Cuba","MO"):(38.0631,-91.4032),("Steelville","MO"):(37.9683,-91.3543),
 ("Salem","MO"):(37.6456,-91.5360),("Waynesville","MO"):(37.8286,-92.2007),
 ("Vienna","MO"):(38.1869,-91.9468),("Cape Girardeau","MO"):(37.3059,-89.5181),
 ("Jackson","MO"):(37.3823,-89.6663),("Perryville","MO"):(37.7242,-89.8612),
 ("Sikeston","MO"):(36.8767,-89.5879),("Farmington","MO"):(37.7809,-90.4218),
 ("Ste. Genevieve","MO"):(37.9817,-90.0432),("Fredericktown","MO"):(37.5598,-90.2932),
 ("Potosi","MO"):(37.9362,-90.7879),("Ironton","MO"):(37.5970,-90.6212),
 ("Dexter","MO"):(36.7956,-89.9579),("Doniphan","MO"):(36.6203,-90.8235),
 ("Van Buren","MO"):(36.9942,-91.0151),("Poplar Bluff","MO"):(36.7570,-90.3929),
 ("Greenville","MO"):(37.1253,-90.4515),("Marble Hill","MO"):(37.3061,-89.9701),
 ("West Plains","MO"):(36.7281,-91.8524),("Gainesville","MO"):(36.6017,-92.4288),
 ("Thayer","MO"):(36.5253,-91.5374),("Eminence","MO"):(37.1503,-91.3585),
 ("Ava","MO"):(36.9519,-92.6602),("Houston","MO"):(37.3270,-91.9560),
 # North + West-central Missouri ring (batch 3)
 ("Bowling Green","MO"):(39.3417,-91.1954),("Troy","MO"):(38.9792,-90.9807),
 ("Paris","MO"):(39.4809,-92.0007),("Kirksville","MO"):(40.1947,-92.5830),
 ("Brookfield","MO"):(39.7836,-93.0735),("Trenton","MO"):(40.0792,-93.6169),
 ("Chillicothe","MO"):(39.7956,-93.5527),("Carrollton","MO"):(39.3589,-93.4969),
 ("Macon","MO"):(39.7423,-92.4727),("Salisbury","MO"):(39.4234,-92.8016),
 ("Clinton","MO"):(38.3678,-93.7780),("Warsaw","MO"):(38.2436,-93.3819),
 ("Warrensburg","MO"):(38.7628,-93.7360),("Richmond","MO"):(39.2786,-93.9774),
 ("Butler","MO"):(38.2592,-94.3319),("Nevada","MO"):(37.8392,-94.3547),
 ("Stockton","MO"):(37.6981,-93.7960),
 # Bootheel + Northwest + SW corner (batch 4)
 ("Kennett","MO"):(36.2364,-90.0557),("Caruthersville","MO"):(36.1928,-89.6556),
 ("New Madrid","MO"):(36.5862,-89.5267),("Charleston","MO"):(36.9192,-89.3508),
 ("Campbell","MO"):(36.4942,-90.0740),("Clarkton","MO"):(36.4517,-89.9670),
 ("St. Joseph","MO"):(39.7686,-94.8466),("Bethany","MO"):(40.2681,-94.0277),
 ("Maryville","MO"):(40.3458,-94.8722),("Neosho","MO"):(36.8689,-94.3680),
 ("Mount Vernon","MO"):(37.1031,-93.8088),("Lamar","MO"):(37.4953,-94.2766),
 ("Webb City","MO"):(37.1465,-94.4633),
 # Indianapolis Metro (Indiana)
 ("Indianapolis","IN"):(39.7684,-86.1581),("Carmel","IN"):(39.9784,-86.1180),
 ("Noblesville","IN"):(40.0456,-86.0086),("Greenwood","IN"):(39.6137,-86.1067),
 ("Plainfield","IN"):(39.7042,-86.3994),("Greenfield","IN"):(39.7847,-85.7694),
 # I-70 Corridor (STL-Indy) — IL + IN
 ("Effingham","IL"):(39.1200,-88.5434),("Vandalia","IL"):(38.9606,-89.0937),
 ("Greenville","IL"):(38.8922,-89.4137),("Casey","IL"):(39.2981,-87.9939),
 ("Marshall","IL"):(39.3914,-87.6950),("Terre Haute","IN"):(39.4667,-87.4139),
 ("Brazil","IN"):(39.5234,-87.1250),("Greencastle","IN"):(39.6447,-86.8650),
 # I-74 Corridor (QC-Indy) — IL + IN
 ("Peoria","IL"):(40.6936,-89.5890),("Galesburg","IL"):(40.9478,-90.3712),
 ("Normal","IL"):(40.5142,-88.9906),("Bloomington","IL"):(40.4842,-88.9937),
 ("Urbana","IL"):(40.1106,-88.2073),("Champaign","IL"):(40.1164,-88.2434),
 ("Danville","IL"):(40.1245,-87.6300),("Crawfordsville","IN"):(40.0411,-86.8745),
 ("Covington","IN"):(40.1417,-87.3953),
 # Louisville/Evansville corridors (KY/IN/IL)
 ("Louisville","KY"):(38.2527,-85.7585),("New Albany","IN"):(38.2856,-85.8241),
 ("Jeffersonville","IN"):(38.2776,-85.7372),("Bardstown","KY"):(37.8093,-85.4669),
 ("Elizabethtown","KY"):(37.6936,-85.8591),("Seymour","IN"):(38.9592,-85.8902),
 ("Evansville","IN"):(37.9716,-87.5711),("Mt. Vernon","IL"):(38.3173,-88.9031),
 ("Henderson","KY"):(37.8361,-87.5900),("Owensboro","KY"):(37.7742,-87.1133),
 ("Columbus","IN"):(39.2014,-85.9214),("Bowling Green","KY"):(36.9685,-86.4808),
 # I-40/I-49 + KC-Wichita-Tulsa corridors (TN/AR/KS)
 ("Henderson","TN"):(35.4392,-88.6398),("West Memphis","AR"):(35.1465,-90.1845),
 ("Clarksville","AR"):(35.4715,-93.4666),("Russellville","AR"):(35.2784,-93.1338),
 ("Topeka","KS"):(39.0473,-95.6752),("Lawrence","KS"):(38.9717,-95.2353),
 ("Emporia","KS"):(38.4039,-96.1817),("El Dorado","KS"):(37.8170,-96.8625),
 # Franklin/Warren Co. MO (W of STL)
 ("Washington","MO"):(38.5581,-91.0118),("Warrenton","MO"):(38.8114,-91.1418),
 ("Union","MO"):(38.4500,-91.0085),("Sullivan","MO"):(38.2081,-91.1604),
 ("Pacific","MO"):(38.4822,-90.7407),("St. Clair","MO"):(38.3453,-90.9807),
 ("Festus","MO"):(38.2206,-90.3962),("De Soto","MO"):(38.1392,-90.5557),
 ("Hillsboro","MO"):(38.2317,-90.5629),("Arnold","MO"):(38.4326,-90.3773),
 ("Augusta","MO"):(38.5742,-90.8821),("Defiance","MO"):(38.6256,-90.7868),
 ("Marthasville","MO"):(38.6292,-91.0513),("St. Peters","MO"):(38.7875,-90.6298),
 ("Cottleville","MO"):(38.7459,-90.6543),
 ("Clayton","MO"):(38.6426,-90.3237),("Kirkwood","MO"):(38.5834,-90.4068),
 ("Maplewood","MO"):(38.6125,-90.3232),
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
