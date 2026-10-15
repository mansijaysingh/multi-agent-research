from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from config import MODEL, MAX_CONCURRENCY

load_dotenv()

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.2)

IRRELEVANT = "IRRELEVANT"

SYSTEM = ("You summarise one web source for a research report. "
          "Keep only facts stated in the source. 4-6 sentences, plain language. "
          f"If the source has nothing to do with the research topic, reply with exactly {IRRELEVANT}.")

MAX_CHARS = 4000  # per source, keeps token use low on the free tier


def _summarize_all(msgs):
    """
    Runs all model calls concurrently. return_exceptions=True means a failed call
    comes back as an Exception in its slot instead of losing every summary.
    Kept as a module-level function so tests can monkeypatch it
    (Pydantic won't let you patch llm.batch directly).
    """
    return llm.batch(msgs, config={"max_concurrency": MAX_CONCURRENCY}, return_exceptions=True)


def summarizer_agent(state):
    """
    Takes sources from state
    Summarizes them all in parallel using Gemini, dropping sources that don't match the topic
    Returns summaries and the ids of sources that failed or were irrelevant
    """
    sources = state.get("sources", [])
    topic = state.get("query", "")

    # The topic is in every message so the model can reject off-topic sources
    # (the relevance check costs no extra calls)
    msgs = [
        [("system", SYSTEM),
         ("user", f"Research topic: {topic}\nTitle: {s['title']}\n\n{(s.get('content') or '')[:MAX_CHARS]}")]
        for s in sources
    ]

    outs = _summarize_all(msgs) if msgs else []

    summaries = []
    failed = []

    # batch keeps the input order, so each output lines up with its source
    for s, out in zip(sources, outs):
        if isinstance(out, Exception):
            reason = out
        elif not out.text.strip():
            reason = "empty response"
        elif out.text.strip().rstrip(".") == IRRELEVANT:
            reason = "irrelevant to the topic"
        else:
            summaries.append({"source_id": s["id"], "text": out.text})
            continue
        print(f"summary failed for source {s['id']}: {reason}")
        failed.append(s["id"])

    # Once the summarizer has run, any earlier search error is stale
    return {"summaries": summaries, "failed_sources": failed, "error": None}
