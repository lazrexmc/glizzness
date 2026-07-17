-- The Glizzness — SECURITY HARDENING (from the 2026-07-16 full-system audit)
-- Run ONCE in the Supabase SQL editor. THEN DO STEP 0 AND STEP 5 BELOW — the allowlist starts
-- EMPTY, so the hub will be locked for everyone until you insert your two emails (step 5).
--
-- WHAT THIS FIXES (SYSTEM_AUDIT_2026-07-16.md):
--  A) CRITICAL — self-signup hole. Supabase's /auth/v1/signup is ON by default and reachable with
--     the public anon key, and every private-table policy trusted ANY `authenticated` user. A
--     stranger could sign themselves up and read/write everything private.
--       STEP 0 (dashboard, do it first): Authentication -> Sign In / Providers ->
--       DISABLE "Allow new users to sign up".
--       This file adds the code-level backstop so we never depend on that toggle again:
--       an `app_allowed` email allowlist checked by every private-table policy.
--  B) HIGH — the public Event Finder served Trint's PRIVATE research prospects (ids 500+) and
--     unpublished/defunct rows to anyone with the anon key: the publish gate was client-side JS.
--     Now the RLS policy IS the publish gate.
--  C) MEDIUM — default table grants: catering_leads (customer PII) and cart_schedule predated the
--     revoke-from-anon discipline; Supabase default privileges also over-grant broadly. This does
--     a clean grant reset: revoke everything, re-grant exactly what each surface needs.

begin;

-- ---------------------------------------------------------------------------
-- 1. The allowlist + a SECURITY DEFINER check
--    (definer, so the policies can consult it without granting anyone read on the list itself)
-- ---------------------------------------------------------------------------
create table if not exists app_allowed (
  email      text primary key,
  note       text,
  created_at timestamptz not null default now()
);
alter table app_allowed enable row level security;   -- no policies: service_role/SQL editor only

create or replace function auth_email_allowed()
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (
    select 1 from app_allowed
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;
revoke all on function auth_email_allowed() from public;
grant execute on function auth_email_allowed() to authenticated;

-- ---------------------------------------------------------------------------
-- 2. Private tables: replace "any authenticated user" with "authenticated AND allowlisted"
-- ---------------------------------------------------------------------------
drop policy if exists event_prospects_all    on event_prospects;
drop policy if exists prospect_decisions_all on prospect_decisions;
drop policy if exists prospect_thread_all    on prospect_thread;
drop policy if exists event_signals_all      on event_signals;
drop policy if exists post_drafts_all        on post_drafts;
drop policy if exists demand_profiles_all    on demand_profiles;

create policy event_prospects_all    on event_prospects    for all to authenticated
  using (auth_email_allowed()) with check (auth_email_allowed());
create policy prospect_decisions_all on prospect_decisions for all to authenticated
  using (auth_email_allowed()) with check (auth_email_allowed());
create policy prospect_thread_all    on prospect_thread    for all to authenticated
  using (auth_email_allowed()) with check (auth_email_allowed());
create policy event_signals_all      on event_signals      for all to authenticated
  using (auth_email_allowed()) with check (auth_email_allowed());
create policy post_drafts_all        on post_drafts        for all to authenticated
  using (auth_email_allowed()) with check (auth_email_allowed());
create policy demand_profiles_all    on demand_profiles    for all to authenticated
  using (auth_email_allowed()) with check (auth_email_allowed());

-- ---------------------------------------------------------------------------
-- 3. The Event Finder: RLS becomes the publish gate (was client-side JS only)
--    Public sees ONLY published, non-prospect (< 500), located, non-excluded events.
-- ---------------------------------------------------------------------------
drop policy if exists vending_events_read on vending_events;
create policy vending_events_read on vending_events for select using (
  id < 500
  and verification_status in ('verified','partial')
  and food_truck_friendly <> 'excluded'
  and lat is not null
);
-- child rows follow the parent's visibility (the subquery is itself RLS-filtered)
drop policy if exists vending_sched_read on vending_event_schedules;
create policy vending_sched_read on vending_event_schedules for select using (
  exists (select 1 from vending_events e where e.id = event_id)
);
drop policy if exists vending_sources_read on vending_sources;
create policy vending_sources_read on vending_sources for select using (
  exists (select 1 from vending_events e where e.id = event_id)
);
drop policy if exists vending_fees_read on vending_fees;
create policy vending_fees_read on vending_fees for select using (
  exists (select 1 from vending_events e where e.id = event_id)
);

-- ---------------------------------------------------------------------------
-- 4. Clean grant reset: revoke everything, re-grant exactly what each surface needs.
--    (Supabase default privileges auto-grant broadly on new tables; this zeroes that out.
--     Accounting tables + contacts end with NO grants = service_role only, as intended.)
-- ---------------------------------------------------------------------------
revoke all on all tables in schema public from anon, authenticated;

-- public site surfaces
grant insert on catering_leads to anon, authenticated;                    -- booking form (write-only)
grant select on cart_schedule  to anon, authenticated;                    -- Where We Vend
grant select on vending_markets, vending_events, vending_event_schedules,
                vending_sources, vending_fees to anon, authenticated;     -- Event Finder (rows gated above)
grant select on vending_published_events to anon, authenticated;         -- the gate view

-- gated tools (rows further gated by the allowlist policies)
grant select, insert, update, delete on
  event_prospects, prospect_decisions, prospect_thread,
  event_signals, post_drafts, demand_profiles to authenticated;

commit;

-- ---------------------------------------------------------------------------
-- 5. ⚠️ REQUIRED LAST STEP — add your two logins to the allowlist (EDIT THE EMAILS, then run):
--
--   insert into app_allowed (email, note) values
--     ('YOUR-LANCE-LOGIN-EMAIL',  'Lance'),
--     ('YOUR-TRINT-LOGIN-EMAIL',  'Trint');
--
-- Use the EXACT emails of the two Supabase Auth users. Until this runs, the hub shows no data.
-- (✅ EXECUTED with the real emails 2026-07-16 — the live allowlist is in the DB; the repo copy
--  keeps placeholders on purpose so personal emails stay out of git.)
-- ---------------------------------------------------------------------------

-- VERIFY (all should hold):
--   select auth_email_allowed();                          -- false in the SQL editor (no jwt) is fine
--   select count(*) from app_allowed;                      -- 2 after step 5
--   -- with the ANON key from a browser/curl:
--   --   vending_events?id=gte.500  -> []                  (prospects invisible)
--   --   event_prospects            -> 401/42501           (still sealed)
