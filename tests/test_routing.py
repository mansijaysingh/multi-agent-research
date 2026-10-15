import pytest

from agents.supervisor import decide

S = lambda n: [{"id": i, "title": "", "url": f"u{i}", "content": ""} for i in range(1, n + 1)]


@pytest.mark.parametrize("state, expected", [
    ({}, "search"),
    ({"search_attempts": 1, "sources": S(1)}, "refine_query"),
    ({"search_attempts": 2, "sources": S(1)}, "summarizer"),
    ({"search_attempts": 2, "sources": []}, "fail"),
    ({"search_attempts": 1, "sources": S(5)}, "summarizer"),
    ({"search_attempts": 1, "sources": S(5), "summaries": []}, "fail"),
    ({"search_attempts": 1, "sources": S(5), "summaries": [{"source_id": 1, "text": "x"}]}, "writer"),
    # too few sources but attempts left: refine even though the summarizer hasn't run
    ({"search_attempts": 1, "sources": S(1), "summaries": None}, "refine_query"),
    # out of attempts with 1-2 sources: once summaries exist, move on instead of looping to the summarizer
    ({"search_attempts": 2, "sources": S(2), "summaries": [{"source_id": 1, "text": "x"}]}, "writer"),
    ({"search_attempts": 2, "sources": S(2), "summaries": []}, "fail"),
])
def test_decide(state, expected):
    assert decide(state) == expected
