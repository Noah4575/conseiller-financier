import os
import asyncio
import streamlit as st
from typing import Sequence, Annotated, TypedDict
from dotenv import load_dotenv

# Import necessary LangChain/LangGraph components
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool

# --- 1. Core Setup and Initialization ---

# Load environment variables
load_dotenv()
# Required for tracing and API access
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

# Streamlit App Configuration
st.set_page_config(page_title="Conseiller Financier IA", layout="wide")
st.title("👨‍💼 Conseiller Financier IA (Crédit)")


# Initialize the Gemini model (using st.cache_resource for efficiency)
@st.cache_resource
def initialize_model():
    """Initializes the LLM and the LangGraph application."""
    try:
        model = init_chat_model("gemini-2.5-flash-lite",
                                model_provider="google_genai")
    except Exception as e:
        st.error(f"Erreur d'initialisation du modèle: {e}."
                 "Vérifiez votre GOOGLE_API_KEY.")
        st.stop()

    # --- Tool Definition (Copied from app.py) ---
    @tool
    def simul_credit(revenus: int, montant: int, duree: int):
        """Trouve si un crédit est réalisable en fonction des revenus,
        du montant et de la durée.
        revenus: revenus mensuels
        montant: montant du crédit
        duree: durée du crédit en années
        Retourne un message indiquant si le crédit est réalisable ou non.
        """
        tx_interet = 0.035
        r_div_n = tx_interet / 12
        n_times_t = -duree * 12
        mensualite = (montant * r_div_n) / (1 - (1 + r_div_n) ** n_times_t)
        quot_cessible = revenus * 0.42
        tx_endettement = mensualite/revenus
        disp_mensuel = revenus - quot_cessible
        tx_assurance = 0.011
        nbr_paiements_an = 12
        tx_tps = 0.1

        if mensualite > quot_cessible:
            return (f"Le montant de la mensualité : {mensualite:.2f}, dépasse la quotité cessible : "
                    f"{quot_cessible:.2f}. Crédit non réalisable.")
        else:
            return f"Crédit réalisable avec une mensualité de {mensualite:.2f}"

    # --- LangGraph Setup (Copied from app.py) ---
    class State(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        language: str

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Tu es un conseiller financier expert et polyvalent pour "
         "clients fortunés."
         "Tes objectifs:"
         "1. Répondre aux questions générales sur la finance, la bourse, et "
         "l'économie."
         "2. SI (et seulement si) l'utilisateur parle de projet immobilier ou"
         " d'emprunt, utilise l'outil 'simul_credit'."
         "3. Pour utiliser 'simul_credit', tu dois collecter 3 infos: revenus,"
         " montant, durée."
         "Ton ton doit être professionnel, calme et tu parles en {language}."
         " Ne force pas la conversation vers le crédit si ce n'est "
         "pas le sujet."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    tools = [simul_credit]
    tool_map = {tool.name: tool for tool in tools}
    model_with_tools = model.bind_tools(tools)
    chain = prompt | model_with_tools

    async def call_model(state: State):
        response = await chain.ainvoke(state)
        return {"messages": response}

    def execute_tools(state: State):
        last_message = state["messages"][-1]
        tool_messages = []
        for tool_call in last_message.tool_calls:
            tool_func = tool_map[tool_call["name"]]
            output = tool_func.invoke(tool_call["args"])
            tool_messages.append(ToolMessage(content=str(output), tool_call_id=tool_call["id"]))
        return {"messages": tool_messages}

    def should_continue(state: State):
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(State)
    workflow.add_node("model", call_model)
    workflow.add_node("tools", execute_tools)
    workflow.add_edge(START, "model")
    workflow.add_conditional_edges("model", should_continue, {"tools": "tools",
                                                              END: END})
    workflow.add_edge("tools", "model")

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    return app


# Initialize the LangGraph application
app = initialize_model()

# --- 2. Chat History Management (State) ---

# Initialize chat history in Streamlit session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content="Bonjour! Je suis votre conseiller financier expert."
                  " Comment puis-je vous aider avec vos projets de crédit "
                  "ce soir ?")
    ]
if "thread_id" not in st.session_state:
    # Use a fixed thread ID for persistent memory across the session
    st.session_state.thread_id = "stream_session_123"
# Updated stream_response for streamlit_app.py


def stream_response(prompt_text):
    """Generates and streams the response, handling multi-step tool execution."""
    
    # 1. Prepare inputs
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    input_messages = [HumanMessage(content=prompt_text)]
    inputs = {"messages": input_messages, "language": "Français"}

    # 2. Get the async generator
    async_generator = app.astream(inputs, config, stream_mode="values")

    def response_generator():
        # Create a clean event loop for this interaction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def get_next_chunk():
            try:
                return await async_generator.__anext__()
            except StopAsyncIteration:
                return None

        try:
            while True:
                # Fetch the next step from the graph
                event = loop.run_until_complete(get_next_chunk())
                
                if event is None:
                    break

                if "messages" in event:
                    message = event["messages"][-1]
                    
                    # CASE 1: The model is responding to the user (Final Answer)
                    if isinstance(message, AIMessage) and message.content and not message.tool_calls:
                        yield message.content
                    
                    # CASE 2: The model requested a tool (Intermediate Step)
                    # We do NOT yield here, we just let the loop continue. 
                    # LangGraph will automatically execute the tool and cycle back 
                    # to the model in the NEXT iteration of this 'while' loop.
                    elif isinstance(message, AIMessage) and message.tool_calls:
                        # Optional: Yield a status update to the user
                        # yield "\n*Analysing data...*\n" 
                        pass 

        except Exception as e:
            st.error(f"Error streaming response: {e}")
        finally:
            loop.close()

    return response_generator

# --- 4. Streamlit UI Loop ---
# Display existing messages
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

# Handle user input
if prompt := st.chat_input("Posez votre question sur le crédit..."):
    # 1. Add user message to history and display
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Display assistant response
    with st.chat_message("assistant"):
        # Use st.write_stream to display the response chunks as they arrive
        full_response = st.write_stream(stream_response(prompt))

    # 3. Save the full final AIMessage to history
    # NOTE: LangGraph's checkpointer handles saving the full history to memory
    # We only save the final displayed message for the Streamlit history display
    st.session_state.messages.append(AIMessage(content=full_response))
