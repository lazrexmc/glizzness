/* The Glizzness — Vending Circuit map (zoom-based marker clustering).
   Every event is a colored dot in a single Leaflet.markercluster layer: dots group
   into numbered bubbles when zoomed out and scatter into individual dots when zoomed in.
   Click a bubble to zoom in; click a dot for the detail drawer.
   Reads Supabase REST with the public anon key (vending_* tables have public-read RLS).
   Filters: month / friendliness / trip-type / county + a defunct/excluded toggle. */

const URL = window.SUPABASE_URL, KEY = window.SUPABASE_ANON_KEY;
const HEADERS = { apikey: KEY, Authorization: "Bearer " + KEY };

const statusEl = document.getElementById("status");
const crumbEl  = document.getElementById("crumb");
const drawer   = document.getElementById("drawer");
const drawerBody = document.getElementById("drawer-body");

let EVENTS = [], monthsByEvent = {};
const FILT = { month: "all", friendly: "all", trip: "all", county: "all", showHidden: false };

const map = L.map("map", { zoomControl: true }).setView([38.7, -92.3], 7);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

// one cluster layer for all event dots — groups/scatters by zoom automatically
const clusterGroup = L.markerClusterGroup({
  maxClusterRadius: 55,
  showCoverageOnHover: false,
  spiderfyOnMaxZoom: true,
  chunkedLoading: true
}).addTo(map);

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
const dotIcon = color => L.divIcon({
  className: "evt-dot", iconSize: [16, 16], iconAnchor: [8, 8],
  html: `<span style="background:${color}"></span>`
});

function setStatus(msg) { statusEl.textContent = msg; statusEl.style.display = msg ? "block" : "none"; }

// ---------- render all visible events into the cluster layer ----------
function render(fit) {
  clusterGroup.clearLayers();
  const vis = visibleEvents();
  const markers = [], pts = [];
  vis.forEach(e => {
    if (e.lat == null || e.lng == null) return;
    const mk = L.marker([e.lat, e.lng], { icon: dotIcon(friendlyColor(e)) })
      .bindTooltip(esc(e.name), { direction: "top" });
    mk.on("click", () => openDrawer(e));
    markers.push(mk);
    pts.push([e.lat, e.lng]);
  });
  clusterGroup.addLayers(markers);
  crumbEl.textContent = `${vis.length} event${vis.length === 1 ? "" : "s"}`;
  if (fit && pts.length) map.fitBounds(pts, { padding: [40, 40], maxZoom: 12 });
}
const applyFilters = () => render(true);

// ---------- detail drawer ----------
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
    applyFilters();
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
    [EVENTS, schedules] = await Promise.all([
      fetchJSON("vending_events?select=*&lat=not.is.null&order=id"),
      fetchJSON("vending_event_schedules?select=event_id,month")
    ]);
    monthsByEvent = {};
    schedules.forEach(s => {
      if (s.month == null) return;
      (monthsByEvent[s.event_id] = monthsByEvent[s.event_id] || []).push(Number(s.month));
    });
    wireFilters();
    setStatus("");
    render(true);
  } catch (err) {
    setStatus("Load error: " + err.message);
    console.error(err);
  }
})();
