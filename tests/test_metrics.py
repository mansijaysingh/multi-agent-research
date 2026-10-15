import pytest

import evals.judge as judge
from evals.metrics import citation_coverage, cited_claims, key_findings, sentences

REPORT = """## Introduction
This introduction sentence has no citation at all.

## Key Findings
Remote work raised productivity for many teams [1]. Commuting time dropped sharply for most staff [2].
Office costs fell by a large margin in surveyed firms [1][3]. Some managers reported weaker team culture.

## Conclusion
This conclusion sentence also has no citation.

## Sources
- [1] [A](https://a.com)
"""


def test_key_findings_returns_only_that_section():
    kf = key_findings(REPORT)
    assert "Remote work raised productivity" in kf
    assert "introduction sentence" not in kf
    assert "conclusion sentence" not in kf


def test_key_findings_missing():
    assert key_findings("## Introduction\nNo findings here at all.") is None


def test_key_findings_numbered_heading():
    assert "Fact" in key_findings("## 2. Key Findings\nFact number one is here [1].\n## 3. Conclusion\nEnd.")


def test_citation_coverage():
    assert citation_coverage(REPORT) == 0.75


def test_citation_after_full_stop_stays_with_its_claim():
    text = "Claim number one is stated here. [2] Claim number two is also here [1]."
    assert sentences(text) == ["Claim number one is stated here [2].", "Claim number two is also here [1]."]


def test_split_before_sentence_starting_with_number_or_quote():
    text = 'Adoption grew quickly across firms [1]. 80% of surveyed firms use it daily. "Agents" now handle triage [2].'
    assert sentences(text) == [
        "Adoption grew quickly across firms [1].",
        "80% of surveyed firms use it daily.",
        '"Agents" now handle triage [2].',
    ]


def test_bullets_are_separate_sentences():
    report = "## Key Findings\n- The first fact in the list [1].\n- The second fact in the list.\n"
    assert len(sentences(key_findings(report))) == 2
    assert citation_coverage(report) == 0.5


def test_subheadings_are_not_sentences():
    report = "## Key Findings\n### Costs and benefits overview\nCosts fell sharply in most firms [1].\n"
    assert citation_coverage(report) == 1.0


def test_cited_claims_drops_ids_without_summary():
    summaries = [{"source_id": 1, "text": "a"}, {"source_id": 2, "text": "b"}]
    claims = cited_claims(REPORT, summaries)
    assert [c["ids"] for c in claims] == [[1], [2], [1]]   # [3] has no summary, so it's dropped


def test_groundedness(monkeypatch):
    claims = [{"claim": f"c{i}", "ids": [1]} for i in range(3)]
    summaries = [{"source_id": 1, "text": "a"}]
    verdicts = judge.Verdicts(verdicts=[
        judge.Verdict(claim=1, supported=True),
        judge.Verdict(claim=2, supported=False),
        judge.Verdict(claim=3, supported=True),
    ])
    monkeypatch.setattr(judge, "_judge", lambda prompt: verdicts)
    assert judge.groundedness(claims, summaries) == pytest.approx(2 / 3)

    def boom(prompt):
        raise RuntimeError("quota")

    monkeypatch.setattr(judge, "_judge", boom)
    assert judge.groundedness(claims, summaries) is None


def test_groundedness_no_claims():
    assert judge.groundedness([], []) is None
