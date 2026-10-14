MODEL = "gemini-3.8-flash"
MAX_RESULTS = 5          # per search call
MIN_SOURCES = 3          # fewer than this triggers a refined search
MAX_SEARCH_ATTEMPTS = 2
RECURSION_LIMIT = 25     # LangGraph safety net
MAX_CONCURRENCY = 3      # low because of Gemini's free-tier rate limits
