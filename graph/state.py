from typing import TypedDict


class Source(TypedDict):
    id: int          # 1-based, used for [1], [2] citations
    title: str
    url: str
    content: str


class Summary(TypedDict):
    source_id: int
    text: str


class AgentState(TypedDict, total=False):
    query: str                 # user's topic, never changed
    search_query: str          # current query sent to search
    search_attempts: int
    sources: list[Source]
    summaries: list[Summary]
    failed_sources: list[int]  # ids whose summary failed
    final_report: str
    error: str | None          # last error, for routing and UI
    next_step: str             # set by supervisor, read by route()
