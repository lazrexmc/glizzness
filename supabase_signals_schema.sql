-- The Glizzness — Signal Net schema (Supabase / Postgres)
-- Run ONCE in the Supabase SQL editor, AFTER supabase_scout_schema.sql.
-- Safe alongside the accounting + vending_* + catering + cart_schedule + scout tables.
--
-- SECURITY (same model as the Scout tables): RLS ON, policy only for `authenticated`, and
-- `anon` grants revoked. The public anon key can't touch this. The crawler (GitHub Actions)
-- writes with the service_role key (bypasses RLS); the gated Signals page reads/updates as an
-- authenticated user. See SIGNAL_NET.md.

begin;

-- ---------------------------------------------------------------------------
-- event_signals — raw finds from the crawler + manual paste-adds, before triage
-- ---------------------------------------------------------------------------
create table if not exists event_signals (
  id                   bigint generated always as identity primary key,
  source               text not null,                 -- e.g. 'reddit:CoMo', 'rss:missourian', 'venue:rosemusichall', 'manual'
  dedup_hash           text not null unique,          -- hash(source + external id/url); idempotency key
  title                text not null,
  url                  text,
  starts_text          text,                          -- raw date/time text as published
  event_date           date,                          -- parsed when confidently possible, else null
  location_text        text,
  city                 text,
  description          text,
  image_url            text,
  raw                  jsonb,                          -- original item (debugging / later enrichment)
  status               text not null default 'new'
                         check (status in ('new','kept','dismissed')),
  promoted_prospect_id bigint references event_prospects(id) on delete set null,
  found_at             timestamptz not null default now(),
  reviewed_at          timestamptz
);
create index if not exists event_signals_status_idx on event_signals(status);
create index if not exists event_signals_found_idx  on event_signals(found_at desc);

-- RLS: authenticated-only, anon revoked (Scout-board pattern).
alter table event_signals enable row level security;
grant select, insert, update, delete on event_signals to authenticated;
create policy event_signals_all on event_signals
  for all to authenticated using (true) with check (true);
-- Defense in depth: even if RLS is ever disabled, the public key still gets permission-denied.
revoke all on event_signals from anon;

-- ---------------------------------------------------------------------------
-- Allow event_prospects.source = 'signal' (a Keep on the Signals feed creates one of these).
-- The original check was: source in ('research','inbound').
-- ---------------------------------------------------------------------------
alter table event_prospects drop constraint if exists event_prospects_source_check;
alter table event_prospects add  constraint event_prospects_source_check
  check (source in ('research','inbound','signal'));

commit;

-- Peek (run as service_role):
--   select found_at, source, title, starts_text, status from event_signals order by found_at desc limit 50;
--   select status, count(*) from event_signals group by status;
