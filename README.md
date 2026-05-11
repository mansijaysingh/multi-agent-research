# 🤖 Multi-Agent Research Assistant

> An AI-powered research tool that autonomously searches the web, summarizes findings, and generates structured research reports using a multi-agent architecture built with LangGraph.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-FF6B6B?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)

🔗 **[Live Demo](https://multi-agent-research-npcdcfptpcfjxfcplhunpk.streamlit.app/)** &nbsp;|&nbsp; 📂 **[GitHub Repo](https://github.com/mansijaysingh/multi-agent-research)**

---

## 📌 What It Does

Type any research topic — the system automatically dispatches 4 specialized AI agents that work together to deliver a clean, structured research report in seconds.

**Example:**
```
Input:  "Research the impact of AI on healthcare"
Output: A full structured report with Introduction, Key Findings, and Conclusion
```

---

## 🧠 How It Works — Agent Architecture

```
User Input
    ↓
[Supervisor Agent]   ──  reads the query, orchestrates the workflow
    ↓
[Search Agent]       ──  searches the web using Tavily API (5-10 sources)
    ↓
[Summarizer Agent]   ──  extracts key information from each source
    ↓
[Writer Agent]       ──  compiles a well-structured final report
    ↓
Final Research Report → User
```

All agents are connected as **nodes in a LangGraph StateGraph**, sharing a single state object that carries data from one agent to the next.

---

## ✨ Features

- 🔍 **Real-time web search** using Tavily API — not outdated training data
- 🤖 **4 specialized agents** each with a dedicated role
- 🧠 **LangGraph orchestration** — reliable, stateful multi-agent workflow
- 📝 **Structured reports** with Introduction, Key Findings, and Conclusion
- 🌐 **Clean Streamlit UI** — simple input, instant output
- ⚡ **Fast and cost-efficient** using GPT-4o-mini

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Web Search | Tavily API |
| Backend | Python |
| UI | Streamlit |
| Deployment | Streamlit Cloud / Render |

---

## 📁 Project Structure

```
multi-agent-research/
│
├── agents/
│   ├── supervisor.py        # Reads query, initializes state
│   ├── search_agent.py      # Web search using Tavily
│   ├── summarizer_agent.py  # Summarizes search results
│   └── writer_agent.py      # Writes the final report
│
├── graph/
│   └── workflow.py          # LangGraph StateGraph definition
│
├── app.py                   # Streamlit UI
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/mansijaysingh/multi-agent-research.git
cd multi-agent-research
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up API Keys

Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

> Get your Tavily API key for free at [app.tavily.com](https://app.tavily.com)

### 4. Run the App
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 💻 How to Use

1. Open the app in your browser
2. Type any research topic in the input field
3. Click **"Generate Report"**
4. Wait a few seconds while the agents work
5. Read your structured research report!

---

## 🔧 How LangGraph Connects the Agents

```python
from langgraph.graph import StateGraph
from typing import TypedDict

class AgentState(TypedDict):
    query: str
    search_results: list
    summaries: list
    final_report: str

graph = StateGraph(AgentState)

graph.add_node("supervisor",  supervisor_agent)
graph.add_node("search",      search_agent)
graph.add_node("summarizer",  summarizer_agent)
graph.add_node("writer",      writer_agent)

graph.set_entry_point("supervisor")
graph.add_edge("supervisor",  "search")
graph.add_edge("search",      "summarizer")
graph.add_edge("summarizer",  "writer")

app = graph.compile()
```

---

## 📦 Requirements

```
langchain
langchain-openai
langchain-community
langgraph
tavily-python
streamlit
python-dotenv
openai
```

---

## 🙋 About

Built by **Mansi Singh** — AI Developer specializing in LLM applications, LangChain, RAG, and agentic workflows.

[![GitHub](https://img.shields.io/badge/GitHub-mansijaysingh-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/mansijaysingh)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-mansi--ai-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/mansi-ai)
[![Portfolio](https://img.shields.io/badge/Portfolio-mansijaysingh.netlify.app-FF5722?style=for-the-badge&logo=google-chrome&logoColor=white)](https://mansijaysingh.netlify.app)

---

## ⭐ If you found this useful, give it a star!
