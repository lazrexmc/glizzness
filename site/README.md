# glizzness.com — the unified site (scaffold)

The new, code-based **glizzness.com**: one cohesive site where every revenue lane
has a front door. Built from the business north-star
(`../docs/superpowers/specs/2026-07-06-glizzness-north-star.md`, §12). This
**replaces** the fragmented setup (GoDaddy builder homepage + loose `menu.html` /
`catering.html` at the repo root + the Netlify map).

> Status: **scaffold, not deployed.** GoDaddy DNS is intentionally untouched.
> Nothing here is live until someone deploys it (see "Deploy" below).

---

## Pages

| File | URL | Purpose |
|---|---|---|
| `index.html` | `/` | Home — brand, "where's the cart," the four lanes, why-us, menu teaser |
| `menu.html` | `/menu` | Full menu (from Square, the single source of truth) |
| `order.html` | `/order` | Delivery / pickup — DoorDash |
| `catering.html` | `/catering` | Catering **and** corporate/workplace — 8 packages + booking form |
| `events.html` | `/events` | Where we vend — **map hidden** (coming soon) + book-your-event/venue |
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
  email `glizzness@gmail.com`, DoorDash store `38788821`, and **empty social URLs**
  (fill these in — links stay hidden until set).
- The catering form POSTs a lead to Supabase `catering_leads` (`source: site_catering`),
  same table + schema as the standalone catering page (`../catering/`).

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

All images in `assets/img/` are AI-generated (local SDXL / Juggernaut-XL on the RTX 3080,
from the `inoculated-by-the-phoenix` genai pipeline). Regenerate/retune via `comfy_gen.py`
+ re-run the compressor.

- **Section backgrounds** (atmosphere, no fake food) — sit under a dark CSS overlay so
  text stays readable: `hero-smoke.jpg` (home hero), `section-gold.jpg` (home menu
  texture), `menu-grill.jpg` (menu header), `order-motion.jpg` (order hero),
  `catering-embers.jpg` (catering hero), `events-bokeh.jpg` (events hero).
- **Feature panels** (image boxes, real subjects): `feat-kitchen.jpg` (home — flat-top),
  `feat-cart.jpg` (home — cart at a night market), `feat-event.jpg` (order — cart at an event).

## TODO before launch

- [ ] **Real food photos** — the menu items still have no photos, and the feature panels
      use AI *ambiance* shots (cart/grill/event), not the actual Glizzy. AI can't honestly
      stand in for a specific menu item — shoot real cart/food photos and swap them in.
- [ ] **Social URLs** — set `GLIZZNESS_FACEBOOK` / `GLIZZNESS_INSTAGRAM` in
      `config.js` (links + "follow us" buttons are hidden until then).
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
