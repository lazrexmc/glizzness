-- Phase 2 audit patch: 3 events were typed 'festival' but are food-truck rallies.
-- Run once in the Supabase SQL editor (cosmetic — only affects the drawer's type badge).
-- Already reflected in data/events.csv + supabase_vending_data.sql for future reloads.

update vending_events set event_type = 'food_truck_rally'
where name in (
  'Crossroads First Fridays',
  'Final Friday Food & Booze Truck Rally',
  'Downtown Bentonville First Fridays'
);
-- expect: UPDATE 3
