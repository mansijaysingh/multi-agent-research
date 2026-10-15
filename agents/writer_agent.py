import re

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from config import MODEL

load_dotenv()

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.3)


def _write(prompt):
    """Model call kept as a module-level function so tests can monkeypatch it."""
    return llm.invoke(prompt).text


def writer_agent(state):
    """
    Takes summaries from state
    Generates a cited research report; the Sources list is built in code from state
    Returns the report, or an error if it can't write one
    """
    summaries = state.get("summaries", [])
    if not summaries:
        return {"error": "no summaries to write a report from"}

    try:
        query = state["query"]
        by_id = {s["id"]: s for s in state.get("sources", [])}

        notes = "\n\n".join(
            f"[{m['source_id']}] {by_id[m['source_id']]['title']}: {m['text']}" for m in summaries
        )

        prompt = f"""
Write a research report on: {query}

Use these sections as ## headings: Introduction, Key Findings, Conclusion.

Rules:
- Use only the notes below.
- After every factual claim, cite the note number it came from, like [2].
- For more than one source, give each number its own brackets, like [1][3], not [1, 3].
- Do not add a sources or references list.

Notes:
{notes}
"""
        body = _write(prompt)

        # The model sometimes adds its own list anyway; ours is the only one we trust.
        # Only a heading that is exactly "Sources" or "References" counts, so a heading
        # like "### Sources of Error" inside the report is kept.
        body = re.split(r"(?im)^#{1,6}[ \t]*(?:sources|references)[ \t]*:?[ \t]*$", body)[0].rstrip()

        # Only summarized sources can be cited: drop any other [n] (and the spaces before it, not line breaks)
        valid = {m["source_id"] for m in summaries}
        body = re.sub(r"[ \t]*\[(\d+)\]", lambda m: m.group(0) if int(m.group(1)) in valid else "", body)

        # The Sources list comes from state, never from the model, so URLs can't be made up
        refs = "\n".join(
            f"- [{i}] [{by_id[i]['title'] or by_id[i]['url']}]({by_id[i]['url']})" for i in sorted(valid)
        )

        # Clear any earlier error (e.g. a failed retry search) now that there is a report
        return {"final_report": f"{body}\n\n## Sources\n{refs}", "error": None}

    except Exception as e:
        return {"error": f"writer failed: {e}"}
