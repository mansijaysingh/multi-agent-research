from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from config import MODEL

load_dotenv()

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.2)


def summarizer_agent(state):
  """
    Takes search results from state
    Summarizes them using Gemini
    Stores summaries back in state
    """
  try: 
      search_results=state["search_results"]

      summaries=[]

      for result in search_results:
         
         content= result.get("content", " ")

         prompt = f"""
You are an expert research summarizer.

Read the research content below and create a clear, concise, and informative summary.

Requirements:
- Focus on the most important insights
- Avoid unnecessary details
- Keep the summary professional and easy to understand
- Use simple and clean language

Research Content:
{content}
"""

         response = llm.invoke(prompt)

         summary=response.text
         summaries.append(summary)

      state["summaries"]=summaries
      return state
  except Exception as e:
     
     state["summaries"]=[f"Error:{str(e)}"]
     return state
  

if __name__ == "__main__":
   
   dummy_state={
      "search_results":[
         {
            "content": "AI is transforming healthcare through diagnosis automation and predictive analytics."
         },

         {
            "content": "Hospitals are using AI chatbots to improve patient communication and reduce workload."
         }
      ]
   }

   output=summarizer_agent(dummy_state)

   print("\n✅ SUMMARIES:\n")

   for summary in output["summaries"]:
      print(summary)
      print("\n------------------\n")