# Evaluation notes (Step 8)

Run on 2026-10-15 with `python -m evals.run_eval`, in 3 batches (topics 1–2, 3–8 and 9–15),
using **gemini-3.5-flash-lite** for the agents and the judge. The free-tier quota for
`gemini-3.8-flash` was used up, so these numbers are for the lite model. Raw data is in
`results.csv`, and every report is in `reports/`.

## Summary

| Group | Topics | Completed | Report | Fail | Crash | Sources (mean) | Refined | Citation coverage | Groundedness | Latency (median / max) |
|---|---|---|---|---|---|---|---|---|---|---|
| **All** | 15 | 100% | 100% | 0% | 0 | 5.0 | 0% | **0.97** | **1.00** | **29.1 s** / 53.7 s |
| broad | 5 | 100% | 100% | 0% | 0 | 5.0 | 0% | 0.96 | 1.00 | 33.6 s / 53.7 s |
| recent | 4 | 100% | 100% | 0% | 0 | 5.0 | 0% | 0.98 | 1.00 | 31.9 s / 40.4 s |
| niche | 3 | 100% | 100% | 0% | 0 | 5.0 | 0% | 1.00 | 1.00 | 20.6 s / 29.1 s |
| vague | 3 | 100% | 100% | 0% | 0 | 5.0 | 0% | 0.93 | 1.00 | 18.8 s / 30.7 s |

No summaries failed, so the free-tier rate limit was never hit with 15 s pauses between
topics.

## What the metrics mean

- **Completed:** the run ended with a report or a clean fail message. A crash doesn't count.
- **Citation coverage:** the share of Key Findings sentences with at least one `[n]`. The
  sentence split is a heuristic.
- **Groundedness:** the share of cited claims that an LLM judge rates "fully supported by
  the cited notes". It uses one judge call per report.
- **Latency:** wall-clock time for the whole run, with approval automatic.

## Tokens and cost (from LangSmith, project `research-agent-v2-eval`)

| | Calls | Tokens (in / out / total) | Per topic |
|---|---|---|---|
| Agent graph (summaries + writer) | 90 (6 per topic) | 33,580 / 18,198 / **51,778** | ~3,450 |
| Judge | 15 (1 per topic) | **36,755** total | ~2,450 |

- The judge uses about 70% as many tokens as the whole agent. It re-sends the cited notes for
  every claim, which makes the prompt large. But those tokens are mostly input (33,260 in,
  3,495 out), which is the cheap side, so the judge's *cost* is only about a third of the
  agent's.
- The cost on the free tier is $0.

**What the eval would cost at paid prices.** The prices are the Standard paid tier per 1M
tokens, from ai.google.dev/gemini-api/docs/pricing, last updated 2026-10-15. Token counts:
agent 33,580 in / 18,198 out; judge 33,260 in / 3,495 out.

| Model | Price in / out | Agent (15 topics) | Judge | **Total eval** | Per report | 1,000 reports (agent only) |
|---|---|---|---|---|---|---|
| **3.5 Flash-Lite** (used) | $0.30 / $2.50 | $0.056 | $0.019 | **$0.074** | **~$0.004** | **~$3.70** |
| 3.8 Flash, until 31 Dec 2026 | $0.75 / $3.75 | $0.093 | $0.038 | $0.132 | ~$0.006 | ~$6.23 |
| 3.8 Flash, from 1 Jan 2027 | $1.50 / $7.50 | $0.187 | $0.076 | $0.263 | ~$0.012 | ~$12.46 |

- **Output tokens drive the cost.** Output is 8× the input price on Flash-Lite, so the
  writer's long report is the most expensive single call, as well as the slowest (16.7 s in
  the Step 7 trace).
- Tavily isn't included; its free plan covered all of this.

## Free-tier rate limits (Google AI Studio, checked 2026-10-15 after the eval)

| Model | Requests/min used / limit | Tokens/min used / limit | Requests/day used / limit |
|---|---|---|---|
| **Gemini 3.5 Flash Lite** (used for the eval) | **16 / 15** | 49.86K / 250K | **195 / 500** |
| Gemini 3.8 Flash (the intended model) | 4 / 5 | 11.82K / 250K | **24 / 20**, over the limit |
| Gemini 3.7 Flash | 5 / 5 | 3 / 250K | 6 / 20 |
| Gemini 3.6 Flash | 4 / 5 | 4 / 250K | 6 / 20 |

What this means for the project:
- **Requests per minute, not tokens, are the tight limit.** One run makes about 6–8 Gemini
  calls within about 30 s, and the lite model allows 15 a minute. That's why
  `MAX_CONCURRENCY = 3` and the eval waits `--pause 15` between topics.
- The lite model's per-minute count **peaked at 16, one over the limit**. No summary failed,
  because the Gemini client retries with backoff. That's also why a few runs were slow
  (the 22–41 s summary times measured in Step 4).
- Per day, a full 15-topic eval is about 105 calls, about a fifth of the lite model's 500,
  so it fits in one day. On `gemini-3.8-flash` (20 a day) it would take about 6 days. That's
  why the eval ran on the lite model.
- Tokens per minute are far below the limit (50K of 250K), so the 4,000-character limit on
  each source is about cost, not about this limit.
- The usage on Gemini 3.6 and 3.7 Flash didn't come from this project, which never used
  those models. It's another app or tool using the same key or Google project.

## Is the judge just saying "yes" to everything?

Groundedness was 1.00 on all 15 reports, so I tested the judge separately:
1. I took 4 real claims from report 1 and added 2 planted false claims that cite the same
   notes: "AI chatbots have completely replaced all human agents worldwide since 2019" and
   "customer satisfaction fell by 80 percent after every AI deployment".
2. The judge marked all 4 real claims as supported and **rejected both false ones**
   (score 4/6).

So it catches made-up facts. It probably misses subtle distortions (see report 3 below), and
it's the same model that wrote the reports, so it may be lenient with its own style of
wording.

## What I found by reading 5 reports

- **#14 `qwxz plorbt vrenk` (vague):**
  - Tavily returned pages about the 1991 film *Point Break*, and the app wrote a confident,
    fully cited report about the film.
  - It scored **coverage 1.0, groundedness 1.0**.
  - **The metrics measure whether the report matches its sources, not whether it answers the
    question asked.** This is the biggest gap.
- **#10 zinc-air battery recycling in India (niche):**
  - The Introduction is about India, but Key Findings is generic recycling advice, and 5 of
    its 6 sentences cite the same patent-search page [4].
  - Almost nothing about recycling *in India* was found, yet the report doesn't say so.
  - Source [5], a YouTube lecture, is in the Sources list but never cited. That's the open
    decision about listing only cited sources.
- **#1 impact of AI on customer support (broad):**
  - "Gartner predicts 80%… will use generative AI **by 2025**" comes from a 2024 article and
    is presented as current.
  - 3 of the 5 sources are vendor blogs or sponsored content (Forethought, Precog, and an
    Intercom-sponsored HBR page), so the report leans optimistic.
  - The metrics don't look at the date or the quality of a source.
- **#3 how EVs affect the power grid (broad):**
  - A solid, well-structured report from strong sources (DOE, RMI, MIT).
  - One phrase, "help grids … by **strengthening the duck curve**", is probably a distortion,
    since EVs are usually said to help *flatten* it. The judge accepted it.
- **#6 latest developments in AI regulation in 2026 (recent):**
  - Good: current 2026 sources, specific dates and bill names, and clear EU / US federal / US
    state sections.
  - Source [4] is a YouTube video, so its content is only Tavily's text snippet.

## Limitations to state honestly (README)

1. **The refine and fail paths never ran in the eval.** Tavily returned 5 results for every
   topic, including nonsense, so "refined 0%" and "fail 0%" don't show those paths work.
   Unit tests (`test_routing.py`) and forced runs in Steps 3 and 6 cover them instead.
2. **No relevance check.** An off-topic or nonsense query still produces a confident report
   (#14).
3. **Groundedness is judged by the same model** that wrote the report, it isn't perfect at
   catching subtle distortions (#3), and 15 topics is a small sample.
4. **Source quality and dates aren't checked**: vendor content, and outdated forecasts
   presented as current (#1).
5. **Citation coverage uses a heuristic sentence split.**
6. **The numbers are for `gemini-3.5-flash-lite`**, not the intended `gemini-3.8-flash`.
