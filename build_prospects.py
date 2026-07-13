"""build_prospects.py — turn the 7-run VENDING_PROSPECTS.md research into structured
data/prospects.csv + data/prospect_schedules.csv (same schema as data/events.csv), so the
prospects load into the SAME vending_events table and render on the festival map.

IDs start at 500 (events.csv tops out at 415) so the two datasets never collide, and the
vending-circuit ETL (VendingCircuit.csv -> data/events.csv) never clobbers these.

Re-run any time you edit the PROSPECTS table below:  python build_prospects.py
"""
import csv

# city -> (lat, lng, county, market_id, distance_from_columbia_mi)
CITY = {
    "Fulton":        (38.8467, -91.9479, "Callaway", 1, 26),
    "Moberly":       (39.4184, -92.4382, "Randolph", 1, 33),
    "California":    (38.6303, -92.5666, "Moniteau", 1, 33),
    "Boonville":     (38.9739, -92.7433, "Cooper",   1, 25),
    "Rocheport":     (38.9769, -92.5627, "Boone",    1, 14),
    "Jefferson City":(38.5767, -92.1735, "Cole",     1, 32),
    "Sedalia":       (38.7045, -93.2283, "Pettis",   1, 68),
    "Marthasville":  (38.6295, -91.0499, "Warren",   3, 95),
    "Warrensburg":   (38.7628, -93.7360, "Johnson",  24, 95),
    "Urich":         (38.4589, -94.0002, "Henry",    24, 92),
    "Lee's Summit":  (38.9108, -94.3822, "Jackson",  2, 110),
    "Kansas City":   (39.0997, -94.5786, "Jackson",  2, 125),
    "Kansas City KS":(39.1142, -94.7405, "Wyandotte",2, 135),
    "Osage Beach":   (38.1503, -92.6382, "Camden",   18, 95),
    "Macks Creek":   (37.9439, -92.9691, "Camden",   18, 105),
    "Wheatland":     (37.9484, -93.4066, "Hickory",  4, 120),
    "Springfield":   (37.2090, -93.2923, "Greene",   4, 165),
    "Nixa":          (37.0431, -93.2941, "Christian",4, 175),
    "Ridgedale":     (36.5487, -93.2610, "Taney",    4, 210),
    "Potosi":        (37.7420, -90.8510, "Washington",3, 150),  # Council Bluff Lake / Belleview area
    "Eureka":        (38.5028, -90.6251, "St. Louis",3, 115),
    "Pevely":        (38.2828, -90.3971, "Jefferson",3, 130),
    "Hermann":       (38.7042, -91.4374, "Gasconade",1, 78),
    "Augusta":       (38.5714, -90.8807, "St. Charles",3, 105),
    "Rolla":         (37.9514, -91.7713, "Phelps",   19, 78),
    "Sikeston":      (36.8767, -89.5879, "Scott",    20, 190),
    "Columbia":      (38.9517, -92.3341, "Boone",    1, 0),
}

# name, city, event_type, food_truck_friendly, cadence, verification_status, needs_confirm,
#   month, typical_dates, attendance_text, fee, apply_method, contact, url, notes
P = [
 # ---- Run 4: dirt-track ----
 ("Callaway Raceway","Fulton","dirt_track","unconfirmed","weekly","partial",True,
  "","Weekly race nights, 2026 season","Grandstand crowd (unverified)","","Call track to confirm outside-cart policy","",
  "callawayraceway.com/schedule","CLOSEST dirt track (~25 mi). USRA/POWRi classes. Verify official site + vendor policy (hyphenated 'callaway-raceway.com' is NOT correct)."),
 ("Moberly Motorsports Park","Moberly","dirt_track","unconfirmed","weekly","partial",True,
  "","Weekly dirt oval, 2026 season","(unverified)","","Call to confirm vendor policy","",
  "moberlymotorsportspark.com","fka Randolph County Raceway, 4081 US-24. ~40 min N. Weekly nights; policy unverified."),
 ("Double X Speedway","California","dirt_track","excluded","weekly","excluded",False,
  5,"Sun nights May 3-Aug 2","(unverified)","","","",
  "doublexspeedway.com","COMPETES: track sells its own hot dogs $1.50 / Polish $2.50. Likely blocked for a dog cart."),
 ("Central Missouri Speedway","Warrensburg","dirt_track","unconfirmed","weekly","partial",True,
  "","Weekly Sat series Apr-Sep","(unverified)","","Call to confirm","",
  "","~1.5 hr W. POWRi B-Mods/Super Stocks. Weekly Saturday; policy unverified."),
 ("Lucas Oil Speedway (marquee events)","Wheatland","dirt_track","excluded","annual","partial",True,
  5,"Show-Me 100 May 21-23; Fall Nationals Sep 29-Oct 3","National-event crowds","","Special-event application only (417-282-5984 / lisa@LucasOilSpeedway.com)","417-282-5984",
  "lucasoilspeedway.com","Marquee national venue ~2.5-3 hr. Midway booths are NON-food; concessions in-house. Cart only via special-event app."),
 # ---- Run 5: wineries ----
 ("Rocheport Second Saturdays","Rocheport","festival","explicit_yes","monthly","verified",False,
  "","2nd Sat, Apr-Oct","Town street crowd","","Book via Rocheport Area Merchants Assn (Community Hall, 503 3rd St)","",
  "","BEST open door near home (~20 min). CONFIRMED rotating vendors incl. food trucks."),
 ("Les Bourgeois A-Frame Winegarden","Rocheport","winery","unconfirmed","weekly","partial",True,
  6,"Free Summer Music, Fri 6-9pm, Jun-Aug","Weekly free-admission music crowd","","Confirm cart access (venue serves 'light eats')","",
  "labourgeois.com","Closest winery (~20 min). Recurring Friday crowds; no published food-truck policy - outreach."),
 ("Augusta Harvest Festival","Augusta","winery","explicit_yes","annual","verified",False,
  9,"Sep 19-20, 2026","Town-square festival","booth reservation","Vendor application (Augusta Chamber 636-228-4005)","636-228-4005",
  "","Explicitly welcomes street food + runs a vendor application. ~1.5 hr toward STL."),
 ("Augusta Bottoms Festival","Augusta","winery","explicit_yes","annual","verified",False,
  11,"Nov 7, 2026","Festival crowd","","Greater Augusta Chamber (636-228-4005)","636-228-4005",
  "","Advertises 'Live Music ~ Food Trucks ~ Vendors'. Cart-friendly."),
 ("OakGlenn Vineyards live music","Hermann","winery","unconfirmed","weekly","partial",True,
  "","Live music most Sat/Sun, Apr-Oct","Weekend patio crowd","","Direct outreach","",
  "oakglenn.com","Hermann (~1.5-2 hr). Recurring weekend live music; policy unverified."),
 ("Serenity Valley Winery","California","winery","excluded","recurring","excluded",False,
  "","","","","","",
  "","EXCLUDE: own exclusive kitchen, bans outside food."),
 # ---- Run 6: moto ----
 ("Head's Blacktop Harley-Davidson","Columbia","moto_rally","unconfirmed","weekly","partial",True,
  "","Wed Night Ride & Social (weekly) + Biker Swap Meet (4th Sat)","Rider gatherings","","Call the dealership (5704 Freedom Dr)","",
  "","HOME-CITY recurring, zero travel. Weekly Wed ride + monthly Sat swap meet. Confirm cart access."),
 ("FORR Show Me Rally / Bikers Homecoming","Urich","moto_rally","explicit_yes","annual","verified",False,
  8,"Aug 20-23, 2026","Multi-day camping 'tent city'","","Open vendor application (Freedom of Road Riders Sponsor & Vendor forms)","",
  "forr.info","OPEN application-based vendors + captive overnight crowd shuttled to food. ~1.5 hr."),
 ("Lake of the Ozarks Bikefest","Osage Beach","moto_rally","concession_friendly","annual","partial",True,
  9,"Sep 15-20, 2026 (6 days)","125,000+ riders","Vendor Village booth fee","Contracted Vendor Village - health inspection + $500k liability insurance (info@lakebikefest.com)","",
  "lakebikefest.com","MASSIVE 6-day rally but gated: insurance + health inspection required. Poker runs at Leprechaun's Corner/Shady Gators."),
 ("Santa's Helpers Memorial Toy Run","Sedalia","moto_rally","unconfirmed","annual","partial",True,
  12,"Fall/holiday","Riders gather + eat on-site","","Contact organizer","",
  "","Gathers riders at Yeager's Cycle (3001 S Limit Ave), ~1 hr. Riders eat on-site."),
 # ---- Run 7: fairs (new/close ones; State Fair + Cooper already on map) ----
 ("Moniteau County Fair","California","county_fair","concession_friendly","annual","partial",True,
  8,"Early-mid Aug 2026","County-fair crowd","","Apply-to-vend (no online form - contact fair board)","",
  "","~50 min. Accepts outside vendors; contact board. CHECK carnival-exclusivity clause."),
 # ---- Run 1: MTB/gravel (new ones) ----
 ("NICA #1 - Binder Lake Mini Bash","Jefferson City","mtb_gravel","unconfirmed","annual","partial",True,
  8,"Aug 29-30, 2026","Youth MTB + families, all day","","Confirm vendor policy (missourimtb.org)","",
  "missourimtb.org","CLOSEST NICA (~35 min). Captive all-day family crowd."),
 ("NICA #2 - Escape from the Lion's Den","Rolla","mtb_gravel","unconfirmed","annual","partial",True,
  9,"Sep 12-13, 2026","Youth MTB + families","","Confirm (missourimtb.org)","",
  "missourimtb.org","~1 hr 15. Same weekend as Loki Burnin at the Bluff."),
 ("Loki - The Incinerator","Eureka","mtb_gravel","unconfirmed","annual","partial",True,
  9,"Sep 20, 2026","Enduro/XC field + crews","","Confirm (lokievents.com)","",
  "lokievents.com","Route 66 State Park ~2 hr. Long dwell time."),
 ("The Equalizer 50K/100K (MO gravel champ)","Marthasville","mtb_gravel","concession_friendly","annual","partial",True,
  11,"Nov 7, 2026","Gravel field","","Coordinate/differentiate","",
  "bikesignup.com","~1.5-2 hr, Katy Trail. Already has a burger vendor (KT Caboose) - differentiate."),
 # ---- Run 2: tournaments (new ones) ----
 ("USSSA July Diamond Challenge","Lee's Summit","sports_tournament","unconfirmed","one_time","partial",True,
  7,"Jul 17-19, 2026","59 teams baseball","","Confirm w/ complex","",
  "mobaseball.usssa.com","KC metro ~1.5-2 hr. Big captive field; confirm vendor access."),
 # ---- Run 3: rodeos/car/air (new ones) ----
 ("Show Me State Air Show","Jefferson City","air_show","excluded","annual","partial",True,
  9,"Sep 12-13, 2026","Air-show crowd","","Currently NOT accepting food-vendor apps - ask anyway","",
  "showmestateairshow.org","CLOSEST big event (~35 min) but food-vendor apps reportedly closed. Worth a direct ask."),
 ("American Royal World Series of BBQ","Kansas City KS","bbq_fest","concession_friendly","annual","partial",True,
  9,"Sep 30-Oct 4, 2026","55,000-60,000, open to public","","Apply (americanroyal.com)","",
  "americanroyal.com","One of the world's largest BBQ contests, open to public. ~2.5-3 hr (KS side)."),
 ("Birthplace of Route 66 Festival","Springfield","car_show","concession_friendly","annual","partial",True,
  8,"Aug 7-8, 2026","65,000+ (car + motorcycle show)","","Juried vendor application (route66festivalsgf.com/vendors) - city limiting outside vendors for centennial","",
  "route66festivalsgf.com","~2.5 hr SW. Big but competitive/limited vendor access."),
 ("PBR Outlaw Days","Kansas City","rodeo","unconfirmed","one_time","partial",True,
  10,"Oct 23-25, 2026","Free 3-day street festival","","Confirm street-festival vendor policy","",
  "pbr.com","T-Mobile Center ~2 hr. Anchored by a free street festival crowd."),
 ("Sikeston Jaycee Bootheel Rodeo","Sikeston","rodeo","unconfirmed","annual","partial",True,
  8,"Aug 5-8, 2026","Big regional rodeo","","Confirm w/ Sikeston Jaycees","",
  "sikestonrodeo.com","~3 hr SE (edge of range). Vendor access likely exists; confirm."),
 ("My Car Swap Meet","Sedalia","car_show","explicit_yes","annual","verified",False,
  10,"Oct 16-17, 2026","Swap-meet crowd","$50 preregistered / $60 gate","Simple apply-as-vendor booth","",
  "mycarswapmeet.com","MO State Fairgrounds ~1 hr. EASY low-barrier vendor booths."),
]

EVENT_COLS = ["id","market_id","name","city","state","county","event_type","cadence",
    "is_recurring_venue","food_truck_friendly","trip_type","verification_status","needs_confirmation",
    "distance_from_columbia_mi","month","typical_dates","attendance_estimate","attendance_text",
    "food_vendor_fee","application_method","contact_name","contact_email","contact_phone",
    "homepage_url","primary_source_url","lat","lng","notes","last_verified"]
SCHED_COLS = ["id","event_id","month","start_date","end_date","recurrence_text","display_text","year_specific"]

def trip(d):
    return "hometown" if d <= 45 else ("day_trip" if d <= 150 else "overnight")

erows, srows = [], []
eid = 500
for (name, city, etype, friendly, cadence, verif, needs, month, dates, att, fee, apply, contact, url, notes) in P:
    lat, lng, county, market, dist = CITY[city]
    recurring = cadence in ("weekly","monthly","recurring","year_round")
    erows.append({
        "id": eid, "market_id": market, "name": name, "city": city, "state": "MO",
        "county": county, "event_type": etype, "cadence": cadence,
        "is_recurring_venue": "true" if recurring else "false",
        "food_truck_friendly": friendly, "trip_type": trip(dist),
        "verification_status": verif, "needs_confirmation": "true" if needs else "false",
        "distance_from_columbia_mi": dist, "month": (str(month) if month else ""),
        "typical_dates": dates, "attendance_estimate": "", "attendance_text": att,
        "food_vendor_fee": fee, "application_method": apply,
        "contact_name": "", "contact_email": "", "contact_phone": contact,
        "homepage_url": url, "primary_source_url": url, "lat": lat, "lng": lng,
        "notes": notes, "last_verified": "2026-07-13",
    })
    srows.append({
        "id": eid, "event_id": eid, "month": (str(month) if month else ""),
        "start_date": "", "end_date": "", "recurrence_text": "",
        "display_text": dates, "year_specific": "false",
    })
    eid += 1

with open("data/prospects.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=EVENT_COLS); w.writeheader(); w.writerows(erows)
with open("data/prospect_schedules.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=SCHED_COLS); w.writeheader(); w.writerows(srows)

from collections import Counter
print(f"wrote data/prospects.csv ({len(erows)}) + data/prospect_schedules.csv ({len(srows)})")
print("by event_type:", dict(Counter(r["event_type"] for r in erows)))
print("by food access:", dict(Counter(r["food_truck_friendly"] for r in erows)))
