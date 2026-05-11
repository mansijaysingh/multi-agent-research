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

st.sidebar.title("⚙️ Workflow")

st.sidebar.markdown("""
### Agents Used

✅ Supervisor Agent  
✅ Search Agent  
✅ Summarizer Agent  
✅ Writer Agent
"""
  
)

# ---------------- USER INPUT ----------------

query=st.text_input(
  "Enter your research topic:"
)

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

      result=app.invoke(initial_state)

    final_report= result["final_report"]

    st.markdown("---")
    st.subheader("📄 Final Research Report")
    st.markdown(final_report)