def supervisor(state):
  """"
   Supervisor Agent

    Initializes the workflow state.
  """

  print("\n🧠 Supervisor started...")

  query=state["query"]

  print(f"\n📌 User Query: {query}")
  state["query"] = query

  return state
