from langgraph.graph import StateGraph, START, END

from config import RECURSION_LIMIT
from graph.state import AgentState

from agents.supervisor import supervisor
from agents.search_agent import search_agent
from agents.refine_query import refine_query
from agents.summarizer_agent import summarizer_agent
from agents.writer_agent import writer_agent
from agents.fail_node import fail_node


# ---------------- NODES ----------------

g = StateGraph(AgentState)

for name, fn in [
    ("supervisor", supervisor),
    ("search", search_agent),
    ("refine_query", refine_query),
    ("summarizer", summarizer_agent),
    ("writer", writer_agent),
    ("fail", fail_node),
]:
    g.add_node(name, fn)

# ---------------- EDGES ----------------
# The supervisor is the hub: it picks the next step, and search and summarizer report back to it.
# refine_query always leads to search, so every refine counts as another search attempt.

g.add_edge(START, "supervisor")

g.add_conditional_edges(
    "supervisor",
    lambda s: s["next_step"],
    {n: n for n in ["search", "refine_query", "summarizer", "writer", "fail"]},
)

g.add_edge("search", "supervisor")
g.add_edge("refine_query", "search")
g.add_edge("summarizer", "supervisor")
g.add_edge("writer", END)
g.add_edge("fail", END)

# ---------------- COMPILE ----------------
# MemorySaver and interrupt_before=["writer"] come in Step 6 (human review)

app = g.compile()


# ---------------- TEST ----------------

if __name__ == "__main__":
    initial_state = {
        "query": "Future of AI in healthcare"
    }

    result = app.invoke(initial_state, {"recursion_limit": RECURSION_LIMIT})

    print("\n✅ FINAL REPORT:\n")

    print(result.get("final_report") or result.get("error"))
