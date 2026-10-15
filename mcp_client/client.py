import asyncio, json, os, sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent.parent / "mcp_servers" / "search_server.py"

# sys.executable: the server runs in the same Python environment as the app.
# env: pass our environment through so the server sees TAVILY_API_KEY (needed on Streamlit Cloud).
PARAMS = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=dict(os.environ))


async def _call(tool: str, args: dict) -> dict:
    async with stdio_client(PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=args)

    # Handle the result after the session closes: an exception raised inside
    # stdio_client gets wrapped in an ExceptionGroup and loses its message.
    if result.isError:
        text = " ".join(c.text for c in result.content
                        if isinstance(c, types.TextContent))
        raise RuntimeError(f"MCP tool {tool} failed: {text}")

    if result.structuredContent:
        return result.structuredContent

    for c in result.content:  # fallback: JSON in text
        if isinstance(c, types.TextContent):
            return json.loads(c.text)
    return {}


def call_tool(tool: str, args: dict) -> dict:
    """Sync wrapper so LangGraph nodes and Streamlit stay synchronous."""
    return asyncio.run(_call(tool, args))
