/* The Glizzness — Vending Circuit map (two-tier, lazy render).
   Tier 1: market hub pins. Tier 2: events of the selected market. Tier 3: detail drawer.
   Reads Supabase REST with the public anon key (vending_* tables have public-read RLS).
   Phase 6: month / friendliness / trip-type filters + a defunct/excluded toggle. */

const URL = window.SUPABASE_URL, KEY = window.SUPABASE_ANON_KEY;
const HEADERS = { apikey: KEY, Authorization: "Bearer " + KEY };

const statusEl = document.getElementById("status");
const crumbEl  = document.getElementById("crumb");
const backBtn  = document.getElementById("back");
const drawer   = document.getElementById("drawer");
const drawerBody = document.getElementById("drawer-body");

let MARKETS = [], EVENTS = [], marketsById = {}, monthsByEvent = {};
let currentMarket = null;                       // null = Tier 1; else selected market id
const FILT = { month: "all", friendly: "all", trip: "all", county: "all", showHidden: false };

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

// ---------- publish gate + filtering ----------
// "Published" mirrors the Supabase vending_published_events gate. Anything else
// (defunct / excluded) is hidden unless the user toggles it on.
const isPublished = e =>
  (e.verification_status === "verified" || e.verification_status === "partial")
  && e.food_truck_friendly !== "excluded";
const isHidden = e => !isPublished(e);

function passesFilter(e) {
  if (e.lat == null || e.lng == null) return false;
  if (!FILT.showHidden && isHidden(e)) return false;
  if (FILT.friendly !== "all" && e.food_truck_friendly !== FILT.friendly) return false;
  if (FILT.trip !== "all" && e.trip_type !== FILT.trip) return false;
  if (FILT.county !== "all" && (e.county || "") + "|" + (e.state || "") !== FILT.county) return false;
  if (FILT.month !== "all") {
    const ms = monthsByEvent[e.id] || [];
    // year-round / recurring events carry no month -> they match any month filter.
    if (ms.length && !ms.includes(Number(FILT.month))) return false;
  }
  return true;
}
const visibleEvents = () => EVENTS.filter(passesFilter);

const friendlyColor = e => {
  if (isHidden(e)) return "#d0594f";            // red — defunct / excluded
  const f = e.food_truck_friendly;
  return f === "explicit_yes" ? "#5bbf6a" : f === "unconfirmed" ? "#e0b14a" : "#5aa7e0";
};

function setStatus(msg) { statusEl.textContent = msg; statusEl.style.display = msg ? "block" : "none"; }

// ---------- Tier 1: markets ----------
function showMarkets() {
  currentMarket = null;
  eventLayer.clearLayers();
  marketLayer.clearLayers();
  drawer.classList.remove("open");
  backBtn.style.display = "none";

  const vis = visibleEvents();
  const counts = {};
  vis.forEach(e => { counts[e.market_id] = (counts[e.market_id] || 0) + 1; });

  const pts = [];
  MARKETS.forEach(m => {
    if (m.center_lat == null || m.center_lng == null) return;
    const n = counts[m.id] || 0;
    const mk = L.circleMarker([m.center_lat, m.center_lng], {
      radius: n ? Math.min(10 + n, 26) : 8, color: "#7a5a1e", weight: 2,
      fillColor: n ? "#e8a33d" : "#5a4a2e", fillOpacity: n ? 0.9 : 0.3
    }).bindTooltip(`${esc(m.name)} — ${n} event${n === 1 ? "" : "s"}`, { direction: "top" });
    if (n) { mk.on("click", () => selectMarket(m.id)); pts.push([m.center_lat, m.center_lng]); }
    marketLayer.addLayer(mk);
  });
  if (pts.length) map.fitBounds(pts, { padding: [40, 40] });
  crumbEl.textContent = `${MARKETS.length} markets · ${vis.length} event${vis.length === 1 ? "" : "s"}`;
}

// ---------- Tier 2: events in a market ----------
function selectMarket(id) {
  currentMarket = id;
  const m = marketsById[id];
  const evs = visibleEvents().filter(e => String(e.market_id) === String(id));
  marketLayer.clearLayers();
  eventLayer.clearLayers();
  backBtn.style.display = "inline-block";
  crumbEl.textContent = `${m.name} · ${evs.length} event${evs.length === 1 ? "" : "s"}`;

  const pts = [];
  evs.forEach(e => {
    if (e.lat == null || e.lng == null) return;
    const mk = L.circleMarker([e.lat, e.lng], {
      radius: 8, color: "#000", weight: 1,
      fillColor: friendlyColor(e), fillOpacity: 0.95
    }).bindTooltip(esc(e.name), { direction: "top" });
    mk.on("click", () => openDrawer(e));
    eventLayer.addLayer(mk);
    pts.push([e.lat, e.lng]);
  });
  if (pts.length) map.fitBounds(pts, { padding: [60, 60], maxZoom: 12 });
  else if (m.center_lat != null) map.setView([m.center_lat, m.center_lng], m.default_zoom || 9);
}

// re-render the current tier after a filter change
function applyFilters() {
  if (currentMarket != null && marketsById[currentMarket]) selectMarket(currentMarket);
  else showMarkets();
}

// ---------- Tier 3: detail drawer ----------
const ESC = { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" };
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ESC[c]);
function badge(text, cls) { return `<span class="badge ${cls}">${esc(text)}</span>`; }

function openDrawer(e) {
  const friendly = {
    explicit_yes:  badge("Food-truck friendly", "b-green"),
    concession_friendly: badge("Concession friendly", "b-blue"),
    unconfirmed:   badge("Food fit unconfirmed", "b-amber"),
    excluded:      badge("Not food-truck", "b-red")
  }[e.food_truck_friendly] || "";
  const statusB = e.verification_status === "defunct" ? badge("Defunct", "b-red")
    : (e.verification_status === "excluded" || e.food_truck_friendly === "excluded")
      ? badge("Excluded — not vending", "b-red") : "";
  const verify = e.needs_confirmation === true || e.needs_confirmation === "true"
    ? badge("Verify before relying", "b-amber") : "";
  const typeB = badge((e.event_type || "").replace(/_/g, " "), "b-grey");

  const rows = [];
  const add = (label, val) => { if (val) rows.push(`<dt>${esc(label)}</dt><dd>${esc(val)}</dd>`); };
  add("When", e.typical_dates || e.month);
  add("Size / attendance", e.attendance_text);
  add("Distance from Columbia", e.distance_from_columbia_mi ? e.distance_from_columbia_mi + " mi (" + (e.trip_type || "").replace("_", " ") + ")" : "");
  add("Apply via", e.application_method);
  const contact = [e.contact_name, e.contact_email, e.contact_phone].filter(Boolean).join(" · ");
  add("Contact", contact);
  add("Fee", e.food_vendor_fee && e.food_vendor_fee !== "Not researched" ? e.food_vendor_fee : "");
  add("Notes", e.notes);

  let home = "";
  if (e.homepage_url) {
    const url = /^https?:\/\//.test(e.homepage_url) ? e.homepage_url : "https://" + e.homepage_url;
    home = `<a class="home" href="${esc(url)}" target="_blank" rel="noopener">Event page ↗</a>`;
  }

  const countyTxt = e.county ? " · " + esc(e.county) + (/city$/i.test(e.county) ? "" : " County") : "";
  drawerBody.innerHTML = `
    <h2>${esc(e.name)}</h2>
    <div class="loc">${esc(e.city)}, ${esc(e.state)}${countyTxt}</div>
    <div>${typeB}${friendly}${statusB}${verify}</div>
    <dl>${rows.join("")}</dl>
    ${home}`;
  drawer.classList.add("open");
}

document.querySelector("#drawer .close").addEventListener("click", () => drawer.classList.remove("open"));
backBtn.addEventListener("click", showMarkets);

// ---------- filter controls ----------
const MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function wireFilters() {
  const monthSel = document.getElementById("f-month");
  for (let i = 1; i <= 12; i++) {
    const o = document.createElement("option");
    o.value = String(i); o.textContent = MONTH_NAMES[i];
    monthSel.appendChild(o);
  }
  // County options: distinct (county, state) present in the data, sorted state-then-county.
  const countySel = document.getElementById("f-county");
  const seenCty = new Set();
  EVENTS.forEach(e => { if (e.county) seenCty.add(e.county + "|" + (e.state || "")); });
  [...seenCty].sort((a, b) => {
    const [ca, sa] = a.split("|"), [cb, sb] = b.split("|");
    return sa === sb ? ca.localeCompare(cb) : sa.localeCompare(sb);
  }).forEach(key => {
    const [cty, st] = key.split("|");
    const o = document.createElement("option");
    o.value = key; o.textContent = `${cty} (${st})`;
    countySel.appendChild(o);
  });
  const bind = (elId, key) => {
    const el = document.getElementById(elId);
    el.addEventListener("change", () => { FILT[key] = el.value; applyFilters(); });
  };
  bind("f-month", "month");
  bind("f-friendly", "friendly");
  bind("f-trip", "trip");
  bind("f-county", "county");
  document.getElementById("f-hidden").addEventListener("change", e => {
    FILT.showHidden = e.target.checked; applyFilters();
  });
  document.getElementById("f-reset").addEventListener("click", () => {
    FILT.month = "all"; FILT.friendly = "all"; FILT.trip = "all"; FILT.county = "all"; FILT.showHidden = false;
    monthSel.value = "all";
    document.getElementById("f-friendly").value = "all";
    document.getElementById("f-trip").value = "all";
    countySel.value = "all";
    document.getElementById("f-hidden").checked = false;
    showMarkets();
  });
}

// ---------- boot ----------
(async function init() {
  if (!KEY || KEY.includes("PASTE_YOUR")) {
    setStatus("⚠ Set SUPABASE_ANON_KEY in config.js to load data."); return;
  }
  try {
    setStatus("Loading…");
    let schedules;
    [MARKETS, EVENTS, schedules] = await Promise.all([
      fetchJSON("vending_markets?select=*&order=id"),
      fetchJSON("vending_events?select=*&lat=not.is.null&order=id"),
      fetchJSON("vending_event_schedules?select=event_id,month")
    ]);
    marketsById = Object.fromEntries(MARKETS.map(m => [String(m.id), m]));
    monthsByEvent = {};
    schedules.forEach(s => {
      if (s.month == null) return;
      (monthsByEvent[s.event_id] = monthsByEvent[s.event_id] || []).push(Number(s.month));
    });
    wireFilters();
    setStatus("");
    showMarkets();
  } catch (err) {
    setStatus("Load error: " + err.message);
    console.error(err);
  }
})();
