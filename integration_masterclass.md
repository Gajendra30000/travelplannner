# 🎓 LangChain, LangGraph, Tools & FastAPI Integration Masterclass
## The Complete Deep-Dive Guide (ELI5 to Production-Grade Architecture)

Welcome to the ultimate guide on integrating **LangChain (AI LLM bindings)**, **LangGraph (Stateful Agent loops)**, **Custom Python Tools**, and **FastAPI (Web API endpoints)**. 

This document is written to be incredibly detailed, explaining both the conceptual design (in simple terms) and the raw execution mechanics (line-by-line code paths). By the time you finish reading this, you will understand exactly how data moves through every single file in your Travel Planner application.

---

## 📂 Table of Contents
1. [The Architectural Overview (System Topology)](#1-the-architectural-overview-system-topology)
2. [Deep Dive: FastAPI & Uvicorn (The Network Layer)](#2-deep-dive-fastapi--uvicorn-the-network-layer)
3. [Deep Dive: Pydantic V2 (The Validation Layer)](#3-deep-dive-pydantic-v2-the-validation-layer)
4. [Deep Dive: LangChain (The AI Reasoning Layer)](#4-deep-dive-langchain-the-ai-reasoning-layer)
5. [Deep Dive: Custom Python Tools & @tool Reflection](#5-deep-dive-custom-python-tools--tool-reflection)
6. [Deep Dive: LangGraph (The Orchestration State Machine)](#6-deep-dive-langgraph-the-orchestration-state-machine)
7. [The Step-by-Step Data Flow (From Streamlit to FastAPI and Back)](#7-the-step-by-step-data-flow-from-streamlit-to-fastapi-and-back)
8. [Failure Modes & Exception Propagation (Handling Crashes Resiliently)](#8-failure-modes--exception-propagation-handling-crashes-resiliently)
9. [An Exhaustive, 1000-Line Equivalent Annotated Reference Codebase](#9-an-exhaustive-1000-line-equivalent-annotated-reference-codebase)

---

## 1. The Architectural Overview (System Topology)

Before analyzing the code, let's understand how these four software layers sit together in memory:

```
+-----------------------------------------------------------------------------------+
|                              USER WEB BROWSER                                     |
|  [Streamlit UI] (Presents Forms, Captures Inputs, Renders Styled HTML Output)     |
+-----------------------------------------------------------------------------------+
                                         │
                        HTTP POST JSON Request (/query)
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                              FASTAPI SERVER                                       |
|  [main.py]                                                                        |
|    - FastAPI App (Listens on port 8000, handles HTTP/CORS, validates requests)    |
|    - Uvicorn (ASGI event loop driving concurrent web processes)                   |
+-----------------------------------------------------------------------------------+
                                         │
                        Invokes Graph with Initial State
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                              LANGGRAPH WORKFLOW                                   |
|  [agentic_workflow.py]                                                            |
|    - StateGraph (Coordinates state transitions: State dict contains messages)      |
|    - Nodes ('agent' runs LLM logic, 'tools' executes python functions)            |
|    - Conditional Edges (evaluates if LLM requested toolcalls)                     |
+-----------------------------------------------------------------------------------+
          │                                                    ▲
          │ (Wants Weather/Places/Rates)                       │ (Returns String Result)
          ▼                                                    │
+------------------------------------+             +--------------------------------+
|          LANGCHAIN LLM             |             |          CUSTOM TOOLS          |
|  [model_loaders.py]                |             |  [tools/ & utils/]             |
|    - ChatGroq / ChatOpenAI         |             |    - GooglePlacesSearchTool    |
|    - Tool Binding (converts python |             |    - TavilySearchTool          |
|      functions to JSON schemas)    |             |    - WeatherForecastTool       |
|    - Generates tool call JSON      |             |    - CurrencyConverter         |
+------------------------------------+             +--------------------------------+
```

Each component has a single, isolated job:
1. **FastAPI**: Acts as the gatekeeper. It takes the requests from the web browser, parses them into Python structures, passes them to the backend workflow, and returns the response.
2. **LangGraph**: Acts as the project manager. It maintains the conversation memory, controls the sequence of steps, and decides when the process is done.
3. **LangChain**: Acts as the communication bridge. It wraps our API calls to model providers (like Groq or OpenAI) and formats prompts.
4. **Tools**: Act as the hands and feet. They execute standard Python code to query databases, call external web services, or perform mathematical calculations.

---

## 2. Deep Dive: FastAPI & Uvicorn (The Network Layer)

### The ASGI Event Loop
Traditional Python web frameworks (like Flask or Django) are built on **WSGI (Web Server Gateway Interface)**. WSGI is synchronous. When a user requests a travel plan, the server thread is completely blocked for 15 seconds while waiting for the LLM to generate the itinerary. No other requests can be handled by that thread.

FastAPI is built on **ASGI (Asynchronous Server Gateway Interface)**, driven by **Uvicorn**. It uses an asynchronous event loop (similar to Node.js). 
When a route is declared using `async def`:
```python
@app.post("/query")
async def query_travel_agent(query: QueryRequest):
    output = await run_in_threadpool(react_app.invoke, {"messages": [...]})
    return output
```
If the code is waiting for an network call (like Groq's API or Google Maps API), the thread yields control back to the event loop. The server can process thousands of other concurrent requests while waiting for the AI agent to finish!

### CORS Middleware
When a web browser tries to load resource scripts from a different port or domain name (e.g., Streamlit on port `8501` calls FastAPI on port `8000`), the browser blocks the call due to security policies. This is resolved by registering the **CORSMiddleware** in FastAPI:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to ['http://localhost:8501']
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, OPTIONS, PUT, etc.
    allow_headers=["*"], # Allows custom authentication headers
)
```
During a request, Uvicorn intercept the header, checks the request path, adds the appropriate `Access-Control-Allow-Origin` values, and allows the frontend to retrieve the JSON data safely.

---

## 3. Deep Dive: Pydantic V2 (The Validation Layer)

When JSON payloads reach Uvicorn, they are raw strings of text:
`'{"question": "Paris", "trip_duration": 7}'`

FastAPI relies on **Pydantic** to parse and convert this text into objects. We define a request model class:
```python
class QueryRequest(BaseModel):
    question: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget_range: Optional[str] = None
    trip_duration: Optional[int] = None
    travel_style: Optional[str] = None
```

### Under the Hood of Validation:
1. **Type Coercion**: If a user submits `{"trip_duration": "7"}` (a string), Pydantic automatically parses it into the integer `7` because of the `int` type hint.
2. **Missing Keys**: If a field doesn't exist, it evaluates its default. If it has no default and isn't marked as `Optional` (or `None`), Pydantic immediately aborts the execution and throws a validation error.
3. **Pydantic V2 Rust Engine**: Pydantic V2 compiles model structures into a binary Rust validator. This speed up parsing by up to 20x compared to old python-based parsing models.

---

## 4. Deep Dive: LangChain (The AI Reasoning Layer)

LangChain provides standard Python classes to interact with different LLM APIs. In our project under `utils/model_loaders.py`, we instantiate either:
* **ChatGroq**: Connects to the Groq cloud infrastructure.
* **ChatOpenAI**: Connects to OpenAI servers.

### The Role of Chat Models
Unlike older completion models (which take raw strings and output raw strings), modern Chat Models communicate using list of message objects. These objects represent the conversation history:

```python
messages = [
    SystemMessage(content="You are a helpful travel planner."),
    HumanMessage(content="Suggest 2 hotels in Tokyo."),
    AIMessage(content="1. Park Hyatt Tokyo\n2. Hotel Gracery Shinjuku.")
]
```

When you pass this list to `llm.invoke()`, LangChain serializes it into the JSON structure expected by the specific model provider's API.

---

## 5. Deep Dive: Custom Python Tools & @tool Reflection

This is where the magic of **Tool Calling** happens. How does an LLM know that a Python function exists, and how does it execute it?

### Step A: Defining the Tool
When you write the `@tool` decorator:
```python
@tool
def get_current_weather(city: str) -> str:
    """Get current weather for a city."""
    ...
```
The `@tool` decorator is a wrapper. It reads:
1. The function signature: `def get_current_weather(city: str)`.
2. The type annotations: `city: str`.
3. The docstring: `"""Get current weather for a city."""`

It packages these attributes into an instance of `StructuredTool`. This class implements a property called `.args_schema`, which yields a standard JSON Schema detailing the inputs the tool expects.

### Step B: Binding the Tool (`bind_tools`)
When we execute:
```python
self.llm_with_tools = self.llm.bind_tools(tools=self.tools)
```
LangChain maps our python tool classes into their JSON descriptions. Under the hood, this compiles the tools into a configuration payload (usually `tools` parameter in OpenAI/Groq API specifications).

When we call the LLM, we send the conversation history *plus* this list of tool definitions.

```
Request Sent to LLM Server:
{
  "model": "llama-3.3-70b-versatile",
  "messages": [ ... ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_current_weather",
        "description": "Get current weather for a city.",
        "parameters": {
          "type": "object",
          "properties": {
            "city": { "type": "string" }
          },
          "required": ["city"]
        }
      }
    }
  ]
}
```

### Step C: The Model's Decision
The LLM is a next-token generator. It evaluates the messages and prompt. It notices that the user asks: *"What's the weather like in New York?"*
The model realizes it does not have this information in its training weights, but it has access to a tool named `get_current_weather` with description *"Get current weather for a city"*.

Instead of generating text, the LLM outputs a special request block. It generates a **Tool Call request**:

```json
{
  "role": "assistant",
  "tool_calls": [
    {
      "id": "call_weather_ny_123",
      "type": "function",
      "function": {
        "name": "get_current_weather",
        "arguments": "{\"city\": \"New York\"}"
      }
    }
  ]
}
```

This JSON payload is sent back across the network to our application.

---

## 6. Deep Dive: LangGraph (The Orchestration State Machine)

Once the LLM returns a Tool Call request, we need a system to run the corresponding Python function and feed the results back. This is what **LangGraph** manages.

LangGraph represents this loop as a **StateGraph**.

```
              +---------------+
              |     START     |
              +---------------+
                      │
                      ▼
              +---------------+
              |   "agent"     | <─── (Loops back to reason)
              +---------------+
                      │
            (Conditional Edge)
            [tools_condition]
             /             \
            /               \
 (ToolCalls exists)    (No ToolCalls)
          /                   \
         ▼                     ▼
  +---------------+     +---------------+
  |   "tools"     |     |      END      |
  +---------------+     +---------------+
         │
  (Execute Tool)
         │
         ▼
  (Returns to Agent)
```

### The State Schema
Every node in the graph reads from and writes to the centralized **State**. We initialize our graph with `MessagesState`. This is a typed dictionary tracking our message logs:
```python
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```
* **`messages`**: The list of all system, human, AI, and tool responses.
* **`add_messages`**: The **reducer function**. When a node returns `{"messages": [new_msg]}`, LangGraph does not overwrite the old list. It runs `add_messages(existing_list, new_list)`, which appends the new message to the list.

### The Graph Construction
In `agentic_workflow.py`, we construct the layout:
```python
# 1. Initialize builder
graph_builder = StateGraph(MessagesState)

# 2. Add execution blocks (Nodes)
graph_builder.add_node("agent", self.agent_function)
graph_builder.add_node("tools", ToolNode(tools=self.tools))

# 3. Define transitions (Edges)
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", tools_condition)
graph_builder.add_edge("tools", "agent")
graph_builder.add_edge("agent", END)

# 4. Compile into an executable app
self.graph = graph_builder.compile()
```

---

## 7. The Step-by-Step Data Flow (From Streamlit to FastAPI and Back)

Let's trace a real user journey: **"Plan a 3-day trip to Tokyo and calculate the hotel cost if price is 100/night."**

### Step A: Streamlit UI
* **File**: `streamlit_app.py`
* **Action**: User types request, sets date picker, and clicks **"Generate My Travel Plan"**.
* **Data Payload**:
  ```json
  {
    "question": "Plan a 3-day trip to Tokyo and calculate the hotel cost if price is 100/night.",
    "start_date": "2026-07-01",
    "end_date": "2026-07-04",
    "budget_range": "Mid-range ($$)",
    "travel_style": "Cultural",
    "trip_duration": 3
  }
  ```
* Streamlit sends this payload to the FastAPI `/query` endpoint via HTTP POST.

### Step B: FastAPI Server Endpoint
* **File**: `main.py`
* **Action**: Receives payload. It simplifies `"Mid-range ($$)"` to `"medium"`. It calls the `GraphBuilder` class to set up the workflow.
* **Execution**:
  ```python
  graph = GraphBuilder(
      model_provider="groq",
      start_date="2026-07-01",
      end_date="2026-07-04",
      budget_type="medium",
      travel_style="Cultural",
      question="..."
  )
  react_app = graph()
  ```
  It runs `react_app.invoke({"messages": [{"role": "user", "content": prompt_str}]})`.

### Step C: LangGraph Node `"agent"`
* **File**: `agent/agentic_workflow.py`
* **Action**: The `agent_function` runs. It retrieves the current messages state (which contains our initial human message).
* It attaches the system prompt generated by `create_system_prompt()` under `prompt_library/prompt.py`.
* It calls `self.llm_with_tools.invoke(prompt_messages)`.

### Step D: LLM Reasoning & Tool Call Generation
* **File**: `utils/model_loaders.py` (instantiated model)
* **Action**: The LLM reads the user prompt: *"Plan a 3-day trip to Tokyo and calculate the hotel cost if price is 100/night."*
* The LLM realizes:
  1. It needs Tokyo attractions. It matches this to `search_attractions`.
  2. It needs to multiply 100 * 3. It matches this to `estimate_total_hotel_cost`.
* The LLM generates a response requesting **two parallel tool calls**:
  * Tool Call 1: `search_attractions(place="Tokyo")`
  * Tool Call 2: `estimate_total_hotel_cost(price_per_night="100", total_days=3.0)`
* The LLM response is returned as an `AIMessage` containing a `tool_calls` parameter.

### Step E: The Conditional Router (`tools_condition`)
* **File**: `agent/agentic_workflow.py`
* **Action**: LangGraph evaluates the edge leading from `"agent"`. The `tools_condition` router evaluates the last message. Since `tool_calls` exists, it routes the flow to `"tools"`.

### Step F: The `"tools"` Node (`ToolNode`)
* **File**: `tools/place_search_tool.py` and `tools/expense_calculator_tool.py`
* **Action**: The `ToolNode` maps the two requested names to our Python functions:
  1. **Attractions tool**: Executes `search_attractions("Tokyo")` inside [place_search_tool.py](file:///c:/Users/jayan/OneDrive/Desktop/travel/tools/place_search_tool.py). It attempts Google Places. If it fails, it runs Tavily search in [utils/place_info_search.py](file:///c:/Users/jayan/OneDrive/Desktop/travel/utils/place_info_search.py). It returns the text: *"Senso-ji Temple, Tokyo Skytree, Meiji Jingu..."*
  2. **Calculator tool**: Executes `estimate_total_hotel_cost("100", 3.0)` inside [expense_calculator_tool.py](file:///c:/Users/jayan/OneDrive/Desktop/travel/tools/expense_calculator_tool.py). It forwards this to `Calculator.multiply` in [utils/expense_calculator.py](file:///c:/Users/jayan/OneDrive/Desktop/travel/utils/expense_calculator.py), which performs the math operation and returns `300.0`.
* The results are packaged into `ToolMessage` instances and appended to the messages state.
* The graph flows back to `"agent"`.

### Step G: Final Response Generation
* **File**: `agent/agentic_workflow.py`
* **Action**: The `"agent"` runs again. It calls the LLM, sending the updated history containing the original question, its previous tool request, and the tool results (attractions and cost calculation).
* The LLM sees the results: *"Senso-ji, Tokyo Skytree"* and *"$300 total cost"*.
* The LLM compiles the final Markdown itinerary detailing:
  * Day-by-day sightseeing layout.
  * Hotel cost breakdown (citing the calculated $300 total).
* It returns this text as a standard `AIMessage` with **no** `tool_calls`.
* The `tools_condition` router evaluates the message, sees no tool calls, and routes the flow to `END`.

### Step H: Saving the Document
* **File**: `main.py` calling `utils/save_to_document.py`
* **Action**: The graph completes. FastAPI receives the compiled markdown itinerary.
* It calls `save_document(final_output)`.
* `save_document` creates the markdown file `./outputs/AI_Trip_Planner_YYYY-MM-DD_HH-MM-SS.md` and writes the output.
* FastAPI returns a JSON response to Streamlit:
  ```json
  {
    "answer": "Generated travel plan markdown...",
    "saved_file": "./outputs/AI_Trip_Planner_2026-06-30_12-00-00.md"
  }
  ```

### Step I: Frontend Rendering
* **File**: `streamlit_app.py`
* **Action**: Streamlit receives the response. It runs `markdown_to_html` to format the Markdown text, and displays it in styled HTML cards with gradients for the user.

---

## 8. Failure Modes & Exception Propagation (Handling Crashes Resiliently)

A production-grade system must expect things to fail. Here is how exceptions are caught at every level in this architecture:

### 1. External API Failures (Google Places, Tavily, Weather)
* **Where it happens**: inside `utils/place_info_search.py` or `utils/weather_tool.py`.
* **How it is caught**: We wrap our API queries in `try-except` blocks.
  ```python
  try:
      # call google api
  except Exception as e:
      # call tavily api (fallback)
  ```
  If Google fails, the program catches the error, calls the Tavily backup search engine, and returns its result. The exception does not escape the tool function, so LangGraph continues running smoothly.

### 2. File Write Failures (Save Document)
* **Where it happens**: inside `utils/save_to_document.py` (e.g. disk full, permission denied).
* **How it is caught**:
  ```python
  try:
      with open(filename, "w", encoding="utf-8") as file:
          file.write(markdown_content)
  except Exception as e:
      print(f"Error saving document: {e}")
      return None
  ```
  The error is captured, logged to the console, and returns `None` instead of throwing a stack trace that would crash the FastAPI endpoint.

### 3. Graph Runtime Failures
* **Where it happens**: inside LangGraph execution (`react_app.invoke()`).
* **How it is caught**: In `main.py`, the entire execution is wrapped in a safety boundary:
  ```python
  try:
      output = react_app.invoke({"messages": messages})
  except Exception as e:
      return JSONResponse(status_code=500, content={"error": str(e)})
  ```
  If the LLM engine crashes or a tool throws an unhandled exception, FastAPI catches the error and returns a clean `500 Internal Server Error` payload back to the browser instead of letting the server crash.

---

## 9. An Exhaustive, 1000-Line Equivalent Annotated Reference Codebase

Here is a complete, fully annotated implementation showing how all these modules and components connect. You can reference this file structure to see how data flows from classes, decorators, and routers in a real python app:

```python
"""
🎓 INTEGRATION REFERENCE CODEBASE
=================================
This codebase contains a mock implementation of the entire Travel Planner system.
It details every module, class relationship, validation schema, and routing loop.
"""

import os
import json
import datetime
from typing import List, Dict, Any, Optional, Literal, Annotated
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# MODULE 1: CONFIGURATION & LLM LOADING
# [config/config.yaml] and [utils/model_loaders.py]
# ---------------------------------------------------------

class MockConfigLoader:
    """Simulates loading configurations from config.yaml"""
    def __init__(self):
        # Simulated YAML dictionary structures
        self.config_data = {
            "llm": {
                "groq": {
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile"
                },
                "openai": {
                    "provider": "openai",
                    "model": "gpt-4o-mini"
                }
            }
        }

    def __getitem__(self, key: str) -> Any:
        return self.config_data[key]


class MockModelLoader:
    """Handles initialization of the LLM wrapper interfaces"""
    def __init__(self, provider: str = "groq"):
        self.provider = provider
        self.config = MockConfigLoader()

    def load_llm(self) -> "MockLLM":
        """Returns our custom mock LLM configured with model names"""
        if self.provider == "groq":
            model_name = self.config["llm"]["groq"]["model"]
            print(f"[ModelLoader] Initializing ChatGroq using model {model_name}")
            return MockLLM(model_name=model_name, provider="groq")
        else:
            model_name = self.config["llm"]["openai"]["model"]
            print(f"[ModelLoader] Initializing ChatOpenAI using model {model_name}")
            return MockLLM(model_name=model_name, provider="openai")


# ---------------------------------------------------------
# MODULE 2: DATABASE SEARCH UTILITIES
# [utils/place_info_search.py] and [utils/weather_tool.py]
# ---------------------------------------------------------

class GooglePlacesSearchEngine:
    """Mock Google Places API client"""
    def run_query(self, query: str) -> str:
        # Simulating a search query response
        print(f"[GooglePlaces] Querying: {query}")
        if "attractions" in query.lower():
            return "Google Places: 1. Senso-ji Temple (Historical), 2. Tokyo Skytree (Modern Tower)."
        elif "restaurants" in query.lower():
            return "Google Places: 1. Ichiran Ramen, 2. Sukiyabashi Jiro (Sushi)."
        else:
            return "Google Places: Default search details."


class TavilySearchEngine:
    """Mock Tavily Search API client (fallback)"""
    def search(self, query: str) -> str:
        print(f"[TavilySearch] Fallback query running: {query}")
        return f"Tavily Search: Found comprehensive attractions for {query}."


class OpenWeatherMapEngine:
    """Mock Weather API client"""
    def get_forecast(self, city: str) -> dict:
        print(f"[WeatherAPI] Fetching forecast for {city}")
        return {
            "city": city,
            "forecast": [
                {"date": "2026-07-01", "temp": 26.0, "desc": "clear sky"},
                {"date": "2026-07-02", "temp": 24.5, "desc": "scattered clouds"}
            ]
        }


# ---------------------------------------------------------
# MODULE 3: LANGCHAIN CUSTOM TOOLS REGISTRATION
# [tools/place_search_tool.py] and [tools/weather_info_tool.py]
# ---------------------------------------------------------

# Langchain uses Python decorators to register functions as tools
def mock_decorator_tool(func):
    """
    Simulates the @tool decorator.
    It reads the function signature and wraps it in a class.
    """
    class WrappedTool:
        def __init__(self):
            self.name = func.__name__
            self.description = func.__doc__.strip() if func.__doc__ else ""
            self.func = func

        def run(self, *args, **kwargs) -> Any:
            return self.func(*args, **kwargs)

        def __call__(self, *args, **kwargs) -> Any:
            return self.run(*args, **kwargs)

    return WrappedTool()


class PlaceSearchToolWrapper:
    """Wraps place search logic with Google vs Tavily fallbacks"""
    def __init__(self, google_api_key: Optional[str] = None):
        self.google_api_key = google_api_key
        self.google_engine = GooglePlacesSearchEngine() if google_api_key else None
        self.tavily_engine = TavilySearchEngine()

        # Build tools
        self.tools_list = self._setup_tools()

    def _setup_tools(self) -> List[Any]:
        
        @mock_decorator_tool
        def search_attractions(place: str) -> str:
            """Search for attractions in a given place."""
            try:
                if not self.google_api_key:
                    raise ValueError("Google API key missing.")
                # Call Google Places Search
                return self.google_engine.run_query(f"top attractions in {place}")
            except Exception as e:
                # Catch failures and fall back to Tavily
                print(f"[PlaceTool] Google search failed ({e}). Falling back to Tavily.")
                return self.tavily_engine.search(f"attractions in {place}")

        @mock_decorator_tool
        def search_restaurants(place: str) -> str:
            """Search for restaurants in a given place."""
            try:
                if not self.google_api_key:
                    raise ValueError("Google API key missing.")
                return self.google_engine.run_query(f"top restaurants in {place}")
            except Exception as e:
                print(f"[PlaceTool] Google search failed. Falling back to Tavily.")
                return self.tavily_engine.search(f"restaurants in {place}")

        return [search_attractions, search_restaurants]


class WeatherToolWrapper:
    """Wraps weather forecasting tool logic"""
    def __init__(self, api_key: str):
        self.engine = OpenWeatherMapEngine()
        self.tools_list = [self.get_forecast_tool()]

    def get_forecast_tool(self) -> Any:
        @mock_decorator_tool
        def get_weather_forecast(city: str) -> str:
            """Get weather forecast for a city."""
            data = self.engine.get_forecast(city)
            summary = []
            for item in data["forecast"]:
                summary.append(f"{item['date']}: {item['temp']}°C, {item['desc']}")
            return f"Weather forecast for {city}:\n" + "\n".join(summary)
        
        return get_weather_forecast


# ---------------------------------------------------------
# MODULE 4: THE MOCK LLM ENGINE (REASONING LAYER)
# ---------------------------------------------------------

class MockLLM:
    """Simulates ChatOpenAI / ChatGroq API interfaces"""
    def __init__(self, model_name: str, provider: str):
        self.model_name = model_name
        self.provider = provider
        self.bound_tools = []

    def bind_tools(self, tools: List[Any]) -> "MockLLM":
        """Binds tool blueprints to the LLM instance"""
        self.bound_tools = tools
        return self

    def invoke(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simulates the model evaluating prompts and deciding whether to:
        A) Call a tool (if data is missing)
        B) Write the final itinerary text
        """
        # Get the content of the user's latest query
        user_query = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_query = m["content"]
                break

        # Check if we have tool execution results in the history
        has_tool_results = any(m["role"] == "tool" for m in messages)

        # Decides behavior
        if not has_tool_results:
            # First run: We have no tool data. LLM decides to call tools!
            print("[LLM] Reasoning... I need attractions and weather details. Generating tool calls.")
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "search_attractions",
                        "arguments": {"place": "Tokyo"}
                    },
                    {
                        "id": "call_2",
                        "name": "get_weather_forecast",
                        "arguments": {"city": "Tokyo"}
                    }
                ]
            }
        else:
            # Second run: We have tool results! LLM writes the final markdown itinerary.
            print("[LLM] Reasoning... Tool results found! Compiling final travel itinerary.")
            
            # Retrieve tool outputs to reference in the text
            attractions_info = ""
            weather_info = ""
            for m in messages:
                if m["role"] == "tool":
                    if "Weather" in m["content"]:
                        weather_info = m["content"]
                    else:
                        attractions_info = m["content"]

            itinerary_text = (
                f"# 🌍 Your Customized Trip to Tokyo\n\n"
                f"### ⛅ Weather Forecast:\n{weather_info}\n\n"
                f"### 📍 Recommended Attractions:\n{attractions_info}\n\n"
                f"Enjoy your trip!"
            )
            return {
                "role": "assistant",
                "content": itinerary_text,
                "tool_calls": None
            }


# ---------------------------------------------------------
# MODULE 5: THE LANGGRAPH STATE ORCHESTRATION
# [agent/agentic_workflow.py]
# ---------------------------------------------------------

class MockLangGraphApp:
    """Simulates compiled LangGraph Pregel state machine execution"""
    def __init__(self, agent_node_func: Any, tools_list: List[Any]):
        self.agent_node_func = agent_node_func
        # Map tools by their names for quick execution lookup
        self.tools_map = {t.name: t for t in tools_list}

    def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the graph nodes, routing conditions, and edges in a loop
        """
        # 1. Initialize State
        state = {"messages": list(initial_state["messages"])}
        
        # 2. Enter Start Node (routes to 'agent')
        loop_counter = 0
        max_loops = 10
        
        while loop_counter < max_loops:
            loop_counter += 1
            print(f"\n--- LangGraph Loop Step #{loop_counter} ---")
            
            # Run Agent Node
            agent_update = self.agent_node_func(state)
            # Apply reducer (append message to state)
            state["messages"].extend(agent_update["messages"])
            
            last_message = state["messages"][-1]
            
            # Evaluate conditional edge (tools_condition)
            if last_message.get("tool_calls"):
                print("[GraphRouter] Tool calls requested! Routing to 'tools' node.")
                
                # Execute tools node (ToolNode)
                for tool_call in last_message["tool_calls"]:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["arguments"]
                    tool_id = tool_call["id"]
                    
                    # Fetch Python tool
                    active_tool = self.tools_map[tool_name]
                    print(f"[ToolNode] Executing python function '{tool_name}' with args {tool_args}")
                    
                    # Execute tool function
                    result_str = active_tool(**tool_args)
                    
                    # Create ToolMessage and append to state
                    tool_message = {
                        "role": "tool",
                        "content": result_str,
                        "tool_call_id": tool_id
                    }
                    state["messages"].append(tool_message)
                
                # Loop back to agent node
                continue
            else:
                # No tool calls generated -> route to END
                print("[GraphRouter] No tool calls requested. Routing to END.")
                break
                
        return state


class GraphBuilder:
    """Builds and compiles our state workflow graph"""
    def __init__(self, provider: str = "groq", google_key: Optional[str] = None):
        self.model_loader = MockModelLoader(provider=provider)
        self.llm = self.model_loader.load_llm()
        
        # Instantiate tool wrappers
        self.place_tools = PlaceSearchToolWrapper(google_api_key=google_key)
        self.weather_tools = WeatherToolWrapper(api_key="mock_weather_key")
        
        # Register tools
        self.tools = []
        self.tools.extend(self.place_tools.tools_list)
        self.tools.extend(self.weather_tools.tools_list)
        
        # Bind tools to our model
        self.llm.bind_tools(self.tools)

    def agent_function(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node function representing our LLM executor"""
        system_prompt = {
            "role": "system",
            "content": "You are a helpful travel planner. You must search attractions and weather."
        }
        history = state["messages"]
        full_payload = [system_prompt] + history
        
        # Invoke LLM
        response = self.llm.invoke(full_payload)
        return {"messages": [response]}

    def build_graph(self) -> MockLangGraphApp:
        """Compiles the StateGraph"""
        # Returns a compiled application simulator
        return MockLangGraphApp(
            agent_node_func=self.agent_function,
            tools_list=self.tools
        )


# ---------------------------------------------------------
# MODULE 6: SAVE TO DOCUMENT UTILITY
# [utils/save_to_document.py]
# ---------------------------------------------------------

class DocumentSaver:
    """Simulates writing markdown documents to outputs/ directory"""
    @staticmethod
    def save(text: str) -> str:
        os.makedirs("./outputs", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%H-%M-%S")
        filename = f"./outputs/Trip_Plan_{timestamp}.md"
        
        with open(filename, "w", encoding="utf-8") as file:
            file.write(text)
            
        print(f"[DocumentSaver] Saved file successfully at: {filename}")
        return filename


# ---------------------------------------------------------
# MODULE 7: THE FASTAPI SERVER
# [main.py]
# ---------------------------------------------------------

app = FastAPI()

# Config parameters
GOOGLE_KEY = "mock_google_key"  # Set to None to simulate Tavily fallbacks

@app.post("/query")
async def handle_request(question: str):
    """
    REST Endpoint representing the entry point of the backend system
    """
    print(f"\n[FastAPI] HTTP POST received. User Question: '{question}'")
    
    # 1. Initialize Graph Builder
    builder = GraphBuilder(provider="groq", google_key=GOOGLE_KEY)
    react_app = builder.build_graph()
    
    # 2. Package initial question into state format
    initial_messages = [{"role": "user", "content": question}]
    
    # 3. Invoke LangGraph loop
    final_state = react_app.invoke({"messages": initial_messages})
    
    # 4. Extract final AI response
    final_ai_response = final_state["messages"][-1]["content"]
    
    # 5. Save document to output folder
    saved_file_path = DocumentSaver.save(final_ai_response)
    
    # 6. Return response to HTTP Client
    return {
        "status": "success",
        "answer": final_ai_response,
        "saved_file": saved_file_path
    }


# ---------------------------------------------------------
# EXECUTION SIMULATOR (CLI Simulation)
# This simulates Streamlit triggering the endpoint
# ---------------------------------------------------------

if __name__ == "__main__":
    # We simulate running the FastAPI server and making a call to it.
    import asyncio
    
    async def simulate_streamlit_call():
        print("==================================================")
        print("🚀 RUNNING FULL END-TO-END FLOW SIMULATION")
        print("==================================================")
        
        # Call the endpoint handler directly
        response = await handle_request("Plan a trip to Tokyo.")
        
        print("\n==================================================")
        print("🎉 RESPONSE RECEIVED BY STREAMLIT FRONTEND")
        print("==================================================")
        print(f"Status: {response['status']}")
        print(f"Saved Path: {response['saved_file']}")
        print(f"Final Answer Content:\n{response['answer']}")
        print("==================================================")

    asyncio.run(simulate_streamlit_call())
```
