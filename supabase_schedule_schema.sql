-- The Glizzness — public cart schedule ("Where We Vend")
-- A SANITIZED, public-safe mirror of the business Google Calendar. Run once in the
-- Supabase SQL editor. Safe alongside the accounting + vending_* + catering tables.
--
-- Populated server-side by sync_calendar.py (service_role); read by the website
-- (anon key). PUBLIC events (Visibility = "Public" on the calendar) carry a title + location;
-- EVERY other event is stored only as a "Booked — Unavailable" time block with NO
-- title and NO location — so private catering details never reach the web.

begin;

create table if not exists cart_schedule (
  id            bigint generated always as identity primary key,
  gcal_event_id text not null unique,   -- Google Calendar event id (idempotent key)
  starts_at     timestamptz not null,
  ends_at       timestamptz,
  all_day       boolean not null default false,
  is_public     boolean not null default false,
  title         text,                   -- venue/appearance name — PUBLIC only, else NULL
  location      text,                   -- e.g. "Logboat Brewing, Columbia" — PUBLIC only, else NULL
  updated_at    timestamptz not null default now()
);
create index if not exists cart_schedule_starts_idx on cart_schedule(starts_at);

-- RLS: the public may READ (rows are already sanitized). Only service_role writes
-- (it bypasses RLS), so there is intentionally NO anon insert/update/delete policy.
alter table cart_schedule enable row level security;
grant select on cart_schedule to anon, authenticated;
create policy cart_schedule_read on cart_schedule
  for select to anon, authenticated using (true);

commit;

-- Peek (run as service_role):
--   select starts_at, is_public, title, location from cart_schedule order by starts_at;
