-- The Glizzness — internal Contact Hub (Supabase / Postgres)
-- Run once in the Supabase SQL editor. This is PRIVATE, internal-only data (phones/emails,
-- sales status). Unlike vending_* (public-read) and catering_leads (anon-insert), this table
-- has NO anon/public access at all — only the service_role (your dashboard / SQL editor) can
-- read or write it. Mirrors Contacts.md.

begin;

create table if not exists contacts (
  id           bigint generated always as identity primary key,
  created_at   timestamptz not null default now(),
  name         text,               -- person or org name
  organization text,
  category     text,               -- corporate | worksite | campus | venue | cannabis |
                                    -- supplier | event | government | media | catering_lead
  role         text,               -- title / department to reach
  phone        text,
  email        text,
  website      text,
  address      text,
  status       text default 'to_call',  -- to_call | contacted | booked | recurring | dead
  priority     text,               -- hot | warm | cold  (or a tier)
  notes        text,               -- fit, pitch angle, caveats
  source       text,               -- where the contact came from
  last_contacted date
);
create index if not exists contacts_category_idx on contacts(category);
create index if not exists contacts_status_idx   on contacts(status);

-- RLS ON with NO policies => anon & authenticated get nothing; service_role bypasses RLS.
alter table contacts enable row level security;

commit;

-- Quick references (run as service_role in the SQL editor):
--   select name, organization, phone, email, status from contacts where category='corporate' and status='to_call';
--   select category, count(*) from contacts group by category order by 2 desc;
--   update contacts set status='contacted', last_contacted=current_date where name='...';
