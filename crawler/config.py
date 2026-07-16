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

# An item is "event-like" if its text hits one of these (unless its source is a pure event feed).
EVENT_TERMS = [
    "event", "show", "concert", "festival", "fest", "market", "farmers market",
    "live music", "live at", "tour", "rally", "fair", "parade", "block party",
    "gig", "vendor", "food truck", "pop-up", "popup", "open mic", "showcase",
    "tailgate", "5k", "10k", "race", "expo", "craft show", "celebration",
    "night market", "street party", "cook-off", "cookoff", "bbq", "car show",
]
