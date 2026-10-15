def fail_node(state):
    """
    End of a run that can't produce a report.
    Keeps an existing error (e.g. "search failed: MCP tool ..."), since that's the most useful one;
    otherwise explains what went wrong from the state.
    """
    if state.get("error"):
        return {"error": state["error"]}

    if not state.get("sources"):
        attempts = state.get("search_attempts", 0)
        return {"error": f"no sources found after {attempts} searches"}

    # Sources were found, but none survived the summarizer
    return {"error": "no relevant sources found (every source was off-topic or couldn't be summarized)"}
