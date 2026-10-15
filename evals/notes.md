# Evaluation notes (Step 8)

All 15 topics were run on 2026-10-15 with `python -m evals.run_eval` on the **final code**,
which includes the relevance check and the corrected sentence split. They used
**gemini-3.5-flash-lite** for the agents and the judge. The free-tier quota for
`gemini-3.8-flash` was used up, so these numbers are for the lite model. Raw data is in
`results.csv`, and every report is in `reports/`.

## Summary

| Group | Topics | Completed | Report | Fail | Crash | Sources (mean) | Off-topic / failed sources | Citation coverage | Groundedness | Latency (median / max) |
|---|---|---|---|---|---|---|---|---|---|---|
| **All** | 15 | **100%** | 93% | 7% | 0 | 5.0 | 12 of 75 | **0.96** | **0.99** | **26.1 s** / 40.2 s |
| broad | 5 | 100% | 100% | 0% | 0 | 5.0 | 0 | 0.93 | 1.00 | 34.1 s / 40.2 s |
| recent | 4 | 100% | 100% | 0% | 0 | 5.0 | 1 | 0.97 | 1.00 | 27.6 s / 33.4 s |
| niche | 3 | 100% | 100% | 0% | 0 | 5.0 | 1 | 1.00 | 0.97 | 26.1 s / 31.3 s |
| vague | 3 | 100% | 67% | 33% | 0 | 5.0 | 10 | 1.00 | 1.00 | 19.7 s / 22.3 s |

- The one fail is #14 `qwxz plorbt vrenk`. That's the correct outcome, a clean
  "no relevant sources found", not a report.
- None of the 12 dropped sources failed because of the rate limit. All were rejected as
  off-topic.

## Relevance check: before and after (Step 8 review fix 1)

The first eval run had no relevance check, and the nonsense topic #14 got a confident,
fully cited report about the film *Point Break* with perfect scores. The summarizer now gets
the research topic in every message and replies `IRRELEVANT` for an off-topic source, at no
extra cost, since it's the same call. Topics 10–15, before and after:

| Topic | Before | After |
|---|---|---|
| #10 zinc-air recycling in India | report, 0 dropped | report, 1 dropped (a hearing-aid battery paper) |
| #11 drones for apple pollination | report, 0 dropped | report, 0 dropped |
| #12 biochar in Kenya | report, groundedness 1.00 | report, groundedness 0.92 |
| #13 "the thing about the new rules" | report from 5 sources | report from 2 sources (3 dropped) |
| **#14 `qwxz plorbt vrenk`** | **[confident report about *Point Break*](before_relevance_check/14.md)** | **clean fail: "no relevant sources found"** |
| #15 "is it good or bad" | report from 5 sources | report from 3 sources (2 dropped) |

The check is lenient on vague topics. #13 and #15 still produce reports from whichever
sources the model judged "related", because a vague question can't really be judged
off-topic.

## Forced paths: refine (Step 8 review fix 2)

Tavily returned 5 results for every topic, so `MIN_SOURCES = 3` never triggers a refine in
normal runs. To measure the refine path, the 3 niche topics were run with only 2 results
per search: `python -m evals.run_eval --only 10,11,12 --max-results 2`, which writes
`results_max2.csv` and `reports_max2/`.

| Topic | Refined query | Sources after 2nd search | Dropped as off-topic | Result |
|---|---|---|---|---|
| #10 | "zinc-air battery recycling infrastructure and startups in India" | 2 → 4 | 2 (both from the refined search) | report |
| #11 | "artificial pollination drone technology cost effectiveness apple orchard trials" | 2 → 4 | 1 | report |
| #12 | "economic barriers and drivers for biochar adoption among smallholder farmers in Kenya" | 2 → 3 | 0 | report |

- The refine ran 3 out of 3 times.
- The second search always added new sources (+2, +2, +1).
- But in #10, the refined query drifted ("startups"), and both new sources were rejected as
  off-topic. **Refining adds sources, but not always relevant ones.**
- The fail path is covered by #14 above, and by the wrong-key runs in Steps 3 and 6.

## What the metrics mean

- **Completed:** the run ended with a report or a clean fail message. A crash doesn't count.
- **Citation coverage:** the share of Key Findings sentences with at least one `[n]`. The
  sentence split is a heuristic.
- **Groundedness:** the share of cited claims that an LLM judge rates "fully supported by
  the cited notes". It uses one judge call per report.
- **Latency:** wall-clock time for the whole run, with approval automatic.

## Tokens and cost (from LangSmith, project `research-agent-v2-eval`)

Measured on the first full 15-topic run, before the relevance check. That check adds no calls
and only a short topic line per message, so the figures still hold.

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

| Model | Price in / out | Agent (15 topics) | Judge | **Total eval** | Per report (agent only) | 1,000 reports (agent only) |
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
  because the Gemini client retries with backoff. That's also why some runs were slow (rate-limited
  summary stages took 7.5–41.7 s in Step 4, against about 3 s normally).
- Per day, a full 15-topic eval is about 105 calls, about a fifth of the lite model's 500,
  so it fits in one day. On `gemini-3.8-flash` (20 a day) it would take about 6 days. That's
  why the eval ran on the lite model.
- Tokens per minute are far below the limit (50K of 250K), so the 4,000-character limit on
  each source is about cost, not about this limit.
- The usage on Gemini 3.6 and 3.7 Flash didn't come from this project, which never used
  those models. It's another app or tool using the same key or Google project.

## Is the judge just saying "yes" to everything?

In the first run groundedness was 1.00 on all 15 reports, so I tested the judge separately:
1. I took 4 real claims from report 1 and added 2 planted false claims that cite the same
   notes: "AI chatbots have completely replaced all human agents worldwide since 2019" and
   "customer satisfaction fell by 80 percent after every AI deployment".
2. The judge marked all 4 real claims as supported and **rejected both false ones**
   (score 4/6).

So it catches made-up facts. It probably misses subtle distortions (see report 3 below), and
it's the same model that wrote the reports, so it may be lenient with its own style of
wording.

## What I found by reading 5 reports (first run, before the relevance check)

- **#14 `qwxz plorbt vrenk` (vague):**
  - Tavily returned pages about the 1991 film *Point Break*, and the app wrote a confident,
    fully cited report about the film.
  - It scored **coverage 1.0, groundedness 1.0**.
  - **The metrics measure whether the report matches its sources, not whether it answers the
    question asked.** This was the biggest gap. **Fixed:** the relevance check now turns it
    into a clean fail.
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

1. **Refine never triggers on its own.** Tavily returns 5 results for almost anything, so
   `MIN_SOURCES` is rarely hit. It's measured with a forced batch (`--max-results 2`), where
   the refined query can drift (#10).
2. **The relevance check is a single yes/no from the same model.** It stops nonsense (#14)
   but is lenient on vague questions (#13, #15). An off-topic source can still slip through,
   and a relevant one can be dropped.
3. **Groundedness is judged by the same model** that wrote the report, it isn't perfect at
   catching subtle distortions (#3), and 15 topics is a small sample.
4. **Source quality and dates aren't checked**: vendor content, and outdated forecasts
   presented as current (#1).
5. **Citation coverage uses a heuristic sentence split.**
6. **The numbers are for `gemini-3.5-flash-lite`**, not the intended `gemini-3.8-flash`.
