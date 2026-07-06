-- The Glizzness — catering lead capture (Supabase / Postgres)
-- Run once in the Supabase SQL editor. Safe alongside the accounting + vending_* tables.
-- The public catering page INSERTs leads with the anon key; nobody can read them back
-- with that key (no SELECT policy) — only the service_role / your dashboard can.

begin;

create table if not exists catering_leads (
  id           bigint generated always as identity primary key,
  created_at   timestamptz not null default now(),
  name         text not null,
  email        text,
  phone        text,
  event_date   date,
  guest_count  int,
  package      text,          -- which package they clicked (or "Custom / help me choose")
  location     text,          -- event city / venue
  message      text,
  source       text default 'catering_page',
  status       text default 'new'   -- new -> contacted -> booked -> lost (you manage this)
);
create index if not exists catering_leads_created_idx on catering_leads(created_at desc);
create index if not exists catering_leads_status_idx  on catering_leads(status);

-- RLS: the anon (public) key may INSERT a lead, but has NO read access.
alter table catering_leads enable row level security;

-- the public form can submit
grant insert on catering_leads to anon, authenticated;
create policy catering_leads_insert on catering_leads
  for insert to anon, authenticated with check (true);

-- NOTE: intentionally NO select/update/delete policy for anon -> leads are private.
-- service_role (your automation / dashboard) bypasses RLS and can read/manage them.

commit;

-- Peek at leads (run as service_role in the SQL editor):
--   select created_at, name, phone, email, package, event_date, guest_count, status
--   from catering_leads order by created_at desc;
