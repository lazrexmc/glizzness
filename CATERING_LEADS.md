# Catering Lead Notifications — how a "Send my request" becomes an email

When someone fills out the **Book the Cart** form (`catering.html#book`), this pipeline turns that
submission into a formatted email in the shop inbox. Built & verified **2026-07-13**.

```
catering.html#book  ──POST──▶  Supabase  ──INSERT webhook──▶  Make.com  ──▶  Gmail
  (booking form)              catering_leads                  scenario         glizzness@gmail.com
```

Nothing is exposed to the browser except Supabase's **anon** key (INSERT-only). All the notification
logic lives server-side in Supabase + Make.

## The three pieces

1. **Supabase table `catering_leads`** — anon **INSERT-only** RLS, no SELECT policy (the public can
   submit but can't read leads back). Columns: `name, phone, email, event_date, guest_count, package,
   location, message, source, created_at`. Read leads as service_role in the SQL editor:
   `select * from catering_leads order by created_at desc;`. Schema DDL: `supabase_catering_schema.sql`.

2. **Supabase Database Webhook** — in the dashboard under **Integrations → Database Webhooks** (NOT the
   old "Database → Webhooks" spot; it moved). Webhook **`catering-lead-notify`**: table `catering_leads`,
   event **INSERT**, type **POST**, URL = the Make scenario's Custom-webhook URL (`https://hook.us2.make.com/…`).
   Supabase POSTs a JSON body shaped `{ "type":"INSERT", "table":"catering_leads", "record": { …the row… }, … }`.

3. **Make.com scenario** — two modules:
   - **Trigger: Webhooks → "Custom webhook"** (search the *Webhooks* app; it's not under a "Supabase"
     app). Its generated URL is what you paste into the Supabase webhook above. Run "Determine data
     structure" once and submit a test lead so Make learns the shape.
   - **Action: Gmail → "Send an email"** to glizzness@gmail.com, with Subject + Body built from the
     **individual fields inside `record`** (see gotcha #2).

## Rebuild from scratch

1. Run `supabase_catering_schema.sql` in the Supabase SQL editor (creates the table + INSERT-only RLS).
2. In **Make.com**: new scenario → add **Webhooks › Custom webhook** → copy its URL.
3. In **Supabase → Integrations → Database Webhooks**: create `catering-lead-notify` on `catering_leads`
   / INSERT / POST → paste the Make URL.
4. Back in Make, click **Determine data structure**, then submit a real test through `catering.html#book`
   so Make captures the payload.
5. Add a **Gmail › Send an email** module; connect the Gmail account (grant **all** requested scopes —
   see gotcha #1). Map Subject/Body from `record.*` leaves (gotcha #2). Save + turn the scenario **ON**.

## Gotchas that cost us time

1. **Gmail 403 "insufficient authentication scopes."** The first Gmail connection didn't grant send
   permission. Fix: reconnect the Gmail account in Make and **accept every requested permission** (the
   send scope specifically). Then the module sends.

2. **Subject/Body arrived as a raw JSON blob.** Cause: mapping the whole **`record`** object into the
   field instead of its children. Fix: in the mapping panel, **expand `record`** and click the individual
   leaves — `record: name`, `record: event_date`, `record: guest_count`, etc. — so the email reads like a
   message, not a dump.

3. **Body must be "collection of contents (text/images)"**, not **Raw HTML**, unless you're actually
   writing HTML — otherwise Make escapes it oddly. (This was already correct on our end.)

## Test it

Submit a real request at `catering.html#book` (or the live site). Within ~a minute an email lands in
glizzness@gmail.com with the lead's details, and the row is in `catering_leads`. If no email: check the
Make scenario's **History** tab for the run + error, confirm the scenario is **ON**, and confirm the
Supabase webhook shows a 200 in its logs.

## Secrets — where they live (never commit)

- Supabase URL + anon key: `catering/config.js` (anon is public by design). Service_role: **not in git**.
- Make webhook URL + Gmail connection: inside Make / the Supabase webhook config — **not in git**.
- See `REBUILD.md` and the private memory for the full credential map.

> Still open (see `TODO.md`): lead **status tracking**, optional **calendar** on confirmed bookings,
> customer **auto-reply**, and an operator **working view**. Only the notification is built so far.
