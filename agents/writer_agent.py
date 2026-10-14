from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from config import MODEL

load_dotenv()

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.3)


def writer_agent(state):
   """
    Takes summaries from state
    Generates final research report
    Stores report in state
    """
   
   try:
       query=state["query"]
    #    report_length = state["report_length"]

       summaries=state["summaries"]

       combined_summaries="\n\n".join(summaries)

       prompt = f"""
You are an expert research report writer.

Write a detailed, professional, and well-structured research report.

Research Topic:
{query}

Based on these research summaries:
{combined_summaries}

Requirements:
- Use clear headings
- Keep the report informative and easy to read
- Avoid repetition
- Explain key insights properly
- Make the report professional and polished

The report must include:

1. Introduction
2. Key Findings
3. Conclusion
"""
       response = llm.invoke(prompt)

       final_report=response.text

       state["final_report"]=final_report
       return state
   
   except Exception as e:
       state["final_report"]=f"Error: {str(e)}"
       return state
   


if __name__ == "__main__":
    
    dummy_state={
        "summaries": [
            "AI is improving healthcare diagnosis systems.",
            "Hospitals use AI chatbots for patient interaction.",
            "Predictive analytics helps detect diseases early."
        ]
    }

    output=writer_agent(dummy_state)

    print("\n✅ FINAL REPORT:\n")

    print(output["final_report"])