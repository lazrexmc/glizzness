-- The Glizzness — Post Cards (social post drafts for public cart stops)
-- Run ONCE in the Supabase SQL editor, AFTER supabase_scout_schema.sql.
--
-- WHAT THIS IS: the gated page /hub/posts reads your PUBLIC upcoming stops from cart_schedule,
-- generates post copy client-side (deterministically), and shows one card per (stop x touch).
-- Only your REVIEW DECISION persists here — the drafts themselves are regenerated on each load.
-- No row for a card = "not reviewed yet".
--
-- ⚠️ WHY event_ref AND NOT cart_schedule.id:
--   sync_calendar.py replaces the managed window on EVERY run (delete future rows -> reinsert),
--   so cart_schedule.id churns every 2 hours. A foreign key to it would orphan every approval
--   twice an hour. `gcal_event_id` is Google's own id and is STABLE across syncs — that's the key.
--
-- SECURITY: same model as the Scout/Signal tables — RLS authenticated-only, anon revoked.

begin;

create table if not exists post_drafts (
  id           bigint generated always as identity primary key,
  event_ref    text not null,          -- cart_schedule.gcal_event_id for a stop;
                                       -- 'week:2026-W29' for the weekly roundup card
  touch        text not null
                 check (touch in ('night_before','morning_of','weekly')),
  send_at      timestamptz,            -- when to schedule this post for (what you set in Business Suite)
  stop_title   text,                   -- denormalized for the log: which stop this was about
  starts_at    timestamptz,            -- ditto: when the stop was
  body_fb      text,                   -- final copy (edited or as-generated) — FB variant, link OK
  body_ig      text,                   -- final copy — IG variant, "link in bio" (captions aren't clickable)
  photo        text,                   -- which real photo to attach
  edited       boolean not null default false,   -- did Lance change the generated wording?
  status       text not null default 'approved'
                 check (status in ('approved','skipped')),
  reviewed_at  timestamptz not null default now(),
  unique (event_ref, touch)            -- one decision per card; re-approving upserts
);
create index if not exists post_drafts_status_idx on post_drafts(status);
create index if not exists post_drafts_send_idx   on post_drafts(send_at);

-- RLS: authenticated-only, anon revoked (Scout-board pattern).
alter table post_drafts enable row level security;
grant select, insert, update, delete on post_drafts to authenticated;
create policy post_drafts_all on post_drafts
  for all to authenticated using (true) with check (true);
-- Defense in depth: even if RLS is ever disabled, the public key still gets permission denied.
revoke all on post_drafts from anon;

commit;

-- Peek (run as service_role):
--   select send_at, touch, stop_title, status, edited from post_drafts order by send_at desc limit 50;
--   select status, count(*) from post_drafts group by status;
