r"""demand_baseline.py - the "brain": what do we ACTUALLY sell, and what does that mean for crew + prep?

Reads the LOCAL, gitignored exports (no credentials, no writes to anything live):
  Sales/items-*.csv     ~25k line items, 2022-2026 (Square item-level export)
  past_cart_events.csv  294 past Google Calendar events (from pull_past_events.py)

Writes:
  demand_baseline.md          human report (gitignored - carries revenue)
  data/demand_profiles.json   machine-readable profiles (feeds suggested_crew + prep lists)

THE LOAD-BEARING DESIGN CALL (owner's, 2026-07-13 - and the data proved it):
  The Google Calendar is NOT the complete event list. Measured: only 27% of real selling
  sessions have a calendar event, and the 73% that don't carry 69% of all revenue (the
  late-night bar trade, unlogged regular gigs, private parties). So we do NOT join off the
  calendar. We cluster the SALES first - that's ground truth - then attach a calendar event
  where one matches, and classify the leftovers by their transaction signature.

WHAT THIS CAN'T KNOW (don't pretend otherwise):
  * Crowd size -> so a true "capture rate" is NOT derivable. For a venue we've never worked,
    the estimate is an informed guess, not evidence.
  * Crew size per past session -> so the sustainable PACE cannot be derived from data. It is
    an owner-set labor standard (PACE_PER_PERSON below).
  * Square is ONE location -> it tells you WHEN, never WHERE. Venue only comes from the
    calendar match.

Usage:
  python demand_baseline.py            # build the report + profiles
  python demand_baseline.py --sql      # also emit supabase_demand_data.sql (Lance runs it in the
                                       #   SQL editor after supabase_demand_schema.sql) -> the
                                       #   profiles reach the Scout board's cards
  python demand_baseline.py --aliases  # just show how item names collapse (review this!)
"""
import argparse
import csv
import glob
import json
import os
import statistics as stats
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SALES_DIR = os.path.join(HERE, "Sales")
EVENTS_CSV = os.path.join(HERE, "past_cart_events.csv")
# NOTE: named *_report so it can't case-collide on Windows with DEMAND_BASELINE.md (the runbook).
REPORT_MD = os.path.join(HERE, "demand_baseline_report.md")
PROFILES_JSON = os.path.join(HERE, "data", "demand_profiles.json")

# ---------------------------------------------------------------------------
# CONFIG - the knobs a human owns
# ---------------------------------------------------------------------------

# Owner-set labor standard (2026-07-16): orders/hr ONE person handles at a sustainable pace.
# Not derivable from data - the exports never record how many hands worked a session.
# Philosophy: scale volume by adding PEOPLE, never by making anyone work faster.
PACE_PER_PERSON = 15.0
CREW_BUFFER = 1.15          # +15% headroom so a normal surge doesn't blow the line

SESSION_GAP = timedelta(hours=3)   # a >3h quiet gap = a new selling session
MATCH_WINDOW = timedelta(hours=5)  # calendar event within +/-5h of session start = a match

# --- item name -> canonical name -------------------------------------------
# Four years of renames left 94 distinct names for ~25 real products.
# "Dawg" is the OLD spelling; the hard rule is now "Dog" (the item is "Hog' N' Dog").
# REVIEW THIS MAP - some collapses are judgement calls. `--aliases` prints the result.
ALIASES = {
    # the flagship, 4 spellings, 13k+ sold
    "glizzyclassic": "Glizzy", "glizzy classic": "Glizzy", "glizzy": "Glizzy",
    "classic glizzy": "Glizzy", "original glizzy": "Glizzy",
    # Dawg -> Dog
    "chili dawg": "Chili Dog", "chili dog": "Chili Dog",
    "hog n' dawg": "Hog' N' Dog", "hog'n dawg special": "Hog' N' Dog", "hog' n' dog": "Hog' N' Dog",
    "nacho dawg": "Nacho Dog", "nacho dawg special": "Nacho Dog",
    "bangkok dog": "Bangkok Dog", "bangkok special": "Bangkok Dog",
    # burgers
    "burger": "Burger", "boujee burger": "Boujee Burger", "bujie burger": "Boujee Burger",
    # brats stay distinct (different products), oddballs grouped
    "beer brat": "Beer Brat", "apple brat": "Apple Brat",
    "brat": "Brat (other)", "goat brat": "Brat (other)", "special brat": "Brat (other)",
    # links
    "link": "Link", "turkey link": "Link",
    # sides / drinks
    "chips": "Chips", "walking chips": "Walking Chips", "fries": "Fries", "nachos": "Nachos",
    "street corn": "Street Corn", "side of chili": "Side of Chili", "sides": "Sides (unspecified)",
    "beverage": "Beverage", "water": "Water", "dasani": "Water", "iced coffee": "Beverage",
    # other mains that recur
    "pulled pork": "Pulled Pork", "pulled pork sandwich": "Pulled Pork",
    "shredded chicken": "Shredded Chicken", "sloppy joe": "Sloppy Joe",
    "grill cheese": "Grilled Cheese", "jackfruit": "Jackfruit", "all the way": "All The Way",
    "something fowl": "Something Fowl",
}

# NOT preppable food - these are money/service lines. If they leak into a prep list it will
# cheerfully tell Trint to prep 332 "Custom Amounts".
NON_FOOD_EXACT = {
    "custom amount", "vouchers redeemed", "keychain", "event deposit", "setup service fee",
    "on site service", "on site catering", "onsite catering", "on-site catering",
    "catering entree and side", "catering for 100", "special",
}
NON_FOOD_CONTAINS = (
    "on site", "onsite", "on-site", "deposit", "setup", "service", "catering",
    "food truck fest", "barn party", "kickoff", "lunch 1", "wounded warriors", "memorial day",
)


def canon(name):
    """Canonical item name, or None if it isn't preppable food."""
    n = (name or "").strip()
    if not n:
        return None
    low = n.lower()
    if low in NON_FOOD_EXACT or any(k in low for k in NON_FOOD_CONTAINS):
        return None
    if low in ALIASES:
        return ALIASES[low]
    return n          # an unmapped one-off special - keep it, it'll show as low volume


def money(s):
    s = (s or "").replace("$", "").replace(",", "").strip()
    if not s:
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def parse_ts(d, t):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime((d + " " + t).strip(), fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# 1. line items -> orders -> sessions
# ---------------------------------------------------------------------------
def load_orders():
    orders = {}
    for f in sorted(glob.glob(os.path.join(SALES_DIR, "items-*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            ts = parse_ts(r.get("Date") or "", r.get("Time") or "")
            if not ts:
                continue
            tx = (r.get("Transaction ID") or "").strip() or ("_synth_" + ts.isoformat())
            o = orders.get(tx)
            if not o:
                o = orders[tx] = {"ts": ts, "gross": 0.0, "lines": 0, "items": defaultdict(int),
                                  "units": 0, "channel": (r.get("Channel") or "").strip()}
            o["ts"] = min(o["ts"], ts)
            o["gross"] += money(r.get("Gross Sales"))
            o["lines"] += 1
            item = canon(r.get("Item"))
            try:
                q = int(float(r.get("Qty") or 0))
            except ValueError:
                q = 0
            if item and q > 0:
                o["items"][item] += q
                o["units"] += q
    return sorted(orders.values(), key=lambda o: o["ts"])


def build_sessions(orders):
    sessions, cur = [], []
    for o in orders:
        if cur and (o["ts"] - cur[-1]["ts"]) > SESSION_GAP:
            sessions.append(cur)
            cur = []
        cur.append(o)
    if cur:
        sessions.append(cur)

    out = []
    for c in sessions:
        start, end = c[0]["ts"], c[-1]["ts"]
        hrs = max((end - start).total_seconds() / 3600.0, 0.5)   # floor: a burst isn't infinite rate
        mix = defaultdict(int)
        for o in c:
            for k, v in o["items"].items():
                mix[k] += v
        out.append({
            "start": start, "end": end, "hrs": hrs,
            "orders": len(c), "gross": sum(o["gross"] for o in c),
            "units": sum(o["units"] for o in c),
            "oph": len(c) / hrs,
            "max_lines": max(o["lines"] for o in c),
            "max_gross": max(o["gross"] for o in c),
            "mix": dict(mix),
            "venue": None, "label": None,
        })
    return out


# ---------------------------------------------------------------------------
# 2. attach calendar events, then classify the leftovers
# ---------------------------------------------------------------------------
def load_events():
    evs = []
    if not os.path.exists(EVENTS_CSV):
        return evs
    for r in csv.DictReader(open(EVENTS_CSV, encoding="utf-8-sig")):
        s = (r.get("start") or "").strip()
        if not s:
            continue
        dt = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s[:19] if "T" in s else s[:10], fmt)
                break
            except ValueError:
                continue
        if dt:
            evs.append({"start": dt, "summary": (r.get("summary") or "").strip(),
                        "all_day": (r.get("all_day") or "").lower() == "true"})
    return evs


# Calendar titles drift exactly like item names did ("Logboat" vs "Log boat" were being counted
# as two separate venues, splitting the anchor account's evidence in half). So normalize away
# spaces/punctuation before matching, same trick as the item alias map.
VENUE_KEYS = [
    ("logboat", "Logboat"), ("buroak", "Bur Oak"), ("cooper", "Cooper's Landing"),
    ("rosemusic", "Rose Music Hall"), ("rosepark", "Rose Park"), ("bluenote", "The Blue Note"),
    ("mizzou", "Mizzou"), ("universityofmissouri", "Mizzou"), ("eastside", "Eastside Tavern"),
    ("cafeberlin", "Cafe Berlin"), ("shelter", "Shelter Gardens"), ("harley", "Harley-Davidson"),
    ("murr", "Murry's"), ("arcade", "Arcade District"),
]
# Calendar entries that are NOT a venue (the business's own name, admin blocks, etc.)
NOT_A_VENUE = ("theglizzness", "glizzness", "cart", "prep", "off", "closed")


def venue_of(summary):
    """Squash a calendar title to a canonical venue, or None if it isn't a venue at all."""
    raw = (summary or "").strip()
    if not raw:
        return None
    s = "".join(ch for ch in raw.lower() if ch.isalnum())
    if not s:
        return None
    for key, label in VENUE_KEYS:
        if key in s:
            return label
    if s in NOT_A_VENUE:
        return None
    return raw[:40]


def classify(s):
    """Owner's hypotheses - all four confirmed present in the data."""
    h = s["start"].hour
    if s["orders"] <= 2 and s["max_gross"] >= 200:
        return "private_party_one_payer"
    if s["max_lines"] >= 15 and s["orders"] <= 5:
        return "big_tab_settled_at_close"
    if h >= 21 or h < 4:
        return "late_night_bar_trade"
    if 9 <= h < 16:
        return "daytime_unlogged_gig"
    return "evening_unlogged"


def attach(sessions, events):
    by_day = defaultdict(list)
    for e in events:
        by_day[e["start"].date()].append(e)
    for s in sessions:
        hit = None
        for e in by_day.get(s["start"].date(), []):
            if e["all_day"] or abs(e["start"] - s["start"]) <= MATCH_WINDOW:
                hit = e
                break
        if hit:
            s["venue"] = venue_of(hit["summary"])
            s["label"] = "calendar:" + (s["venue"] or "event")
        else:
            s["label"] = classify(s)
    return sessions


# ---------------------------------------------------------------------------
# 3. profiles
# ---------------------------------------------------------------------------
def crew_for(oph):
    import math
    return max(1, math.ceil((oph * CREW_BUFFER) / PACE_PER_PERSON))


def profile(group, name):
    ophs = sorted(s["oph"] for s in group)
    units = sorted(s["units"] for s in group)
    def p(v, q):
        # nearest-rank on n-1: int(len*q) made p90 return the sample MAXIMUM whenever len*q was
        # whole (n=10 -> index 9), silently inflating crew_busy
        return v[min(int(round(q * (len(v) - 1))), len(v) - 1)] if v else 0
    mix = defaultdict(int)
    for s in group:
        for k, v in s["mix"].items():
            mix[k] += v
    per_session = {k: round(v / len(group), 1) for k, v in
                   sorted(mix.items(), key=lambda x: -x[1])[:12] if v / len(group) >= 0.5}
    return {
        "name": name,
        "sessions": len(group),
        "orders_per_hr_median": round(p(ophs, .5), 1),
        "orders_per_hr_p90": round(p(ophs, .9), 1),
        "orders_per_hr_max": round(ophs[-1], 1) if ophs else 0,
        "crew_typical": crew_for(p(ophs, .5)),
        "crew_busy": crew_for(p(ophs, .9)),
        "units_median": p(units, .5),
        "units_p90": p(units, .9),
        "units_per_order": round(sum(s["units"] for s in group) / max(sum(s["orders"] for s in group), 1), 2),
        "gross_median": round(stats.median([s["gross"] for s in group]), 2) if group else 0,
        "prep_per_session": per_session,
    }


DATA_SQL = os.path.join(HERE, "supabase_demand_data.sql")


def _sq(v):
    """SQL literal: NULL / number / escaped string."""
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(round(v, 2))
    return "'" + str(v).replace("'", "''") + "'"


_ASCII_ALNUM = set("abcdefghijklmnopqrstuvwxyz0123456789")


def norm_key(s):
    """Match key both sides agree on — ASCII a-z0-9 ONLY, matching demand.js's /[^a-z0-9]/ strip.
    (str.isalnum() keeps unicode letters — 'Café Berlin' would diverge between the two sides.)"""
    return "".join(ch for ch in (s or "").lower() if ch in _ASCII_ALNUM)


def emit_sql(profiles):
    """supabase_demand_data.sql — delete-all + insert, so a re-run always mirrors the latest
    baseline (same idempotent shape as the vending data load)."""
    rows = []
    def add(kind, key, p):
        rows.append("  (%s, %s, %s, %d, %s, %s, %s, %d, %d, %d, %d, %s, %s, %s::jsonb, %s)" % (
            _sq(kind), _sq(key), _sq(p["name"]), p["sessions"],
            _sq(p["orders_per_hr_median"]), _sq(p["orders_per_hr_p90"]), _sq(p["orders_per_hr_max"]),
            p["crew_typical"], p["crew_busy"], p["units_median"], p["units_p90"],
            _sq(p["units_per_order"]), _sq(p["gross_median"]),
            _sq(json.dumps(p["prep_per_session"])), _sq(PACE_PER_PERSON)))

    # Venue rows: CURATED venues only. venue_of() falls through to raw calendar titles, and
    # emitting those as match keys is dangerous — a generic squashed title ("privateparty",
    # a short "mu") would substring-match unrelated prospects and present the wrong venue's
    # history as evidence. Raw-title venues still appear in the report; they just never
    # become client-side match keys until added to VENUE_KEYS deliberately.
    curated = {label for _, label in VENUE_KEYS}
    seen, skipped = set(), []
    for key, p in profiles["by_venue"].items():
        k = norm_key(key)
        if p["name"] not in curated:
            skipped.append(p["name"])
            continue
        if ("venue", k) in seen:      # two spellings normalizing to one key — keep the first (largest)
            skipped.append(p["name"] + " (dup key)")
            continue
        seen.add(("venue", k))
        add("venue", k, p)
    if skipped:
        print("  (emit_sql: skipped %d non-curated/dup venue profile(s): %s)"
              % (len(skipped), ", ".join(skipped[:6])))
    for key, p in profiles["by_label"].items():
        if p["sessions"] >= 3 and not key.startswith("calendar:"):   # venue rows already carry those
            add("label", key, p)
    add("overall", "overall", profiles["overall"])

    cols = ("kind, key, display_name, sessions, oph_median, oph_p90, oph_max, crew_typical, "
            "crew_busy, units_median, units_p90, units_per_order, gross_median, prep, pace_per_person")
    with open(DATA_SQL, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Generated by demand_baseline.py --sql. Run AFTER supabase_demand_schema.sql.\n"
                "-- Idempotent: wipes and reloads the whole table so it always mirrors the latest baseline.\n\n"
                "begin;\n\ndelete from demand_profiles;\n\n"
                "insert into demand_profiles (%s) values\n" % cols
                + ",\n".join(rows) + ";\n\ncommit;\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aliases", action="store_true", help="show how item names collapse, then exit")
    ap.add_argument("--sql", action="store_true", help="also emit supabase_demand_data.sql for the Scout board")
    args = ap.parse_args()

    orders = load_orders()
    if args.aliases:
        mix = defaultdict(int)
        dropped = defaultdict(int)
        for f in sorted(glob.glob(os.path.join(SALES_DIR, "items-*.csv"))):
            for r in csv.DictReader(open(f, encoding="utf-8-sig")):
                raw = (r.get("Item") or "").strip()
                if not raw:
                    continue
                try:
                    q = int(float(r.get("Qty") or 0))
                except ValueError:
                    q = 0
                c = canon(raw)
                (mix if c else dropped)[c or raw] += q
        print("CANONICAL FOOD ITEMS (what a prep list is made of):")
        for k, v in sorted(mix.items(), key=lambda x: -x[1]):
            print("  %-28s %6d" % (k, v))
        print("\nEXCLUDED as non-food (money/service lines, NOT preppable):")
        for k, v in sorted(dropped.items(), key=lambda x: -x[1])[:20]:
            print("  %-28s %6d" % (k[:28], v))
        return

    sessions = attach(build_sessions(orders), load_events())

    groups = defaultdict(list)
    for s in sessions:
        groups[s["label"]].append(s)
    venues = defaultdict(list)
    for s in sessions:
        if s["venue"]:
            venues[s["venue"]].append(s)

    profiles = {
        "generated_from": {"sessions": len(sessions), "orders": len(orders),
                           "span": [sessions[0]["start"].date().isoformat(),
                                    sessions[-1]["start"].date().isoformat()]},
        "labor_standard": {"pace_per_person_orders_hr": PACE_PER_PERSON, "buffer": CREW_BUFFER},
        "by_venue": {k: profile(v, k) for k, v in sorted(venues.items(), key=lambda x: -len(x[1])) if len(v) >= 3},
        "by_label": {k: profile(v, k) for k, v in sorted(groups.items(), key=lambda x: -len(x[1]))},
        "overall": profile(sessions, "All history"),
    }
    os.makedirs(os.path.dirname(PROFILES_JSON), exist_ok=True)
    with open(PROFILES_JSON, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)

    # ---- report ----
    matched = [s for s in sessions if s["venue"]]
    L = []
    L.append("# Demand Baseline — what we actually sell\n")
    L.append("*Generated by `demand_baseline.py`. Gitignored: carries revenue.*\n")
    L.append("**Sessions:** %d · **Orders:** %d · **Span:** %s → %s\n" % (
        len(sessions), len(orders), sessions[0]["start"].date(), sessions[-1]["start"].date()))
    L.append("**Labor standard:** 1 person ≈ **%.0f orders/hr** sustainable (owner-set) · buffer ×%.2f\n"
             % (PACE_PER_PERSON, CREW_BUFFER))
    orphan_rev = sum(s["gross"] for s in sessions if not s["venue"])
    total_rev = sum(s["gross"] for s in sessions)
    L.append("\n## The calendar is not the business\n")
    L.append("- sessions **with** a calendar event: **%d** (%.0f%%)\n" % (len(matched), 100.0 * len(matched) / len(sessions)))
    L.append("- sessions with **no** event: **%d** (%.0f%%) — carrying **$%s of $%s (%.0f%%)** of all revenue\n" % (
        len(sessions) - len(matched), 100.0 * (len(sessions) - len(matched)) / len(sessions),
        format(int(orphan_rev), ","), format(int(total_rev), ","), 100.0 * orphan_rev / max(total_rev, 1)))
    L.append("\n> Building this off the calendar would have modelled a third of the business.\n")

    L.append("\n## By venue (evidence — we've actually worked these)\n")
    L.append("| venue | sessions | ord/hr med | p90 | crew (typical → busy) | units/session | $ median |\n")
    L.append("|---|---:|---:|---:|:---:|---:|---:|\n")
    for k, p in profiles["by_venue"].items():
        L.append("| **%s** | %d | %.1f | %.1f | **%d → %d** | %d | $%s |\n" % (
            p["name"], p["sessions"], p["orders_per_hr_median"], p["orders_per_hr_p90"],
            p["crew_typical"], p["crew_busy"], p["units_median"], format(int(p["gross_median"]), ",")))

    L.append("\n## By session type (incl. the unlogged trade)\n")
    L.append("| type | sessions | ord/hr med | p90 | crew (typical → busy) | units/session |\n")
    L.append("|---|---:|---:|---:|:---:|---:|\n")
    for k, p in profiles["by_label"].items():
        if p["sessions"] < 3:
            continue
        L.append("| %s | %d | %.1f | %.1f | **%d → %d** | %d |\n" % (
            p["name"], p["sessions"], p["orders_per_hr_median"], p["orders_per_hr_p90"],
            p["crew_typical"], p["crew_busy"], p["units_median"]))

    L.append("\n## Prep lists (typical session, by venue)\n")
    for k, p in list(profiles["by_venue"].items())[:6]:
        if not p["prep_per_session"]:
            continue
        L.append("\n**%s** — typical session ≈ %d units, busy ≈ %d\n\n" % (p["name"], p["units_median"], p["units_p90"]))
        for item, n in p["prep_per_session"].items():
            L.append("- %s × **%.0f** (busy: %.0f)\n" % (item, n, n * (p["units_p90"] / max(p["units_median"], 1))))

    L.append("\n---\n\n*Caveats: no crowd data → capture rate is not derivable, so a never-worked venue "
             "is an informed guess. No crew-size history → the pace is an owner-set standard, not learned. "
             "Square is one location → it knows WHEN, never WHERE.*\n")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("".join(L))

    print("sessions %d - orders %d - venues profiled %d - labels %d"
          % (len(sessions), len(orders), len(profiles["by_venue"]), len(profiles["by_label"])))
    print("wrote %s" % REPORT_MD)
    print("wrote %s" % PROFILES_JSON)
    if args.sql:
        n = emit_sql(profiles)
        print("wrote %s (%d profile rows) -> run it in the Supabase SQL editor" % (DATA_SQL, n))


if __name__ == "__main__":
    main()
