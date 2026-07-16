-- The Glizzness — Demand Profiles (the baseline's learned numbers, served to the gated tools)
-- Run ONCE in the Supabase SQL editor, AFTER supabase_scout_schema.sql.
--
-- WHAT THIS IS: demand_baseline.py distills 4 years of Square sales (15k+ orders, 639 sessions)
-- into per-venue and per-session-type profiles: orders/hr, crew needed, units sold, prep mix.
-- This table is how those numbers reach the Scout board — Trint's card can say
-- "Crew: 1–2 (from 74 past nights here)" on real evidence instead of a guess.
--
-- Data flow:  Sales/items-*.csv (local) -> python demand_baseline.py --sql
--             -> supabase_demand_data.sql (delete-all + insert; idempotent) -> Lance runs it here.
-- Re-run the generator + data SQL whenever fresh sales exports land. The web pages only READ this.
--
-- SECURITY: same model as the other gated tables — RLS authenticated-only, anon revoked.
-- (gross_median is revenue detail; it must never be anon-readable.)

begin;

create table if not exists demand_profiles (
  id              bigint generated always as identity primary key,
  kind            text not null check (kind in ('venue','label','overall')),
  key             text not null,        -- normalized match key: venue 'logboat' / label 'daytime_unlogged_gig' / 'overall'
  display_name    text not null,
  sessions        int  not null,        -- how much evidence backs this profile
  oph_median      numeric,              -- orders per hour
  oph_p90         numeric,
  oph_max         numeric,
  crew_typical    int,                  -- ceil(oph_median * buffer / pace)
  crew_busy       int,                  -- ceil(oph_p90    * buffer / pace)
  units_median    int,                  -- items sold in a typical session
  units_p90       int,
  units_per_order numeric,
  gross_median    numeric,              -- PRIVATE revenue detail (desk-only display)
  prep            jsonb,                -- {"Glizzy": 16.2, "Chili Dog": 4.1, ...} per typical session
  pace_per_person numeric not null,     -- the owner-set labor standard the crew numbers assume
  generated_at    timestamptz not null default now(),
  unique (kind, key)
);
create index if not exists demand_profiles_kind_idx on demand_profiles(kind);

-- RLS: authenticated-only, anon revoked (Scout-board pattern).
alter table demand_profiles enable row level security;
grant select, insert, update, delete on demand_profiles to authenticated;
create policy demand_profiles_all on demand_profiles
  for all to authenticated using (true) with check (true);
-- Defense in depth: even if RLS is ever disabled, the public key still gets permission denied.
revoke all on demand_profiles from anon;

commit;

-- Peek (run as service_role):
--   select kind, display_name, sessions, oph_median, crew_typical, crew_busy, units_median
--   from demand_profiles order by kind, sessions desc;
