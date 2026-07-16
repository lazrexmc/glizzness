-- The Glizzness — lunch-rush / worksite prospect seed for the Scout board
-- Run ONCE in the Supabase SQL editor (idempotent: each insert skips if the name already exists,
-- so re-running never duplicates and never clobbers desk edits).
--
-- ⚠️ KNOWN LIMIT: the guard is NAME-equality. If you RENAME a seeded card on the desk and later
-- re-run this file, the original name no longer exists and the row is re-inserted as a duplicate.
-- Rule of thumb: run this once; if you renamed cards, don't re-run (or delete the dupes after).
--
-- WHY (owner, 2026-07-16): "My desk seems a little light... businesses that have a shitload of
-- people that leave for lunch — we'll post up on the curb next to the parking lot."
-- The Signal Net can't find these (employers aren't "events") — they come from the verified
-- employer research in CorporateProspects.md (REDI Boone County largest-employers + 2026 checks).
-- And the sales data agrees with the instinct: daytime lunch trade is ALREADY the biggest session
-- type in the demand baseline (252 sessions). These land as stage='researching' -> Lance enriches
-- (curb legality / property permission / named contact) -> Ready -> Trint.
--
-- event_type 'lunch_rush' / 'worksite_crew' maps to the daytime-sessions demand profile, so each
-- card automatically shows crew + prep estimates from real history (assets/demand.js).

begin;

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Veterans United','lunch_rush','Columbia',0,10,'Weekdays 11–1','~2,800 staff (largest private employer)','REPEAT CLIENT — reconnect via the prior events contact (invoices on file), do NOT cold-pitch','unknown','#1 target. 1400 & 550 Veterans United Dr. Young office workforce, big culture/perks budget. Pitch a standing prepaid cart day on their lot.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Veterans United');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — EquipmentShare HQ','lunch_rush','Columbia',0,12,'Weekdays 11–1','~600 staff, 555 more coming (phased)','Call the office manager / people team — cart day on the campus','unknown','5710 Bull Run Dr; 35-acre campus near the I-70 Lake of the Woods exit. New $100M tech center, young tech staff, above-average salaries. Top-tier cart-day target.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — EquipmentShare HQ');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Shelter Insurance HQ','lunch_rush','Columbia',0,8,'Weekdays 11–1','~1,100–1,375 staff','Facilities / office services — cart day on the campus','unknown','W Broadway HQ campus. Big office workforce; verify cafeteria status (determines cart-day vs event-only fit).'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Shelter Insurance HQ');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Paris Road corridor run','lunch_rush','Columbia',0,10,'Weekdays 11–1 + shift changes','~1,400 workers within blocks (4 plants)','Pick the curb spot, then per-plant HR/facilities for on-lot permission','unknown','THE curb play: Schneider Electric (4800 Paris Rd, +241 jobs by Mar 2026) + Quaker Oats (4501 Paris Rd, 24/7) + Swift/Principe ($200M meat plant, 5008 Paris Rd) + Kraft Heinz/Oscar Mayer (4600 Waco Rd, 24/7 hot-dog plant — fun angle). One spot catches four plants'' lunch + shift traffic.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Paris Road corridor run');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Watlow','lunch_rush','Columbia',0,10,'Weekdays 11–1','~236 staff','Facilities / HR / site manager','unknown','2101 Pennsylvania Dr. Manufacturing + engineering; confirmed active.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Watlow');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Central Bank of Boone County','lunch_rush','Columbia',0,5,'Weekdays 11–1','~340 staff (downtown)','Ask for HR / community relations — 573-874-8100','unknown','720 E Broadway. Downtown banking offices; walkable curb potential nearby.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Central Bank of Boone County');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — MidwayUSA','lunch_rush','Columbia',0,15,'Weekdays 11–1','~300 staff (HQ + warehouse)','573-445-6363 — ask for the People/HR events team','unknown','5875 W Van Horn Tavern Rd. Retailer HQ/warehouse — warehouse staff rarely leave for lunch; bring it to them.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — MidwayUSA');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — MBS Textbook Exchange','lunch_rush','Columbia',0,10,'Weekdays 11–1','~470 staff','VERIFIED: Mark Nistendirk (HR Mgr) — humanresources@mbsbooks.com — 573-446-5258','unknown','2711 W Ash St. Textbook distribution warehouse + offices.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — MBS Textbook Exchange');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Eurofins labs (2 sites)','lunch_rush','Columbia',0,12,'Weekdays 11–1','~336 lab staff across 2 sites','Pitch each site''s office/facilities separately — BioPharma 573-777-6100, Agroscience 573-777-6000','unknown','4780 Discovery Dr + 7200 E ABC Ln. Lab staff on tight lunch windows = captive curb audience.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Eurofins labs (2 sites)');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Emery Sapp & Sons HQ','lunch_rush','Columbia',0,10,'Weekdays 11–1','~501 staff (office + crews)','573-445-8331 — office manager','unknown','2301 I-70 Drive NW. DOUBLE ACCOUNT: pitch the HQ office staff AND the I-70 night crews (separate card).'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Emery Sapp & Sons HQ');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Dana Light Axle','lunch_rush','Columbia',0,12,'Weekdays 11–1 + shift changes','~380 plant workers','Plant HR / facilities','unknown','2400 Lemone Industrial Blvd. Auto-parts plant; shift schedule means predictable meal windows.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Dana Light Axle');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Joe Machens dealership row','lunch_rush','Columbia',0,12,'Weekdays 11–2 (sales can''t leave the lot)','~600 staff across multiple lots','Per-dealership GM / office manager','unknown','Multiple Columbia lots. Sales staff are chained to the floor at lunch — bring the cart to the row. Also customer-appreciation event fit.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Joe Machens dealership row');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Worksite — I-70 night crews (Emery Sapp, Rocheport→Columbia)','worksite_crew','Boone County',5,10,'Overnight shifts, spring 2026 → late 2029','~350 workers on the corridor at peak','Call ESS (573-445-8331) for field-office locations + which zones run night shifts','unknown','TOP worksite play: $441M rebuild, 14 mi all in Boone County, LOCAL contractor, longest runway (→2029). Captive overnight crews with nowhere to eat. Time-boxed gold.'
where not exists (select 1 from event_prospects where name = 'Worksite — I-70 night crews (Emery Sapp, Rocheport→Columbia)');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Worksite — I-70 crews (Millstone Weber, Columbia→Kingdom City)','worksite_crew','Boone County',5,10,'Active now → late 2027','Corridor crews (west end near Columbia)','Ask HQ (636-949-0038) for the Columbia-to-Kingdom City project superintendent','unknown','$426M segment, US-63 → Kingdom City. West end is reachable; crews already working.'
where not exists (select 1 from event_prospects where name = 'Worksite — I-70 crews (Millstone Weber, Columbia→Kingdom City)');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Event fit — Truman VA Hospital','lunch_rush','Columbia',0,8,'Dept events / appreciation days','~2,074 staff, 24/7','Volunteer services / dept admins','unknown','800 Hospital Dr. Likely has a cafeteria -> event/appreciation fit rather than daily curb. Big, stable institution.'
where not exists (select 1 from event_prospects where name = 'Event fit — Truman VA Hospital');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Lunch rush — Amazon Ashland','lunch_rush','Ashland',15,18,'Weekdays + holiday surges','~100+ warehouse staff (staffs up for holidays)','Site ops / HR','unknown','Delivery/distribution facility in Ashland (Boone County). Shift meal windows; biggest at the holiday surge.'
where not exists (select 1 from event_prospects where name = 'Lunch rush — Amazon Ashland');

insert into event_prospects (source, stage, name, event_type, city, distance_mi, drive_time_min, date_text, crowd_text, application_method, food_policy, notes)
select 'research','researching','Verify — Aurora Organic Dairy','lunch_rush','Columbia',0,12,'Weekdays + shifts','Milk plant (size unverified)','Verify size + contact first','unknown','The "big dairy" — real, but headcount/site specifics unverified. Enrich before pitching.'
where not exists (select 1 from event_prospects where name = 'Verify — Aurora Organic Dairy');

commit;

-- Verify: select count(*) from event_prospects where event_type in ('lunch_rush','worksite_crew');  -- expect 17
