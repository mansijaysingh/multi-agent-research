from agents.fail_node import fail_node


def test_keeps_existing_error():
    assert fail_node({"error": "search failed: boom"}) == {"error": "search failed: boom"}


def test_no_sources():
    assert fail_node({"search_attempts": 2, "sources": []}) == {"error": "no sources found after 2 searches"}


def test_every_summary_failed():
    state = {"sources": [{"id": 1, "title": "", "url": "u1", "content": ""}], "summaries": []}
    assert fail_node(state) == {"error": "no relevant sources found (every source was off-topic or couldn't be summarized)"}
