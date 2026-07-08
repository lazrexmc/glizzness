# The Glizzness — Business North-Star

*Living strategic guide — the single source of truth that points the cart, website, social, and menu in the same direction. Update it as lanes prove out or the numbers move.*
*Last updated: 2026-07-06 · Owners: Lance (systems/strategy) + Trint (operator/chef)*

---

## 1. The One-Liner
The Glizzness is a Columbia, MO chef-driven hot-dog cart that just turned profitable — and the plan is to **stop chasing low-value foot traffic and fill the week with the things that reliably clear $500+/day** (events, catering, corporate accounts, delivery), earning our way up to a food truck or a brick-and-mortar.

## 2. The Goal (success, concretely)
- **Daily floor:** every working day should project **$750+ in sales** — the number Trint can actually see day-of. (At ~57% margins that's ~$425 gross before fuel/setup, so it's the practical go/no-go line; under it, don't roll out.)
- **Weekly engine:** a repeatable mix of **booked, prepaid, weather-proof** revenue — not hope-based streetside.
- **Upgrade ladder:** (1) a used **trailer (~$1–2k)** to unlock reachable regional events → (2) a **food truck** → (3) a **brick-and-mortar** — funded by reinvested profit + a modest equipment loan, **not** by giving away equity.

## 3. Where We Are Now (honest snapshot)
| Year | Revenue | Owner profit (SDE) | Gross margin |
|---|---|---|---|
| 2023 | $49.5k | −$11.2k | 28% |
| 2024 | $49.3k | −$9.1k | 42% |
| 2025 | $56.0k | **+$2.5k** | 57% |
| 2026 YTD (thru Jun) | $26.6k | **+$8.5k** | 57% |

- **2025 was the first profitable year; 2026 is tracking far better.** This is an inflection, not a rescue.
- **What makes money:** event days at **$2,000+**. **What doesn't:** random streetside foot traffic (~$50 days that burn capital and morale). The whole strategy follows from this one fact.

## 4. Hard Constraints (the strategy must respect these)
- **The cart can't travel far.** Trint has a truck + SUV, but **no trailer** — the small cart is towable on Boone County back roads only; anything past that needs a flatbed trailer we don't own yet. → **Local is the game until we buy a trailer.**
- **Columbia's seasonality is inverted:** great when MU is in session (fall/spring), **dead** at peak fair/festival summer. → summer demands counter-cyclical revenue.
- **Solo operator; no A/C in the cart.** Real limits on how many lanes run at once, and on comfort.
- **Strengths to exploit:** Trint holds a culinary degree (Art Institute of Phoenix), and the cart is a **full portable kitchen** (grill, hot wells, ice-packed cold wells, customer toppings bar). Menu quality and variety are an edge, not a limit.

## 5. Who We Serve
- **Nightlife & event crowds** — breweries, concerts, festivals, Show-Me State Games.
- **Delivery customers** — the brewery/late-night crowd already ordering delivery right past us.
- **Catering clients** — parties, weddings, grad parties, church/community events.
- **Local employers (NEW)** — big Columbia workplaces for prepaid cart days + boxed drop-offs.
- **MU campus** — students & staff during the school year (permitted cart program).

## 6. Revenue Lanes (ranked by ease × margin × predictability, for a towing-constrained solo cart)
Ranked deliberately: **the prepaid, bulk, low-hassle lanes come first.** Catering and corporate drop-offs are the easiest money we can make — booked ahead, made in bulk, no platform middleman — and they beat juggling three delivery apps for commission-thin per-order sales.

1. **Catering** — the easiest, highest-margin lane: booked ahead, **prepaid**, made in bulk, weather/towing-proof. Booking page → Supabase `catering_leads` is built. *Status: needs final deploy + the marketing push.*
2. **Corporate & Workplace Accounts (prepaid)** — recurring **drop-off lunches** and on-site **cart days** for big Columbia employers. **In-town = reachable, prepaid = no-risk, recurring = predictable — and far simpler than the delivery apps.** Internal prospect sheet (NOT on the public events map). *Status: verified target list in research — see below.*
   > **Target list: `CorporateProspects.md`** (verified against REDI's official employer roster). Tier-1 bullseyes (big office staff, likely no cafeteria): **Veterans United** (~2,800 — #1), **EquipmentShare** (~600, growing fast), **Shelter Insurance**, Schneider Electric, Watlow, Central Bank, Midway USA, MBS. Tier-2 (event/appreciation): MU depts, MU Health Care, Boone Health, CPS, City/County (Boone Co HR contact verified), + the Kraft Heinz **Oscar Mayer hot-dog plant**. Cannabis: Hippos, Good Day Farm.
3. **Reachable local events & nightlife** — the proven **$2,000 days**, limited to safe local/back-road range: breweries (Logboat/Bur Oak/Cooper's Landing), Show-Me State Games (⏰ Jul 17-19 / 24-26), First Fridays, festivals. Backed by the 415-event vending map. **Best play: be at the venue AND on the delivery apps** to catch both crowds.
4. **Delivery / ghost kitchen (DoorDash / GrubHub / UberEats) at Flyover** — captures the delivery demand we've watched walk past the cart, and it's counter-seasonal. **But it's the operationally heaviest lane** — 15–30% platform commissions, packaging, and per-order logistics across three apps — so it ranks *below* the prepaid lanes even though the demand is real. *Status: DoorDash live (store `38788821`); Square menu just cleaned & taxed.*
5. **Mizzou campus vending** — permitted Food Cart agreement (~$500/yr, school-year = our money season). The **On-Demand add-on lets student orgs / Greek life book the cart**. *Status: renew FY27 before fall (Casey Forbis / EHS).*
6. **Kill random streetside.** The ~$50/day morale-killer. Only known-good spots (MU game days, downtown events) — never "park and hope."

## 7. Menu & Operations
- **Square is the single source of truth** for the menu → auto-feeds DoorDash. Just cleaned (2026-07-06): 67 → **37 items** in real sections (Glizzies / Not-a-Glizzy / Vegetarian / Sides / Drinks / Cart-Only), **all collecting 7.975% sales tax**, 30/37 described. Tooling: `catalog_*.py`.
- **Flyover commissary** = legal prep + the ghost-kitchen base for delivery.
- **Books on autopilot:** Square → Wave automation + Supabase/Streamlit dashboards (Lance's systems). Sales tax now auto-collected (was hand-trued).
- **Menu is flexible** — Trint builds custom/upscale for catering & corporate.

## 8. Marketing & Social
- **~4,000 FB + ~4,000 IG followers = the demand engine, and it's underused.** They drive catering leads, delivery orders, and "where's the cart today / order tonight."
- **Automate it** (Lance's systems): scheduled posts, an auto-reply on new `catering_leads`, "today's location / order delivery" pushes.
- **B2B outreach** (email/DM/in-person) to the corporate target list is the highest-value, most repeatable marketing we can do.

## 9. Competition & Our Edge
- **2 Odd Dawgs** (another Columbia hot-dog cart) + ~20 local food trucks.
- **Our edge:** chef-driven quality & variety (not just dogs), a real brand ("Glizzy"), reach across catering + corporate + delivery, and Lance's systems/automation that most one-person carts don't have.

## 10. The Money & the Path
- Margins are healthy (~57%). The problem was never the product — it was **too many low-value days.** The fix is filling the week with **$1,000+ booked days** (events, catering, corporate, delivery volume).
- **Cash infusion:** reinvested profit + a small **equipment loan** for the trailer (the 2025→2026 SDE trend is the lender story) beats giving up equity in a ~$15–30k business. A **strategic partner** (who brings a truck/trailer/location) or **small-business grants** are the only "investor" angles worth chasing.
- **The trailer (~$1–2k) is the single highest-leverage purchase** — it turns the 400-event regional map from aspiration into reachable revenue.

## 11. Roadmap — Now / Next / Later
**Now (this month):**
- ⏰ **Show-Me State Games** — call Jessie Sida (573-884-2946) about food vending (Jul 17-19 / 24-26).
- **Finish the catering page deploy** (blocked on the Netlify cap → Cloudflare Pages or drag-drop) + launch the follower/B2B marketing push.
- **Renew the Mizzou FY27 agreement** before fall (Casey Forbis / EHS; COI to risk@umsystem.edu).
- **Confirm the DoorDash/GrubHub ghost kitchen** at Flyover; push it to the 4k followers.
- **Pilot the corporate lane** — 3 first calls (e.g., Veterans United, one dispensary, one hospital) once the prospect list lands.

**Next (1–3 months):**
- **Buy a used trailer** → open up reachable regional events.
- **Rebuild glizzness.com** as one cohesive site (see §12).
- **Historical sales-tax true-up audit** (Square→Wave) for the pre-fix period.

**Later:**
- Food truck → brick-and-mortar, funded by the improved profit.

## 12. How Website / Social / Cart Serve the Plan
The web presence is currently fragmented (GoDaddy builder homepage + the map on Netlify + a half-deployed catering page + an unlinked `menu.html`). The rebuild goal: **one cohesive glizzness.com** where every lane has a front door:
- **Home** → brand + "where's the cart today" status.
- **Order** → DoorDash (the delivery lane).
- **Menu** → live from Square (single source of truth).
- **Catering / Corporate** → the booking form (→ Supabase leads).
- **Where We Vend** → the events map.
- **Social** → the funnel feeding all of the above.

*This §12 is the bridge to the next design — the unified-site spec — which we'll write once this north-star is agreed. The website exists to serve the lanes above; we design it from this plan, not the other way around.*

---
*Living doc. When a lane proves out (or dies), or the numbers move, update it here first.*
