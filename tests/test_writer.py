import agents.writer_agent as mod

SOURCES = [{"id": i, "title": f"T{i}", "url": f"https://e.com/{i}", "content": ""} for i in (1, 2, 3)]
SUMMARIES = [{"source_id": 1, "text": "a"}, {"source_id": 2, "text": "b"}]  # source 3's summary failed
STATE = {"query": "x", "sources": SOURCES, "summaries": SUMMARIES}


def _fake(monkeypatch, text):
    monkeypatch.setattr(mod, "_write", lambda prompt: text)


def test_invalid_citation_removed(monkeypatch):
    _fake(monkeypatch, "Fact [1]. Other [9]. More [2].")
    report = mod.writer_agent(STATE)["final_report"]
    assert "Fact [1]." in report and "More [2]." in report
    assert "[9]" not in report
    assert "Other." in report and "Other ." not in report


def test_failed_source_not_citable(monkeypatch):
    _fake(monkeypatch, "Claim [3].")
    report = mod.writer_agent(STATE)["final_report"]
    assert "[3]" not in report
    assert "https://e.com/3" not in report


def test_sources_list_built_from_state(monkeypatch):
    _fake(monkeypatch, "Body [1].")
    report = mod.writer_agent(STATE)["final_report"]
    assert "## Sources" in report
    assert report.endswith("- [1] [T1](https://e.com/1)\n- [2] [T2](https://e.com/2)")


def test_model_sources_list_is_dropped(monkeypatch):
    _fake(monkeypatch, "Body [1].\n\n## References\n- made up https://fake.com")
    report = mod.writer_agent(STATE)["final_report"]
    assert "fake.com" not in report
    assert report.count("## Sources") == 1 and "References" not in report


def test_heading_starting_with_sources_is_kept(monkeypatch):
    _fake(monkeypatch, "Intro [1].\n\n### Sources of Error\nBias [2].\n\n## Conclusion\nDone.")
    report = mod.writer_agent(STATE)["final_report"]
    assert "### Sources of Error" in report
    assert "Bias [2]." in report and "Done." in report


def test_invalid_citation_at_line_start_keeps_line_break(monkeypatch):
    _fake(monkeypatch, "Line one [1].\n[9] Line two.")
    report = mod.writer_agent(STATE)["final_report"]
    assert "Line one [1].\n Line two." in report


def test_prompt_uses_numbered_notes(monkeypatch):
    seen = {}

    def fake(prompt):
        seen["prompt"] = prompt
        return "ok"

    monkeypatch.setattr(mod, "_write", fake)
    mod.writer_agent(STATE)
    assert "[1] T1: a" in seen["prompt"]
    assert "[2] T2: b" in seen["prompt"]


def test_writer_failure(monkeypatch):
    def boom(prompt):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "_write", boom)
    out = mod.writer_agent(STATE)
    assert out["error"].startswith("writer failed")
    assert "final_report" not in out


def test_no_summaries():
    out = mod.writer_agent({"query": "x", "sources": SOURCES, "summaries": []})
    assert out == {"error": "no summaries to write a report from"}
