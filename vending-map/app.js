/* The Glizzness — Vending Circuit map (two-tier, lazy render).
   Tier 1: market hub pins. Tier 2: events of the selected market. Tier 3: detail drawer.
   Reads Supabase REST with the public anon key (vending_* tables have public-read RLS). */

const URL = window.SUPABASE_URL, KEY = window.SUPABASE_ANON_KEY;
const HEADERS = { apikey: KEY, Authorization: "Bearer " + KEY };

const statusEl = document.getElementById("status");
const crumbEl  = document.getElementById("crumb");
const backBtn  = document.getElementById("back");
const drawer   = document.getElementById("drawer");
const drawerBody = document.getElementById("drawer-body");

let MARKETS = [], EVENTS = [], marketsById = {};
let marketLayer = L.layerGroup(), eventLayer = L.layerGroup();

const map = L.map("map", { zoomControl: true }).setView([39.2, -93.0], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);
marketLayer.addTo(map);
eventLayer.addTo(map);

async function fetchJSON(path) {
  const res = await fetch(URL + "/rest/v1/" + path, { headers: HEADERS });
  if (!res.ok) throw new Error(res.status + " " + res.statusText + " — " + (await res.text()));
  return res.json();
}

const friendlyColor = f =>
  f === "explicit_yes" ? "#5bbf6a" : f === "unconfirmed" ? "#e0b14a" : "#5aa7e0";

function setStatus(msg) { statusEl.textContent = msg; statusEl.style.display = msg ? "block" : "none"; }

// ---------- Tier 1: markets ----------
function showMarkets() {
  eventLayer.clearLayers();
  marketLayer.clearLayers();
  drawer.classList.remove("open");
  backBtn.style.display = "none";
  const counts = {};
  EVENTS.forEach(e => { counts[e.market_id] = (counts[e.market_id] || 0) + 1; });

  const pts = [];
  MARKETS.forEach(m => {
    if (m.center_lat == null || m.center_lng == null) return;
    const n = counts[m.id] || 0;
    const mk = L.circleMarker([m.center_lat, m.center_lng], {
      radius: Math.min(10 + n, 26), color: "#7a5a1e", weight: 2,
      fillColor: "#e8a33d", fillOpacity: 0.9
    }).bindTooltip(`${m.name} — ${n} event${n === 1 ? "" : "s"}`, { direction: "top" });
    mk.on("click", () => selectMarket(m.id));
    marketLayer.addLayer(mk);
    pts.push([m.center_lat, m.center_lng]);
  });
  if (pts.length) map.fitBounds(pts, { padding: [40, 40] });
  crumbEl.textContent = `${MARKETS.length} markets · ${EVENTS.length} events`;
}

// ---------- Tier 2: events in a market ----------
function selectMarket(id) {
  const m = marketsById[id];
  const evs = EVENTS.filter(e => String(e.market_id) === String(id));
  marketLayer.clearLayers();
  eventLayer.clearLayers();
  backBtn.style.display = "inline-block";
  crumbEl.textContent = `${m.name} · ${evs.length} event${evs.length === 1 ? "" : "s"}`;

  const pts = [];
  evs.forEach(e => {
    if (e.lat == null || e.lng == null) return;
    const mk = L.circleMarker([e.lat, e.lng], {
      radius: 8, color: "#000", weight: 1,
      fillColor: friendlyColor(e.food_truck_friendly), fillOpacity: 0.95
    }).bindTooltip(e.name, { direction: "top" });
    mk.on("click", () => openDrawer(e));
    eventLayer.addLayer(mk);
    pts.push([e.lat, e.lng]);
  });
  if (pts.length) map.fitBounds(pts, { padding: [60, 60], maxZoom: 12 });
  else if (m.center_lat != null) map.setView([m.center_lat, m.center_lng], m.default_zoom || 9);
}

// ---------- Tier 3: detail drawer ----------
function badge(text, cls) { return `<span class="badge ${cls}">${text}</span>`; }

function openDrawer(e) {
  const friendly = {
    explicit_yes:  badge("Food-truck friendly", "b-green"),
    concession_friendly: badge("Concession friendly", "b-blue"),
    unconfirmed:   badge("Food fit unconfirmed", "b-amber"),
    excluded:      badge("Not food-truck", "b-red")
  }[e.food_truck_friendly] || "";
  const verify = e.needs_confirmation === true || e.needs_confirmation === "true"
    ? badge("Verify before relying", "b-amber") : "";
  const typeB = badge((e.event_type || "").replace(/_/g, " "), "b-grey");

  const rows = [];
  const add = (label, val) => { if (val) rows.push(`<dt>${label}</dt><dd>${val}</dd>`); };
  add("When", e.typical_dates || e.month);
  add("Size / attendance", e.attendance_text);
  add("Distance from Columbia", e.distance_from_columbia_mi ? e.distance_from_columbia_mi + " mi (" + (e.trip_type || "").replace("_", " ") + ")" : "");
  add("Apply via", e.application_method);
  const contact = [e.contact_name, e.contact_email, e.contact_phone].filter(Boolean).join(" · ");
  add("Contact", contact);
  add("Fee", e.food_vendor_fee && e.food_vendor_fee !== "Not researched" ? e.food_vendor_fee : "");
  add("Notes", e.notes);

  const home = e.homepage_url
    ? `<a class="home" href="${/^https?:\/\//.test(e.homepage_url) ? e.homepage_url : "https://" + e.homepage_url}" target="_blank" rel="noopener">Event page ↗</a>`
    : "";

  drawerBody.innerHTML = `
    <h2>${e.name}</h2>
    <div class="loc">${e.city}, ${e.state}</div>
    <div>${typeB}${friendly}${verify}</div>
    <dl>${rows.join("")}</dl>
    ${home}`;
  drawer.classList.add("open");
}

document.querySelector("#drawer .close").addEventListener("click", () => drawer.classList.remove("open"));
backBtn.addEventListener("click", showMarkets);

// ---------- boot ----------
(async function init() {
  if (!KEY || KEY.includes("PASTE_YOUR")) {
    setStatus("⚠ Set SUPABASE_ANON_KEY in config.js to load data."); return;
  }
  try {
    setStatus("Loading…");
    [MARKETS, EVENTS] = await Promise.all([
      fetchJSON("vending_markets?select=*&order=id"),
      fetchJSON("vending_events?select=*&verification_status=in.(verified,partial)&food_truck_friendly=neq.excluded&lat=not.is.null")
    ]);
    marketsById = Object.fromEntries(MARKETS.map(m => [String(m.id), m]));
    setStatus("");
    showMarkets();
  } catch (err) {
    setStatus("Load error: " + err.message);
    console.error(err);
  }
})();
