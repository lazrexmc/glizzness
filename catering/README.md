# Glizzness Catering — Booking Page

A self-contained catering menu + **booking form** that captures leads straight into Supabase.
Built 2026-07-06 as the first "cash infusion" move (see the growth strategy): turn the catering
menu from a dead-end brochure into a lead funnel. Catering is high-margin, booked ahead, and
weather/towing-proof — the lane that doesn't depend on foot traffic.

## Files
| File | Purpose |
|---|---|
| `index.html` | The menu (8 packages, $350–$1,100) + hero "Book" CTA + per-package "Request this package" buttons + a booking form. Vanilla HTML/CSS/JS, no build. |
| `config.js` | Supabase URL + **anon** key (public-safe) + booking phone/email for the fallback CTA. |
| `netlify.toml` | Site config so its Netlify site publishes THIS folder (see Deploy). |
| `MARKETING.md` | Ready-to-post social + B2B outreach content to drive traffic here. |
| `../supabase_catering_schema.sql` | The `catering_leads` table (run once in Supabase). |

## How it works
The form POSTs to `POST {SUPABASE_URL}/rest/v1/catering_leads` with the anon key and
`Prefer: return=minimal`. The `catering_leads` table has an **anon INSERT-only** RLS policy and
**no SELECT policy** — the public can submit a lead but cannot read leads back with the anon key.
Only the service_role (your dashboard / SQL editor) can read them:
`select * from catering_leads order by created_at desc;`

## Deploy — status + steps

**As of 2026-07-06: NOT yet fully deployed.** A Netlify site exists (`leafy-smakager-ba1103.netlify.app`)
but was serving the vending MAP, not this page — see the gotcha below. Remaining work:

1. **Create the table (once):** run `../supabase_catering_schema.sql` in the Supabase SQL editor.
2. **Host on Netlify — THE KEY SETTING is Base directory.** The repo-root `netlify.toml` pins
   `publish = "vending-map"` for *every* site built from this repo. To make the catering site serve
   THIS folder, set that Netlify site's **Base directory = `catering`** (Site configuration → Build &
   deploy → Build settings). That makes Netlify read `catering/netlify.toml` (publish `.`) instead of
   the root one. Leave the Publish-directory field **empty**. Then **Clear cache and deploy site**.
   - Verify in the deploy log: it should build/deploy (not "Skipped") and the publish path should be
     `.`/`catering`, NOT `vending-map`.
   - Guaranteed fallback if the base-directory route fights you: **drag-and-drop the `catering/` folder**
     onto the site's Deploys tab (manual deploy, no git config, but no auto-deploy on push).
3. **Domain:** Netlify → Add domain `catering.glizzness.com` → add a `catering` CNAME at GoDaddy →
   auto HTTPS. Then link a "Catering" button from the GoDaddy site menu.

## Next enhancements (not built)
- **Instant alert:** Supabase Database Webhook on `catering_leads` INSERT → text/email to Trint +
  auto "we got your request!" reply to the customer.
- **Lead dashboard:** surface `catering_leads` (status new → contacted → booked) in the Streamlit app.
