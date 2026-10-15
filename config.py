# Free tier: flash-lite allows 15 requests/min and 500/day; gemini-3.8-flash only 5/min and 20/day,
# which isn't enough for a public demo or the 15-topic eval (one run is ~7 Gemini calls)
MODEL = "gemini-3.5-flash-lite"
MAX_RUNS_PER_SESSION = 5  # public demo: protects the shared free-tier quota
MAX_RESULTS = 5          # per search call
MIN_SOURCES = 3          # fewer than this triggers a refined search
MAX_SEARCH_ATTEMPTS = 2
RECURSION_LIMIT = 25     # LangGraph safety net
MAX_CONCURRENCY = 3      # low because of Gemini's free-tier rate limits
