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

- [ ] **Catering / "Book the cart" booking backend** — partially built; see `CATERING_LEADS.md` for the
  live pipeline. Form (`catering.html#book`) INSERTs a row into Supabase `catering_leads`.
  - **(a) Notification — ✅ DONE (2026-07-13).** Supabase Database Webhook on `catering_leads` INSERT →
    Make.com scenario → Gmail sends a formatted alert to glizzness@gmail.com. (Runbook: `CATERING_LEADS.md`.)
  - **(b) Triage / status** — *still open.* Track a lead new → contacted → booked → done (a status column +
    a simple admin view, or just work them in the Supabase table).
  - **(c) Calendar** — *still open.* Should a *confirmed* booking become a Google Calendar event? (would then
    flow to Where-We-Vend via `sync_calendar.py` if marked Public). Decide manual vs. automatic.
  - **(d) Auto-reply** — *still open.* Send the customer a "thanks, we'll be in touch" confirmation on submit.
  - **(e) Where leads live day-to-day** — *still open.* The operator's actual working view of the pipeline.
  *(added 2026-07-12; notification shipped 2026-07-13)*

- [ ] **Add niche event sources + event-type sorting to the vending map** — high-value niches food carts
  can hit that aren't in the general festival lists:
  - **Mountain-bike festivals** (booming in MO & AR) — sources: https://www.lokievents.com/ and
    https://www.bikereg.com/events
  - **Sports tournaments** (captive, hungry crowds) — source: https://www.tournamentlinks.com/
  Mine these into the vending-circuit dataset, and add a **category / event-type filter** to the map
  (festivals, concerts, music venues, mountain-bike events, sports tournaments, fairs, …) so we can sort by
  type. *(added 2026-07-12)*
