"""
LLM-as-judge for groundedness: is each cited claim supported by the notes it cites?

Limitation: the judge is the same model that wrote the report, so it may be lenient
with its own output. The number is a signal, not proof.
"""
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from config import MODEL

load_dotenv()


class Verdict(BaseModel):
    claim: int  # the claim's number in the list we sent (1-based)
    supported: bool


class Verdicts(BaseModel):
    verdicts: list[Verdict]


llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0).with_structured_output(Verdicts)


def _judge(prompt):
    """Model call kept as a module-level function so tests can monkeypatch it."""
    return llm.invoke(prompt)


def groundedness(claims: list[dict], summaries: list[dict]) -> float | None:
    """
    Share of cited claims the judge marks as supported, using one judge call per report.
    A claim the judge leaves out counts as unsupported. None if there are no claims or the call fails.
    """
    if not claims:
        return None

    notes = {m["source_id"]: m["text"] for m in summaries}
    blocks = []
    for i, c in enumerate(claims, 1):
        cited = "\n".join(f"  [{n}] {notes[n]}" for n in c["ids"] if n in notes)
        blocks.append(f"Claim {i}: {c['claim']}\nCited notes:\n{cited}")

    prompt = (
        "You check a research report against its sources.\n"
        "For each claim, is it fully supported by the cited notes? "
        "Answer false if the notes don't state it.\n"
        "Return one verdict per claim, using the claim's number.\n\n" + "\n\n".join(blocks)
    )

    try:
        result = _judge(prompt)
    except Exception as e:
        print(f"judge failed: {e}")
        return None

    supported = {v.claim for v in result.verdicts if v.supported and 1 <= v.claim <= len(claims)}
    return len(supported) / len(claims)
