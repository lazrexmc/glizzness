/* The Glizzness — demand estimates for the gated tools (PRIVATE pages only).
   Loaded by scout/ and hub/desk after scout.js. Reads the demand_profiles table
   (built by demand_baseline.py from 4 years of Square sales) and answers, per prospect:
   "how many hands, how much food?"

   Matching ladder — most evidence wins, and the answer SAYS which rung it used:
     1. suggested_crew set on the prospect  -> the pages use it directly (manual override; not here)
     2. venue match ("Logboat Brewing" ~ profile 'logboat')      -> real history
     3. event-type analog (dirt_track -> evening sessions)        -> estimate
     4. overall median of all sessions                            -> weakest estimate
   A guess must never masquerade as evidence: `fromHistory` is true only on rung 2. */
(function () {
  "use strict";

  var venues = [], labels = {}, overall = null, loaded = false;

  /* IDENTICAL rule to demand_baseline.py::norm_key (both keep ASCII a-z0-9 ONLY — the Python
     side was fixed to match; "Café Berlin" squashes to "cafberlin" on BOTH sides). */
  function norm(s) { return (s || "").toLowerCase().replace(/[^a-z0-9]/g, ""); }

  /* Word-boundary venue match. Substring-anywhere was a review finding: "McMurry's Family Farm
     Fest" contains "murrys" and would have shown Murry's history as evidence for an unrelated
     festival. So: the squashed run of words STARTING AT A WORD BOUNDARY must begin with the key. */
  function nameMatchesKey(name, key) {
    var words = (name || "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
    for (var i = 0; i < words.length; i++) {
      var acc = "";
      for (var j = i; j < words.length && acc.length < key.length; j++) acc += words[j];
      if (acc.length >= key.length && acc.slice(0, key.length) === key) return true;
    }
    return false;
  }

  /* Which past-session population is the nearest analog for a prospect type we've never worked.
     Coarse on purpose — it picks a POPULATION (daytime / evening / late-night), not a venue. */
  var TYPE_TO_LABEL = {
    lunch_rush: "daytime_unlogged_gig", worksite_crew: "daytime_unlogged_gig",
    festival: "daytime_unlogged_gig", county_fair: "daytime_unlogged_gig",
    state_fair: "daytime_unlogged_gig", farmers_market: "daytime_unlogged_gig",
    food_truck_rally: "daytime_unlogged_gig", craft_fair: "daytime_unlogged_gig",
    art_fair: "daytime_unlogged_gig", bbq_fest: "daytime_unlogged_gig",
    car_show: "daytime_unlogged_gig", air_show: "daytime_unlogged_gig",
    sports_tournament: "daytime_unlogged_gig", mtb_gravel: "daytime_unlogged_gig",
    moto_rally: "daytime_unlogged_gig", balloon_fest: "daytime_unlogged_gig",
    dirt_track: "evening_unlogged", rodeo: "evening_unlogged", winery: "evening_unlogged",
    music_fest: "evening_unlogged", oktoberfest: "evening_unlogged",
    venue: "late_night_bar_trade"
  };
  var FRIENDLY = {
    daytime_unlogged_gig: "daytime gigs", evening_unlogged: "evening gigs",
    late_night_bar_trade: "late-night runs", private_party_one_payer: "private parties"
  };

  async function load(db) {
    try {
      var res = await db.from("demand_profiles").select("*");
      if (res.error || !res.data) return false;   // table absent/empty -> estimates just don't show
      res.data.forEach(function (r) {
        if (r.kind === "venue") venues.push(r);
        else if (r.kind === "label") labels[r.key] = r;
        else if (r.kind === "overall") overall = r;
      });
      venues.sort(function (a, b) { return b.key.length - a.key.length; }); // longest key first
      loaded = venues.length > 0 || overall !== null;
      return loaded;
    } catch (e) { return false; }
  }

  function crewText(p) {
    return p.crew_typical === p.crew_busy
      ? String(p.crew_typical)
      : p.crew_typical + "–" + p.crew_busy + " busy";
  }

  function prepText(p, approx) {
    var prep = p.prep || {};
    var top = Object.keys(prep)
      .map(function (k) { return [k, prep[k]]; })
      .filter(function (kv) { return kv[1] >= 1; })
      .sort(function (a, b) { return b[1] - a[1]; })
      .slice(0, 2);
    if (!top.length) return null;
    var parts = top.map(function (kv) { return kv[0] + " ×" + Math.round(kv[1]); });
    return (approx ? "~" : "") + parts.join(" · ") +
      (p.units_median > 0 ? "  (" + (approx ? "~" : "") + p.units_median + " items)" : "");
  }

  function make(row, basisKind) {
    var fromHistory = basisKind === "venue";
    var prep = prepText(row, !fromHistory);
    return {
      fromHistory: fromHistory,
      crew: crewText(row),
      crewLabel: "Crew: " + crewText(row) + (fromHistory ? "" : " (est.)"),
      prep: prep,
      /* the "(est.)" marker must travel with the prep line too — the crew line can be replaced
         by a manual override, and then this is the only estimate flag on Trint's card */
      prepLabel: prep ? prep + (fromHistory ? "" : " (est.)") : null,
      basis: fromHistory
        ? "from " + row.sessions + " past sessions here"
        : basisKind === "label"
          ? "estimate from " + row.sessions + " similar " + (FRIENDLY[row.key] || row.display_name)
          : "estimate from all " + row.sessions + " past sessions",
      sessions: row.sessions,
      ophMedian: row.oph_median, ophP90: row.oph_p90,
      unitsMedian: row.units_median, unitsP90: row.units_p90,
      grossMedian: row.gross_median,   // PRIVATE — desk display only, never on a public surface
      pace: row.pace_per_person
    };
  }

  /* prospect: an event_prospects row (name, event_type, ...). Returns an estimate or null. */
  function estimate(prospect) {
    if (!loaded || !prospect) return null;
    for (var i = 0; i < venues.length; i++) {
      var k = venues[i].key;
      if (k.length >= 4 && nameMatchesKey(prospect.name, k)) return make(venues[i], "venue");
    }
    var lbl = TYPE_TO_LABEL[(prospect.event_type || "").toLowerCase()];
    if (lbl && labels[lbl]) return make(labels[lbl], "label");
    if (overall) return make(overall, "overall");
    return null;
  }

  window.Demand = { load: load, estimate: estimate, _norm: norm };
})();
