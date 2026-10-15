# Do not print() to stdout in this file: stdout carries the MCP stdio protocol.
# Use print(..., file=sys.stderr) for debugging.
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

load_dotenv()

mcp = FastMCP("research-search")


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web for current information on a topic.

    Args:
        query: what to search for, e.g. "LangGraph supervisor pattern".
        max_results: how many results to return (1-10, default 5).

    Returns {"results": [{"title", "url", "content"}, ...]}.
    Raises an error if the query is empty or the search fails.
    """
    # Read the key here, not at import: a missing key then comes back as a clear
    # tool error instead of the server crashing before it starts.
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set")
    if not query.strip():
        raise ValueError("query must not be empty")
    max_results = min(max(max_results, 1), 10)

    resp = TavilyClient(api_key=api_key).search(query=query, max_results=max_results)
    results = [
        {"title": r.get("title", ""), "url": r["url"], "content": r.get("content", "")}
        for r in resp.get("results", [])
        if r.get("url")
    ]
    return {"results": results}


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
