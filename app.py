import uuid

import streamlit as st
from config import MAX_RUNS_PER_SESSION, RECURSION_LIMIT
from graph.workflow import app

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    layout="wide"
)

# ---------------- TITLE ----------------

st.title("🤖 Multi-Agent Research Assistant")

st.markdown(
    "Generate AI-powered research reports using multiple AI agents."
)

st.caption(f"Free-tier demo: up to {MAX_RUNS_PER_SESSION} runs per session.")

st.markdown("---")

# ---------------- SIDEBAR ----------------

st.sidebar.title("⚙️ Agent Workflow")

status_box = st.sidebar.empty()

# ---------------- HELPERS ----------------


def run_config():
    """
    Config for the current run; the thread_id picks its checkpoint.
    run_name, tags and metadata label the run in LangSmith; the thread_id in metadata
    groups the part before approval and the part after it into one thread.
    """
    return {
        "configurable": {"thread_id": st.session_state.thread_id},
        "recursion_limit": RECURSION_LIMIT,
        "run_name": "research-run",
        "tags": ["streamlit"],
        "metadata": {"thread_id": st.session_state.thread_id},
    }


def show_status(values, paused=False):
    sources = values.get("sources", [])

    # The first stage without output is the one that failed; later ones were skipped
    stages = [
        ("Search Agent", bool(sources)),
        ("Summarizer Agent", bool(values.get("summaries"))),
        ("Writer Agent", bool(values.get("final_report"))),
    ]
    lines = ["✅ Supervisor Agent Completed  "]
    failed = False
    for name, done in stages:
        if done:
            lines.append(f"✅ {name} Completed  ")
        elif paused and name == "Writer Agent":
            lines.append(f"⏸️ {name} Waiting for approval  ")
        elif not failed:
            lines.append(f"❌ {name} Failed  ")
            failed = True
        else:
            lines.append(f"⏭️ {name} Skipped  ")

    lines.append(f"\nSearch attempts: {values.get('search_attempts', 0)}  ")
    if values.get("search_query"):
        lines.append(f"🔁 Refined query: {values['search_query']}  ")

    status_box.markdown("### Current Status\n\n" + "\n".join(lines))


def show_failed_warning(failed_ids):
    if failed_ids:
        st.warning(f"{len(failed_ids)} source(s) were off-topic or couldn't be summarized: {failed_ids}")


def show_all_sources(sources, failed_ids):
    # The report ends with its own Sources list; this shows everything search found
    if sources:
        with st.expander(f"🔎 All sources searched ({len(sources)})"):
            for s in sources:
                mark = " ⚠️ not used (off-topic or not summarized)" if s["id"] in failed_ids else ""
                st.markdown(f"{s['id']}. [{s['title'] or s['url']}]({s['url']}){mark}")


# ---------------- USER INPUT ----------------

query=st.text_input(
    "Enter your research topic:"
)

# ---------------- BUTTON ----------------

generate=st.button("🚀 Generate Report")

# ---------------- START A RUN ----------------
# The run stops before the writer; the page below is drawn from the saved checkpoint,
# because Streamlit re-runs this whole script on every click.

if generate:
    if query.strip() == "":
        st.warning("Please enter a research topic.")

    elif st.session_state.get("runs", 0) >= MAX_RUNS_PER_SESSION:
        # Protects the shared free-tier quota; a new browser session resets it, so it only stops casual overuse
        st.info("Demo limit reached for this session.")

    else:
        st.session_state.runs = st.session_state.get("runs", 0) + 1

        # A new thread for every run, so a new topic never mixes with an old run's state
        st.session_state.thread_id = str(uuid.uuid4())

        initial_state={
            "query":query
        }

        with st.spinner("🤖 AI Agents are working on your report..."):
            # "  \n" is a Markdown line break, written out so editors can't strip the trailing spaces
            status_box.markdown("### Current Status\n\n" + "  \n".join([
                "🔄 Supervisor Agent Running",
                "⏳ Search Agent Waiting",
                "⏳ Summarizer Agent Waiting",
                "⏳ Writer Agent Waiting",
            ]))
            app.invoke(initial_state, run_config())

# ---------------- SHOW THE RUN ----------------

if "thread_id" in st.session_state:
    snap = app.get_state(run_config())
    values = snap.values

    sources = values.get("sources", [])
    failed_ids = values.get("failed_sources") or []

    if not values:
        # MemorySaver lives in memory, so a paused run is gone after an app restart
        st.info("This run was lost (the app restarted). Please generate again.")
        del st.session_state.thread_id

    elif snap.next == ("writer",):
        show_status(values, paused=True)

        st.subheader("📝 Review before writing")
        st.caption("Untick any source you don't want in the report, then approve.")

        by_id = {s["id"]: s for s in sources}
        summaries = values.get("summaries", [])
        kept = []
        for m in summaries:
            src = by_id[m["source_id"]]
            with st.expander(f"[{src['id']}] {src['title'] or src['url']}"):
                keep = st.checkbox("Use in report", value=True, key=f"keep_{st.session_state.thread_id}_{src['id']}")
                st.markdown(f"[{src['url']}]({src['url']})")
                st.write(m["text"])
            if keep:
                kept.append(m)

        show_failed_warning(failed_ids)

        approve_col, restart_col = st.columns(2)

        if approve_col.button("✅ Approve and write report", disabled=not kept):
            if len(kept) < len(summaries):
                # A human editing agent state: as_node="supervisor" keeps the writer as the next step
                app.update_state(run_config(), {"summaries": kept}, as_node="supervisor")
            with st.spinner("Writing report..."):
                app.invoke(None, run_config())
            st.rerun()

        if restart_col.button("↩️ Start over"):
            del st.session_state.thread_id
            st.rerun()

    else:
        show_status(values)

        if values.get("error"):
            st.error(values["error"])

        else:
            st.markdown("---")
            st.subheader("📄 Final Research Report")

            st.markdown("---")
            with st.container(border=True):
                st.markdown(values["final_report"])
            st.markdown("---")

            show_failed_warning(failed_ids)

        show_all_sources(sources, failed_ids)
