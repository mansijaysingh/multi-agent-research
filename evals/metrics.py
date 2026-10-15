"""
Report metrics computed in code (no LLM).

The sentence splitting here is a heuristic: it works for the reports this app writes
(prose and bullet lists with [n] citations), not for arbitrary text.
"""
import re

CITATION = re.compile(r"\[(\d+)\]")


def key_findings(report: str) -> str | None:
    """Text between the "## Key Findings" heading and the next "## " heading, or None."""
    # Allows "## Key Findings" and a numbered "## 2. Key Findings", in any case
    m = re.search(r"(?im)^##[ \t]*(?:\d+\.?[ \t]*)?key findings\b.*$", report)
    if not m:
        return None
    rest = report[m.end():]
    nxt = re.search(r"(?m)^##[ \t]", rest)  # level-2 heading only; ### subheadings stay inside
    return rest[:nxt.start()] if nxt else rest


def sentences(text: str) -> list[str]:
    """Heuristic sentence split of a report section."""
    # Drop subheadings and bullet/number markers at the start of lines
    text = re.sub(r"(?m)^[ \t]*#+.*$", "", text)
    text = re.sub(r"(?m)^[ \t]*(?:[-*]|\d+\.)[ \t]+", "", text)
    # Move citations written after the full stop ("claim. [2]") in front of it ("claim [2].")
    # so they stay with their claim instead of starting the next sentence
    text = re.sub(r"([.!?])((?:[ \t]*\[\d+\])+)", r"\2\1", text)
    # Split only where the next sentence starts with a capital letter, a digit ("80% of firms..."),
    # a quote, or a bullet/bold marker
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9*\-\"'“])", text)
    return [p.strip() for p in parts if len(p.strip()) >= 20]


def citation_coverage(report: str) -> float | None:
    """Share of Key Findings sentences with at least one [n]. None if there's nothing to measure."""
    kf = key_findings(report)
    if kf is None:
        return None
    sents = sentences(kf)
    if not sents:
        return None
    return sum(1 for s in sents if CITATION.search(s)) / len(sents)


def cited_claims(report: str, summaries: list[dict]) -> list[dict]:
    """Key Findings sentences with citations, as {"claim", "ids"}; only ids that have a summary."""
    kf = key_findings(report)
    if kf is None:
        return []
    valid = {m["source_id"] for m in summaries}
    claims = []
    for s in sentences(kf):
        ids = list(dict.fromkeys(int(n) for n in CITATION.findall(s) if int(n) in valid))
        if ids:
            claims.append({"claim": s, "ids": ids})
    return claims
