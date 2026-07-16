"""Signal Net — configuration + the area/event term lists used for filtering.

SUPABASE_SERVICE_KEY comes from the environment (a GitHub Actions secret in CI). It is NEVER
committed. SUPABASE_URL is public (same project as the rest of the site)."""
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikhcbncnaojrndilmnnd.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# A descriptive UA — some feeds/Reddit block the default urllib/feedparser agent.
USER_AGENT = "GlizznessSignalNet/1.0 (+https://glizzness.com; local events aggregator)"

# An item is "in the area" if its text hits one of these (unless its source is already local).
AREA_TERMS = [
    "columbia", "como", "boone county", "mid-missouri", "mid missouri",
    "jefferson city", "jeff city", "fulton", "ashland", "rocheport", "moberly",
    "centralia", "hallsville", "mizzou", "university of missouri",
    "65201", "65202", "65203", "65205", "65211",
]

# ---------------------------------------------------------------------------------------------
# COMPETITOR FILTER (added 2026-07-16, owner: "it lists other food carts as events, skip that")
#
# Venue calendars (Cooper's Landing especially) list WHO IS VENDING FOOD that night. A rival cart's
# booking is not an opportunity — it's the opposite: that slot is TAKEN. Drop them.
#
# Order of operations in is_competitor():
#   1. explicit VENDOR_NAMES  -> drop (for vendors whose name carries no food word)
#   2. EVENT_RESCUE hit       -> KEEP (a real event that happens to contain a food word:
#                                "BBQ Fest", "Rock the River w/ ... Dog Rescue", "Trivia Night")
#   3. VENDOR_TERMS hit       -> drop
# The rescue pass runs BEFORE the terms pass on purpose — without it a legit "Food Truck Festival"
# or "World Series of BBQ" would be thrown away, and those are exactly the gigs we want.
# ---------------------------------------------------------------------------------------------

# Food-business words. A title with one of these and no event word is somebody else's cart.
VENDOR_TERMS = [
    "bbq", "barbecue", "grill", "kitchen", "cantina", "cuisine", "catering", "caterer",
    "meats", "smokehouse", "smokin", "patty", "wagon", "munch", "eats", "potatoes",
    "taqueria", "creamery", "concession", "food co", "foods", "bakery", "sweets",
    "shaved ice", "kettle corn", "funnel", "lemonade stand",
]

# Vendors whose business name has no food word, so the term list can't catch them.
# EXTEND THIS as you spot repeat offenders on the Signals feed — it's data, not logic.
VENDOR_NAMES = [
    "smash & dash", "smash and dash",   # confirmed: also books as "Smash & Dash Grill"
    "the munchbox", "munchbox",
    "delias",                            # confirmed a food vendor (owner, 2026-07-16)
]

# Words that mean "this is an EVENT" and override the vendor terms above.
EVENT_RESCUE = [
    "fest", "festival", "market", "series", "championship", "concert", "show", "showcase",
    "live", "band", "music", "night", "party", "benefit", "fundraiser", "race", "run",
    "tournament", "parade", "fair", "expo", "rally", "trivia", "rides", "crafts", "rescue",
    "open mic", "karaoke", "bingo", "cook-off", "cookoff", "tailgate", "reunion", "homecoming",
]

# Dead entries — never worth surfacing.
DEAD_TERMS = ["cancelled", "canceled", "postponed", "sold out"]


def is_competitor(text):
    """True if this looks like ANOTHER food vendor's booking rather than an event we could work."""
    t = (text or "").lower()
    if any(n in t for n in VENDOR_NAMES):
        return True
    if any(w in t for w in EVENT_RESCUE):
        return False
    return any(w in t for w in VENDOR_TERMS)


def is_dead(text):
    t = (text or "").lower()
    return any(w in t for w in DEAD_TERMS)


# An item is "event-like" if its text hits one of these (unless its source is a pure event feed).
EVENT_TERMS = [
    "event", "show", "concert", "festival", "fest", "market", "farmers market",
    "live music", "live at", "tour", "rally", "fair", "parade", "block party",
    "gig", "vendor", "food truck", "pop-up", "popup", "open mic", "showcase",
    "tailgate", "5k", "10k", "race", "expo", "craft show", "celebration",
    "night market", "street party", "cook-off", "cookoff", "bbq", "car show",
]
