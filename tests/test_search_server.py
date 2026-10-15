import pytest

import mcp_servers.search_server as mod


class FakeTavily:
    calls = []

    def __init__(self, api_key):
        pass

    def search(self, **kwargs):
        FakeTavily.calls.append(kwargs)
        return {"results": [
            {"title": "A", "url": "https://a.com", "content": "x", "score": 0.9},
            {"url": "https://b.com"},              # no title or content
            {"title": "No URL", "content": "y"},   # dropped
        ]}


@pytest.fixture
def fake_tavily(monkeypatch):
    FakeTavily.calls = []
    monkeypatch.setattr(mod, "TavilyClient", FakeTavily)
    monkeypatch.setenv("TAVILY_API_KEY", "dummy")
    return FakeTavily


def test_results_reshaped(fake_tavily):
    out = mod.web_search("LangGraph")
    assert out == {"results": [
        {"title": "A", "url": "https://a.com", "content": "x"},
        {"title": "", "url": "https://b.com", "content": ""},
    ]}


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_raises(fake_tavily, query):
    with pytest.raises(ValueError, match="empty"):
        mod.web_search(query)
    assert fake_tavily.calls == []


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        mod.web_search("LangGraph")


def test_max_results_clamped(fake_tavily):
    mod.web_search("LangGraph", max_results=50)
    mod.web_search("LangGraph", max_results=0)
    assert [c["max_results"] for c in fake_tavily.calls] == [10, 1]
