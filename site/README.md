# glizzness.com — the unified site

The new, code-based **glizzness.com**: one cohesive site where every revenue lane
has a front door. Built from the business north-star
(`../docs/superpowers/specs/2026-07-06-glizzness-north-star.md`, §12). This
**replaces** the fragmented setup (GoDaddy builder homepage + loose `menu.html` /
`catering.html` at the repo root + the Netlify map).

> Status: **LIVE** — deployed to Cloudflare Pages (glizzness.pages.dev) on 2026-07-12.
> Custom domain glizzness.com via GoDaddy DNS is still pending (see "Deploy" below).

---

## Pages

| File | URL | Purpose |
|---|---|---|
| `index.html` | `/` | Home — brand, "where's the cart," the four lanes, why-us, menu teaser |
| `our-menu.html` | `/our-menu` | Full menu — rendered from `menu.json` by `gen_menu.py` (the source of truth; Square is downstream) |
| `order.html` | `/order` | Delivery / pickup — DoorDash |
| `catering.html` | `/catering` | Catering **and** corporate/workplace — 8 packages + booking form |
| `events.html` | `/events` | Where we vend — **"Upcoming stops" calendar** (live from Supabase `cart_schedule`) + map teaser (hidden/coming soon) + book-your-event/venue |
| `404.html` | any miss | Branded not-found |

Shared, reused verbatim on every page: the top nav and the footer.

## Design system — `assets/site.css`

- **Palette = the condiments.** Near-black `#0e0d0a`, mustard-**gold** `#ffd700`
  (primary), **ketchup red** `#c1301a` (secondary — order/delivery), plus a
  **cream** `#fbf7ea` break so it isn't monotone black. DoorDash red `#ff3008`
  is used only on the DoorDash button.
- **Type:** *Anton* (condensed poster / menu-board display, used big and sparingly)
  + *Inter* (body), via Google Fonts with system fallbacks so it still renders offline.
- **Signature:** the **mustard-drizzle squiggle** (inline SVG) — the recurring
  section accent. It's literally the product, not a generic gradient bar.
- Component classes are prefixed/BEM-ish to avoid selector collisions. Bands
  alternate `--dark` / `--ink2` / `--cream` for rhythm.
- Quality floor: responsive to mobile, visible keyboard focus, `prefers-reduced-motion`
  respected, skip-link.

## Behavior — `assets/site.js` + `assets/config.js`

- **Progressive enhancement:** every page works with JS off. The booking form
  degrades to call/text/email.
- `config.js` holds the public constants: Supabase URL + **anon** key (INSERT-only
  into `catering_leads`, no read policy — safe to expose), phone `314-266-8636`,
  email `glizzness@gmail.com`, DoorDash store `38788821`, and the **Facebook +
  Instagram URLs** (both set — the "follow us" buttons show once a URL is present).
- The catering form POSTs a lead to Supabase `catering_leads` (`source: site_catering`),
  same table + schema as the standalone catering page (`../catering/`).
- **Where We Vend** — `events.html` fetches Supabase `cart_schedule` (anon key, read-only) and
  renders "Upcoming stops": public dates show venue + location, private dates show only
  "Booked — Unavailable". Data is a **sanitized** mirror of the Google Calendar, written
  server-side by `../sync_calendar.py`. Setup + activation: `../CALENDAR_SETUP.md`, `../GO_LIVE.md` §3.
  Degrades to a "coming soon" message if the table/sync isn't live yet.

## Deploy — Cloudflare Pages (do NOT touch GoDaddy yet)

Decision from planning: **code-based site, hosted on Cloudflare Pages**, GoDaddy
stays the **domain registrar only**, lanes live on **subdomains** with a shared
design system. Netlify was dropped (hit its cap).

When ready to go live:

1. **Push** this repo to GitHub (already the remote).
2. **Cloudflare Pages → Create project → Connect to Git.** Framework preset:
   **None** (static). **Build command:** *(none)*. **Build output directory:** `site`.
3. First deploy lands on `*.pages.dev` — **verify everything there** before any DNS change.
4. **Then** (separate, deliberate step) point the domain: add `glizzness.com` (and/or
   the `www`/subdomain) as a custom domain in Cloudflare Pages and update the DNS
   record at GoDaddy. **Not done here** — this is the only step that touches GoDaddy,
   and it's left for when you're ready.

`_redirects` handles friendly aliases (`/book`, `/delivery`, `/festivals`, …).

## Imagery

`assets/img/` mixes **real photos** and **AI-generated backgrounds**.

- **Real photos** (anything a customer could mistake for the product): `day1-cart.jpg`
  (the 2022 day-one cart — Our Story), `cart-mizzou.jpg` (the cart on MU campus),
  `glizzy.jpg` (a real loaded Glizzy), `logo.jpg` (the brand mark).
- **AI section backgrounds** — atmosphere only, no food or carts. Local SDXL /
  Juggernaut-XL on the RTX 3080 via the `inoculated-by-the-phoenix` genai pipeline;
  regenerate via `comfy_gen.py` + re-run the compressor. Each sits under a dark CSS
  overlay so text stays readable: `hero-smoke.jpg`, `section-gold.jpg`, `menu-grill.jpg`,
  `order-motion.jpg`, `catering-embers.jpg`, `events-bokeh.jpg`.

> **Rule:** never use AI-generated food or cart imagery — it reads as fabricated, which is
> poison for a real food business. Real photos only for anything depicting the product.
> Also do not use the cart manufacturer's marketing photo (it isn't our cart, and it's
> their copyrighted image).

## TODO before launch

- [ ] **More real food photos** — individual menu items still have no photos. Shoot them
      and drop them in `assets/img/`.
- [x] **Social URLs** — Facebook + Instagram are set in `config.js`; the
      "follow us" buttons render.
- [ ] **Confirm the DoorDash storefront** resolves and the store shows as
      "The Glizzness" (the Order page falls back to "search The Glizzness" if the
      link is unset).
- [ ] **"Where's the cart"** on the home hero is static copy — decide whether to
      wire it to live data later (the vending map data exists in Supabase, but the
      **map stays hidden** for now per direction).
- [ ] **Retire the old pages** once this is live: root `menu.html`, `catering.html`,
      and the GoDaddy builder homepage.
- [ ] Deploy to Cloudflare Pages, verify on `*.pages.dev`, **then** update DNS.

## Local preview

```
# from the repo root
python -m http.server 8011
# open http://127.0.0.1:8011/site/
```
