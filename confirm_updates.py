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

    # ---------- Columbia / Mid-Missouri (hub 1) ----------
    ("True/False Film Fest", "Columbia"): dict(
        month="March", typical_dates="Mar 5-8 (2026)",
        application_method="Via truefalse.org",
        contact="truefalse.org", url="truefalse.org",
        status="Verified",
        notes="Documentary film festival; downtown street parties carry some food trucks but it is ticketed-film-centric (weak fit for vending). Boone Co.",
    ),
    ("Art in the Park", "Columbia"): dict(
        month="June", typical_dates="Jun 6-7 (2026)",
        food_vendor_fee="$700/weekend + city temp license",
        application_method="Food vendor application via columbiaartleague.org/artinthepark/participate (deadline ~Mar 6)",
        contact="columbiaartleague.org", url="columbiaartleague.org",
        status="Verified - food trucks",
        notes="Columbia Art League art fair at Stephens Lake Park; food trucks & food tents welcome. Boone Co.",
    ),
    ("Heritage Festival & Craft Show", "Columbia"): dict(
        month="September", typical_dates="Sep 19-20 (2026)",
        application_method="Vendor info via Columbia Parks & Rec (como.gov)",
        contact="573-874-7475", url="como.gov",
        status="Verified - food trucks",
        notes="Nifong Park heritage festival: crafts, music, living history, local food trucks. Boone Co.",
    ),
    ("Kingdom of Callaway Fair", "Fulton"): dict(
        month="July", typical_dates="Late July 2026 (TBD)",
        application_method="Vendor info via Kingdom of Callaway Fair (Facebook) / Callaway Chamber",
        contact="callawaychamber.net", url="callawaycountyfairfultonmo.com",
        status="Verified - food vendors",
        notes="Callaway County fair, Fulton: carnival, demo derby, tractor pulls, music, BBQ mutton & food vendors. Callaway Co.",
    ),
    ("Pedaler's Jamboree", "Boonville"): dict(
        month="May", typical_dates="May 23-24 (2026)",
        application_method="Vendor application via pedalersjamboree.com/vendors",
        contact="pedalersjamboree.com", url="pedalersjamboree.com",
        status="Verified - food trucks",
        notes="Memorial Day rolling music festival on the Katy Trail (Boonville/Columbia); multiple food trucks, vendor apps open. Cooper Co.",
    ),
    ("Big Muddy Folk Festival", "Boonville"): dict(
        month="April", typical_dates="Apr 10-11 (2026)",
        application_method="Via bigmuddy.org / Friends of Historic Boonville",
        contact="bigmuddy.org", url="bigmuddy.org",
        status="Verified",
        notes="Indoor folk-music festival at Thespian Hall, Boonville (34th yr): concerts, workshops, dance & BBQ; outside food vendors not typical (weak fit). Cooper Co.",
    ),
    ("Taste of Osage County", "Linn"): dict(
        month="September", typical_dates="Sep 12 (2026)",
        application_method="Via Naturally Meramec / Osage County (naturallymeramec.org)",
        contact="naturallymeramec.org", url="naturallymeramec.org",
        status="Verified - food vendors",
        notes="Linn City Park: local food producers, vendors, live music, 4-H activities. Osage Co.",
    ),
    ("Hatton Craft Fair", "Auxvasse"): dict(
        month="October", typical_dates="Oct 3 (2026)",
        application_method="Via Hatton Craft Day (Facebook) / Hatton Extension Club",
        contact="facebook.com/Hatton-Craft-Day", url="facebook.com/Hatton-Craft-Day",
        status="Verified",
        notes="51st+ annual rural craft fair (180 booths) with 7 community-run food booths; first Saturday of October; limited outside food-vendor fit (weak fit). Callaway Co.",
    ),
    ("Scott Joplin International Ragtime Festival", "Sedalia"): dict(
        month="May", typical_dates="May 27-30 (2026)",
        application_method="Food-truck vendor interest form via scottjoplin.org",
        contact="scottjoplin.org", url="scottjoplin.org",
        status="Verified - food trucks",
        notes="Ragtime music festival, Historic Downtown Sedalia; food-truck vendor interest form posted. Pettis Co.",
    ),
    ("Living Windows Festival", "Columbia"): dict(
        month="December", typical_dates="First Friday Dec (Dec 4, 2026), 6-8pm",
        application_method="Via The District (discoverthedistrict.com)",
        contact="discoverthedistrict.com", url="discoverthedistrict.com",
        status="Verified",
        notes="Downtown Columbia (The District) 2-hr holiday evening: living window displays, open houses, shopping; limited food vending (weak fit). Boone Co.",
    ),
    ("Walk Back in Time", "Mexico"): dict(
        month="September", typical_dates="Last full weekend September (biennial; verify 2026 occurrence)",
        application_method="Food vendor: contact Janice 573-581-3910 before applying (limited space) - Audrain County Historical Society",
        contact="573-581-3910", url="audrain.org",
        status="Verified - vending unconfirmed",
        notes="Living-history reenactment festival at Audrain County Historical Museum, Mexico: many food vendors (limited space). Biennial - sources conflict on odd/even years, so 2026 occurrence unconfirmed. Audrain Co.",
    ),

    # ---------- Kansas City Metro (hub 2) ----------
    ("Kansas City Irish Fest", "Kansas City"): dict(
        month="September", typical_dates="Sep 4-6 (2026)",
        application_method="Food vendor application via kcirishfest.com/vendor-applications (Eventeny; selective; KC health permit, no beverage sales)",
        contact="kcirishfest.com", url="kcirishfest.com",
        status="Verified - food vendors",
        notes="Crown Center & Washington Square Park: large Irish festival, food vendors (compostable supplies required). Jackson Co.",
    ),
    ("Ethnic Enrichment Festival", "Kansas City"): dict(
        month="August", typical_dates="Aug 21-23 (2026)",
        application_method="Vendor application via eeckc.org (Eventeny)",
        contact="eeckc.org", url="eeckc.org",
        status="Verified - food vendors",
        notes="Swope Park: one of KC's largest multicultural festivals (47th yr), international food booths. Jackson Co.",
    ),
    ("Snake Saturday Parade & Festival", "North Kansas City"): dict(
        month="March", typical_dates="Mar 14 (2026)",
        application_method="Vendor info via snakesaturday.com/festival",
        contact="snakesaturday.com", url="snakesaturday.com",
        status="Verified - food vendors",
        notes="North KC St. Patrick's parade & festival: ~20 vendors + food court (funnel cake, sausage, etc.). Clay Co.",
    ),
    ("Liberty Fall Fest", "Liberty"): dict(
        month="September", typical_dates="Sep 25-27 (2026)",
        application_method="Food vendor application via Eventeny (Liberty Fall Festival 26) / City of Liberty",
        contact="libertyfallfest.com", url="libertyfallfest.com",
        status="Verified - food vendors",
        notes="Historic Downtown Liberty: food vendors, farmers market, family activities. Clay Co.",
    ),
    ("Overland Park Fall Festival", "Overland Park"): dict(
        month="September", typical_dates="Sep 25-26 (2026)",
        application_method="Vendor info via opkansas.org / Arts & Rec Foundation of Overland Park",
        contact="opkansas.org", url="opkansas.org",
        status="Verified - food trucks",
        notes="Downtown Overland Park: artists, food trucks & local restaurants, farmers market. Johnson Co. KS.",
    ),
    ("Brookside Art Annual", "Kansas City"): dict(
        month="May", typical_dates="May 1-3 (2026)",
        application_method="Vendor info via brooksideartannual.com",
        contact="brooksideartannual.com", url="brooksideartannual.com",
        status="Verified - food vendors",
        notes="40th Brookside Art Annual: 170+ juried artists; food booths (local restaurants). Jackson Co.",
    ),
    ("Kansas City Renaissance Festival", "Bonner Springs"): dict(
        month="September", typical_dates="Weekends Sep 5 - Oct 18 (2026)",
        application_method="Vendor application + Craft Coordinator agreement via kcrenfest.com (913-721-2110)",
        contact="913-721-2110", url="kcrenfest.com",
        status="Verified - food vendors",
        notes="Renaissance festival, Bonner Springs: 7 weekends; food & artisan vendors (full-season commitment). Wyandotte Co. KS.",
    ),
    ("Lawrence Busker Festival", "Lawrence"): dict(
        month="May", typical_dates="May 22-24 (2026)",
        application_method="Food vendor application via lawrencebuskerfest.com/vendor1 (Eventeny)",
        contact="lawrencebuskerfest.com", url="lawrencebuskerfest.com",
        status="Verified - food vendors",
        notes="Downtown Lawrence street-performer festival (Memorial Day weekend): food vendors of all kinds. Douglas Co. KS.",
    ),
    ("Gladstone Summertime Bluesfest", "Gladstone"): dict(
        month="May", typical_dates="May 15-16 (2026)",
        application_method="Vendor info via Gladstone Chamber (gladstonechamber.com/bluesfest)",
        contact="gladstonechamber.com", url="gladstonechamber.com",
        status="Verified - food vendors",
        notes="Blues festival at Linden Square, Gladstone: live blues, food vendors (brats, hot dogs, nachos). Clay Co.",
    ),

    # ---------- Lake of the Ozarks (hub 18) ----------
    ("Magic Dragon Street Meet", "Lake Ozark"): dict(
        month="May", typical_dates="May 1-2 (2026)",
        application_method="Vendor info via magicdragoncarshow.com / Lake Area Chamber",
        contact="magicdragoncarshow.com", url="magicdragoncarshow.com",
        status="Verified - food vendors",
        notes="36th annual classic-car street meet on the Bagnell Dam Strip, Lake Ozark: food vendors, shopping. Miller Co.",
    ),
    ("Lake of the Ozarks Shootout", "Osage Beach"): dict(
        month="August", typical_dates="Aug 29-30 (2026); street party Aug 26",
        application_method="Vendor info via lakeoftheozarksshootout.com",
        contact="lakeoftheozarksshootout.com", url="lakeoftheozarksshootout.com",
        status="Verified - food vendors",
        notes="Largest unsanctioned lake boat race; race days + Bagnell Dam Strip street party draw local food vendors. Camden Co.",
    ),
    ("Lake of the Ozarks Bikefest", "Osage Beach"): dict(
        month="September", typical_dates="Sep 15-20 (2026)",
        application_method="Vendor info via lakebikefest.com",
        contact="lakebikefest.com", url="lakebikefest.com",
        status="Verified - food vendors",
        notes="6-day biker rally, Bagnell Dam Strip: 300+ bars/restaurants, vendor villages (outside food-vendor fit moderate). Camden Co.",
    ),
    ("Cole Camp Oktoberfest", "Cole Camp"): dict(
        month="September", typical_dates="Sep 26 (2026)",
        application_method="Vendor info via Cole Camp (colecampmo.com); 660-668-2295 / lstelling@citizensfarmersbank.com",
        contact="660-668-2295", url="colecampmo.com",
        status="Verified - food vendors",
        notes="Cole Camp German Oktoberfest: brats, kraut, craft & food booths. Benton Co.",
    ),
    ("Fall Harbor Hop", "Sunrise Beach"): dict(
        month="October", typical_dates="Oct 10 (2026)",
        application_method="Via funlake.com / Lake Area Chamber",
        contact="funlake.com", url="funlake.com",
        status="Verified",
        notes="On-water poker run; checkpoints are 40+ waterfront restaurants/bars/marinas that serve their own food - no central food-vendor space (poor fit). Camden Co.",
    ),

    # ---------- SE / South-Central MO singletons (hubs 19, 20, 21) ----------
    ("MoRoots Music Festival", "Steelville"): dict(
        month="September", typical_dates="Sep 24-26 (2026)",
        application_method="Vendor info via MoRoots (Facebook) / Bass River Resort 573-786-8517",
        contact="573-786-8517", url="naturallymeramec.org",
        status="Verified - food vendors",
        notes="Roots/Americana camping music festival at Bass River Resort, Steelville: food vendors on site. Crawford Co.",
    ),
    ("Downtown Sikeston Wine Festival", "Sikeston"): dict(
        month="September", typical_dates="Early September 2026 (Saturday, TBD)",
        application_method="Vendor application via downtownsikeston.org/become-a-vendor (573-380-3801)",
        contact="573-380-3801", url="downtownsikeston.org",
        status="Verified - food trucks",
        notes="Historic Downtown Sikeston wine festival (15th+ yr): wineries + food trucks on site. Scott Co.",
    ),
    ("Ozark Mountain Festival", "Eminence"): dict(
        month="May", typical_dates="May 2026 (TBD; ~May 1)",
        application_method="Vendor info via Eminence Chamber / Area Arts Council (visiteminence.com)",
        contact="visiteminence.com", url="visiteminence.com",
        status="Verified - food vendors",
        notes="Eminence community festival: demos, car show & drag races, food & craft vendors. Shannon Co.",
    ),

    # ---------- Bootheel (hub 25) ----------
    ("Campbell Peach Fair", "Campbell"): dict(
        month="August", typical_dates="Mid-to-late August 2026 (TBD; 10-day fair)",
        application_method="Vendor info via Mo Peach Fair (Facebook) / Downtown Campbell",
        contact="downtowncampbell.com", url="downtowncampbell.com",
        status="Verified - food vendors",
        notes="Missouri Peach Fair, Campbell (10-day): food, pageants, games, peaches. Dunklin Co.",
    ),
    ("Clarkton Purple Hull Pea Festival", "Clarkton"): dict(
        month="August", typical_dates="Late August (verify 2026 occurrence)",
        application_method="Via City of Clarkton / festival Facebook",
        contact="", url="",
        status="Verified - vending unconfirmed",
        notes="Small-town festival at Ernie Woodall Memorial Park, Clarkton; 2026 occurrence/date unconfirmed (limited recent info). Dunklin Co.",
    ),

    # ---------- Indianapolis Metro (hub 27) ----------
    ("Indiana State Fair", "Indianapolis"): dict(
        month="August", typical_dates="Aug 7-23 (2026)",
        application_method="Concessionaire application via indianastatefair.com/vendor-information (entry@indianastatefair.com / 317-927-7515)",
        contact="entry@indianastatefair.com / 317-927-7515", url="indianastatefair.com",
        status="Verified - food vendors",
        notes="Indiana State Fair, Indianapolis: outside concessionaires permitted via application. Marion Co. IN.",
    ),
    ("Indiana Black Expo Summer Celebration", "Indianapolis"): dict(
        month="July", typical_dates="Jul 9-19 (2026)",
        application_method="Vendor registration via indianablackexpo.com / summercelebration.net (early-bird deadline Feb 28)",
        contact="indianablackexpo.com", url="indianablackexpo.com",
        status="Verified - food vendors",
        notes="Indiana Black Expo Summer Celebration, Indianapolis: 300+ vendors incl. food. Marion Co. IN.",
    ),
    ("Talbot Street Art Fair", "Indianapolis"): dict(
        month="June", typical_dates="Jun 20-21 (2026)",
        application_method="Vendor info via talbotstreet.org",
        contact="talbotstreet.org", url="talbotstreet.org",
        status="Verified - food vendors",
        notes="69th Talbot St art fair, Indianapolis: artists + diverse food vendors (tacos, wood-fired pizza, kettle corn). Marion Co. IN.",
    ),
    ("500 Festival Parade", "Indianapolis"): dict(
        month="May", typical_dates="May 23 (2026)",
        application_method="Vendor info via 500festival.com/parade",
        contact="500festival.com", url="500festival.com",
        status="Verified - food vendors",
        notes="Indy 500 Festival Parade, downtown Indianapolis: food trucks/vendors along the route. Marion Co. IN.",
    ),
    ("CarmelFest", "Carmel"): dict(
        month="July", typical_dates="Jul 3-4 (2026)",
        application_method="Food vendor application via carmelfest.net (Eventeny; deadline May 31)",
        contact="carmelfest.net", url="carmelfest.net",
        status="Verified - food vendors",
        notes="CarmelFest July 4th celebration, Carmel Civic Square: food vendors, marketplace, parade, fireworks. Hamilton Co. IN.",
    ),
    ("Carmel International Arts Festival", "Carmel"): dict(
        month="September", typical_dates="Sep 26-27 (2026)",
        application_method="Vendor application via carmelartsfestival.org/vendors",
        contact="carmelartsfestival.org", url="carmelartsfestival.org",
        status="Verified - food vendors",
        notes="Carmel Arts Festival, Main St & Rangeline Rd: food & beverage trucks + food tents. Hamilton Co. IN.",
    ),
    ("Penrod Arts Fair", "Indianapolis"): dict(
        month="September", typical_dates="Sep 12 (2026)",
        application_method="Vendor info via penrod.org / Newfields",
        contact="penrod.org", url="penrod.org",
        status="Verified - food vendors",
        notes="Penrod Arts Fair at Newfields, Indianapolis (59th): 350+ artists, dozens of food/beverage vendors, beer garden. Marion Co. IN.",
    ),
    ("Fountain Square Art Festival", "Indianapolis"): dict(
        month="April", typical_dates="Apr 18 (2026)",
        application_method="Via Fountain Fletcher District Assn (fountainfletcher.com)",
        contact="fountainfletcher.com", url="fountainfletcher.com",
        status="Verified",
        notes="Art festival at Fountain Square Park, Indianapolis: artists, music; food-vendor presence not confirmed (weak fit). Marion Co. IN.",
    ),
    ("Indiana Peony Festival", "Noblesville"): dict(
        month="May", typical_dates="May 16 (2026)",
        application_method="Vendor info via indianapeonyfestival.com/festival",
        contact="indianapeonyfestival.com", url="indianapeonyfestival.com",
        status="Verified - food vendors",
        notes="Downtown Noblesville peony festival: 30+ food vendors & trucks, shopping, family fun. Hamilton Co. IN.",
    ),
    ("HATCH Fest", "Noblesville"): dict(
        month="June", typical_dates="Jun 14 (2026)",
        application_method="Vendor info via Noblesville Creates (noblesvillecreates.org/hatchfest)",
        contact="noblesvillecreates.org", url="noblesvillecreates.org",
        status="Verified - food vendors",
        notes="HATCH Fest + St. Michael's Strawberry Festival, Noblesville Square: makers market, strawberry shortcake, live music. Hamilton Co. IN.",
    ),
    ("Riley Festival", "Greenfield"): dict(
        month="October", typical_dates="Oct 1-4 (2026)",
        application_method="Food vendor forms via rileyfestival.com (317-462-2141 / jwrileyfestival@outlook.com)",
        contact="317-462-2141 / jwrileyfestival@outlook.com", url="rileyfestival.com",
        status="Verified - food vendors",
        notes="James Whitcomb Riley Festival, Greenfield: 400+ arts/crafts/food vendors. Hancock Co. IN.",
    ),
    ("Ethnic Expo", "Columbus"): dict(
        month="October", typical_dates="Oct 9-10 (2026)",
        application_method="Food vendor application via ethnicexpo.org/vendor-information",
        contact="ethnicexpo.org", url="ethnicexpo.org",
        status="Verified - food vendors",
        notes="Ethnic Expo, downtown Columbus IN: international food & culture festival. Bartholomew Co. IN.",
    ),
    ("Our Lady of the Greenwood Parish Festival", "Greenwood"): dict(
        month="June", typical_dates="Jun 4-6 (2026)",
        application_method="Via olgreenwood.org (317-888-2861)",
        contact="317-888-2861", url="olgreenwood.org",
        status="Verified",
        notes="Catholic parish summer festival, Greenwood: parish-run food booths, beer tent, rides, music; outside food-vendor fit weak. Johnson Co. IN.",
    ),
    ("Plainfield Quaker Day Festival", "Plainfield"): dict(
        month="September", typical_dates="Sep 17-20 (2026)",
        application_method="Vendor info via quakerdayfestival.org / Town of Plainfield",
        contact="quakerdayfestival.org", url="quakerdayfestival.org",
        status="Verified - food trucks",
        notes="Plainfield Quaker Day Festival: craft fair (100+ booths), parade, food trucks from central Indiana. Hendricks Co. IN.",
    ),

    # ---------- I-70 Corridor (hub 28) ----------
    ("Moccasin Creek Festival", "Effingham"): dict(
        month="June", typical_dates="Jun 18-21 (2026)",
        application_method="Vendor application via moccasincreekfestival.com (possmusicworks@gmail.com)",
        contact="possmusicworks@gmail.com", url="moccasincreekfestival.com",
        status="Verified - food vendors",
        notes="4-day Americana music festival at Lake Sara, Effingham: food & beverage vendors on site. Effingham Co. IL.",
    ),
    ("Casey Popcorn Festival", "Casey"): dict(
        month="September", typical_dates="Sep 4-7 (2026)",
        application_method="Vendor info via popcornfestival.net",
        contact="popcornfestival.net", url="popcornfestival.net",
        status="Verified - food vendors",
        notes="Casey Popcorn Festival, Fairview Park: carnival, crafts, food vendors, grandstand concerts. Clark Co. IL.",
    ),
    ("Fayette County Fair", "Vandalia"): dict(
        month="July", typical_dates="Jul 9-14 (2026)",
        application_method="Vendor info via fayettecofair.org / fayettefair.com",
        contact="fayettecofair.org", url="fayettecofair.org",
        status="Verified - food vendors",
        notes="Fayette County Fair (Brownstown fairgrounds): 4-H, carnival, grandstand, food vendors. Fayette Co. IL.",
    ),
    ("Bond County Fair", "Greenville"): dict(
        month="August", typical_dates="Late July / early August 2026 (TBD)",
        application_method="Vendor info via Bond County Fair Assn / greenvilleillinois.com",
        contact="greenvilleillinois.com", url="greenvilleillinois.com",
        status="Verified - food vendors",
        notes="Bond County Fair, Greenville: vendors, food, contests, carnival. Bond Co. IL.",
    ),
    ("Vigo County Fair", "Terre Haute"): dict(
        month="July", typical_dates="Jul 11-18 (2026)",
        application_method="Concession Row vendor application via vigofair.com (Eventeny)",
        contact="vigofair.com", url="vigofair.com",
        status="Verified - food vendors",
        notes="Vigo County Fair, Terre Haute: 4-H, carnival, grandstand, Concession Row food vendors. Vigo Co. IN.",
    ),
    ("Banks of the Wabash Festival", "Terre Haute"): dict(
        month="May", typical_dates="May 21-30 (2026)",
        application_method="Vendor info via Banks of the Wabash Festival (terrehaute.com / Facebook)",
        contact="terrehaute.com", url="terrehaute.com",
        status="Verified - food vendors",
        notes="53rd Banks of the Wabash Festival, Terre Haute: carnival, food vendors, free admission. Vigo Co. IN.",
    ),
    ("Vandalia Grand Levee", "Vandalia"): dict(
        month="June", typical_dates="Jun 20 (2026)",
        application_method="Vendor info via downstateil.org / Vandalia Statehouse",
        contact="downstateil.org", url="downstateil.org",
        status="Verified - food trucks",
        notes="Vandalia Statehouse Grand Levee history celebration: food trucks, period activities, funnel cakes. Fayette Co. IL.",
    ),
    ("Summer Sundown Music Festival", "Effingham"): dict(
        month="September", typical_dates="Sep 11-13 (2026)",
        application_method="Vendor application: contact Andrew Evans andrew@adotevans.com",
        contact="andrew@adotevans.com", url="summersundownfest.com",
        status="Verified - food vendors",
        notes="Music festival at The Stage @ Lake Sara, Effingham: local food & craft vendors. Effingham Co. IL.",
    ),
    ("Clark County Fair", "Marshall"): dict(
        month="August", typical_dates="Aug 6-17 (2026)",
        application_method="Food vendor application via clarkcofair.com/vendors",
        contact="clarkcofair.com", url="clarkcofair.com",
        status="Verified - food vendors",
        notes="123rd Clark County Fair, Marshall: carnival, grandstand, food vendors. Clark Co. IL.",
    ),
    ("Clay County 4-H Fair", "Brazil"): dict(
        month="July", typical_dates="Jul 18-24 (2026)",
        application_method="Outside food vendor application via claycountyfair.net/vendors",
        contact="claycountyfair.net", url="claycountyfair.net",
        status="Verified - food vendors",
        notes="Clay County 4-H Fair, Brazil: carnival, food vendors; 2026 outside-vendor spots full (apply early for next year). Clay Co. IN.",
    ),
    ("Putnam County Fair", "Greencastle"): dict(
        month="July", typical_dates="Jul 17-24 (2026)",
        application_method="Vendor info via putcofair.org",
        contact="putcofair.org", url="putcofair.org",
        status="Verified - food vendors",
        notes="Putnam County Fair, Greencastle: 4-H, carnival, food vendors. Putnam Co. IN.",
    ),
    ("Miracle on 7th Street", "Terre Haute"): dict(
        month="December", typical_dates="Dec 4-5 (2026)",
        application_method="Vendor info via miracleon7thstreet.com",
        contact="miracleon7thstreet.com", url="miracleon7thstreet.com",
        status="Verified - food vendors",
        notes="Holiday festival, downtown Terre Haute / Hulman Center: 60-business vendor market, concessions, local food trucks. Vigo Co. IN.",
    ),
    ("First Friday Greencastle", "Greencastle"): dict(
        application_method="Vendor info via Mainstreet Greencastle (mainstreetgc.org/first-friday)",
        contact="mainstreetgc.org", url="mainstreetgc.org",
        status="Verified - food trucks",
        notes="Downtown Greencastle monthly First Friday (May-Oct), 6-10pm: 8 food & beverage trucks, crafts, live music on 3 stages. Putnam Co. IN.",
    ),

    # ---------- I-74 Corridor (hub 29) ----------
    ("Heart of Illinois Fair", "Peoria"): dict(
        month="July", typical_dates="Jul 14-18 (2026)",
        food_vendor_fee="$150 temp food license (5 days)",
        application_method="Vendor/food concessionaire application via heartofillinoisfair.com/vendors",
        contact="heartofillinoisfair.com", url="heartofillinoisfair.com",
        status="Verified - food vendors",
        notes="Heart of Illinois Fair, Peoria: carnival, grandstand, food concessionaires. Peoria Co. IL.",
    ),
    ("Galesburg Railroad Days", "Galesburg"): dict(
        month="June", typical_dates="Jun 25-28 (2026)",
        application_method="Vendor application via galesburgrailroaddays.net/vendors",
        contact="galesburgrailroaddays.net", url="galesburgrailroaddays.net",
        status="Verified - food vendors",
        notes="Galesburg Railroad Days: train viewing, vendors, food trucks, crafts. Knox Co. IL.",
    ),
    ("Vermilion County Fair", "Danville"): dict(
        month="June", typical_dates="Jun 24-28 (2026)",
        application_method="Vendor info via vermilioncountyfair.org",
        contact="vermilioncountyfair.org", url="vermilioncountyfair.org",
        status="Verified - food vendors",
        notes="Vermilion County Fair & Expo (Oakwood): carnival, grandstand, food vendors. Vermilion Co. IL.",
    ),
    ("Urbana Sweetcorn Festival", "Urbana"): dict(
        month="August", typical_dates="Late August 2026 (TBD)",
        application_method="Vendor info via urbanasweetcornfestival.com",
        contact="urbanasweetcornfestival.com", url="urbanasweetcornfestival.com",
        status="Verified - food vendors",
        notes="Downtown Urbana Sweetcorn Festival (40th): ~30 food/drink vendors, 50k visitors. Champaign Co. IL.",
    ),
    ("Champaign County Fair", "Urbana"): dict(
        month="July", typical_dates="Jul 25 - Aug 1 (2026)",
        application_method="Vendor info via Champaign County Fair IL (facebook.com/ChampaignCountyFairIL)",
        contact="facebook.com/ChampaignCountyFairIL", url="",
        status="Verified - food vendors",
        notes="Champaign County Fair, Urbana IL (173rd): carnival, grandstand, ~25 food booths. Champaign Co. IL.",
    ),
    ("Sweet Corn Circus", "Normal"): dict(
        month="August", typical_dates="Aug 23-24 (2026)",
        application_method="Vendor info via normalil.gov/1644/Sweet-Corn-Circus",
        contact="normalil.gov", url="normalil.gov",
        status="Verified - food vendors",
        notes="Uptown Normal Sweet Corn Circus: 120+ booths, food court with food trucks, fresh sweet corn. McLean Co. IL.",
    ),
    ("McLean County Fair", "Bloomington"): dict(
        month="July", typical_dates="Jul 29 - Aug 2 (2026)",
        application_method="Vendor info via mcleancountyfair.org",
        contact="mcleancountyfair.org", url="mcleancountyfair.org",
        status="Verified - food vendors",
        notes="McLean County Fair, Bloomington: carnival, grandstand, food vendors. McLean Co. IL.",
    ),
    ("Crawfordsville Strawberry Festival", "Crawfordsville"): dict(
        month="June", typical_dates="Jun 12-14 (2026)",
        application_method="Food vendor application via crawfordsvillestrawberryfest.com (food@crawfordsvillestrawberryfest.com; deadline May 1)",
        contact="food@crawfordsvillestrawberryfest.com", url="crawfordsvillestrawberryfest.com",
        status="Verified - food vendors",
        notes="Crawfordsville Strawberry Festival, downtown: food vendors, crafts, strawberries. Montgomery Co. IN.",
    ),
    ("Covington Apple Fest", "Covington"): dict(
        month="September", typical_dates="Sep 26 (2026)",
        application_method="Vendor info via Covington Business Assn / Covington Apple Fest (Facebook)",
        contact="facebook.com/covingtoninapplefest", url="facebook.com/covingtoninapplefest",
        status="Verified - food vendors",
        notes="35th Covington Apple Fest, historic downtown: 100+ booths incl. food trucks & food tents. Fountain Co. IN.",
    ),
    ("Peoria Irish Fest", "Peoria"): dict(
        month="August", typical_dates="Aug 28-30 (2026)",
        application_method="Vendor info via peoriairishfest.com/food-drink",
        contact="peoriairishfest.com", url="peoriairishfest.com",
        status="Verified - food vendors",
        notes="Peoria Irish Fest (44th), riverfront: Irish culture, music, food vendors throughout grounds. Peoria Co. IL.",
    ),

    # ---------- Louisville Metro (hub 30) ----------
    ("Kentucky State Fair", "Louisville"): dict(
        month="August", typical_dates="Aug 20-30 (2026)",
        application_method="Concessionaire application (new vendors) via kystatefair.org/get-involved/concessionaires-commercial-vendors",
        contact="kystatefair.org", url="kystatefair.org",
        status="Verified - food vendors",
        notes="Kentucky State Fair, KY Expo Center Louisville: concessionaires & commercial vendors. Jefferson Co. KY.",
    ),
    ("St. James Court Art Show", "Louisville"): dict(
        month="October", typical_dates="Oct 2-4 (2026)",
        application_method="Food vendor application via stjamescourtartshow.com/food-vendors (dlayman@stjamescourtartshow.com; Jan-Aug)",
        contact="dlayman@stjamescourtartshow.com", url="stjamescourtartshow.com",
        status="Verified",
        notes="Major juried art show, Historic Old Louisville; food vendors but EXPLICITLY excludes typical fair food (hot dogs, brats, corn dogs) - poor fit for a hot-dog truck. Jefferson Co. KY.",
    ),
    ("Kentucky Bourbon Festival", "Bardstown"): dict(
        month="September", typical_dates="Sep 10-13 (2026)",
        application_method="Food vendor application via kybourbonfestival.com",
        contact="kybourbonfestival.com", url="kybourbonfestival.com",
        status="Verified - food vendors",
        notes="Kentucky Bourbon Festival (34th), Bardstown: food trucks welcome in Bourbon Capital Bites + marketplace. Nelson Co. KY.",
    ),
    ("Harvest Homecoming", "New Albany"): dict(
        month="October", typical_dates="Oct 3-11 (2026); booths Oct 8-11",
        application_method="Food vendor application via harvesthomecoming.com (deadline Jul 8)",
        contact="harvesthomecoming.com", url="harvesthomecoming.com",
        status="Verified - food vendors",
        notes="Southern Indiana's largest fall festival, New Albany (~700k): 250+ craft/food booths (~150 food). Floyd Co. IN.",
    ),
    ("Kentucky Derby Festival", "Louisville"): dict(
        month="April", typical_dates="Fest-a-Ville Apr 23 - May 1 (2026)",
        application_method="Food vendors via official concessionaire Khalil's Catering / kdf.org (Chow Wagon)",
        contact="kdf.org", url="kdf.org",
        status="Verified - food vendors",
        notes="Kentucky Derby Festival Fest-a-Ville, Waterfront Park: Chow Wagon food trucks via official concessionaire Khalil's Catering. Jefferson Co. KY.",
    ),
    ("NuLu Summer Fest", "Louisville"): dict(
        month="July", typical_dates="Jul 18 (2026)",
        application_method="Vendor application via nulu.org/summer (Eventeny)",
        contact="nulu.org", url="nulu.org",
        status="Verified - food vendors",
        notes="NuLu Summer Fest, East Market St Louisville: food trucks welcome + local restaurants, 80+ vendors, live music. Jefferson Co. KY.",
    ),
    ("Seymour Oktoberfest", "Seymour"): dict(
        month="October", typical_dates="Oct 1-3 (2026)",
        application_method="Vendor info via seymouroktoberfest.com/vendor-faq",
        contact="seymouroktoberfest.com", url="seymouroktoberfest.com",
        status="Verified - food vendors",
        notes="Seymour Oktoberfest, Indiana: 75+ food booths, carnival, German fest. Jackson Co. IN.",
    ),
    ("Jammin' in Jeff", "Jeffersonville"): dict(
        month="June", typical_dates="Summer Friday nights (RiverStage); 2026 dates Jun 5, Jun 19, Jul 4",
        application_method="Vendor info via jeffparks.org/jammininjeff",
        contact="jeffparks.org", url="jeffparks.org",
        status="Verified - food vendors",
        notes="Jeffersonville RiverStage free summer concert series: themed night market with food trucks welcome each night. Clark Co. IN.",
    ),
    ("Highland Farms Country Fest", "Elizabethtown"): dict(
        month="September", typical_dates="Labor Day weekend (2026)",
        application_method="Vendor info via highlandfarmscountryfest.com/contact",
        contact="highlandfarmscountryfest.com", url="highlandfarmscountryfest.com",
        status="Verified - food vendors",
        notes="Country music festival at Highland Sod Farms, Elizabethtown: food trucks welcome & beverage tents. Hardin Co. KY.",
    ),

    # ---------- Evansville / Tri-State (hub 31) ----------
    ("West Side Nut Club Fall Festival", "Evansville"): dict(
        month="October", typical_dates="First full week of October 2026",
        application_method="Via nutclubfallfestival.com / West Side Nut Club",
        contact="nutclubfallfestival.com", url="nutclubfallfestival.com",
        status="Verified",
        notes="One of the largest US street festivals, Evansville: 137+ food booths run by nonprofits; independent outside food vendors not accepted (weak fit). Vanderburgh Co. IN.",
    ),
    ("ShrinersFest", "Evansville"): dict(
        month="May", typical_dates="May 29-30 (2026)",
        application_method="Vendor info via shrinersfest.org",
        contact="shrinersfest.org", url="shrinersfest.org",
        status="Verified - food vendors",
        notes="Hadi ShrinersFest, Evansville riverfront: food trucks welcome, beer garden, air show, rides. Vanderburgh Co. IN.",
    ),
    ("Frog Follies", "Evansville"): dict(
        month="August", typical_dates="Aug 28-30 (2026)",
        application_method="N/A - food handled internally by E'ville Iron Street Rods",
        contact="frogfollies.org", url="frogfollies.org",
        status="Verified",
        notes="Street rod show, Evansville: food booths run by charities; no independent food vendors accepted (poor fit). Vanderburgh Co. IN.",
    ),
    ("W.C. Handy Blues & Barbecue Festival", "Henderson"): dict(
        month="June", typical_dates="Jun 17-20 (2026)",
        application_method="Food vendor application via handyblues.org/become-a-vendor (deadline Apr 14; selective)",
        contact="handyblues.org", url="handyblues.org",
        status="Verified - food vendors",
        notes="W.C. Handy Blues & Barbecue Festival, Henderson: blues + BBQ, food vendors (selection committee, local priority). Henderson Co. KY.",
    ),
    ("BBQ & Barrels (International Bar-B-Q Festival)", "Owensboro"): dict(
        month="May", typical_dates="May 8-9 (2026)",
        application_method="Vendor application via bbqandbarrels.com/vendors",
        contact="bbqandbarrels.com", url="bbqandbarrels.com",
        status="Verified - food vendors",
        notes="BBQ & Barrels (formerly Int'l Bar-B-Q Festival), downtown Owensboro: church cook teams, music, food vendors; outdoor spaces full for 2026. Daviess Co. KY.",
    ),
    ("Mt. Vernon Fall Fest", "Mt. Vernon"): dict(
        month="September", typical_dates="Sep 25-26 (2026)",
        food_vendor_fee="$150/booth",
        application_method="Food vendor application via mtvfestivals.com/fall-fest (Eventeny; committee-selected)",
        contact="mtvfestivals.com", url="mtvfestivals.com",
        status="Verified - food vendors",
        notes="Mt. Vernon Fall Fest: car show, kids zone, marketplace, food & drink vendors, parade, music. Jefferson Co. IL.",
    ),

    # ---------- Thin out-of-state markets (hubs 5, 9-17) ----------
    ("Illinois State Fair", "Springfield"): dict(
        month="August", typical_dates="Aug 13-23 (2026)",
        application_method="Food vendor applications via statefair.illinois.gov/food/vendor-applications.html",
        contact="statefair.illinois.gov", url="statefair.illinois.gov/food/vendor-applications.html",
        status="Verified - food vendors",
        notes="Illinois State Fair, Springfield: food concessionaire/vendor applications. Sangamon Co. IL.",
    ),
    ("Huff 'n Puff Hot Air Balloon Rally", "Topeka"): dict(
        month="September", typical_dates="Early-mid September 2026 (TBD; 2025 was Sep 5-7)",
        application_method="Vendor info via huff-n-puff.org",
        contact="huff-n-puff.org", url="huff-n-puff.org",
        status="Verified - food vendors",
        notes="Huff 'n Puff Hot Air Balloon Rally, Topeka (50+ yrs): balloons, food trucks, craft vendors. Shawnee Co. KS.",
    ),
    ("Fiesta Topeka (Fiesta Mexicana)", "Topeka"): dict(
        month="July", typical_dates="Jul 14-18 (2026)",
        food_vendor_fee="$1,000 / 10x10 (food)",
        application_method="Vendor application via fiestatopeka.com/partner-vendor-information",
        contact="fiestatopeka.com", url="fiestatopeka.com",
        status="Verified - food vendors",
        notes="Fiesta Topeka (93 yrs), Our Lady of Guadalupe grounds: Mexican food & culture festival. Shawnee Co. KS.",
    ),
    ("SeptemberFest Omaha", "Omaha"): dict(
        month="September", typical_dates="Sep 1-4 (2026)",
        application_method="Vendor info via septemberfestomaha.com",
        contact="septemberfestomaha.com", url="septemberfestomaha.com",
        status="Verified - food vendors",
        notes="SeptemberFest Omaha Labor Day Salute: parade, carnival, international food booths, music. Douglas Co. NE.",
    ),
    ("Lancaster County Super Fair", "Lincoln"): dict(
        month="July", typical_dates="Jul 31 - Aug 8 (2026)",
        application_method="Vendor application via superfair.org/support/vendor",
        contact="superfair.org", url="superfair.org",
        status="Verified - food vendors",
        notes="Lancaster County Super Fair, Lincoln (10-day): carnival, Ribfest, fair food, vendor booths. Lancaster Co. NE.",
    ),
    ("Johnson County Peach Festival", "Clarksville"): dict(
        month="July", typical_dates="Jul 16-18 (2026)",
        application_method="Vendor application via jocopeachfest.com/vendors (479-754-9152)",
        contact="479-754-9152", url="jocopeachfest.com",
        status="Verified - food vendors",
        notes="Johnson County Peach Festival, Clarksville: home cookin', peach treats, food & craft vendors. Johnson Co. AR.",
    ),
    ("Pope County Fair", "Russellville"): dict(
        month="September", typical_dates="Sep 15-19 (2026)",
        application_method="Vendor info via popecountyfair.com/commercialbooth (479-857-5744)",
        contact="479-857-5744", url="popecountyfair.com",
        status="Verified - food vendors",
        notes="Pope County Fair, Russellville: carnival, food & commercial vendors, arts/crafts. Pope Co. AR.",
    ),
    ("Kansas Veterans Festival", "El Dorado"): dict(
        month="June", typical_dates="Jun 19-21 (2026)",
        application_method="Food truck/vendor application via kansasveteransfestival.org/vendorinfo",
        contact="kansasveteransfestival.org", url="kansasveteransfestival.org",
        status="Verified - food vendors",
        notes="Kansas Veterans Festival at El Dorado Lake: live music, car show, BBQ comp, food trucks welcome, craft vendors. Butler Co. KS.",
    ),
    ("Gold Fest", "El Dorado"): dict(
        month="September", typical_dates="Sep 24-26 (2026)",
        application_method="Food vendor application via experienceeldo.com/gold-fest-vendor (KS food license + $1M liability req'd)",
        contact="experienceeldo.com", url="experienceeldo.com",
        status="Verified - food vendors",
        notes="Gold Fest, downtown El Dorado: block party, food court, Main Street market. Butler Co. KS.",
    ),
    ("Mulvane Mountain/Plains Art Fair", "Topeka"): dict(
        month="June", typical_dates="Jun 6-7 (2026)",
        application_method="Vendor info via mulvaneartmuseum.org/artfair",
        contact="mulvaneartmuseum.org", url="mulvaneartmuseum.org",
        status="Verified - food vendors",
        notes="Mulvane Art Fair, Washburn University Topeka: 85+ juried artists, beer garden, food trucks welcome. Shawnee Co. KS.",
    ),
    ("Great American Market", "Emporia"): dict(
        month="September", typical_dates="Sep 12 (2026)",
        application_method="Vendor info via emporiamainstreet.com (620-340-6430)",
        contact="620-340-6430", url="emporiamainstreet.com",
        status="Verified - food vendors",
        notes="Great American Market, downtown Emporia: 6-block market, food trucks welcome (tacos, burgers, sweets). Lyon Co. KS.",
    ),
    ("Memphis in May / World Championship BBQ", "Memphis"): dict(
        month="May", typical_dates="May 13-16 (2026)",
        application_method="Food vendor application via memphisinmay.org/vendor",
        contact="memphisinmay.org", url="memphisinmay.org",
        status="Verified - food vendors",
        notes="World Championship Barbecue Cooking Contest, Liberty Park Memphis (48th): official food vendors apply. Shelby Co. TN.",
    ),
    ("West Tennessee State Fair", "Henderson"): dict(
        month="October", typical_dates="Oct 16-25 (2026)",
        application_method="Food vendor application via wtsfair.com (Show Director Mike Peery)",
        contact="wtsfair.com", url="wtsfair.com",
        status="Verified - food vendors",
        notes="West Tennessee State Fair, Henderson: rides, livestock, ~50 food booths. Chester Co. TN.",
    ),
    ("West Memphis Freedom Fest", "West Memphis"): dict(
        month="June", typical_dates="Late June 2026 (around July 4)",
        application_method="Vendor info via City of West Memphis (schristian@citywm.com / 877-732-7598)",
        contact="schristian@citywm.com / 877-732-7598", url="visitwestmemphis.com",
        status="Verified - food vendors",
        notes="West Memphis Freedom Fest, Tilden Rodgers Park: fireworks, live music, food vendors. Crittenden Co. AR.",
    ),
    ("Bowling Green International Festival", "Bowling Green"): dict(
        month="September", typical_dates="Sep 26 (2026)",
        application_method="Vendor info via bginternationalfest.com (Eventbrite)",
        contact="bginternationalfest.com", url="bginternationalfest.com",
        status="Verified - food vendors",
        notes="Bowling Green International Festival (36th), Circus Square Park: international foods, bazaar, music/dance. Warren Co. KY.",
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
