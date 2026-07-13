# Glizzness Catering — Marketing Kit

Ready-to-post content to point your ~4,000 FB/IG followers (and local businesses) at the new
booking page. Replace `{{BOOKING_URL}}` (e.g. `catering.glizzness.com`) and `{{PHONE}}` before posting.

The goal: turn latent demand into booked, high-margin catering ($350–$1,100/event) — weather-proof,
towing-proof, booked in advance. This is the lane that doesn't depend on foot traffic.

---

## Social posts (FB + IG)

**1 — Launch announcement (pin this)**
> 🌭 You can now BOOK The Glizzness for your event in 60 seconds.
> Grad parties, office lunches, game days, weddings, church events, team nights — we bring the
> cart, the grill, and a made-to-order menu right to you. Packages from $350.
> 👉 Book now: {{BOOKING_URL}}  ·  or call/text {{PHONE}}

**2 — Package spotlight (rotate weekly)**
> Feeding a crowd? **The Glizzy Beast** — 50 guests, premium dogs + brats, chili, pulled pork,
> house-made queso — $450, one hour of on-site service included. 🔥
> Lock your date 👉 {{BOOKING_URL}}

**3 — "We cater ANYTHING"**
> Not just hot dogs — tell us your vision and we'll build a custom menu for your event.
> Nacho bars, brats & sausages, full spreads, and more.
> Fully customizable 👉 {{BOOKING_URL}}

**4 — Seasonal / urgency (swap the occasion)**
> Graduation season is here 🎓 — book The Glizzness before your date's gone. Made to order, delivered
> hot, zero cleanup for you. Dates fill fast in {month}. 👉 {{BOOKING_URL}}
> _(Rotate the hook: grad parties → summer BBQs → back-to-school/Mizzou move-in → tailgates →
>  holiday parties. Post 2–3×/week; boost the launch post with $20–30 targeted to Columbia + 25mi.)_

---

## Local business outreach (B2B — highest-value, most repeatable)

Columbia businesses book recurring lunches and events. One landed office account = steady revenue.

**Email / DM template**
> Subject: Feeding your team or event? The Glizzness caters Columbia 🌭
>
> Hi {name} — I run The Glizzness, a Columbia food cart with a made-to-order menu. We cater office
> lunches, client events, staff appreciation days, and parties — packages from $350, fully
> customizable, delivered hot with on-site service.
>
> Would a team lunch be useful this month? You can see packages and grab a date here: {{BOOKING_URL}}
> — or just reply and I'll take care of it. Thanks! — Trint, The Glizzness · {{PHONE}}

**Hit list (Columbia):** real-estate & insurance offices, car dealerships, apartment complexes
(resident events), churches, MU Greek life & student orgs, gyms/CrossFit boxes, medical/dental
offices, banks/credit unions, HR teams (staff-appreciation lunches), wedding & event venues
(get on their preferred-vendor lists).

---

## Make it automatic (ties into the existing systems)

- **Lead auto-reply:** a Supabase Database Webhook on `catering_leads` INSERT → instant text/email
  to Trint + an auto "we got your request!" reply to the customer. (Ask Lance/Claude to wire this.)
- **Scheduled posting:** queue the posts above (Meta Business Suite is free) so the feed stays
  active without daily effort.
- **Lead dashboard:** surface `catering_leads` (status new → contacted → booked) alongside the
  existing Streamlit/Supabase dashboards so nothing slips.
