import re
import time
import uuid

import streamlit as st
from config import MAX_RUNS_PER_SESSION, MODEL, RECURSION_LIMIT
from graph.workflow import app

EXAMPLES = [
    "Impact of AI on customer support",
    "How electric vehicles affect the power grid",
    "Latest developments in AI regulation in 2026",
    "Microplastics and human health",
]

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Palette: soft sage background, dark forest-green anchor, sage accent, terracotta only for warnings and "not used".
CREAM = "#F7F5F0"        # light text on the dark header
CARD = "#FFFFFF"
BORDER = "#DCE5DE"       # soft green-grey, fits the sage background
SAGE = "#5B8C6E"         # accent: buttons, active step, links
SAGE_DARK = "#44705A"
SAGE_SOFT = "#E3EEE7"    # done steps, chips, stat cards
TERRACOTTA = "#D98E73"   # warnings, sources not used
FOREST = "#1F3A2E"       # dark anchor: header banner, sidebar
FOREST_MID = "#2F5D46"   # dark accent: primary buttons, done steps, numbers
TEXT = "#2F3A33"
MUTED = "#6B746D"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
/* Nunito everywhere, except Streamlit's icon font (expander arrows etc.) and code */
html, body, .stApp, .stApp *:not([data-testid="stIconMaterial"]):not(code):not(pre) {{
    font-family: 'Nunito', sans-serif !important; }}
.block-container {{ max-width: 1000px; padding-top: 2rem; padding-bottom: 4rem; }}
footer {{ visibility: hidden; }}
a {{ color: {SAGE_DARK}; }}

.hero {{ background: linear-gradient(135deg, {FOREST} 0%, {FOREST_MID} 100%); border-radius: 20px;
         padding: 1.6rem 1.9rem 1.4rem; margin-bottom: 1.1rem; box-shadow: 0 6px 20px rgba(31, 58, 46, 0.18); }}
.hero-title {{ font-size: 2.1rem; font-weight: 760; letter-spacing: -0.02em; margin: 0; color: {CREAM}; }}
.hero-title span {{ color: #A9D1B6; }}
.hero-sub {{ color: #C9D8CE; font-size: 1.02rem; margin: 0.3rem 0 0.8rem 0; }}
.badge {{ display: inline-block; font-size: 0.78rem; font-weight: 600; padding: 0.2rem 0.7rem; border-radius: 999px;
          margin: 0 0.35rem 0.2rem 0; background: rgba(255, 255, 255, 0.12); color: #E3EEE7;
          border: 1px solid rgba(255, 255, 255, 0.18); }}

section[data-testid="stSidebar"] {{ background: {FOREST}; }}
section[data-testid="stSidebar"] * {{ color: #E3EEE7 !important; }}
section[data-testid="stSidebar"] a {{ color: #A9D1B6 !important; }}

div[data-testid="stTabs"] button[aria-selected="true"] p {{ color: {FOREST_MID}; font-weight: 700; }}
h4 {{ color: {FOREST}; }}

.stepper {{ display: flex; align-items: center; gap: 0.5rem; margin: 1rem 0 0.9rem 0; flex-wrap: wrap; }}
.step {{ display: flex; align-items: center; gap: 0.45rem; font-size: 0.93rem; color: #A7ADA8; white-space: nowrap; }}
.dot {{ width: 1.75rem; height: 1.75rem; border-radius: 50%; display: inline-flex; align-items: center;
        justify-content: center; font-size: 0.85rem; font-weight: 700; border: 2px solid {BORDER}; background: {CARD}; }}
.line {{ flex: 1; min-width: 1.5rem; height: 3px; border-radius: 3px; background: {BORDER}; }}
.step.done {{ color: {TEXT}; }}
.step.done .dot {{ background: {FOREST_MID}; border-color: {FOREST_MID}; color: #FFF; }}
.step.active {{ color: {SAGE_DARK}; font-weight: 650; }}
.step.active .dot {{ border-color: {SAGE}; color: {SAGE}; box-shadow: 0 0 0 5px {SAGE_SOFT}; }}
.step.failed {{ color: {TERRACOTTA}; font-weight: 650; }}
.step.failed .dot {{ background: {TERRACOTTA}; border-color: {TERRACOTTA}; color: #FFF; }}

div[data-testid="stMetric"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; padding: 0.7rem 1rem; }}
div[data-testid="stMetricLabel"] p {{ color: {MUTED}; font-size: 0.82rem; font-weight: 600; }}
div[data-testid="stMetricValue"] {{ color: {FOREST}; }}

[class*="st-key-card_"] {{ background: {CARD}; border-left: 4px solid {FOREST_MID} !important; }}
.st-key-report {{ background: {CARD}; border: 1px solid {BORDER} !important; border-radius: 18px; }}

button[data-testid="stBaseButton-pills"] {{ background: {CARD}; border: 1px solid {BORDER}; color: {SAGE_DARK}; }}
button[data-testid="stBaseButton-pills"]:hover {{ background: {SAGE_SOFT}; border-color: {SAGE}; }}
div[data-testid="stTextInput"] input {{ border-radius: 12px; background: {CARD}; }}
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {{
    border-radius: 12px; font-weight: 650; }}
button[data-testid="stBaseButton-secondary"] {{ border-radius: 12px; }}
.not-used {{ color: {TERRACOTTA}; font-weight: 600; }}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

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


def stream_run(graph_input, status):
    """
    Runs the graph (until the pause, or to the end) and writes each step into the status box.
    stream() runs exactly what invoke() would; it just reports node by node.
    """
    for event in app.stream(graph_input, run_config(), stream_mode="updates"):
        for node, update in event.items():
            if node.startswith("__") or not update:  # e.g. the interrupt marker
                continue
            if node == "search":
                if update.get("sources") is not None:
                    status.write(f"🔍 Searched the web: **{len(update['sources'])}** sources")
                else:
                    status.write("🔍 Search failed")
            elif node == "refine_query":
                status.write(f"🔁 Too few sources, refined the query: *{update['search_query']}*")
            elif node == "summarizer":
                used, dropped = len(update["summaries"]), len(update["failed_sources"])
                status.write(f"🧠 Summarized **{used}** sources" + (f", dropped {dropped} off-topic or failed" if dropped else ""))
            elif node == "writer":
                status.write("✍️ Wrote the cited report")
            elif node == "fail":
                status.write("⚠️ Couldn't produce a report")


def start_run(topic):
    st.session_state.runs = st.session_state.get("runs", 0) + 1
    # A new thread for every run, so a new topic never mixes with an old run's state
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.timings = {}

    start = time.perf_counter()
    with st.status(f"Researching **{topic}**…", expanded=True) as status:
        stream_run({"query": topic}, status)
        status.update(label="Research done. Review the sources below.", state="complete", expanded=False)
    st.session_state.timings["research"] = time.perf_counter() - start


def stepper(values, paused):
    """Search → Summarize → Review → Write, each done / active / failed / pending."""
    sources, summaries = values.get("sources") or [], values.get("summaries")
    names = ["Search", "Summarize", "Review", "Write"]

    if values.get("final_report"):
        states = ["done"] * 4
    elif paused:
        states = ["done", "done", "active", "pending"]
    elif not sources:
        states = ["failed", "pending", "pending", "pending"]
    elif not summaries:
        states = ["done", "failed", "pending", "pending"]
    else:
        states = ["done", "done", "done", "failed"]

    marks = {"done": "✓", "failed": "!", "active": "", "pending": ""}
    parts = []
    for i, (name, state) in enumerate(zip(names, states)):
        if i:
            parts.append('<div class="line"></div>')
        parts.append(f'<div class="step {state}"><span class="dot">{marks[state] or i + 1}</span>{name}</div>')
    st.markdown(f'<div class="stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


def metrics(values):
    t = st.session_state.get("timings", {})
    total = sum(t.values())
    cols = st.columns(4)
    cols[0].metric("Sources found", len(values.get("sources") or []))
    cols[1].metric("Used in report", len(values.get("summaries") or []))
    cols[2].metric("Searches", values.get("search_attempts", 0))
    cols[3].metric("Time", f"{total:.0f} s" if total else "–")


def source_line(s, note=""):
    return f"**[{s['id']}]** [{s['title'] or s['url']}]({s['url']}){note}"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "report"


def new_research():
    # Callback: runs before the rerun, so it may clear the text box. The old checkpoint stays in
    # memory but is never read again, because the next run gets a new thread_id.
    st.session_state.pop("thread_id", None)
    st.session_state.pop("timings", None)
    st.session_state.topic = ""


def use_example():
    # Runs before the rerun, so it may still set the text box's value
    if st.session_state.example:
        st.session_state.topic = st.session_state.example
        st.session_state.example = None
        st.session_state.start_requested = True


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.markdown("### 🔬 How it works")
    st.markdown(
        "1. **Search** the web through an MCP tool (Tavily)\n"
        "2. **Summarize** every source in parallel and drop off-topic ones\n"
        "3. **Review**: you choose which sources to keep\n"
        "4. **Write** a report whose citations are checked in code"
    )
    st.caption(f"Model: {MODEL} · LangGraph · MCP · LangSmith")
    st.markdown("[GitHub repo](https://github.com/mansijaysingh/multi-agent-research)")

# ---------------- HEADER + INPUT ----------------

badges = "".join(
    f'<span class="badge">{label}</span>'
    for label in ["🔍 Live web search", "🧠 Parallel summaries", "📝 You review", "✍️ Cited report"]
)
st.markdown(
    '<div class="hero">'
    '<p class="hero-title">🔬 Research <span>Agent</span></p>'
    '<p class="hero-sub">Cited research reports from the live web, and you approve the sources before anything is written.</p>'
    f'{badges}</div>',
    unsafe_allow_html=True,
)

with st.form("search", border=False):
    col_input, col_button = st.columns([5, 1], vertical_alignment="bottom")
    query = col_input.text_input("Research topic", key="topic", placeholder="What do you want to research?",
                                 label_visibility="collapsed")
    submitted = col_button.form_submit_button("Research →", type="primary", width="stretch")

st.pills("Try an example", EXAMPLES, key="example", on_change=use_example, label_visibility="collapsed")

runs_used = st.session_state.get("runs", 0)
runs_caption = st.empty()  # filled in after a possible new run, so the count is current

# ---------------- START A RUN ----------------
# The run stops before the writer; the page below is drawn from the saved checkpoint,
# because Streamlit re-runs this whole script on every click.

if submitted or st.session_state.pop("start_requested", False):
    topic = (query or "").strip()
    if not topic:
        st.warning("Please enter a research topic.")
    elif runs_used >= MAX_RUNS_PER_SESSION:
        # Protects the shared free-tier quota; a new browser session resets it, so it only stops casual overuse
        st.info("Demo limit reached for this session.")
    else:
        start_run(topic)

runs_left = max(MAX_RUNS_PER_SESSION - st.session_state.get("runs", 0), 0)
runs_caption.caption(f"Free-tier demo: {runs_left} of {MAX_RUNS_PER_SESSION} runs left in this session.")

# ---------------- SHOW THE RUN ----------------

if "thread_id" in st.session_state:
    snap = app.get_state(run_config())
    values = snap.values
    paused = snap.next == ("writer",)

    if not values:
        # MemorySaver lives in memory, so a paused run is gone after an app restart
        st.info("This run was lost (the app restarted). Please start it again.")
        del st.session_state.thread_id
        st.stop()

    sources = values.get("sources") or []
    summaries = values.get("summaries") or []
    failed_ids = values.get("failed_sources") or []
    by_id = {s["id"]: s for s in sources}

    st.divider()
    title_col, new_col = st.columns([4, 1], vertical_alignment="center")
    title_col.markdown(f"#### {values['query']}")
    new_col.button("＋ New research", on_click=new_research, width="stretch",
                   help="Clear this run and search another topic")
    stepper(values, paused)
    metrics(values)

    if paused:
        # ---------- REVIEW ----------
        st.markdown("##### Review the sources before writing")
        st.caption("Untick any source you don't want in the report. Only the ticked ones can be cited.")

        kept = []
        for m in summaries:
            src = by_id[m["source_id"]]
            with st.container(border=True, key=f"card_{src['id']}"):
                keep = st.checkbox(f"**[{src['id']}] {src['title'] or src['url']}**", value=True,
                                   key=f"keep_{st.session_state.thread_id}_{src['id']}")
                st.caption(src["url"])
                st.markdown(m["text"])
            if keep:
                kept.append(m)

        if failed_ids:
            with st.expander(f"Not used: {len(failed_ids)} source(s) were off-topic or couldn't be summarized"):
                for i in failed_ids:
                    st.markdown(source_line(by_id[i]))

        approve_col, _ = st.columns([2, 3])
        if approve_col.button(f"✅ Approve and write ({len(kept)} sources)", type="primary", disabled=not kept,
                              width="stretch"):
            if len(kept) < len(summaries):
                # A human editing agent state: as_node="supervisor" keeps the writer as the next step
                app.update_state(run_config(), {"summaries": kept}, as_node="supervisor")
            start = time.perf_counter()
            with st.status("Writing the report…", expanded=True) as status:
                stream_run(None, status)
                status.update(label="Report written", state="complete", expanded=False)
            st.session_state.timings["write"] = time.perf_counter() - start
            st.rerun()

    elif values.get("error"):
        # ---------- FAILED ----------
        st.error(f"**No report.** {values['error']}")
        st.caption("Try a more specific topic, or check the sources the search found below.")
        if sources:
            with st.expander(f"Sources searched ({len(sources)})"):
                for s in sources:
                    st.markdown(source_line(s, " · not used" if s["id"] in failed_ids else ""))

    else:
        # ---------- REPORT ----------
        report = values["final_report"]
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", report.split("## Sources")[0])}

        tab_report, tab_sources, tab_details = st.tabs(["📄 Report", f"🔗 Sources ({len(sources)})", "⚙️ Run details"])

        with tab_report:
            st.download_button("⬇️ Download (.md)", data=f"# {values['query']}\n\n{report}\n",
                               file_name=f"{slug(values['query'])}.md", mime="text/markdown")
            with st.container(border=True, key="report"):
                st.markdown(report)

        with tab_sources:
            st.caption("Everything the search found. Only summarized sources you kept can be cited.")
            kept_ids = {m["source_id"] for m in summaries}
            for s in sources:
                if s["id"] in failed_ids:
                    note = " · ⚠️ not used (off-topic or not summarized)"
                elif s["id"] not in kept_ids:
                    note = " · ✖ removed by you in review"
                elif s["id"] in cited:
                    note = " · ✅ cited"
                else:
                    note = " · used, not cited"
                st.markdown(source_line(s, note))

        with tab_details:
            st.markdown(f"- **Search query:** {values.get('search_query') or values['query']}"
                        + (" *(refined)*" if values.get("search_query") else ""))
            st.markdown(f"- **Search attempts:** {values.get('search_attempts', 0)}")
            st.markdown(f"- **Sources not used:** {failed_ids or 'none'}")
            t = st.session_state.get("timings", {})
            if t:
                st.markdown(f"- **Time:** research {t.get('research', 0):.0f} s, writing {t.get('write', 0):.0f} s")
            st.markdown(f"- **Model:** {MODEL}")
            st.caption(f"Thread: {st.session_state.thread_id}")
