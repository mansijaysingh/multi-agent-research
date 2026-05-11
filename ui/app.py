import streamlit as st
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

report_length=st.selectbox(
  "Select report length:",
  ["Short", "Detailed"]
)
# ---------------- BUTTON ----------------

generate=st.button("🚀 Generate Report")

# ---------------- WORKFLOW ----------------

if generate:
  if query.strip() == "":
    st.warning("Please enter a research topic.")

  else:
    
    initial_state={
      "query":query,
      "report_length":report_length
    }

    with st.spinner("🤖 AI Agents are working on your report..."):
      status_box.markdown("""
### Current Status

🔄 Supervisor Agent Running  
⏳ Search Agent Waiting  
⏳ Summarizer Agent Waiting  
⏳ Writer Agent Waiting
""")
      result=app.invoke(initial_state)

      status_box.markdown("""
### Current Status

✅ Supervisor Agent Completed  
✅ Search Agent Completed  
✅ Summarizer Agent Completed  
✅ Writer Agent Completed
""")

    final_report= result["final_report"]

    st.markdown("---")
    st.subheader("📄 Final Research Report")
    st.markdown("---")
    with st.container(border=True):
     st.markdown(final_report)
    st.markdown("---")