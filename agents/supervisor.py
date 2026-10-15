from config import MIN_SOURCES, MAX_SEARCH_ATTEMPTS


def decide(state) -> str:
    """
    Picks the next step from the state using fixed rules (no LLM).
    Pure function, so it can be unit-tested without any API calls.
    """
    sources = state.get("sources", [])
    attempts = state.get("search_attempts", 0)
    summaries = state.get("summaries")  # None = summarizer hasn't run, [] = every summary failed

    if attempts == 0:
        return "search"

    if len(sources) < MIN_SOURCES and attempts < MAX_SEARCH_ATTEMPTS:
        return "refine_query"  # then search again

    # Out of attempts (or enough sources): carry on with what we have.
    # summaries must still be checked here, or a run with 1-2 sources loops back to the summarizer forever.
    if not sources:
        return "fail"

    if summaries is None:
        return "summarizer"

    if not summaries:
        return "fail"

    return "writer"


def supervisor(state):
    """
    Supervisor Agent

    The hub: every worker returns here, and it picks the next step.
    """
    step = decide(state)
    print(f"\n🧠 Supervisor -> {step}")
    return {"next_step": step}
