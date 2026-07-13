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

## Auto-reply to the customer (confirmation email)

A **second** email in the SAME Make scenario — but instead of the shop inbox, it goes back to the
person who submitted, so they instantly know we got them. **Email is OPTIONAL on the form** (only
`name` + `phone` are required), so this must fire **only when an email was actually given**.

**Make.com steps (append to the existing `catering-lead-notify` scenario — don't build a new one):**

1. After the existing owner-notify **Gmail › Send an email** module, add **another** Gmail › Send an
   email module (call it module 3).
2. On the link feeding module 3, add a **Filter** (click the wrench/spanner on the connector). Set the
   condition: **`record: email`  →  Contains  →  `@`**. An empty/blank email can't contain "@", so
   no-email leads are simply skipped — no errors, no blank sends.
   - **⚠ GOTCHA (cost us a test):** the operator dropdown **defaults to "Text operators: Equal to"** — you
     MUST change it to **Contains**. `email Equal to @` is always false, so it silently blocks *every*
     auto-reply. **Tell-tale:** the Make run log shows only **2 operations** (webhook + owner email) instead
     of **3**. A passing run = 3 operations.
3. In module 3: **To** = `record: email` (expand `record`, pick the `email` leaf — same gotcha #2 as
   below). **Subject** + **Body** = the copy below; map `record: name` into the two `{{name}}` spots.
   Body type = **"collection of contents (text)"**, same as the notify module.
4. Save. The scenario is already **ON**.

**The copy** (plain text — `{{name}}` is the `record: name` mapping):

```
Subject:  Thanks, {{name}} — we got your Glizzness request 🌭

Hi {{name}},

Thanks for reaching out to The Glizzness — your catering request just landed
in our inbox and we're on it.

Here's what's next: we'll get back to you by call or text, usually within a
day, to lock in the details and build the right menu for your crowd. If your
date is coming up fast, don't wait on us — give us a shout anytime.

  Call or text:  314-266-8636
  Email:         glizzness@gmail.com

Can't wait to bring the fun to the bun for you.

— Trint & the Glizzness crew
```

**Why "call or text," not "reply to this email":** phone is the required field and email is optional, so
the real follow-up happens by phone — the copy sets that expectation. Replies still land in
glizzness@gmail.com anyway (it sends from the connected Gmail), so a reply is fine too.

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

> Built & LIVE: the **owner notification** + the customer **auto-reply** (both verified end-to-end
> 2026-07-13). Still open (see `TODO.md`): lead **status tracking**, optional **calendar** on confirmed
> bookings, and an operator **working view**.
