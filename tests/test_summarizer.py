from types import SimpleNamespace

import agents.summarizer_agent as mod


def _sources(*ids, content="x"):
    return [{"id": i, "title": "t", "url": f"u{i}", "content": content} for i in ids]


def test_one_failure_keeps_others(monkeypatch):
    fake = [SimpleNamespace(text="a"), RuntimeError("boom"), SimpleNamespace(text="c")]
    monkeypatch.setattr(mod, "_summarize_all", lambda msgs: fake)
    out = mod.summarizer_agent({"sources": _sources(1, 2, 3)})
    assert [s["source_id"] for s in out["summaries"]] == [1, 3]
    assert [s["text"] for s in out["summaries"]] == ["a", "c"]
    assert out["failed_sources"] == [2]


def test_empty_summary_counts_as_failure(monkeypatch):
    fake = [SimpleNamespace(text="a"), SimpleNamespace(text="  "), SimpleNamespace(text="c")]
    monkeypatch.setattr(mod, "_summarize_all", lambda msgs: fake)
    out = mod.summarizer_agent({"sources": _sources(1, 2, 3)})
    assert [s["source_id"] for s in out["summaries"]] == [1, 3]
    assert out["failed_sources"] == [2]


def test_no_sources(monkeypatch):
    monkeypatch.setattr(mod, "_summarize_all", lambda msgs: [])
    out = mod.summarizer_agent({})
    assert out["summaries"] == []
    assert out["failed_sources"] == []


def test_long_content_is_cut(monkeypatch):
    seen = {}

    def fake(msgs):
        seen["msgs"] = msgs
        return [SimpleNamespace(text="ok")]

    monkeypatch.setattr(mod, "_summarize_all", fake)
    mod.summarizer_agent({"sources": _sources(1, content="x" * 10000)})
    user_msg = seen["msgs"][0][1][1]
    assert user_msg.count("x") == mod.MAX_CHARS


def test_clears_stale_search_error(monkeypatch):
    monkeypatch.setattr(mod, "_summarize_all", lambda msgs: [SimpleNamespace(text="a")])
    out = mod.summarizer_agent({"sources": _sources(1), "error": "search failed: boom"})
    assert out["error"] is None
