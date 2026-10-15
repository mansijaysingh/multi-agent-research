from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from config import MODEL

load_dotenv()

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.2)


def summarizer_agent(state):
  """
    Takes sources from state
    Summarizes each one using Gemini
    Returns summaries and the ids of sources that failed
    """
  # Temporary: skip if an earlier node failed. Supervisor routing replaces this in Step 3
  if state.get("error"):
      return {}

  sources = state.get("sources", [])

  summaries = []
  failed = []

  for s in sources:
      try:
         content = s.get("content", " ")

         prompt = f"""
You are an expert research summarizer.

Read the research content below and create a clear, concise, and informative summary.

Requirements:
- Focus on the most important insights
- Avoid unnecessary details
- Keep the summary professional and easy to understand
- Use simple and clean language

Research Content:
{content}
"""

         response = llm.invoke(prompt)

         summaries.append({"source_id": s["id"], "text": response.text})
      except Exception as e:
         print(f"summary failed for source {s['id']}: {e}")
         failed.append(s["id"])

  return {"summaries": summaries, "failed_sources": failed}
