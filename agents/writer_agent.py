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

       prompt= f"""
You are a professional research report writer.

Write a detailed research report on:

Topic:
{query}

Using the summaries below.

The report must contain:

1. Introduction
2. Key Findings
3. Conclusion

Summaries:
{combined_summaries}
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