"""
Runs the research graph on the topics in evals/topics.json and writes evals/results.csv.

    python -m evals.run_eval                      # all topics
    python -m evals.run_eval --only 1,2 --pause 10

Results are merged by topic id, so topics can be run in batches across days
(the Gemini free tier can't do all 15 in one go).
"""
import os

# Must run before any project import: eval traces go to their own LangSmith project.
# load_dotenv() never overwrites a variable that's already set, so this wins over .env.
os.environ.setdefault("LANGSMITH_PROJECT", "research-agent-v2-eval")

import argparse
import csv
import json
import statistics
import time
import uuid
from pathlib import Path

from config import MODEL, RECURSION_LIMIT
from graph.workflow import app
from evals.metrics import citation_coverage, cited_claims
from evals.judge import groundedness

HERE = Path(__file__).resolve().parent
TOPICS = HERE / "topics.json"
RESULTS = HERE / "results.csv"
REPORTS = HERE / "reports"

COLUMNS = ["id", "category", "topic", "model", "status", "error", "sources", "search_attempts",
           "refined", "failed_summaries", "citation_coverage", "groundedness", "latency_s"]


def run_topic(t: dict) -> dict:
    cfg = {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "recursion_limit": RECURSION_LIMIT,
        "run_name": "eval-run",
        "tags": ["eval", t["category"]],
        "metadata": {"topic_id": t["id"]},
    }
    row = {"id": t["id"], "category": t["category"], "topic": t["topic"], "model": MODEL}

    start = time.perf_counter()
    try:
        app.invoke({"query": t["topic"]}, cfg)
        if app.get_state(cfg).next == ("writer",):
            app.invoke(None, cfg)  # auto-approve: no human pause to subtract from latency
        row["latency_s"] = round(time.perf_counter() - start, 1)

        values = app.get_state(cfg).values
        report = values.get("final_report")
        summaries = values.get("summaries") or []

        row.update({
            "status": "report" if report else "fail",
            "error": "" if report else (values.get("error") or ""),
            "sources": len(values.get("sources") or []),
            "search_attempts": values.get("search_attempts", 0),
            "refined": bool(values.get("search_query")),
            "failed_summaries": len(values.get("failed_sources") or []),
        })

        if report:
            (REPORTS / f"{t['id']}.md").write_text(f"# {t['topic']}\n\n{report}\n", encoding="utf-8")
            cov = citation_coverage(report)
            grd = groundedness(cited_claims(report, summaries), summaries)
            row["citation_coverage"] = "" if cov is None else round(cov, 3)
            row["groundedness"] = "" if grd is None else round(grd, 3)

    except Exception as e:  # anything that escapes the graph is a crash, not a clean fail
        row.update({"status": "crash", "error": f"{type(e).__name__}: {e}",
                    "latency_s": round(time.perf_counter() - start, 1)})

    return {c: row.get(c, "") for c in COLUMNS}


def load_results() -> dict[int, dict]:
    if not RESULTS.exists():
        return {}
    with RESULTS.open(newline="", encoding="utf-8") as f:
        return {int(r["id"]): r for r in csv.DictReader(f)}


def save_results(rows: dict[int, dict]) -> None:
    with RESULTS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for i in sorted(rows):
            w.writerow(rows[i])


def _num(v):
    return None if v in ("", None) else float(v)


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return f"{statistics.mean(vals):.2f}" if vals else "-"


def summary(rows: list[dict], label: str) -> str:
    n = len(rows)
    status = [r["status"] for r in rows]
    pct = lambda k: f"{100 * k / n:.0f}%"
    lat = [_num(r["latency_s"]) for r in rows if _num(r["latency_s"]) is not None]
    return (
        f"{label:<8} n={n:<3}"
        f" completed={pct(sum(s in ('report', 'fail') for s in status)):<5}"
        f" report={pct(status.count('report')):<5}"
        f" fail={pct(status.count('fail')):<5}"
        f" crash={status.count('crash'):<3}"
        f" sources={_mean([_num(r['sources']) for r in rows]):<6}"
        f" refined={pct(sum(str(r['refined']) == 'True' for r in rows)):<5}"
        f" failed_summ={sum(int(_num(r['failed_summaries']) or 0) for r in rows):<3}"
        f" citation_cov={_mean([_num(r['citation_coverage']) for r in rows]):<6}"
        f" grounded={_mean([_num(r['groundedness']) for r in rows]):<6}"
        f" latency_med={f'{statistics.median(lat):.1f}s' if lat else '-':<7}"
        f" latency_max={f'{max(lat):.1f}s' if lat else '-'}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated topic ids, e.g. 1,2,3")
    parser.add_argument("--pause", type=float, default=10, help="seconds between topics (rate limit)")
    args = parser.parse_args()

    topics = json.loads(TOPICS.read_text(encoding="utf-8"))
    if args.only:
        wanted = {int(x) for x in args.only.split(",")}
        topics = [t for t in topics if t["id"] in wanted]

    REPORTS.mkdir(exist_ok=True)
    rows = load_results()

    for i, t in enumerate(topics):
        if i:
            time.sleep(args.pause)
        print(f"\n===== [{t['id']}] {t['category']}: {t['topic']}")
        rows[t["id"]] = run_topic(t)
        save_results(rows)  # save after every topic, so a crash or Ctrl+C keeps what's done
        r = rows[t["id"]]
        print(f"===== [{t['id']}] {r['status']} | sources={r['sources']} | coverage={r['citation_coverage']}"
              f" | grounded={r['groundedness']} | {r['latency_s']}s {r['error'][:100]}")

    all_rows = list(rows.values())
    print(f"\nSummary of {RESULTS.name} ({len(all_rows)} topics, model {MODEL}):\n")
    print(summary(all_rows, "ALL"))
    for cat in dict.fromkeys(r["category"] for r in sorted(all_rows, key=lambda r: int(r["id"]))):
        print(summary([r for r in all_rows if r["category"] == cat], cat))


if __name__ == "__main__":
    main()
