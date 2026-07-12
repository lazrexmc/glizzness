# The Glizzness — TODO / Backlog

Running list of open action items. Add dated entries; check them off or delete when done.
(For the full go-live sequence see `GO_LIVE.md`; for strategy see the north-star spec.)

## Open

- [ ] **Find Trint a verified food supplier that will deliver to us** — a distributor/wholesaler
  willing to deliver despite (a) currently **low volume** and (b) **no fixed home / commercial
  address** (cart + Flyover commissary, no brick-and-mortar). Most big distributors (Sysco, US Foods)
  require order minimums and a business delivery address, so the task is finding one that works at our
  scale — e.g. Restaurant Depot / cash-and-carry, a regional/local distributor, or a supplier that
  delivers to the commissary. *(added 2026-07-10)*

- [ ] **Design the catering / "Book the cart" booking backend** — the `catering.html#book` form is in its
  infancy: today it only **INSERTs a row into Supabase `catering_leads`** (write-only for the public; you
  read leads with the service_role key in the Supabase SQL editor / dashboard). That is the *entire* backend
  right now. Decide the full flow:
  - **(a) Notification** — how does Trint/Lance find out a lead arrived? (email/SMS to glizzness@gmail.com /
    314-266-8636 — e.g. a Supabase Edge Function → email, a webhook/Zapier, or a small polling script).
  - **(b) Triage / status** — track a lead new → contacted → booked → done (a status column + a simple admin
    view, or just work them in the Supabase table).
  - **(c) Calendar** — should a *confirmed* booking become a Google Calendar event? (which would then flow to
    the Where-We-Vend page via `sync_calendar.py` if marked Public). Decide manual vs. automatic.
  - **(d) Auto-reply** — send the customer a "thanks, we'll be in touch" confirmation on submit.
  - **(e) Where leads live day-to-day** — the operator's actual working view of the pipeline.
  *(added 2026-07-12)*
