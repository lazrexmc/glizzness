"""Apply per-event confirmation updates to VendingCircuit.csv (idempotent).

Each record matches an existing row by (event_name, city) and overwrites the
listed fields. Re-runnable: matching is exact and only listed fields change.
Built during the 2026-06-18 confirmation pass (clearing the verify badge on
backfilled lightweight leads where the event + date + vendor path are now known).

Status convention (verif() in vending_circuit_etl.py keys the verify badge on
caveat words in STATUS only):
  "Verified - food trucks"  -> explicit food-truck event   (green dot)
  "Verified - food vendors" -> has food vendors/concessions (green/amber)
  "Verified"                -> real+dated but food fit weak/selective
  (left "...unconfirmed"/"Partial - verify dates" -> stays flagged on purpose)
food_friendly() ALSO keys on notes: keep "weak fit"/"favors local" for amber,
and DON'T leave "confirm"/"verify" in notes of a cleared row.
"""
import csv, sys

SRC = "VendingCircuit.csv"
PASS_DATE = "2026-06-18"

# (event_name, city) -> {field: value}
UPDATES = {
    # ---------- Franklin / Warren Co. (STL hub) ----------
    ("Washington Town & Country Fair", "Washington"): dict(
        month="August", typical_dates="Aug 5-9 (2026)",
        application_method="Concessions committee; fillable PDF app at washmofair.com/merchants",
        contact="concessions@washmofair.com / 636-239-2715", url="washmofair.com",
        status="Verified",
        notes="One of Missouri's largest fairs (grandstand, livestock, midway). Does NOT typically allow outside food vendors; concessions selective (weak fit for trucks). Franklin Co.",
    ),
    ("Art Fair & Winefest", "Washington"): dict(
        month="May", typical_dates="May 15-17 (2026)",
        application_method="Vendor info via Downtown Washington Inc.",
        contact="director@downtownwashmo.org / 636-239-1743", url="downtownwashmo.org",
        status="Verified - food vendors",
        notes="45th yr; historic downtown: 65+ wines, art, live music, food vendors; free admission. Organizer Downtown Washington Inc. Franklin Co.",
    ),
    ("Fall Festival of the Arts & Crafts", "Washington"): dict(
        month="September", typical_dates="Sep 25-27 (2026)",
        application_method="Vendor info via Downtown Washington Inc.",
        contact="director@downtownwashmo.org / 636-239-1743", url="downtownwashmo.org",
        status="Verified - food vendors",
        notes="Downtown Washington arts/crafts festival with a food court all weekend. Organizer Downtown Washington Inc. Franklin Co.",
    ),
    ("Warren County Fair", "Warrenton"): dict(
        month="June", typical_dates="Jun 24-27 (2026)",
        application_method="Vendor/concession info via warrencountyfairgrounds.com or Warren County Fair-MO Facebook",
        contact="warrencountyfairgrounds.com", url="warrencountyfairgrounds.com",
        status="Verified - food vendors",
        notes="Warren County Fairgrounds: livestock, carnival, rodeo, fireworks, food vendors. Warren Co.",
    ),
    ("Franklin County Fair", "Union"): dict(
        month="June", typical_dates="Jun 11-14 (2026)",
        application_method="Vendor application at fcfair.org/vendorapp (also unionfair.org/vendors)",
        contact="Franklinmocountyfair@gmail.com", url="franklincountyfair.org",
        status="Verified - food vendors",
        notes="Franklin County Youth Fair, Union fairgrounds: rides, games, food vendors; 2026 vendor rules/contracts posted. Franklin Co.",
    ),
    ("Meramec Community Fair", "Sullivan"): dict(
        month="June", typical_dates="Late June 2026 (TBD; 2025 was Jun 24-28)",
        application_method="Vendor/concession info via merameccommunityfair.com",
        contact="merameccommunityfair.com", url="merameccommunityfair.com",
        status="Verified - food vendors",
        notes="Sullivan community fair: motocross, livestock, midway, food booths, main stage. Franklin Co.",
    ),
    ("Route 66 BBQ & Bluegrass Festival", "Pacific"): dict(
        month="June", typical_dates="Jun 20-22 (2026)",
        application_method="Food/beverage vendors on Vendor Row (first-come) via City of Pacific",
        contact="636-271-0500", url="pacificmissouri.com",
        status="Verified - food vendors",
        notes="Route 66 BBQ Battle & Bluegrass, Liberty Field, Pacific: sanctioned pro BBQ comp, live music, Kid Zone, Vendor Row. Franklin Co.",
    ),
    ("Pacific Car Show & Block Party", "Pacific"): dict(
        month="June", typical_dates="Jun 27 (2026)",
        application_method="Vendor info via City of Pacific (pacificmo.org/event/pacific-car-show)",
        contact="636-271-0500", url="pacificmo.org",
        status="Verified - food vendors",
        notes="Downtown Pacific car show & block party with food vendors. Franklin Co.",
    ),
    ("St. Clair Pickin' on Picknic Festival", "St. Clair"): dict(
        month="July", typical_dates="Mid-July 2026 (TBD; 2025 was Jul 10-13)",
        application_method="Food & craft vendor info via pickinfestival.com",
        contact="info@pickinfestival.com / 314-270-2233", url="pickinfestival.com",
        status="Verified - food vendors",
        notes="Bluegrass/Americana/folk music festival at Lost Hill Lake, St. Clair: food & craft vendors (cash recommended). Franklin Co.",
    ),

    # ---------- Jefferson Co. (STL hub) ----------
    ("Twin City Days", "Festus"): dict(
        month="September", typical_dates="Sep 12 (2026)",
        application_method="Booth application via Twin City Area Chamber (twincitychamber.com/twin-city-days)",
        contact="636-931-7697", url="twincitychamber.com",
        status="Verified",
        notes="Festus/Crystal City Chamber craft fair, Sep, 9a-3p; primarily craft booths ($50 10x10 early-bird). Food-vendor fit limited (weak fit). Jefferson Co.",
    ),
    ("Festus Art & Music Festival", "Festus"): dict(
        month="May", typical_dates="May 2-3 (2026)",
        application_method="Vendor info via Festus Main Street",
        contact="festusmainstreet.org", url="festusmainstreet.org",
        status="Verified - food trucks",
        notes="Downtown Festus art & music fest (now 2 days): food trucks welcome + Main St food court tent, pub crawl, live music. Jefferson Co.",
    ),
    ("De Soto Fall Festival", "De Soto"): dict(
        month="September", typical_dates="Sep 19 (2026)",
        application_method="Vendor info via De Soto Chamber (desotomochamber.com/event/fall-festival)",
        contact="desotomochamber.com", url="desotomochamber.com",
        status="Verified - food vendors",
        notes="35th annual De Soto Main St fest: ~100 exhibitors, 10 food booths, activities; 9a-4p. Jefferson Co.",
    ),
    ("Fountain City Jazz Fest", "De Soto"): dict(
        month="March", typical_dates="Late March 2026 (HS jazz competition)",
        application_method="Via De Soto School District band program",
        contact="desotobands.weebly.com", url="",
        status="Verified",
        notes="Indoor high-school jazz competition at De Soto HS auditorium (16 schools); free daytime, ticketed finale. Not a food-vending venue (poor fit). Jefferson Co.",
    ),
    ("Jefferson County Fair", "Hillsboro"): dict(
        month="July", typical_dates="Mid-July 2026 (TBD; 2025 was Jul 17-20)",
        application_method="Vendor applications via jeffersoncountyfair.net",
        contact="636-797-3900", url="jeffersoncountyfair.net",
        status="Verified - food vendors",
        notes="4-day county fair at Jefferson County Fairgrounds, Hillsboro: rodeo, carnival, food vendors; vendor apps open. Jefferson Co.",
    ),
    ("Arnold Days", "Arnold"): dict(
        month="September", typical_dates="Late September 2026 (TBD; 2025 was Sep 20-22)",
        application_method="Food vendor application (PDF) via City of Arnold (arnoldmo.org)",
        contact="636-282-2380", url="arnoldmo.org",
        status="Verified - food vendors",
        notes="Arnold City Park (since 1973): parade, music, concessions, crafts, rides, car show, fireworks. Jefferson Co.",
    ),

    # ---------- St. Charles Co. / wine country (STL hub) ----------
    ("Augusta Wine & Jazz Festival", "Augusta"): dict(
        month="June", typical_dates="Jun 5-7 (2026)",
        application_method="Vendor info via Town of Augusta / Harmonie Verein (theharmonie.org/jazzfest)",
        contact="townofaugustamo.org", url="townofaugustamo.org",
        status="Verified - food vendors",
        notes="4th annual Augusta wine-country jazz fest: stages, wineries, food (wine/music-leaning). St. Charles Co.",
    ),
    ("Defiance St. Patrick's Day Festival", "Defiance"): dict(
        month="March", typical_dates="Mar 14 (2026)",
        application_method="Vendor info via Defiance MO (defiancemo.com/events)",
        contact="defiancemo.com", url="defiancemo.com",
        status="Verified - food trucks",
        notes="6th annual: Katy Trail 5K, parade at noon, food trucks, drink tents, vendors, live music at wineries/breweries. St. Charles Co.",
    ),
    ("Deutsch Country Days", "Marthasville"): dict(
        month="October", typical_dates="Mid-October 2026 (TBD; typically 3rd weekend)",
        application_method="Via deutschcountrydays.org",
        contact="deutschcountrydays.org", url="deutschcountrydays.org",
        status="Verified - vending unconfirmed",
        notes="German living-history festival at Luxenhaus Farm: 100+ crafts/demos; food run by a Boy Scout stand (outside food vendors not typical, weak fit). 2026 occurrence not yet confirmed online. St. Charles Co.",
    ),
    ("St. Charles Oktoberfest", "St. Charles"): dict(
        month="September", typical_dates="Sep 25-27 (2026)",
        application_method="Vendor application via saintcharlesoktoberfest.com (Eventeny)",
        contact="saintcharlesoktoberfest.com", url="saintcharlesoktoberfest.com",
        status="Verified - food vendors",
        notes="40th yr; Frontier Park, ~150k guests: brats, funnel cakes, oompah bands; actively seeks food vendors. St. Charles Co.",
    ),
    ("St. Charles Riverfest", "St. Charles"): dict(
        month="July", typical_dates="Jul 3-4 (2026)",
        application_method="Vendor application packet via stcharlescitymo.gov (Riverfest Vendor Application)",
        contact="stcharlescitymo.gov", url="stcharlescitymo.gov",
        status="Verified - food vendors",
        notes="Frontier Park: live music, carnival, food vendors, drone show, fireworks; booths first-come, health-dept compliance required. St. Charles Co.",
    ),
    ("St. Charles Christmas Traditions", "St. Charles"): dict(
        month="December", typical_dates="Fri-Sun, Nov 27 - Dec 24 (2026)",
        application_method="Vendor info via discoverstcharles.com / City of St. Charles",
        contact="discoverstcharles.com", url="discoverstcharles.com",
        status="Verified - food vendors",
        notes="Month-long historic Main St holiday festival: strolling characters, food vendors, roasted chestnuts & wassail. St. Charles Co.",
    ),
    ("One World Fest", "St. Peters"): dict(
        month="August", typical_dates="Aug 22-23 (2026)",
        application_method="Vendor application via One World Fest (facebook.com/1WorldFest / Eventbrite)",
        contact="facebook.com/1WorldFest", url="facebook.com/1WorldFest",
        status="Verified - food vendors",
        notes="Free multicultural festival at Mid Rivers Mall, St. Peters: international food, music, art, fashion. St. Charles Co.",
    ),
    ("Cottleville Irish Fest", "Cottleville"): dict(
        month="March", typical_dates="Mar 14 (2026)",
        application_method="Vendor info via City of Cottleville / Cottle Village (cottlevillage.com)",
        contact="cityofcottleville.com", url="cityofcottleville.com",
        status="Verified - food vendors",
        notes="Shamrock Run & Irish Fest in Old Town Cottleville, 11a-8p: curated food vendors (BBQ, tacos, brats), Irish dishes, live music. St. Charles Co.",
    ),
    ("O'Fallon Heritage & Freedom Fest", "O'Fallon"): dict(
        month="July", typical_dates="Jul 1-4 (2026)",
        application_method="Vendor applications via ofallon.mo.us/vendor-applications (coordinator books from January; food vendors need St. Charles Co. TFF license)",
        contact="jchwascinski@ofallonmo.gov / 636-379-5502", url="heritageandfreedomfest.com",
        status="Verified - food vendors",
        notes="Big July 4th fest at Ozzie Smith Complex, O'Fallon: carnival, food vendors, fireworks. St. Charles Co.",
    ),
    ("St. Charles County Fair", "Wentzville"): dict(
        month="July", typical_dates="Jul 23-27 (2026)",
        application_method="Vendor info via stcharlescofair.org or St. Charles County Fair Facebook",
        contact="stcharlescofair.org", url="stcharlescofair.org",
        status="Verified - food vendors",
        notes="5-day fair at Rotary Park, Wentzville (4th week of July): carnival, rodeo, demo derby, food vendors. St. Charles Co.",
    ),

    # ---------- St. Louis City / metro core (STL hub) ----------
    ("Soulard Mardi Gras", "St. Louis"): dict(
        month="February", typical_dates="Grand Parade Feb 14 (2026); season Jan-Feb",
        application_method="Food vendor application (PDF) via stlmardigras.org/vendor-information",
        contact="stlmardigras.org", url="stlmardigras.org",
        status="Verified - food vendors",
        notes="Large Soulard celebration: Bud Light Grand Parade, Taste of Soulard, Pet Parade, food/drink vendors. St. Louis City.",
    ),
    ("Soulard Oktoberfest", "St. Louis"): dict(
        month="October", typical_dates="Oct 9-10 (2026)",
        application_method="Vendor info via soulard-oktoberfest.com/contacts",
        contact="soulard-oktoberfest.com", url="soulard-oktoberfest.com",
        status="Verified - food vendors",
        notes="Soulard Market Park: German food, beer, polka/brass bands. St. Louis City.",
    ),
    ("Festival of Nations", "St. Louis"): dict(
        month="August", typical_dates="Aug 29-30 (2026)",
        application_method="Food + Beverage vendor application via festofnations.com/food-bev (national-cuisine focus)",
        contact="festofnations.com", url="festofnations.com",
        status="Verified - food vendors",
        notes="Tower Grove Park: 80+ countries, 100+ international food/market vendors, music, dance (large). National-cuisine theme. St. Louis City.",
    ),
    ("Japanese Festival", "St. Louis"): dict(
        month="September", typical_dates="Sep 5-7 (2026)",
        application_method="Via Missouri Botanical Garden / Japan America Society of St. Louis",
        contact="missouribotanicalgarden.org", url="missouribotanicalgarden.org",
        status="Verified",
        notes="Missouri Botanical Garden signature festival (40+ yrs); food run by Japanese Activities Committee orgs, outside food vendors not typical (weak fit). St. Louis City.",
    ),
    ("Italian Heritage Parade & Festa", "St. Louis"): dict(
        month="October", typical_dates="Oct 11 (2026)",
        application_method="Vendor info via The Hill STL (hillstl.org)",
        contact="hillstl.org", url="hillstl.org",
        status="Verified - food vendors",
        notes="On The Hill: parade + Festa at Berra Park with local food & beverage vendors, music. St. Louis City.",
    ),
    ("Taste of St. Louis", "Clayton"): dict(
        month="August", typical_dates="Aug 14-16 (2026)",
        application_method="Vendor info via thetastestl.com",
        contact="thetastestl.com", url="thetastestl.com",
        status="Verified - food vendors",
        notes="Downtown Clayton: local eats, chef demos, artisan market, music; 2026 return announced (turnout-driven future uncertainty). St. Louis metro.",
    ),
    ("Saint Louis Art Fair", "Clayton"): dict(
        month="September", typical_dates="Sep 18-20 (2026)",
        application_method="Food vendor & food truck applications via saintlouisartfair.com (apply early; spaces fill up)",
        contact="saintlouisartfair.com", url="saintlouisartfair.com",
        status="Verified - food trucks",
        notes="Major juried art fair, downtown Clayton; food vendor booths + food truck spaces, food trucks welcome (apply early). St. Louis metro.",
    ),
    ("St. Louis Street Food Festival", "St. Louis"): dict(
        month="August", typical_dates="Late August 2026 (TBD; 2025 was Aug 23)",
        application_method="Food vendor application via streetfoodfests.com/event/stlouis",
        contact="streetfoodfests.com", url="streetfoodfests.com",
        status="Verified - food trucks",
        notes="Ballpark Village: 20+ food trucks & restaurants, items $5 or less, live entertainment; food trucks welcome. St. Louis City.",
    ),
    ("Grove Fest", "St. Louis"): dict(
        month="October", typical_dates="Early October 2026 (TBD; 2025 was Oct 4)",
        application_method="Vendor application via stlgrovefest.com/vendor-application",
        contact="stlgrovefest.com", url="stlgrovefest.com",
        status="Verified - food vendors",
        notes="The Grove neighborhood street festival: live music, food vendors. St. Louis City.",
    ),
    ("Greentree Festival", "Kirkwood"): dict(
        month="September", typical_dates="Sep 18-20 (2026)",
        application_method="Food Booth Application via kirkwoodmo.org (deadline ~June 15)",
        contact="henkekk@kirkwoodmo.org / 314-822-5855", url="kirkwoodmo.org",
        status="Verified - food vendors",
        notes="Kirkwood Park: parade, live music, family activities, food booths. St. Louis metro.",
    ),
    ("Let Them Eat Art", "Maplewood"): dict(
        month="July", typical_dates="Jul 10 (2026)",
        application_method="Via City of Maplewood (maplewoodmo.gov)",
        contact="maplewoodmo.gov", url="maplewoodmo.gov",
        status="Verified",
        notes="Downtown Maplewood Bastille-Day art night: 60+ artists, live music; food & drink sold by Maplewood restaurants (limited outside food-vendor fit, weak fit). St. Louis metro.",
    ),
}


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    fields = rows[0].keys()
    applied, missing = 0, []
    seen = set()
    for r in rows:
        key = (r["event_name"], r["city"])
        if key in UPDATES:
            for k, v in UPDATES[key].items():
                r[k] = v
            r["last_verified"] = PASS_DATE
            applied += 1
            seen.add(key)
    for key in UPDATES:
        if key not in seen:
            missing.append(key)
    with open(SRC, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        w.writeheader()
        w.writerows(rows)
    print(f"applied updates to {applied} rows; {len(UPDATES)} records defined")
    if missing:
        print("UNMATCHED records (check name/city):")
        for m in missing:
            print("   -", m)


if __name__ == "__main__":
    main()
