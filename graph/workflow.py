from typing import TypedDict
from langgraph.graph import StateGraph, END

#import agents
from agents.supervisor import supervisor
from agents.search_agent import search_agent
from agents.summarizer_agent import summarizer_agent
from agents.writer_agent import writer_agent


class AgentState(TypedDict):

  query:str
  search_results: list
  summaries: list
  final_report:str


# Add nodes
graph=StateGraph(AgentState)

graph.add_node("supervisor", supervisor)

graph.add_node("search_agent", search_agent)

graph.add_node("summarizer_agent", summarizer_agent)

graph.add_node("writer_agent",writer_agent)

# ---------------- EDGES ----------------

graph.add_edge("supervisor", "search_agent")

graph.add_edge("search_agent", "summarizer_agent")

graph.add_edge("summarizer_agent", "writer_agent")

graph.add_edge("writer_agent", END)

# ---------------- ENTRY POINT ----------------

graph.set_entry_point("supervisor")

# ---------------- COMPILE ----------------

app = graph.compile()


# ---------------- TEST ----------------

if __name__ == "__main__":
  initial_state={
    "query": "Future of AI in healthcare"
  }

  result=app.invoke(initial_state)

  print("\n✅ FINAL REPORT:\n")

  print(result["final_report"])
  