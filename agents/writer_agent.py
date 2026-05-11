from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def writer_agent(state):
   """
    Takes summaries from state
    Generates final research report
    Stores report in state
    """
   
   try:
       query=state["query"]

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
       response=client.chat.completions.create(
           model="gpt-4o-mini",
           messages=[
               {
                   "role":"user",
                   "content":prompt
               }
           ]
       )

       final_report=response.choices[0].message.content

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