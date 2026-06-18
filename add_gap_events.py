"""Append interior-gap-fill events to VendingCircuit.csv (idempotent).

2026-06-18 sweep: fill counties WITH events that sit inside the map footprint but
off the highway corridors / outside the metro hubs already covered. Lightweight
capture only (name/city/county/date + brief note); status "Verified - vending
unconfirmed" so each shows on the map with the amber verify badge for later
confirmation. Re-runnable: rows already present (by event_name+city) are skipped.

New towns must also be added to vending_circuit_etl.py CITY_HUB (-> nearest hub)
and vending_circuit_geocode.py C (lat/lng) or they drop out (market_id=0 / no pin).
"""
import csv

SRC = "VendingCircuit.csv"
PASS_DATE = "2026-06-18"
NR = "Not researched"
S = "Verified - vending unconfirmed"

# Each tuple: (event_name, city, state, county, distance_mi, month, typical_dates, notes)
NEW = [
    # ===== Southern Illinois interior =====
    ("Du Quoin State Fair", "Du Quoin", "IL", "Perry", 155, "August", "Aug 28 - Sep 7 (2026)",
     "Illinois' second state fair: agriculture, country music, harness racing, rides & food. Deep-south IL fill."),
    ("Murphysboro Apple Festival", "Murphysboro", "IL", "Jackson", 165, "September", "Sep 9-12 (2026)",
     "S. Illinois' oldest/largest alcohol-free festival (~45k): carnival, car show, apple treats, food. Deep-south IL fill."),
    ("Williamson County Fair", "Marion", "IL", "Williamson", 165, "August", "Aug 1-8 (2026)",
     "County fair, Marion IL: livestock, grandstand, carnival, food. Deep-south IL fill."),
    ("Old King Coal Festival", "West Frankfort", "IL", "Franklin", 160, "May", "May 7-10 (2026)",
     "Downtown West Frankfort heritage festival (85th): live music, food vendors, rides. Deep-south IL fill."),
    ("Union County Fair", "Anna", "IL", "Union", 180, "August", "Aug 21-29 (2026)",
     "County fair, Anna IL: livestock, grandstand (demo derby, rodeo, harness racing), carnival. Deep-south IL fill."),
    ("Centralia Balloon Fest", "Centralia", "IL", "Marion", 130, "August", "Aug 21-23 (2026)",
     "Free hot-air balloon festival at Fairview Park, Centralia: glows, entertainment, family day. S. IL fill."),
    ("Macon County Fair", "Decatur", "IL", "Macon", 150, "June", "Jun 1-7 (2026)",
     "170th county fair, Decatur IL: grandstand, livestock, carnival, food. Central IL fill."),
    ("Decatur Celebration", "Decatur", "IL", "Macon", 150, "August", "Aug 7-9 (2026)",
     "Large downtown Decatur street festival: stages, food vendors, family fun. Central IL fill."),
    ("Morgan County Fair", "Jacksonville", "IL", "Morgan", 115, "July", "Jul 7-12 (2026)",
     "175th county fair, Jacksonville IL: grandstand, rodeo, demo derby, food. Central IL fill."),
    ("Quincy Dogwood Festival", "Quincy", "IL", "Adams", 125, "May", "May 2 (2026)",
     "Dogwood Parade & festival, downtown Quincy on Maine St: parade, family activities, food. W-central IL fill (across river from Hannibal)."),
    ("Adams County Fair", "Mendon", "IL", "Adams", 130, "July", "Jul 29 - Aug 4 (2026)",
     "County fair near Mendon/Quincy IL (Fairfest concerts): livestock, grandstand, food. W-central IL fill."),
    ("Coles County Fair", "Charleston", "IL", "Coles", 175, "July", "Jul 26 - Aug 2 (2026)",
     "Oldest continuous fair in Illinois (est. 1854), Charleston: livestock, grandstand, carnival, food. Central IL fill."),

    # ===== Southern Iowa interior =====
    ("Midwest Old Threshers Reunion", "Mount Pleasant", "IA", "Henry", 230, "September", "Sep 3-7 (2026)",
     "Huge 5-day living-history reunion (~38k), Mount Pleasant: steam engines, antique tractors, crafts; food by local church/civic groups. SE Iowa fill."),
    ("Fort Madison Tri-State Rodeo", "Fort Madison", "IA", "Lee", 240, "September", "Sep 9-12 (2026)",
     "78th Tri-State Rodeo, Fort Madison: PRCA rodeo, food trucks & vendors. SE Iowa fill."),
    ("Burlington Steamboat Days", "Burlington", "IA", "Des Moines", 230, "June", "Mid-June 2026 (riverfront)",
     "Burlington's biggest community event: riverfront music festival, carnival, food. SE Iowa fill."),
    ("Centerville Pancake Day", "Centerville", "IA", "Appanoose", 130, "September", "Sep 26 (2026)",
     "77th Pancake Day on the 'World's Largest Town Square', Centerville: parade, vendors, food. S. Iowa fill."),
    ("Southern Iowa Fair", "Oskaloosa", "IA", "Mahaska", 180, "July", "Jul 13-18 (2026)",
     "Mahaska County fair, Oskaloosa: 4-H, tractor pull, racing, carnival, vendors, fair food. S. Iowa fill."),
    ("Wapello County Fair", "Ottumwa", "IA", "Wapello", 150, "June", "Jun 17-21 (2026)",
     "County fair (grounds in Eldon), Ottumwa area: carnival, harness/stock-car races, livestock, food. S. Iowa fill."),

    # ===== NE Oklahoma (Green Country) interior =====
    ("Muskogee Azalea Festival", "Muskogee", "OK", "Muskogee", 390, "April", "Throughout April (parade Apr 4), 2026",
     "Month-long spring festival at Honor Heights Park, Muskogee: azaleas, parade, vendors, food. NE Oklahoma fill."),
    ("Cherokee National Holiday", "Tahlequah", "OK", "Cherokee", 370, "September", "Sep 4-6 (2026)",
     "Cherokee Nation's 3-day Labor Day celebration, Tahlequah: parade, games, Artisan Marketplace with food & art vendors. NE Oklahoma fill."),
    ("Grove Pelican Festival", "Grove", "OK", "Delaware", 310, "October", "Oct 1-4 (2026)",
     "40th Pelican Festival at Wolf Creek Park on Grand Lake, Grove: carnival, food trucks, arts/crafts, car show. NE Oklahoma fill."),
    ("Okmulgee Pecan Festival", "Okmulgee", "OK", "Okmulgee", 400, "October", "Oct 10-11 (2026)",
     "Okmulgee Pecan Festival: pecan baking contest, street dance, live music, local vendors & food (Chamber vendor app). NE Oklahoma fill."),
    ("Rogers County Fair", "Claremore", "OK", "Rogers", 330, "August", "August 2026 (TBD)",
     "111th Rogers County Free Fair, Claremore Expo Center: carnival, food trucks, fair food, nightly entertainment. NE Oklahoma fill."),

    # ===== North / NE Arkansas (Ozarks) interior =====
    ("Arkansas Bean Fest & Championship Outhouse Races", "Mountain View", "AR", "Stone", 300, "October", "Oct 23-24 (2026)",
     "Quirky court-square festival, Mountain View: bean cook-off, outhouse races, craft & food vendors (Eventeny app). N. Arkansas fill."),
    ("NEA District Fair", "Jonesboro", "AR", "Craighead", 280, "September", "Mid-September 2026 (9 days, TBD)",
     "Northeast Arkansas District Fair, Jonesboro: 9 days of carnival, food, games, entertainment. NE Arkansas fill."),
    ("Loose Caboose Festival", "Paragould", "AR", "Greene", 270, "May", "May 14-16 (2026)",
     "Downtown Paragould festival (26th): vendor market + food court, music (food vendor app w/ electric/water add-ons). NE Arkansas fill."),
    ("Crawdad Days Festival", "Harrison", "AR", "Boone", 250, "May", "Mid-May 2026 (May 7-9)",
     "Crawdad Days at the NW Arkansas District Fairgrounds, Harrison: craft & food vendors, carnival, music, petting zoo. N. Arkansas fill."),
    ("Baxter County Fair", "Mountain Home", "AR", "Baxter", 250, "September", "Sep 15-19 (2026)",
     "Baxter County Fair, Mountain Home: carnival, livestock, commercial booths, food. N. Arkansas fill."),
    ("Independence County Fair", "Batesville", "AR", "Independence", 290, "June", "Jun 5-13 (2026)",
     "105th Independence County Fair, Batesville: discount-ride nights, fair food, family fun. N. Arkansas fill."),

    # ===== West Kentucky interior =====
    ("BBQ on the River", "Paducah", "KY", "McCracken", 230, "September", "Sep 17-19 (2026)",
     "Paducah's riverfront BBQ festival (now run by Paducah Main Street): 100+ BBQ/food/dessert vendors. West KY fill."),
    ("Tater Day", "Benton", "KY", "Marshall", 245, "April", "Apr 3-6 (2026)",
     "Oldest continuous trade day in the US, Benton court square: vendor market, carnival, mule pulls, parade. West KY fill."),
    ("Murray Freedom Fest", "Murray", "KY", "Calloway", 250, "July", "Jul 3-4 (2026)",
     "Murray's July 4th celebration: street fair w/ food, crafts, beer garden, free concert, FNB parade. West KY fill."),
    ("Black Patch Festival", "Princeton", "KY", "Caldwell", 260, "September", "Sep 12 (2026)",
     "Black Patch Heritage Festival, Princeton Main St: games, food, crafts, live music. West KY fill."),
    ("Madisonville 4th Fest", "Madisonville", "KY", "Hopkins", 270, "July", "Jul 3-5 (2026)",
     "Region's largest 3-day outdoor music fest (~40k), free: food trucks, vendors, beer garden. West KY fill."),
    ("Hopkins County Fair", "Madisonville", "KY", "Hopkins", 270, "July", "Jul 31 - Aug 8 (2026)",
     "Hopkins County Fair, Madisonville: livestock, carnival, fair food (taking food-vendor applications). West KY fill."),
]


def trip_type(d):
    d = int(d)
    if d <= 15: return "hometown"
    if d <= 150: return "day_trip"
    return "overnight"


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    fields = list(rows[0].keys())
    have = {(r["event_name"], r["city"]) for r in rows}
    added = 0
    for name, city, st, county, dist, month, dates, notes in NEW:
        if (name, city) in have:
            continue
        row = {k: "" for k in fields}
        row.update(
            event_name=name, city=city, state=st, county=county,
            distance_mi=str(dist), trip_type=trip_type(dist), month=month,
            typical_dates=dates, attendance="", food_vendor_fee=NR,
            application_method="", contact="", url="", status=S, notes=notes,
            last_verified=PASS_DATE,
        )
        rows.append(row)
        have.add((name, city))
        added += 1
    with open(SRC, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"appended {added} new rows; NEW defines {len(NEW)}")


if __name__ == "__main__":
    main()
