from mcp_client.client import call_tool
from config import MAX_RESULTS


def search_agent(state):
  """
    Search agent:
    Takes the search query from state, searches through the MCP web_search tool
    Returns numbered sources (old ones kept, duplicate URLs skipped), the attempt count and any error
    """
  query = state.get("search_query") or state["query"]
  attempts = state.get("search_attempts", 0) + 1

  try:
      print(f"\n🔍 Searching for: {query}")
      data = call_tool("web_search", {"query": query, "max_results": MAX_RESULTS})
  except Exception as e:
     return {"search_attempts": attempts, "error": f"search failed: {e}"}

  existing = state.get("sources", [])
  seen = {s["url"] for s in existing}
  new = [r for r in data.get("results", []) if r["url"] not in seen]

  sources = existing + [
     {"id": len(existing) + i + 1, **r} for i, r in enumerate(new)
  ]

  if not sources:
     return {"sources": [], "search_attempts": attempts, "error": "no results found"}

  return {"sources": sources, "search_attempts": attempts, "error": None}
