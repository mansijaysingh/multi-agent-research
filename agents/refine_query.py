from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from config import MODEL

load_dotenv()


class Refined(BaseModel):
    query: str


llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0).with_structured_output(Refined)


def refine_query(state):
    """
    Called when a search found too few sources.
    Asks Gemini for one more specific search query.
    Returns the new search_query, or nothing (the old query is kept) if the call fails.
    """
    last_query = state.get("search_query") or state["query"]
    titles = ", ".join(s["title"] for s in state.get("sources", [])) or "none"

    prompt = (
        f"Topic: {state['query']}\n"
        f"Last search query: {last_query}\n"
        f"Results found: {titles}\n"
        "Too few useful results. Write one more specific web search query."
    )

    try:
        result = llm.invoke(prompt)
        print(f"\n🔁 Refined query: {result.query}")
        return {"search_query": result.query}
    except Exception as e:
        print(f"refine query failed, keeping the old query: {e}")
        return {}
