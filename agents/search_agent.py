from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
import os

load_dotenv()



def search_agent(state):
  search_tool=TavilySearchResults(max_results=5)
  """
    Search agent:
    Takes query from state
    Returns search results inside state
    """
  
  try:
      query = state['query']
      
      print(f"\n🔍 Searching for: {query}")

      results=search_tool.invoke(query)
      if not results:
         state["search_results"] = "No results found."
         return state
      
      state["search_results"] = results

      return state
  except Exception as e:
     state["search_results"]=f"Error occured: {str(e)}"
     return state
  

if __name__ == "__main__":
   
   test_state={
      "query":"AI in healthcare"

   }

   output=search_agent(test_state)

   print("\n✅ SEARCH RESULTS:\n")

   print(output["search_results"])

