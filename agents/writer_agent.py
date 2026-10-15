from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from config import MODEL

load_dotenv()

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.3)


def writer_agent(state):
    """
    Takes summaries from state
    Generates final research report
    Returns the report, or an error if it can't write one
    """
    summaries = state.get("summaries", [])
    if not summaries:
        return {"error": "no summaries to write a report from"}

    try:
        query=state["query"]
        #    report_length = state["report_length"]

        combined_summaries = "\n\n".join(m["text"] for m in summaries)

        prompt = f"""
You are an expert research report writer.

Write a detailed, professional, and well-structured research report.

Research Topic:
{query}

Based on these research summaries:
{combined_summaries}

Requirements:
- Use clear headings
- Keep the report informative and easy to read
- Avoid repetition
- Explain key insights properly
- Make the report professional and polished

The report must include:

1. Introduction
2. Key Findings
3. Conclusion
"""
        response = llm.invoke(prompt)

        # Clear any earlier error (e.g. a failed retry search) now that there is a report
        return {"final_report": response.text, "error": None}

    except Exception as e:
        return {"error": f"writer failed: {e}"}
