import os
from typing import List
from langchain.tools import tool
from utils.place_info_search import GooglePlacesSearchTool, TavilySearchTool
from dotenv import load_dotenv


class PlaceSearchTool:

    def __init__(self):
        load_dotenv()
        self.google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        print(f"Google Places API Key: {self.google_places_api_key}")
        self.tavily_search = TavilySearchTool()
        
        # Check if the API key is set and is not the default template string
        if self.google_places_api_key and self.google_places_api_key != "your_api_key_here" and self.google_places_api_key.strip():
            self.google_search = GooglePlacesSearchTool(self.google_places_api_key)
        else:
            self.google_search = None
            print("Google Places API Key is not set or is using placeholder. Google Places Search tool will be disabled (falling back to Tavily).")
            
        self.place_search_tool_list = self._setup_tools()

    def _setup_tools(self) -> List:
        
        """Setup all tools for the place search tool"""

        def _tavily_query(self, query: str):
            """Directly invoke TavilySearch when helper method is missing."""
            try:
                from langchain_tavily import TavilySearch
                tavily_tool = TavilySearch(topic="general", include_answer="advanced")
                result = tavily_tool.invoke({"query": query})
                if isinstance(result, dict) and result.get("answer"):
                    return result["answer"]
                return result
            except Exception as e:
                return f"Tavily fallback failed: {e}"

        @tool
        def search_attractions(place: str) -> str:
            """Search for attractions in a given place"""
            try:
                if not self.google_search:
                    raise ValueError("Google Places Search is disabled because the API key is not configured.")
                attraction_result = self.google_search.google_search_attractions(place)
                if attraction_result:
                    return f"Following are the attractions of {place} as suggested by google:{ attraction_result}"
            except Exception as e:
                tavily_func = getattr(self.tavily_search, "tavily_search_attractions", None)
                if callable(tavily_func):
                    tavily_result = tavily_func(place)
                else:
                    tavily_result = _tavily_query(self, f"top attractive places in and around {place}")
                return f"Google cannot find the details due to {e}. \nFollowing are the attractions of {place}: {tavily_result}"  ## Fallback search using tavily in case google places fail
    
        @tool
        def search_resturants(place: str) -> str:
            """Search for restaurants in a given place"""
            try:
                if not self.google_search:
                    raise ValueError("Google Places Search is disabled because the API key is not configured.")
                resturant_result = self.google_search.google_search_restaurants(place)
                if resturant_result:
                    return f"Following are the restaurants of {place} as suggested by google: {resturant_result}"
            except Exception as e:
                tavily_func = getattr(self.tavily_search, "tavily_search_restaurants", None)
                if callable(tavily_func):
                    tavily_result = tavily_func(place)
                else:
                    tavily_result = _tavily_query(self, f"what are the top 10 restaurants and eateries in and around {place}")
                return f"Google cannot find the details due to {e}. \nFollowing are the restaurants of {place}: {tavily_result}"  ## Fallback search using tavily in case google places fail

        @tool
        def search_activities(place: str) -> str:
            """Search for activities in a given place"""
            try:
                if not self.google_search:
                    raise ValueError("Google Places Search is disabled because the API key is not configured.")
                activity_result = self.google_search.google_search_activities(place)
                if activity_result:
                    return f"Following are the activities of {place} as suggested by google: {activity_result}"
            except Exception as e:
                tavily_func = getattr(self.tavily_search, "tavily_search_activities", None)
                if callable(tavily_func):
                    tavily_result = tavily_func(place)
                else:
                    tavily_result = _tavily_query(self, f"Activities in and around {place}")
                return f"Google cannot find the details due to {e}. \nFollowing are the activities of {place}: {tavily_result}"  ## Fallback search using tavily in case google places fail

        @tool
        def search_transportation(place: str) -> str:
            """Search for transportation options in a given place"""
            try:
                if not self.google_search:
                    raise ValueError("Google Places Search is disabled because the API key is not configured.")
                transport_result = self.google_search.google_search_transportation(place)
                if transport_result:
                    return f"Following are the transportation options of {place} as suggested by google: {transport_result}"
            except Exception as e:
                tavily_func = getattr(self.tavily_search, "tavily_search_transportation", None)
                if callable(tavily_func):
                    tavily_result = tavily_func(place)
                else:
                    tavily_result = _tavily_query(self, f"What are the different modes of transportations available in {place}")
                return f"Google cannot find the details due to {e}. \nFollowing are the transportation options of {place}: {tavily_result}"

        return [search_attractions, search_resturants, search_activities,search_transportation]
