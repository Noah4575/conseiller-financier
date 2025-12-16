import os
import asyncio
from typing import Sequence, Annotated, TypedDict
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool

# --- 1. Environment and Initialization ---
load_dotenv()

# Required for tracing and API access
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

# Initialize the Gemini model
model = init_chat_model("gemini-2.5-flash-lite", model_provider="google_genai")


# --- 2. Tool Definition ---
@tool
def simul_credit(revenus: int, montant: int, duree: int):
    """Trouve si un crédit est réalisable en fonction des revenus, du montant et de la durée.
    revenus: revenus mensuels en euros
    montant: montant du crédit en euros
    duree: durée du crédit en années
    Retourne un message indiquant si le crédit est réalisable ou non.
    """
    taux = 0.035  # Taux d'intérêt fixe de 3.5%
    # Monthly payment formula
    mensualite = (montant * taux / 12) / (1 - (1 + taux / 12) ** (-duree * 12))
    quot_cessible = revenus * 0.42

    if mensualite > quot_cessible:
        return (f"Le montant de la mensualité : {mensualite:.2f}€, "
                "dépasse la quotité cessible : "
                f"{quot_cessible:.2f}€. Crédit non réalisable.")
    else:
        return f"Crédit réalisable avec une mensualité de {mensualite:.2f} €"


# Mapping for the tool executor node
tools = [simul_credit]
tool_map = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)


# --- 3. Graph State and Chain ---
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str


prompt = ChatPromptTemplate.from_messages([
    ("system", "Tu es un conseiller financier expert (High-Net-Worth). "
     "Réponds en {language}. Utilise l'outil simul_credit pour aider à évaluer"
     " les demandes de crédit. Demande toujours son revenus mensuels, le"
     " montant du crédit et la durée en années."),
    MessagesPlaceholder(variable_name="messages"),
])

# Define the chain (returns the full AIMessage object for tool detection)
chain = prompt | model_with_tools


# --- 4. Graph Nodes and Logic ---
async def call_model(state: State):
    """Node: Calls the LLM to generate a response or tool call."""
    response = await chain.ainvoke(state)
    return {"messages": response}


def execute_tools(state: State):
    """Node: Executes requested tools and returns ToolMessages."""
    last_message = state["messages"][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_func = tool_map[tool_call["name"]]
        output = tool_func.invoke(tool_call["args"])
        tool_messages.append(ToolMessage(content=str(output),
                                         tool_call_id=tool_call["id"]))
    return {"messages": tool_messages}


def should_continue(state: State):
    """Conditional Edge: Determines if tools should be called or not."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


# --- 5. Graph Assembly ---
workflow = StateGraph(State)

workflow.add_node("model", call_model)
workflow.add_node("tools", execute_tools)

workflow.add_edge(START, "model")
workflow.add_conditional_edges("model", should_continue, {"tools": "tools",
                                                          END: END})
workflow.add_edge("tools", "model")

# Compile with memory persistence
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)


# --- 6. Execution Entry Point ---
async def run_chat(query: str, thread_id: str = "abc1234"):
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=query)], "language": "Français"}

    print("\n🤖 **Response:**", end=" ", flush=True)
    async for event in app.astream(inputs, config, stream_mode="values"):
        if "messages" in event:
            message = event["messages"][-1]
            # Print text content as it arrives (ignoring tool call requests)
            if isinstance(message, AIMessage) and message.content:
                print(message.content, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    # Example usage
    user_query = "Bonjour, je gagne 5000€ par mois et je veux emprunter"
    "200000€ sur 20 ans."
    asyncio.run(run_chat(user_query))