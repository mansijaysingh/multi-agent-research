# Code Flow: Research Agent v2

This file explains how the code runs: where it starts, what runs in which order, which
function calls which, and how data moves between files. It's updated every time a step is
implemented. For *why* things are built this way, see [decision.md](decision.md).

---

## Contents

1. [File map](#1-file-map)
2. [Entry points](#2-entry-points)
3. [What runs at import time](#3-what-runs-at-import-time)
4. [The graph](#4-the-graph)
5. [The state](#5-the-state)
6. [A full run, step by step (Streamlit)](#6-a-full-run-step-by-step-streamlit)
7. [Inside each node](#7-inside-each-node)
8. [The MCP search call, end to end](#8-the-mcp-search-call-end-to-end)
9. [All the paths a run can take](#9-all-the-paths-a-run-can-take)
10. [The CLI run](#10-the-cli-run)
11. [The tests](#11-the-tests)
12. [Call graph (who calls whom)](#12-call-graph-who-calls-whom)
13. [Tracing (LangSmith)](#13-tracing-langsmith)

---

## 1. File map

```
multi-agent-research/
├── app.py                      Streamlit UI. Entry point for users.
├── config.py                   Constants: model name, limits.
├── graph/
│   ├── state.py                AgentState, Source, Summary types (the shared "memory" of a run)
│   └── workflow.py             Builds and compiles the LangGraph graph -> `app`. CLI entry point.
├── agents/                     One file per graph node
│   ├── supervisor.py           decide() (pure rules) + supervisor() node
│   ├── search_agent.py         search_agent() node -> calls the MCP tool
│   ├── refine_query.py         refine_query() node -> Gemini rewrites the query
│   ├── summarizer_agent.py     summarizer_agent() node -> Gemini, all sources in parallel
│   ├── writer_agent.py         writer_agent() node -> Gemini writes the report; citations fixed in code
│   └── fail_node.py            fail_node() node -> final error message
├── mcp_client/
│   └── client.py               call_tool(): starts the MCP server, calls one tool, returns its result
├── mcp_servers/
│   └── search_server.py        FastMCP server with the web_search tool (calls Tavily). Runs as a subprocess.
├── tests/                      pytest; none of them call an API
│   ├── conftest.py             runs first: LANGSMITH_TRACING=false
│   ├── test_routing.py         decide() table, 10 cases
│   ├── test_summarizer.py      summarizer_agent() with _summarize_all patched
│   ├── test_writer.py          writer_agent() with _write patched
│   ├── test_fail_node.py       fail_node() messages
│   ├── test_search_server.py   web_search() with a fake TavilyClient
│   └── test_search_agent.py    search_agent() with call_tool patched + 2 real MCP round trips
├── pytest.ini                  pythonpath = .  (so tests can import agents/, graph/)
├── requirements.txt
├── .env / .env.example         GOOGLE_API_KEY, TAVILY_API_KEY, LANGSMITH_TRACING / _API_KEY / _PROJECT
├── decision.md                 why things are built this way
└── flow.md                     this file
```

---

## 2. Entry points

There are four ways code starts running:

| Command | Entry file | What it does |
|---|---|---|
| `streamlit run app.py` | `app.py` | The real app. Streamlit runs `app.py` top to bottom, **again on every click**. |
| `python -m graph.workflow` | `graph/workflow.py`, the `if __name__ == "__main__":` block | One run on a fixed topic, approves the pause automatically, prints the report. |
| `pytest` | `pytest.ini` → `tests/test_*.py` | Unit tests. They call node functions directly, not the graph. |
| *(automatic)* `python mcp_servers/search_server.py` | `search_server.py`, the `__main__` block | Not run by you. `mcp_client` starts it as a **subprocess** for every search. |

There's also `mcp dev mcp_servers/search_server.py`, which opens the MCP Inspector so you can
call `web_search` by hand.

---

## 3. What runs at import time

Before any button is clicked, importing modules already does work. When `app.py` runs
`from graph.workflow import app`, Python runs these, in this order:

```
app.py
 ├─ import streamlit, uuid
 ├─ from config import RECURSION_LIMIT          -> config.py: just constants
 └─ from graph.workflow import app              -> graph/workflow.py runs top to bottom:
     ├─ from langgraph... import StateGraph, START, END, MemorySaver
     ├─ from config import RECURSION_LIMIT
     ├─ from graph.state import AgentState      -> defines the TypedDicts
     ├─ from agents.supervisor import supervisor        -> reads MIN_SOURCES, MAX_SEARCH_ATTEMPTS
     ├─ from agents.search_agent import search_agent
     │    └─ from mcp_client.client import call_tool
     │         └─ wraps call_tool with @traceable (a LangSmith step; does nothing when tracing is off)
     │            (the server's parameters, including the env copy, are built later, on each call)
     ├─ from agents.refine_query import refine_query
     │    ├─ load_dotenv()                       <- FIRST time .env is loaded into os.environ
     │    └─ llm = ChatGoogleGenerativeAI(...).with_structured_output(Refined)
     ├─ from agents.summarizer_agent import summarizer_agent
     │    ├─ load_dotenv()
     │    └─ llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.2)
     ├─ from agents.writer_agent import writer_agent
     │    ├─ load_dotenv()
     │    └─ llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.3)
     ├─ from agents.fail_node import fail_node
     ├─ g = StateGraph(AgentState); add 6 nodes; add edges     (section 4)
     └─ app = g.compile(checkpointer=MemorySaver(), interrupt_before=["writer"])
```

Things to know:
- **No network calls happen at import.** Creating `ChatGoogleGenerativeAI` objects doesn't
  call Gemini.
- **Tracing:** the first `load_dotenv()` also loads `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`
  and `LANGSMITH_PROJECT`. From then on, LangChain and LangGraph send a trace of every run to
  LangSmith. Nothing in the agents' code mentions tracing; only `call_tool` has a
  `@traceable` decorator. (See section 13.)
- Python caches imported modules. Streamlit re-runs `app.py` on every click, but
  `graph/workflow.py` runs **only once per server process**. So there is one compiled graph and
  one `MemorySaver`, shared by every rerun. That's why a paused run survives the click on
  Approve.
- The variable name `app` means two things. In `graph/workflow.py` it's the compiled graph.
  The file `app.py` is the Streamlit script, which imports that graph under the same name.

---

## 4. The graph

Built in `graph/workflow.py`:

```
                 START
                   │
                   ▼
   ┌──────────► supervisor ──── route = state["next_step"] ───────────────┐
   │               │                                                      │
   │     ┌─────────┼──────────────┬─────────────┬──────────┐              │
   │     ▼         ▼              ▼             ▼          ▼              │
   │  "search"  "refine_query" "summarizer"  "writer"   "fail"            │
   │     │         │              │             │          │              │
   │     │         └──► search    │       ⏸ PAUSE here     ▼              │
   │     │              (edge)    │      (interrupt_before) END           │
   │     │                        │             │                         │
   │     ▼                        ▼             ▼                         │
   └── back to supervisor ◄───────┘            END                        │
                                                                          │
   (refine_query never returns to the supervisor directly:                │
    refine_query → search → supervisor)  ─────────────────────────────────┘
```

Edges, exactly as in the code:

| From | To | Kind |
|---|---|---|
| `START` | `supervisor` | normal edge (entry point) |
| `supervisor` | `search` / `refine_query` / `summarizer` / `writer` / `fail` | **conditional**, chosen by `lambda s: s["next_step"]` |
| `search` | `supervisor` | normal |
| `refine_query` | `search` | normal: a refine always leads to another search |
| `summarizer` | `supervisor` | normal |
| `writer` | `END` | normal |
| `fail` | `END` | normal |

Node names in the graph (`"search"`) differ from the Python function names
(`search_agent`). The mapping is the `for name, fn in [...]` list in `workflow.py`.

**Pause:** `interrupt_before=["writer"]` means that when the supervisor picks `"writer"`,
LangGraph saves a checkpoint and **stops before running** `writer_agent`. The run continues
only when someone calls `app.invoke(None, cfg)` with the same `thread_id`.

---

## 5. The state

One `AgentState` dict travels through the whole run (`graph/state.py`). Each node gets the
current state, returns **only the fields it changed**, and LangGraph merges them in by
overwriting.

| Field | Written by | Read by | Meaning |
|---|---|---|---|
| `query` | the app (initial input) | refine_query, search, writer | The user's topic. Never changed. |
| `search_query` | refine_query | search, refine_query, app sidebar | The improved query. Missing means use `query`. |
| `search_attempts` | search (+1 per call) | supervisor, fail, app | How many searches ran. |
| `sources` | search (old + new, no duplicate URLs) | supervisor, refine_query, summarizer, writer, fail, app | `[{id, title, url, content}]`, ids 1, 2, 3… |
| `summaries` | summarizer; the app when unticking (`update_state`) | supervisor, writer, app | `[{source_id, text}]`. **None** = not run yet, **[]** = all failed. |
| `failed_sources` | summarizer | app | Ids whose summary failed. |
| `final_report` | writer | app | Markdown report ending in `## Sources`. |
| `error` | search, writer, fail (set); search, summarizer, writer (clear to None) | fail, app | Last error message. Shown in red. |
| `next_step` | supervisor | the conditional edge | Which node runs next. |

---

## 6. A full run, step by step (Streamlit)

A normal topic, "Future of AI in healthcare", from the first click to the report. **Bold**
items are functions in this project.

### Click 1: "🚀 Generate Report"

Streamlit re-runs `app.py` from the top. `generate` is True:

1. `st.session_state.thread_id = str(uuid.uuid4())`: a new id for this run.
2. **`run_config()`** returns `{"configurable": {"thread_id": ...}, "recursion_limit": 25,
   "run_name": "research-run", "tags": ["streamlit"], "metadata": {"thread_id": ...}}`.
   The last three only label the run in LangSmith.
3. `app.invoke({"query": topic}, run_config())`: LangGraph runs the graph:

```
#  node          function called                        returns (merged into state)
1  supervisor    supervisor(state) -> decide(state)     {"next_step": "search"}          attempts == 0
2  search        search_agent(state)                    {"sources": [5 items], "search_attempts": 1, "error": None}
                   └─ call_tool("web_search", {...})    (section 8: subprocess, MCP, Tavily)
3  supervisor    supervisor -> decide                   {"next_step": "summarizer"}      5 >= MIN_SOURCES, summaries is None
4  summarizer    summarizer_agent(state)                {"summaries": [5], "failed_sources": [], "error": None}
                   └─ _summarize_all(msgs) -> llm.batch(...)   5 Gemini calls, 3 at a time
5  supervisor    supervisor -> decide                   {"next_step": "writer"}          summaries not empty
   ⏸ interrupt_before writer: the checkpoint is saved, and invoke() returns
```

4. Still in the same script run, the **"SHOW THE RUN"** block runs, because `thread_id` is now
   in `session_state`:
   - `snap = app.get_state(run_config())`, so `snap.next == ("writer",)`, which means paused.
   - **`show_status(values, paused=True)`**: the sidebar shows "⏸️ Writer Agent Waiting for
     approval".
   - The review screen: one expander per summary, each with a "Use in report" checkbox.
   - **`show_failed_warning(failed_ids)`**.
   - Two buttons: **Approve** and **Start over**.

### Click 2: "✅ Approve and write report"

Streamlit re-runs `app.py` from the top. `generate` is False now, so no new run starts.

1. The "SHOW THE RUN" block draws the paused view again, and this time the Approve button
   returns True.
2. If some boxes are unticked:
   `app.update_state(run_config(), {"summaries": kept}, as_node="supervisor")`.
3. `app.invoke(None, run_config())`. `None` means "continue the saved run":

```
6  writer        writer_agent(state)                    {"final_report": "...## Sources...", "error": None}
                   └─ _write(prompt) -> llm.invoke(prompt).text    1 Gemini call
   -> END
```

4. `st.rerun()` makes Streamlit run `app.py` once more.

### Rerun after Approve

`snap.next` is empty, so the run is finished:
- **`show_status(values)`**: every stage shows ✅.
- If `values["error"]` is set, it's shown in red. Otherwise the report is shown, plus
  **`show_failed_warning`**.
- **`show_all_sources(sources, failed_ids)`**: the collapsed "🔎 All sources searched" section.

**There's no search or summary on click 2.** They ran once, in click 1, and their output was
read back from the checkpoint.

### Other buttons and cases
- **"↩️ Start over"**: `del st.session_state.thread_id`, then `st.rerun()`. The page comes back
  empty. The old checkpoint stays in memory but is never read again.
- **App restarted while paused**: `MemorySaver` was emptied, so `snap.values == {}`. The app
  shows "This run was lost…" and deletes `thread_id`.

---

## 7. Inside each node

### `supervisor(state)`: `agents/supervisor.py`
```
supervisor(state)
 ├─ step = decide(state)          rules, checked in this order:
 │     attempts == 0                                  -> "search"
 │     len(sources) < 3 and attempts < 2              -> "refine_query"
 │     no sources                                     -> "fail"
 │     summaries is None                              -> "summarizer"
 │     summaries == []                                -> "fail"
 │     otherwise                                      -> "writer"
 ├─ print("🧠 Supervisor -> step")
 └─ return {"next_step": step}
```

### `search_agent(state)`: `agents/search_agent.py`
```
query    = state["search_query"] or state["query"]
attempts = state["search_attempts"] + 1
try:   data = call_tool("web_search", {"query": query, "max_results": MAX_RESULTS})   -> section 8
except: return {"search_attempts": attempts, "error": "search failed: <MCP error>"}  (sources unchanged)
for each result: skip a URL already seen; otherwise append {"id": len(sources)+1, title, url, content}
no sources at all -> {"sources": [], "search_attempts": attempts, "error": "no results found"}
otherwise         -> {"sources": old+new, "search_attempts": attempts, "error": None}
```

### `refine_query(state)`: `agents/refine_query.py`
```
prompt = topic + last query + titles found so far + "write one more specific search query"
result = llm.invoke(prompt)        llm = Gemini .with_structured_output(Refined) -> Refined(query=...)
success -> {"search_query": result.query}
failure -> {}                      the old query is kept; the next node is still search
```

### `summarizer_agent(state)`: `agents/summarizer_agent.py`
```
msgs = for each source: [("system", SYSTEM), ("user", "Title: ...\n\n" + content[:4000])]
outs = _summarize_all(msgs)  -> llm.batch(msgs, max_concurrency=3, return_exceptions=True)
for source, out in zip(sources, outs):              same order as the input
    Exception or empty text -> print, add id to failed
    otherwise               -> summaries.append({"source_id": id, "text": out.text})
return {"summaries": ..., "failed_sources": ..., "error": None}
```

### `writer_agent(state)`: `agents/writer_agent.py`
```
no summaries -> {"error": "no summaries to write a report from"}
by_id = {source id -> source}
notes = "[1] Title: summary\n\n[2] Title: summary ..."
prompt = query + section rules + citation rules + notes
body = _write(prompt)                      -> llm.invoke(prompt).text
body = cut at a heading that is exactly "Sources" or "References" (the model's own list);
       "### Sources of Error" is kept
valid = set of summarized ids
body = remove every [n] where n not in valid (and spaces before it)
refs = "- [i] [title](url)" for i in sorted(valid)
return {"final_report": body + "\n\n## Sources\n" + refs, "error": None}
any exception -> {"error": "writer failed: ..."}
```

### `fail_node(state)`: `agents/fail_node.py`
```
error already set -> keep it
no sources        -> "no sources found after N searches"
otherwise         -> "every source summary failed"
```

---

## 8. The MCP search call, end to end

One `web_search` call crosses **two processes**:

```
YOUR PROCESS (Streamlit or CLI)                    CHILD PROCESS (started per call)
──────────────────────────────                     ────────────────────────────────
search_agent(state)
 └─ call_tool("web_search", args)        mcp_client/client.py   (@traceable -> LangSmith step "mcp_web_search")
     └─ asyncio.run(_call(tool, args))   starts an event loop
         └─ stdio_client(_server_params()) ── spawns ──► python mcp_servers/search_server.py
             (_server_params(): sys.executable + server path + env=copy of os.environ *now*)
             │                                          ├─ load_dotenv()  (finds .env)
             │                                          ├─ mcp = FastMCP("research-search")
             │                                          └─ mcp.run()  waits on stdin
             ├─ ClientSession(read, write)
             │   ├─ session.initialize() ◄── handshake over stdin/stdout ──►
             │   └─ session.call_tool("web_search", args) ──────────────────► web_search(query, max_results)
             │                                                                   ├─ key missing    -> raise ValueError
             │                                                                   ├─ empty query    -> raise ValueError
             │                                                                   ├─ clamp max_results to 1..10
             │                                                                   ├─ TavilyClient(api_key).search(...)  -> HTTPS to Tavily
             │                                                                   └─ return {"results": [{title,url,content}]}
             │            ◄────────────── CallToolResult (structuredContent or isError) ──
             └─ leaving `async with` closes the session and ends the child process
     after the blocks close:
       result.isError            -> raise RuntimeError("MCP tool web_search failed: <text>")
       result.structuredContent  -> return it   ({"results": [...]})
       else                      -> json.loads(first text block)
```

So `call_tool` either returns `{"results": [...]}` or raises `RuntimeError`, and
`search_agent` catches that and turns it into `"error": "search failed: ..."`.

---

## 9. All the paths a run can take

Shown as the sequence of `next_step` values (S = supervisor):

| Path | When | Sequence |
|---|---|---|
| **Normal** | 3+ sources first time | S→search→S→summarizer→S→⏸→writer→END |
| **Refine** | first search < 3 sources | S→search→S→refine_query→search→S→summarizer→S→⏸→writer→END |
| **Refine, still few** | after 2 attempts, 1–2 sources | …→search→S→summarizer→S→⏸→writer (writes from what it has) |
| **Search fails twice** | wrong key, Tavily down | S→search(error)→S→refine_query→search(error)→S→fail→END. No pause, red error. |
| **No sources** | 2 searches, 0 results | …→S→fail. Search already set `error="no results found"`, and fail keeps it. ("no sources found after N searches" appears only if no error was set.) |
| **All summaries fail** | Gemini down or quota | …→summarizer([])→S→fail ("every source summary failed") |
| **Some summaries fail** | e.g. 1 of 5 | normal path; `failed_sources=[2]`; a warning plus ⚠️ in the list |
| **Writer fails** | Gemini error at the end | …→writer returns error→END. Red error, no report. |

The loop always ends:
- at most 2 searches;
- refine always leads to search, which counts an attempt;
- `recursion_limit=25` stops anything unexpected.

---

## 10. The CLI run

`python -m graph.workflow`:
```
import graph/workflow.py (section 3) -> app is compiled
__main__ block:
  cfg = {"configurable": {"thread_id": "cli-test"}, "recursion_limit": 25}
  app.invoke({"query": "Future of AI in healthcare"}, cfg)       runs until the pause
  if app.get_state(cfg).next == ("writer",):
      print("⏸ paused before writer, auto-approving")
      app.invoke(None, cfg)                                       runs the writer
  print(final_report or error)
```

---

## 11. The tests

`pytest` reads `pytest.ini` (`pythonpath = .`, `testpaths = tests`), runs `tests/conftest.py`
first (which sets `LANGSMITH_TRACING=false`, so tests never send traces), then every
`tests/test_*.py`. None of them go through the graph or the network:

| File | Calls | Patches | Checks |
|---|---|---|---|
| `test_search_server.py` | `web_search(...)` directly (MCP 1.x leaves the function callable) | `TavilyClient` → `FakeTavily`; `TAVILY_API_KEY` | output reshaped to title/url/content; result without a URL dropped; empty query and missing key raise errors; `max_results` limited to 1–10 |
| `test_search_agent.py` | `search_agent(state)`; and twice the **real** `call_tool` | `agents.search_agent.call_tool` | numbering and duplicate URLs; the refined query is used; MCP failure gives an error, no sources and +1 attempt; no results. Two real round trips start the server subprocess but fail before reaching Tavily (empty query, empty key) |
| `test_routing.py` | `decide(state)` | nothing (pure function) | 10 state → step cases, including the loop-bug cases |
| `test_summarizer.py` | `summarizer_agent(state)` | `_summarize_all` returns fake outputs or exceptions | one failure keeps the others; an empty summary counts as a failure; no sources; the 4,000-character limit; the stale error is cleared |
| `test_writer.py` | `writer_agent(state)` | `_write` returns fake text | invalid citations removed; a failed source can't be cited; the Sources list comes from state; the model's own list is dropped, but "### Sources of Error" is kept; line breaks are kept; the prompt has numbered notes; writer failure; no summaries |
| `test_fail_node.py` | `fail_node(state)` | nothing | the three messages |

Importing `agents.summarizer_agent` or `agents.writer_agent` creates the Gemini objects but
doesn't call them, so the tests run without a network.

---

## 12. Call graph (who calls whom)

```
streamlit run app.py
└─ app.py (re-run on every click)
   ├─ run_config()
   ├─ app.invoke(initial_state, cfg)   / app.invoke(None, cfg)        [LangGraph]
   │   ├─ supervisor()  ──► decide()
   │   ├─ search_agent() ──► mcp_client.call_tool() ──► asyncio.run(_call())
   │   │                         └─ [subprocess] search_server.web_search() ──► TavilyClient.search()  [Tavily API]
   │   ├─ refine_query() ──► llm.invoke()   (structured output)                       [Gemini API]
   │   ├─ summarizer_agent() ──► _summarize_all() ──► llm.batch()                       [Gemini API]
   │   ├─ writer_agent() ──► _write() ──► llm.invoke()                                  [Gemini API]
   │   │                 └─ re.split / re.sub   (cut the model's list, remove bad citations)
   │   └─ fail_node()
   ├─ app.get_state(cfg)                                               [reads the checkpoint]
   ├─ app.update_state(cfg, {"summaries": kept}, as_node="supervisor") [only when sources are unticked]
   ├─ show_status() / show_failed_warning() / show_all_sources()
   └─ st.rerun()

python -m graph.workflow  ──► same graph, approves automatically
pytest                    ──► conftest.py, then decide() / summarizer_agent() / writer_agent() / fail_node() /
                              search_agent() / web_search() directly, wrappers patched
```

---

## 13. Tracing (LangSmith)

There's no tracing code in the nodes. It's switched on by `.env`:

```
LANGSMITH_TRACING=true        -> on (tests force it to "false" in conftest.py)
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=research-agent-v2
```

What one Streamlit run looks like in LangSmith (two traces, because of the pause):

```
research-run          tags: streamlit   metadata.thread_id = <uuid>       (Generate click)
├─ supervisor
├─ search
│   └─ mcp_web_search  (tool)   inputs: tool, args  -> output: {"results": [...]}  | red if it raised
├─ supervisor
├─ summarizer
│   └─ ChatGoogleGenerativeAI × N   (prompt, output, tokens, latency per source)
└─ supervisor                       -> stops: interrupt before writer

research-run          same thread_id                                      (Approve click)
└─ writer
    └─ ChatGoogleGenerativeAI       (the report prompt and output)
```

Where each part comes from:
- **`research-run`, the tag and the metadata:** `run_config()` in `app.py`.
- **The node spans:** LangGraph, automatically.
- **The `ChatGoogleGenerativeAI` spans:** LangChain, automatically.
- **`mcp_web_search`:** the `@traceable` decorator on `call_tool` in `mcp_client/client.py`.
- **Threads:** LangSmith's Threads view groups the two traces through the shared `thread_id`.
