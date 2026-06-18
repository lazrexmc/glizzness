-- Phase 4 audit patch: grant anon read on the gate view so it's API-queryable
-- (the map currently reads base tables, so this is an enhancement, not a fix).
-- Run once in the Supabase SQL editor. Now folded into supabase_vending_schema.sql too.

grant select on vending_published_events to anon, authenticated;

-- verify (run as anon via REST, or):
-- select count(*) from vending_published_events;  -- 124
