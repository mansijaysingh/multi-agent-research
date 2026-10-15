import pytest

from agents.search_agent import search_agent
from mcp_client.client import call_tool


def _results(*urls):
    return {"results": [{"title": u, "url": u, "content": ""} for u in urls]}


def test_numbering_and_duplicates(monkeypatch):
    monkeypatch.setattr("agents.search_agent.call_tool", lambda tool, args: _results("u2", "u3", "u3", "u4"))
    state = {"query": "x", "sources": [{"id": i, "title": f"u{i}", "url": f"u{i}", "content": ""} for i in (1, 2)]}
    out = search_agent(state)
    assert [(s["id"], s["url"]) for s in out["sources"]] == [(1, "u1"), (2, "u2"), (3, "u3"), (4, "u4")]
    assert out["search_attempts"] == 1
    assert out["error"] is None


def test_uses_refined_query(monkeypatch):
    seen = {}

    def fake(tool, args):
        seen.update(args)
        return _results("u1")

    monkeypatch.setattr("agents.search_agent.call_tool", fake)
    search_agent({"query": "topic", "search_query": "better query"})
    assert seen["query"] == "better query"


def test_mcp_failure(monkeypatch):
    def boom(tool, args):
        raise RuntimeError("boom")

    monkeypatch.setattr("agents.search_agent.call_tool", boom)
    out = search_agent({"query": "x", "search_attempts": 1})
    assert out["error"].startswith("search failed")
    assert "sources" not in out
    assert out["search_attempts"] == 2


def test_no_results(monkeypatch):
    monkeypatch.setattr("agents.search_agent.call_tool", lambda tool, args: {"results": []})
    out = search_agent({"query": "x"})
    assert out["error"] == "no results found"


def test_mcp_round_trip_returns_tool_error(monkeypatch):
    # Starts the real server through the real stdio client. The empty query makes the
    # server raise before it calls Tavily, so there's no network call and no API cost.
    monkeypatch.setenv("TAVILY_API_KEY", "dummy")   # reaches the subprocess through env=dict(os.environ)
    with pytest.raises(RuntimeError, match="query must not be empty"):
        call_tool("web_search", {"query": "  "})


def test_env_reaches_server(monkeypatch):
    # The key is set to "" only now, after every module was imported. The server sees ""
    # (its load_dotenv() never overwrites a variable that is already set), which proves the
    # client passes the *current* os.environ, not a copy taken at import (decision.md K1).
    monkeypatch.setenv("TAVILY_API_KEY", "")
    with pytest.raises(RuntimeError, match="TAVILY_API_KEY is not set"):
        call_tool("web_search", {"query": "anything"})
