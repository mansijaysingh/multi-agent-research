# Decision Log: Research Agent v2

This file records every meaningful decision made while building v2: what was chosen, why,
what else was considered, and which trade-off was accepted. It's updated every time a step
is implemented.

**How to read an entry**

- **Decision**: what we did.
- **Why**: the reason.
- **Alternatives**: what we didn't do.
- **Trade-off accepted**: the cost we knowingly took on.

Entries are grouped by build step (Step 0 to Step 9 of `Research_Agent_v2_Build_Plan.pdf`).
"PDF" means that plan, and "v1" means the code on the `main` branch.

---

## Contents

- [Step 0: Setup](#step-0-setup)
- [Step 1: Typed state and clean node contracts](#step-1-typed-state-and-clean-node-contracts)
- [Step 2: MCP search server and client](#step-2-mcp-search-server-and-client)
- [Step 3: Supervisor hub routing](#step-3-supervisor-hub-routing)
- [Step 4: Parallel summaries](#step-4-parallel-summaries)
- [Step 5: Citations](#step-5-citations)
- [Step 6: Human review before writing](#step-6-human-review-before-writing)
- [Step 7: Tracing and the remaining tests](#step-7-tracing-and-the-remaining-tests)
- [Cross-cutting decisions](#cross-cutting-decisions)
- [Open decisions and known issues](#open-decisions-and-known-issues)

---

## Step 0: Setup

### D0.1 Build v2 on a separate `v2` branch
- **Decision:** all v2 work happens on `v2`. It's merged into `main` only at the end (Step 9).
- **Why:** `main` keeps the working v1 that's already on GitHub and in the portfolio. If v2 is
  half-finished, nothing public breaks.
- **Alternatives:** working on `main` directly, or starting a new repo.
- **Trade-off accepted:** a long-lived branch can drift from `main`. That's fine here, because
  nobody else commits to `main`.

### D0.2 Use Gemini instead of OpenAI
- **Decision:** the LLM is Google Gemini, through `langchain-google-genai`
  (`ChatGoogleGenerativeAI`, key `GOOGLE_API_KEY`). The PDF and v1 use OpenAI.
- **Why:** the project owner chose it, because a Gemini key with a free tier was available.
  Going through LangChain's chat-model interface (not the raw SDK, which v1 used) gives all
  LLM calls one interface: `.invoke`, `.batch`, `.with_structured_output`. It also means
  LangSmith can trace them automatically (Step 7).
- **Alternatives:** the raw `google-genai` SDK. It's simpler, but it can't be traced
  automatically, and `batch` and structured output would have to be written by hand.
- **Trade-off accepted:** the free tier has tight limits (requests per day and per minute).
  That shaped later decisions: `MAX_CONCURRENCY = 3` (D4.1) and the temporary model switch
  (D0.3).

### D0.3 Model name: `gemini-3.8-flash`, for now `gemini-3.5-flash-lite`
- **Decision:** `config.MODEL` was `gemini-3.8-flash`. It's temporarily
  `gemini-3.5-flash-lite`.
- **Why:**
  - `gemini-2.5-flash` returns 404 for new accounts.
  - The free quota for `gemini-3.8-flash` is 20 requests a day per model, and it ran out on
    2026-10-14.
  - The lite model has its own quota, so development could continue.
- **Trade-off accepted:**
  - The lite model writes somewhat weaker text.
  - It ignores `temperature`, which causes a harmless warning.
  - **Switch back** before the Step 8 evaluation and the final deploy.

### D0.4 Move the Streamlit app from `ui/app.py` to `app.py` at the root
- **Why:**
  - Streamlit Cloud expects the entry file at the repo root.
  - Running from the root puts the project root on `sys.path`, so `from graph.workflow import
    app` works with no `sys.path` hacks.

### D0.5 One `config.py` for every tunable number
- **Decision:** `MODEL`, `MAX_RESULTS`, `MIN_SOURCES`, `MAX_SEARCH_ATTEMPTS`,
  `RECURSION_LIMIT` and `MAX_CONCURRENCY` live in one file.
- **Why:** the graph, the agents, the app and the tests read the same values. Changing a limit
  is a one-line edit, and the tests use the real thresholds.
- **Alternatives:** environment variables, or a Pydantic `Settings` class.
- **Trade-off accepted:** the values are plain Python constants, so they can't be changed
  without editing code. That's fine for a single-user app.

### D0.6 Secrets in `.env`, loaded with `python-dotenv`
- **Decision:** keys go in `.env`, which is gitignored. `.env.example` is committed with
  empty values, as a template.
- **Why:** this is the standard way to keep keys out of git. On Streamlit Cloud the same names
  come from the app's Secrets, which are set as environment variables.

### D0.7 Dependencies mostly unpinned (except `mcp`)
- **Decision:** `requirements.txt` lists package names without versions, except
  `mcp[cli]>=1.28,<2` (D2.2).
- **Trade-off accepted:** a fresh install may pick up newer versions that behave differently.
  Revisit before the final deploy (Step 9) by pinning what works, e.g. with `pip freeze`.

---

## Step 1: Typed state and clean node contracts

### D1.1 A typed `AgentState` (`graph/state.py`) with separate fields for data, counters and errors
- **Decision:** `AgentState` is a `TypedDict` with `total=False`, plus `Source` and `Summary`
  types.
- **Why:** this fixes v1's main bug. On failure, v1 wrote an error string into
  `search_results`, and the summarizer then looped over the characters of the error message.
  Separate fields mean data fields only ever hold data.
- **Alternatives:** a Pydantic model as the state. That gives runtime validation, but it's
  heavier, and LangGraph works fine with `TypedDict`.
- **Trade-off accepted:**
  - `TypedDict` is only checked by editors and type checkers, not while the program runs.
  - `total=False` means every field is optional, so nodes read with `state.get(...)`.

### D1.2 Nodes return only the fields they change
- **Decision:** a node returns a small dict, such as `{"next_step": "search"}`, and LangGraph
  merges it into the state. v1 mutated the whole state and returned it.
- **Why:** each node's effect is visible in its return value, it's easy to test, and a node
  can't overwrite fields it doesn't own by accident.
- **Alternatives:** reducers such as `Annotated[list, operator.add]`, which append to lists
  automatically.
- **Trade-off accepted:** with the default "overwrite" merge, the search node must return the
  **whole** list (old sources plus new ones), not just the new ones. That's simpler to read,
  but easy to forget.

### D1.3 One `error` field holds the last error
- **Decision:** failures set `state["error"]` to a readable message. The UI shows it in red.
- **Why:** routing and the UI can check one place.
- **Consequence:** a stale error must be cleared once it no longer applies. The search
  (on success), the summarizer (D4.5) and the writer (D3.8) all set `error: None`.

### D1.4 Source ids are 1-based and never change
- **Why:** the ids double as citation numbers (`[1]`, `[2]`) in Step 5, and the UI shows them
  in "All sources searched", so the numbers line up everywhere.

---

## Step 2: MCP search server and client

### D2.1 Web search lives behind our own MCP server
- **Decision:** the search node doesn't call Tavily. It calls the `web_search` tool on our MCP
  server (`mcp_servers/search_server.py`, built with FastMCP) through an MCP client
  (`mcp_client/client.py`).
- **Why:**
  - MCP is the standard way to expose tools to agents, and it's one of the resume claims.
  - The tool is decoupled from the agent: any MCP client (Claude Desktop, the MCP Inspector,
    another agent) can use the same server.
  - Adding tools later, such as `search_arxiv`, doesn't change the agent's plumbing.
- **Alternatives:** calling `tavily-python` directly in the node, which would be simplest and
  fastest.
- **Trade-off accepted:**
  - Each search starts a Python subprocess, which adds roughly 1–2 s of latency.
  - There are more moving parts and more places to fail.

### D2.2 Pin `mcp>=1.28,<2`
- **Why:** version 2 of the Python MCP SDK renamed the core classes (`MCPServer`, `Client`).
  Version 1's `FastMCP` and `ClientSession` API is what most tutorials and docs use.
- **Trade-off accepted:** moving to version 2 later is a separate, small task.

### D2.3 Call Tavily with `tavily-python` inside the server; drop `langchain-community`
- **Why:** v1's `TavilySearchResults` (from `langchain-community`) is deprecated, and it
  *returned* errors as strings instead of raising them, which caused v1's bug. The plain
  `TavilyClient` raises real exceptions.

### D2.4 stdio transport, one session per call, behind a sync wrapper
- **Decision:** `call_tool()` runs `asyncio.run(_call(...))`. `_call` starts the server as a
  subprocess over stdio, initializes a session, calls the tool, and closes everything.
- **Why:**
  - LangGraph nodes and Streamlit here are synchronous, and the sync wrapper keeps them that
    way.
  - stdio needs no ports and no separate server process to deploy.
- **Alternatives:**
  - A long-lived session reused across calls (faster).
  - An HTTP or SSE transport (needs a running server).
- **Trade-off accepted:**
  - Startup cost on every call.
  - `asyncio.run` can't be used where an event loop is already running, such as Jupyter.
  - A reused session is the known optimisation.

### D2.5 Start the server with `sys.executable`, an absolute path, and `env=dict(os.environ)`
- **Why:**
  - `sys.executable` runs the subprocess in the same Python environment (same venv, same
    installed packages), locally and on Streamlit Cloud.
  - The absolute path works whatever the current directory is.
  - `env=...` passes our environment, including `TAVILY_API_KEY`, to the child. Without it,
    the child gets only a minimal environment.
  - See **Known issue K1** below for a subtlety about when that environment is copied.

### D2.6 The server raises errors; the client handles them only after the session closes
- **Decision:**
  - The tool does `raise ValueError(...)`. MCP turns that into a result with `isError=True`.
  - The client turns that into `RuntimeError("MCP tool web_search failed: ...")`, but only
    **after** leaving the `async with` blocks.
- **Why:** this departs from the PDF. Raising inside `stdio_client` makes anyio wrap the
  exception in an `ExceptionGroup`, and the user then sees "unhandled errors in a TaskGroup"
  instead of the real message.

### D2.7 Never `print()` to stdout in the server
- **Why:** with stdio transport, stdout *is* the protocol channel, so a stray print corrupts
  messages. Debug output goes to `sys.stderr`.

### D2.8 Read the Tavily key inside the tool, not at import (Step 2 review fix)
- **Why:** if the key is missing, reading it at import crashes the server before the MCP
  handshake, and the client only sees an unclear "connection closed". Read inside the tool, a
  missing key gives a clear error: `MCP tool web_search failed: ... TAVILY_API_KEY is not
  set`.
- **Trade-off accepted:** a new `TavilyClient` is created on every call, which costs almost
  nothing.

### D2.9 The server limits `max_results` to 1–10 and skips results without a URL
- **Why:** this protects against a caller (including an LLM) asking for 1,000 results, and
  every result is guaranteed one output shape.

### D2.10 The search node skips duplicate URLs, including repeats inside one batch (Step 2 review fix)
- **Why:** a refined second search often returns pages the first one already found. Skipping
  them keeps ids and citations clean.

---

## Step 3: Supervisor hub routing

### D3.1 The supervisor is a hub that routes with fixed rules
- **Decision:** every worker returns to the supervisor, and `decide(state)` picks the next
  step with `if` rules. The only LLM call in routing is `refine_query`, which rewrites a weak
  query.
- **Why:** the routing is predictable, costs nothing, and can be unit-tested completely. "Why
  not let the LLM route?" is a common interview question, and the answer is: because these
  decisions are fully determined by the state.
- **Alternatives:** an LLM router (tool-calling supervisor, or `langgraph-supervisor`). It's
  more flexible, but it's non-deterministic, slower, costs money, and is hard to test.
- **Trade-off accepted:** adding a new kind of step means editing the rules by hand.

### D3.2 `decide()` is separate from the `supervisor()` node
- **Why:** `decide` is a pure function, state in and step name out, with no prints and no
  LLM. `tests/test_routing.py` tests it with a table of cases and no API calls. The node
  wraps it and adds the log line.

### D3.3 `summaries is None` and `summaries == []` mean different things
- **Decision:** `None` means "the summarizer hasn't run yet", and `[]` means "it ran and every
  summary failed". That's why `decide` reads `state.get("summaries")` with no default.

### D3.4 Fixed a bug in the PDF's `decide()` that looped forever
- **Problem:** in the PDF's version, when searches ran out with only 1–2 sources, the rule
  `fewer than MIN_SOURCES, attempts used up, has sources → "summarizer"` was checked
  **before** `summaries`. After the summarizer ran, the next call sent it back to the
  summarizer, forever, until the recursion limit stopped it. This was found in a real run.
- **Decision:** reordered the rules. Refine only while attempts remain; then fail if there
  are no sources; otherwise check `summaries`. There are two regression tests for it.

### D3.5 `refine_query` uses structured output and never blocks the loop
- **Decision:** `llm.with_structured_output(Refined)` makes the model return a validated
  `{"query": ...}`. If the call fails, the node returns `{}`, so the old query is kept.
- **Why:** structured output avoids parsing free text. Returning `{}` on failure means the
  graph still moves on to search, which counts an attempt, so the loop still ends.

### D3.6 Three layers stop the loop
1. `MAX_SEARCH_ATTEMPTS = 2`.
2. `refine_query → search` is a fixed edge, so every refine uses up an attempt.
3. LangGraph's `recursion_limit = 25`, passed in the run config, as a last safety net.

### D3.7 A separate `fail` node ends runs that can't produce a report
- **Decision:** `fail_node` keeps an existing error, for example the exact MCP error, because
  that's the most useful message. Otherwise it explains the problem from the state:
  "no sources found after N searches" or "every source summary failed".
- **Why:** the run ends cleanly with a clear message, instead of crashing or showing an empty
  report.

### D3.8 The writer clears `error` when it succeeds
- **Why:** if search 1 found 1–2 sources and search 2 crashed, the run still continues to a
  report. Without clearing, the UI would show a red "search failed" next to a good report.

### D3.9 `pytest.ini` sets `pythonpath = .`
- **Why:** without it, `from agents.supervisor import decide` fails under pytest, because the
  project root isn't on the import path.

### D3.10 Removed the temporary "skip if error" guards from the summarizer and writer
- **Why:** routing now stops failed runs before they reach those nodes, so the guards were
  dead code.

### D3.11 4-space indentation everywhere (Step 2 review fix)
- **Why:** the files mixed 2-, 3- and 5-space indents. It was converted with a script that
  checked each file's syntax tree, so only whitespace changed.

---

## Step 4: Parallel summaries

### D4.1 `llm.batch(..., max_concurrency=3, return_exceptions=True)`
- **Decision:** all sources are summarized concurrently, at most 3 at a time.
  `return_exceptions=True` puts a failed call's exception in its slot instead of raising it.
- **Why:**
  - It's faster: the summary stage takes about as long as the slowest call, not the total of
    all calls.
  - **One failure no longer loses every summary**, which was v1's behaviour.
  - `batch` is built into LangChain and returns results in input order, so `zip(sources,
    outs)` lines each result up with its source.
- **Alternatives:** threads, `asyncio.gather`, or LangGraph's `Send` API for parallel nodes.
- **Trade-off accepted:** 3 is low on purpose because of Gemini's per-minute free-tier limit.
  When the limit is hit, the client retries with backoff, so a run gets slower rather than
  failing.
- **Measured:** the same 5 sources took **8.0–9.6 s one at a time and 2.8–3.1 s in
  parallel**. When rate-limited, some runs took 7.5–41.7 s.

### D4.2 The model call sits in a module-level `_summarize_all()`
- **Why:** `ChatGoogleGenerativeAI` is a Pydantic model, and Pydantic doesn't allow
  `monkeypatch.setattr(llm, "batch", ...)`. Patching a module function always works, so the
  tests never call Gemini.

### D4.3 A short "facts only" system prompt; content limited to 4,000 characters
- **Why:**
  - "Keep only facts stated in the source" is what makes the Step 5 citations trustworthy.
  - The 4,000-character limit keeps token use (and free-tier quota) down.
- **Trade-off accepted:** anything after 4,000 characters of a page is never seen.

### D4.4 An empty summary counts as a failure (Step 4 review fix)
- **Why:** a blank answer would otherwise become a summary the writer cites.

### D4.5 The summarizer sets `error: None`
- **Why:** once the summarizer has run, any earlier search error is stale. If every summary
  then fails, `fail_node` should report that real cause, not the old search error.

### D4.6 The UI warns about sources that couldn't be summarized
- **Decision:** a yellow warning lists the failed ids, and those sources are marked "⚠️ not
  summarized" in the source list.

---

## Step 5: Citations

### D5.1 The Sources list is built in code from state, never by the model
- **Decision:** the writer adds `## Sources` itself from `state["sources"]`. The prompt tells
  the model not to write a list, and if it writes one anyway (`## Sources` or
  `## References`), that part is cut off.
- **Why:** the model can't invent URLs. Every link in a report comes from a real search
  result.
- **Detail (Step 6 review fix):** only a heading that consists of just "Sources" or
  "References" (an optional colon is allowed) counts as the model's list:
  `(?im)^#{1,6}[ \t]*(?:sources|references)[ \t]*:?[ \t]*$`. The first version matched any
  heading that *started* with those words, so a heading like `### Sources of Error` inside
  Key Findings would have cut off the rest of the report, including the Conclusion. There's a
  regression test for it.

### D5.2 Invalid citations are removed in code
- **Decision:** any `[n]` whose `n` isn't a **summarized** source id is deleted, together
  with the spaces before it.
- **Why:** a source whose summary failed was never shown to the model, so a citation to it
  can't be backed up.
- **Detail:** the regex is `[ \t]*\[(\d+)\]`. It removes spaces and tabs but not line breaks;
  `\s*` would have joined two lines.

### D5.3 One number per bracket
- **Decision:** the prompt asks for `[1][3]`, not `[1, 3]`.
- **Why:** the check in D5.2 only recognises `[n]`, so `[1, 3]` would get past it unchecked.

### D5.4 The notes are numbered `[id] Title: summary`
- **Why:** the model sees the same number it must cite, so citations map directly to source
  ids.

### D5.5 The model call sits in a `_write()` wrapper
- **Why:** same reason as D4.2. The 8 writer tests don't need Gemini.

### D5.6 The app's own list moves into a collapsed "🔎 All sources searched" section
- **Why:** the report now ends with its own Sources list. Showing a second full list would
  repeat it. The collapsed section still shows every search result, including unsummarized
  ones, which helps with debugging.

---

## Step 6: Human review before writing

### D6.1 Pause with LangGraph's `interrupt_before=["writer"]` and a checkpointer
- **Decision:** `g.compile(checkpointer=MemorySaver(), interrupt_before=["writer"])`. The run
  stops when the supervisor picks the writer. `invoke(None, cfg)` resumes it from the saved
  checkpoint.
- **Why:** this is LangGraph's built-in human-in-the-loop. The state is saved, and resuming
  doesn't repeat the search or the summaries (tested: 0 extra calls).
- **Alternatives:**
  - Splitting the graph in two and calling the writer by hand from Streamlit.
  - The newer `interrupt()` function inside a node.
- **Trade-off accepted:** every `invoke` now needs a `thread_id`, and the app has to read its
  page from the checkpoint (D6.4).

### D6.2 `MemorySaver`, not a database
- **Why:** zero setup, and enough for a single-user demo.
- **Trade-off accepted:** a paused run is lost if the app restarts. The app handles this with
  "This run was lost (the app restarted). Please generate again." In production you'd use
  `SqliteSaver` or a Postgres checkpointer. That's documented in a comment in
  `graph/workflow.py`.

### D6.3 A new `thread_id` (`uuid4`) for every run, kept in `st.session_state`
- **Why:**
  - The thread id selects the checkpoint. Reusing it would mix a new topic into the old run's
    state.
  - `session_state` survives Streamlit's reruns within one browser session.

### D6.4 The page is drawn from `app.get_state(cfg)`, not from what `invoke` returned
- **Why:** Streamlit re-runs the whole script on every click. After a click on Approve, there
  is no "return value" from the first run any more, but the checkpoint still exists.
  `snap.next == ("writer",)` means paused, an empty `snap.values` means lost, and anything
  else means finished.

### D6.5 Unticking sources uses `update_state(..., as_node="supervisor")`
- **Decision:** before resuming, the app writes the ticked summaries back with
  `app.update_state(cfg, {"summaries": kept}, as_node="supervisor")`.
- **Why:**
  - This is "a human editing agent state".
  - `as_node="supervisor"` makes LangGraph treat the edit as if the supervisor wrote it, so
    its conditional edge, which still has `next_step="writer"`, sends the run to the writer.
  - `sources` isn't changed: the writer builds citations and the Sources list from the
    summaries, so unticked sources drop out of both (tested).
- **Trade-off accepted:** an unticked source still shows in "All sources searched". That's
  intended, because the list shows everything search found.

### D6.6 Approve is disabled when every source is unticked
- **Why:** with no summaries, the writer would only return an error.

### D6.7 The CLI (`python -m graph.workflow`) approves the pause automatically
- **Why:** the command-line run is for quick checks, with no one there to click Approve.

---

## Step 7: Tracing and the remaining tests

### D7.1 Turn on LangSmith tracing with environment variables, not code
- **Decision:** setting `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`
  in `.env` is enough. LangGraph nodes and `ChatGoogleGenerativeAI` calls are traced
  automatically.
- **Why:**
  - No tracing code in the agents.
  - Tracing turns off with one variable.
  - It works the same on Streamlit Cloud through Secrets.
  - The agents already call `load_dotenv()` at import, before any run starts.
- **Alternatives:** passing LangChain callbacks by hand, or another tracing tool such as
  Langfuse or OpenTelemetry. LangSmith is the native option for LangGraph, and it's one of
  the resume claims.
- **Trade-off accepted:** prompts, source text and outputs are sent to LangSmith's servers.
  That's fine for public web research; it wouldn't be for private data.

### D7.2 `@traceable(name="mcp_web_search", run_type="tool")` on `call_tool`
- **Why:** automatic tracing sees the `search` node, but not what happens inside it. The
  decorator makes the MCP call its own step, with a tool icon, the tool name and arguments as
  inputs, the results as output, and the error message in red when it fails. The trace
  therefore shows how long the MCP round trip takes compared with the rest of the run.
- **Trade-off accepted:** the name says `web_search`, but `call_tool` can call any tool. If a
  second tool is added later (e.g. `search_arxiv`), rename it or build the name from the tool
  name.

### D7.3 Every run gets `run_name="research-run"`, `tags=["streamlit"]` and the `thread_id` in its metadata
- **Why:**
  - `run_name` replaces the generic "LangGraph" label.
  - The tag separates app runs from the Step 8 eval runs (`["eval"]`).
  - A paused run is **two** traces: before Approve and after it. LangSmith groups them in its
    Threads view through the `thread_id` metadata.

### D7.4 `tests/conftest.py` sets `LANGSMITH_TRACING=false`
- **Why:** tests must never send traces, even with a key in `.env`. `conftest.py` runs before
  the test files import the agents, and `load_dotenv()` never overwrites a variable that's
  already set, so this setting wins.

### D7.5 The server and search-node tests call the functions directly, with fakes
- **Decision:**
  - `tests/test_search_server.py` calls `web_search()` directly, which works because in
    MCP 1.x `@mcp.tool()` returns the function unchanged. A fake `TavilyClient` class
    replaces the real one.
  - `tests/test_search_agent.py` replaces `call_tool` where the node imported it
    (`agents.search_agent.call_tool`).
- **Why:**
  - The server's own rules are tested in milliseconds with no Tavily calls: the output shape,
    the empty-query and missing-key errors, and the 1–10 limit.
  - So are the node's rules: numbering, duplicate URLs, the refined query, and failure
    handling.

### D7.6 Two tests start the real MCP server, but never reach the network
- **Decision:** they call the real `call_tool` with an empty query, or with an empty key.
  The server raises its error before calling Tavily.
- **Why:** they prove the whole MCP path works in about 2 s each, at no cost: the subprocess
  starts, the protocol runs, `isError` becomes a clear `RuntimeError`, and the environment
  reaches the child.
- **Trade-off accepted:** they're the slow tests, about 10 of the suite's roughly 12 s.

### D7.7 Fixed K1: the server parameters are built on every call, not at import
- **Problem:** `PARAMS = StdioServerParameters(..., env=dict(os.environ))` ran when
  `mcp_client/client.py` was first imported, before any `load_dotenv()`. So the environment
  passed to the server never included `.env` values, or anything set later. It only worked
  because the server loads `.env` itself.
- **Decision:** `_server_params()` builds the parameters inside `_call()`.
- **Proof:** `test_env_reaches_server` sets the key to `""` *after* import and expects the
  server's "TAVILY_API_KEY is not set". With the old client the test fails, because the
  server falls back to the real key from `.env`. With the fix it passes.

### D7.8 `decision.md` and `flow.md` are committed to the repo
- **Why:** they explain the design to anyone reading the repo, including future me and
  interviewers. Keeping them untracked risked `git add -A` picking them up by accident.

---

## Cross-cutting decisions

### X1 Unit tests never call an API
- Every model call is in a module-level wrapper (`_summarize_all`, `_write`) or a pure
  function (`decide`). The tests patch the wrappers (and `TavilyClient` and `call_tool`), so
  `pytest` is free and always gives the same result: 38 tests in about 12 s. The only
  process they start is the local MCP server (D7.6).

### X2 End-to-end checks drive the real app with Streamlit's `AppTest`
- **Decision:** UI checks use `streamlit.testing.v1.AppTest`. It runs `app.py`, types into
  inputs and clicks buttons. Counting wrappers around `call_tool` and `_summarize_all` prove
  things like "Approve didn't search again".
- **Why:** it's repeatable, and it needs no browser.
- **Trade-off accepted:** after `st.rerun()`, `AppTest` keeps the page from before the rerun.
  Start over is therefore tested by checking `session_state`, and once by hand in a browser.

### X3 Temporary test changes go in test scripts, not in project code
- For example, forcing `MAX_RESULTS = 2` to trigger a refine, breaking source 2's messages to
  force a failure, or adding a fake `[42]` citation. These patches run inside the test
  process, so they can never be committed by accident.

### X4 Commit messages have no `Co-Authored-By` line
- The project owner wants the commits under their own name.

---

## Open decisions and known issues

### Open: should the Sources list show only cited sources? (from the Step 5 review)
- **Now:** it lists every *summarized* source, as in the PDF.
- **Option:** list only the ids that actually appear as `[n]` in the body.
- **Why decide before Step 8:** it changes the "citation coverage" metric in the evaluation.

### ~~Known issue K1: the MCP client copies the environment when it's first imported~~ (fixed in Step 7, see D7.7)

### Known issue K2: the model is still `gemini-3.5-flash-lite`
- Switch `config.MODEL` back to `gemini-3.8-flash` (see D0.3) before the evaluation and the
  final deploy.

### Known issue K3: off-topic results aren't detected
- The nonsense topic `qwxz plorbt vrenk` got "Point Break" pages from Tavily, and the app
  wrote a confident report about them. Nothing checks whether results are relevant. The
  Step 8 groundedness metric, or a relevance filter, could catch this.
