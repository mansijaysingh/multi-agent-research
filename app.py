import streamlit as st
from config import RECURSION_LIMIT
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

st.markdown("---")

# ---------------- SIDEBAR ----------------

st.sidebar.title("⚙️ Agent Workflow")

status_box = st.sidebar.empty()

# ---------------- USER INPUT ----------------

query=st.text_input(
    "Enter your research topic:"
)

# report_length=st.selectbox(
#   "Select report length:",
#   ["Short", "Detailed"]
# )
# ---------------- BUTTON ----------------

generate=st.button("🚀 Generate Report")

# ---------------- WORKFLOW ----------------

if generate:
    if query.strip() == "":
        st.warning("Please enter a research topic.")

    else:
    
        initial_state={
            "query":query
        }

        with st.spinner("🤖 AI Agents are working on your report..."):
            status_box.markdown("""
### Current Status

🔄 Supervisor Agent Running  
⏳ Search Agent Waiting  
⏳ Summarizer Agent Waiting  
⏳ Writer Agent Waiting
""")
            result=app.invoke(initial_state, {"recursion_limit": RECURSION_LIMIT})

        error = result.get("error")
        sources = result.get("sources", [])

        # The first stage without output is the one that failed; later ones were skipped
        stages = [
            ("Search Agent", bool(sources)),
            ("Summarizer Agent", bool(result.get("summaries"))),
            ("Writer Agent", bool(result.get("final_report"))),
        ]
        lines = ["✅ Supervisor Agent Completed  "]
        failed = False
        for name, done in stages:
            if done:
                lines.append(f"✅ {name} Completed  ")
            elif not failed:
                lines.append(f"❌ {name} Failed  ")
                failed = True
            else:
                lines.append(f"⏭️ {name} Skipped  ")

        lines.append(f"\nSearch attempts: {result.get('search_attempts', 0)}  ")
        if result.get("search_query"):
            lines.append(f"🔁 Refined query: {result['search_query']}  ")

        status_box.markdown("### Current Status\n\n" + "\n".join(lines))

        if error:
            st.error(error)

        else:
            final_report= result["final_report"]

            st.markdown("---")
            st.subheader("📄 Final Research Report")

            st.markdown("---")
            with st.container(border=True):
                st.markdown(final_report)
            st.markdown("---")

        if sources:
            st.subheader("🔗 Sources")
            for s in sources:
                st.markdown(f"{s['id']}. [{s['title'] or s['url']}]({s['url']})")