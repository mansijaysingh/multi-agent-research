from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
import os

load_dotenv()

search_tool=TavilySearchResults(max_results=5)

def search_agent(state):
  """
    Search agent:
    Takes the search query from state
    Returns numbered sources, the attempt count and any error
    """
  query = state.get("search_query") or state["query"]
  attempts = state.get("search_attempts", 0) + 1

  try:
      print(f"\n🔍 Searching for: {query}")

      results = search_tool.invoke(query)

      # TavilySearchResults returns errors (e.g. a bad API key) as a string instead of raising
      if isinstance(results, str):
         raise RuntimeError(results)

      sources = []
      for r in results or []:
         if not r.get("url"):
            continue
         sources.append({
            "id": len(sources) + 1,
            "title": r.get("title", ""),
            "url": r["url"],
            "content": r.get("content", ""),
         })

      if not sources:
         return {"sources": [], "search_attempts": attempts, "error": "no results found"}

      return {"sources": sources, "search_attempts": attempts, "error": None}
  except Exception as e:
     return {"search_attempts": attempts, "error": f"search failed: {e}"}
