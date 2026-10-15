# Do not print() to stdout in this file: stdout carries the MCP stdio protocol.
# Use print(..., file=sys.stderr) for debugging.
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

load_dotenv()

mcp = FastMCP("research-search")
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web for current information on a topic.

    Args:
        query: what to search for, e.g. "LangGraph supervisor pattern".
        max_results: how many results to return (1-10, default 5).

    Returns {"results": [{"title", "url", "content"}, ...]}.
    Raises an error if the query is empty or the search fails.
    """
    if not query.strip():
        raise ValueError("query must not be empty")
    max_results = min(max(max_results, 1), 10)

    resp = tavily.search(query=query, max_results=max_results)
    results = [
        {"title": r.get("title", ""), "url": r["url"], "content": r.get("content", "")}
        for r in resp.get("results", [])
        if r.get("url")
    ]
    return {"results": results}


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
