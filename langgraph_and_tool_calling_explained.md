# 🎓 The Ultimate Guide to LangGraph, LangChain Tool Calling & FastAPI (ELI5 Edition)

If you have ever felt confused about how an AI "calls" a Python function, how LangGraph remembers what happened, or how FastAPI connects to everything, **this guide is for you.** 

We are going to break down every single concept using simple analogies (explaining it like you are 5), followed by detailed code flows and explanations showing exactly how data travels through your project.

---

## 📂 Table of Contents
1. [The Big Picture: The Sandbox & The Helpers (ELI5)](#1-the-big-picture-the-sandbox--the-helpers-eli5)
2. [What is "Tool Binding" under the hood?](#2-what-is-tool-binding-under-the-hood)
3. [How the AI Decides which tool to call](#3-how-the-ai-decides-which-tool-to-call)
4. [How LangGraph Takes data from FastAPI and runs the loop](#4-how-langgraph-takes-data-from-fastapi-and-runs-the-loop)
5. [Complete Mini-Project Code Walkthrough (Annotated line-by-line)](#5-complete-mini-project-code-walkthrough-annotated-line-by-line)

---

## 1. The Big Picture: The Sandbox & The Helpers (ELI5)

Let's start with a story. Imagine a kid named **Chef AI** sitting in a sandbox:

* **Chef AI** is super smart and can write recipes, but they are blindfolded and cannot leave the sandbox. They don't know the temperature outside, they don't have a calculator, and they can't see what toys are in the backyard.
* Next to the sandbox stands **FastAPI (The Walkie-Talkie)**. A customer calls on the walkie-talkie and says: *"Hey, Chef AI! I want to plan a outdoor picnic today. What should I cook, and how much will it cost in local coins?"*
* FastAPI writes this question down and drops it into Chef AI's sandbox.

Now Chef AI has a problem: 
1. They don't know if it will rain today (no weather access).
2. They don't know the price of bread (no search access).
3. They are bad at multiplying numbers (no calculator).

To solve this, we give Chef AI **four buttons (Tools)** connected to wires:
* **Button 1 (Weather Tool)**: Runs a thermometer script.
* **Button 2 (Places Tool)**: Runs an internet search script.
* **Button 3 (Currency Tool)**: Checks coin exchange rates.
* **Button 4 (Calculator Tool)**: Runs Python's math engine.

```
[Customer] ──(Ask Question)──> [FastAPI (Walkie-Talkie)]
                                      │
                                      ▼ (Starts Loop)
                              [Chef AI (LLM)]
                                 │       ▲
          (Wants Weather)        │       │ (Here is the weather!)
          Presses Button 1 ──────▼       │
                          [Python Script (Tool Node)]
```

### The Dance:
1. Chef AI reads the user's query: *"Plan a picnic."*
2. Chef AI thinks: *"I need the weather."*
3. Instead of guessing, Chef AI **presses Button 1 (Weather Tool)**. This is called a **Tool Call**.
4. The wire runs, executes a Python function `get_weather()`, and throws the result back into the sandbox: *"It is 25°C and Sunny!"*
5. Chef AI reads this report, thinks for a second, and writes the final recipe: *"Plan a picnic because it is sunny! It will cost $15."*
6. FastAPI picks up the final paper and reads it back to the customer on the walkie-talkie.

---

## 2. What is "Tool Binding" under the hood?

When you write this in your code:
```python
self.llm_with_tools = self.llm.bind_tools(tools=self.tools)
```
What is actually happening? 

Remember, the LLM (like Groq's Llama-3 or OpenAI's GPT) is just a server running on the internet. It does not know anything about your local Python files. It cannot see your code.

### Step A: Reflection (Reading the function)
Langchain looks at your python function:
```python
@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Converts a monetary value from one currency to another."""
    return amount * 0.92
```
Using Python's reflection, Langchain inspects this function and auto-generates a **JSON Schema** description that looks like this:

```json
{
  "name": "convert_currency",
  "description": "Converts a monetary value from one currency to another.",
  "parameters": {
    "type": "object",
    "properties": {
      "amount": {
        "type": "number",
        "description": "The amount of money to convert"
      },
      "from_currency": {
        "type": "string",
        "description": "The source currency code"
      },
      "to_currency": {
        "type": "string",
        "description": "The target currency code"
      }
    },
    "required": ["amount", "from_currency", "to_currency"]
  }
}
```

### Step B: Sending the Schemas
When you call the LLM, Langchain packs up your system prompt, your user question, **and this list of JSON schemas**, and sends them over the network as a single request. 

Essentially, you are saying to the LLM: 
> *"Here is the user's question. By the way, if you need to, you are allowed to request a call to this function named `convert_currency`. Here are the parameters it needs."*

This is **Tool Binding**. You are attaching the blueprints of your Python code to the LLM's instructions.

---

## 3. How the AI Decides which tool to call

The AI model (the LLM) is a text predictor. How does it transition from predicting text to calling a tool?

1. **Reading the System Prompt**: The system prompt tells the AI: *"You must search for attractions before writing the plan. If you calculate budgets, you must use the calculator tool."*
2. **Identifying Missing Data**: The user asks: *"Plan a trip to Paris. My budget is $500 USD. How much is that in Euros?"*
3. **Scanning the Blueprints**: The LLM scans the JSON schemas we sent (under Step B). It notices the tool `convert_currency` matches the description *"Converts a monetary value from one currency to another."*
4. **Generating the Tool Call Request**: Instead of outputting normal text like *"Sure, let me convert that..."*, the LLM's neural network generates a **structured output block** indicating it wants to execute a tool.

The response from the LLM looks like this:
```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "convert_currency",
        "arguments": "{\"amount\": 500.0, \"from_currency\": \"USD\", \"to_currency\": \"EUR\"}"
      }
    }
  ]
}
```

---

## 4. How LangGraph Takes data from FastAPI and runs the loop

Let's trace how the data travels from your FastAPI endpoint into the LangGraph loop and back.

### Step 1: FastAPI receives request
In `main.py`, a user triggers the POST endpoint:
```python
@app.post("/query")
async def query_travel_agent(query: QueryRequest):
    ...
```
FastAPI validates the inputs, creates our compiled LangGraph `react_app` engine, and calls:
```python
output = react_app.invoke({"messages": [HumanMessage(content=prompt)]})
```
This is where the data leaves FastAPI and enters the LangGraph sandbox.

### Step 2: The LangGraph State initialization
LangGraph initializes the state dictionary. In our code, we use `MessagesState`. 
```python
# Initial State
state = {
    "messages": [
        HumanMessage(content="What is the weather in Tokyo and convert $100 to Yen?")
    ]
}
```

### Step 3: Node `"agent"` runs
LangGraph executes the `"agent"` node which calls `agent_function(state)`:
1. It takes the system instructions (instructions on budget, style).
2. It prepends it to the chat history: `[SystemMessage] + [HumanMessage]`.
3. It calls `self.llm_with_tools.invoke(user_input)`.
4. The LLM returns a response requesting **two parallel tool calls**:
   * Tool 1: `get_current_weather(city="Tokyo")`
   * Tool 2: `convert_currency(amount=100.0, from_currency="USD", to_currency="JPY")`
5. The node returns `{"messages": [AIMessage(tool_calls=[...])]}`. LangGraph appends this message to the state history.

### Step 4: The Routing Edge (`tools_condition`)
After `"agent"` finishes, LangGraph looks at the conditional edge:
```python
graph_builder.add_conditional_edges("agent", tools_condition)
```
* `tools_condition` reads the last message in `state["messages"]`.
* It sees the `tool_calls` parameter is populated.
* It routes the execution flow to the `"tools"` node.

### Step 5: Node `"tools"` runs (`ToolNode`)
The `ToolNode` receives the state.
1. It reads the `tool_calls` list:
   * It sees `get_current_weather(city="Tokyo")`. It matches the name `"get_current_weather"` to our Python function, executes it, and gets: `"24°C, Cloudy"`.
   * It sees `convert_currency(amount=100, ...)`. It matches it to our Python function, executes it, and gets: `15800.0`.
2. It packages these results into two `ToolMessage` objects and appends them to the state:
```python
[
  ToolMessage(content="Current weather in Tokyo: 24°C, Cloudy", tool_call_id="call_1"),
  ToolMessage(content="15800.0", tool_call_id="call_2")
]
```

### Step 6: Loop back to `"agent"`
Once the tools finish, the graph follows the static edge:
```python
graph_builder.add_edge("tools", "agent")
```
Control goes back to the `"agent"` node.
1. The `"agent"` node invokes the LLM again, sending the updated state:
   * System Prompt
   * Human Query: *"What is the weather in Tokyo and convert $100 to Yen?"*
   * AI Tool Request message
   * Tool Outputs: Tokyo is 24°C, $100 = 15800 Yen.
2. The LLM reads this entire log. It realizes it has all the data requested!
3. It generates the final text: *"The current weather in Tokyo is 24°C and cloudy. $100 USD converts to approximately 15,800 Japanese Yen."*
4. Because the LLM did not generate any more tool calls, `tools_condition` routes the graph to `END`.

### Step 7: Return to FastAPI
The `invoke()` method completes and returns the final state to `main.py`.
`main.py` extracts the last message content (`final_output`), saves it using `save_document()`, and returns it as a JSON API response to the Streamlit UI!

---

## 5. Complete Mini-Project Code Walkthrough (Annotated line-by-line)

Here is a complete, runnable script representing a miniature version of our project. It contains FastAPI, LangChain, and LangGraph tool calling working together in one file. 

Read the comments carefully to see exactly how variables and data flow between nodes:

```python
import os
from typing import List, Literal, Optional, Any
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

# Import LangChain components
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_groq import ChatGroq
from langchain.tools import tool

# Import LangGraph components
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode, tools_condition

# Load our .env file containing our API keys (like GROQ_API_KEY)
load_dotenv()

# ==========================================
# PHASE 1: DEFINE OUR CUSTOM TOOLS
# ==========================================

@tool
def check_weather(city: str) -> str:
    """
    Get the current weather forecast for a specified city.
    Use this tool whenever the user asks about the weather or temperature.
    """
    # In a real app, this calls requests.get() to OpenWeatherMap.
    # Here we simulate the return value.
    if city.lower() == "tokyo":
        return "25 degrees Celsius, sunny with light winds."
    elif city.lower() == "london":
        return "15 degrees Celsius, light drizzle and overcast."
    else:
        return f"20 degrees Celsius, partly cloudy in {city}."

@tool
def convert_usd_to_eur(amount: float) -> float:
    """
    Converts a currency amount from US Dollars (USD) to Euros (EUR).
    Use this tool whenever a user asks to calculate costs in Euros.
    """
    exchange_rate = 0.92
    return amount * exchange_rate


# ==========================================
# PHASE 2: THE STATEGRAPH ORCHESTRATOR
# ==========================================

class MiniAgentOrchestrator:
    def __init__(self):
        # 1. Initialize the LLM (using Groq Llama-3 model)
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
        
        # 2. Compile our tool definitions into a list
        self.tools = [check_weather, convert_usd_to_eur]
        
        # 3. BIND TOOLS: Tell the LLM that these tools exist.
        # This converts our python functions into JSON Schemas and passes them to the LLM configurations.
        self.llm_with_tools = self.llm.bind_tools(tools=self.tools)
        
        # 4. Define the System Prompt
        self.system_prompt = SystemMessage(
            content=(
                "You are a helpful travel assistant. You have access to tools for weather "
                "checking and currency conversion. You MUST call these tools if the user's "
                "request requires live data. Once you receive tool responses, summarize them clearly."
            )
        )
        
        # 5. Build the LangGraph workflow
        self.graph = self._build_workflow()

    def agent_node(self, state: MessagesState):
        """
        The Agent Node Function.
        This function runs when the graph enters the 'agent' node.
        It takes the current messages from the state, runs the LLM, and returns the response.
        """
        # Get the full chat message history from the graph state
        history = state["messages"]
        
        # Combine the static system instructions with the conversation history
        full_prompt = [self.system_prompt] + history
        
        # Call the LLM bound with tools
        response = self.llm_with_tools.invoke(full_prompt)
        
        # Return a dictionary updating the state (appending the AI response)
        return {"messages": [response]}

    def _build_workflow(self) -> Any:
        """Constructs and compiles the LangGraph StateGraph."""
        
        # Initialize a new StateGraph governed by MessagesState (holds list of messages)
        builder = StateGraph(MessagesState)
        
        # Add our Nodes
        # Node 'agent' runs our agent_node function
        builder.add_node("agent", self.agent_node)
        
        # Node 'tools' runs our python tools automatically using LangGraph's ToolNode helper
        builder.add_node("tools", ToolNode(tools=self.tools))
        
        # Set the entrance edge: When the graph starts, go straight to the 'agent'
        builder.add_edge(START, "agent")
        
        # Set the routing edge: After 'agent' node runs, execute 'tools_condition'
        # - If LLM generated tool calls -> route to 'tools'
        # - If LLM generated final answer -> route to END
        builder.add_conditional_edges("agent", tools_condition)
        
        # Connect the tools node back to the agent: Once tools run, go back to the LLM
        builder.add_edge("tools", "agent")
        
        # Compile the graph structure
        return builder.compile()

    def run(self, user_question: str) -> str:
        """
        Invokes the state machine with the user's question.
        """
        # Pack the user input into a HumanMessage object inside the state dictionary
        initial_state = {"messages": [HumanMessage(content=user_question)]}
        
        # Execute the compiled graph
        final_state = self.graph.invoke(initial_state)
        
        # Extract the content of the final AI message from the state history
        final_answer = final_state["messages"][-1].content
        return final_answer


# ==========================================
# PHASE 3: THE FASTAPI SERVER
# ==========================================

# Instantiate the FastAPI app
app = FastAPI()

# Instantiate our orchestrator class (runs once on startup)
orchestrator = MiniAgentOrchestrator()

# Define our query Pydantic request schema
class UserRequest(BaseModel):
    question: str

@app.post("/query")
async def handle_query(request: UserRequest):
    """
    API Route endpoint that receives requests and runs the LangGraph loop.
    """
    try:
        # Run our LangGraph workflow on the input question
        answer = orchestrator.run(request.question)
        
        # Return the final compiled text back to the HTTP client (like Streamlit)
        return {"status": "success", "answer": answer}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# To run this app locally:
# uvicorn filename:app --reload
```
