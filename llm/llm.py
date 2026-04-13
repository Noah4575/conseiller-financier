from datetime import datetime

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END  # type: ignore
from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
import sqlite3
from functools import partial

import os
import streamlit as st
from dotenv import load_dotenv
from llm.core import State
from llm.prompt import SYSTEM_PROMPT
from tools.simul_credit import (simul_credit, simul_emprunt_max,
                                simul_credit_immo)
from tools.simul_placements import (simul_credimatic, simul_dat, simul_car8,
                                    simul_sogeprimo, simul_pel)
from rag.retriever import retrieve, setup_retriever
from rag.retriever import initialize_embeddings


# --- 1. Core Setup and Initialization ---
# Load environment variables
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = os.environ.get(  # type: ignore
    "LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_API_KEY"] = os.environ.get(  # type: ignore
    "LANGCHAIN_API_KEY")


@st.cache_resource
def _get_llm():
    """Charge le modèle principal une seule fois."""
    try:
        return init_chat_model("gemini-2.5-flash-lite",
                               model_provider="google_genai")
    except Exception as e:
        st.error(f"Erreur d'initialisation du modèle: {e}."
                 "Vérifiez votre GOOGLE_API_KEY.")
        st.stop()


@st.cache_resource
def _get_title_llm():
    """Modèle léger dédié à la génération de titres, mis en cache."""
    return init_chat_model("gemini-2.5-flash-lite",
                           model_provider="google_genai")


@st.cache_resource
def _get_tools():
    """Retourne la liste des tools et leur mapping."""
    tools = [
        simul_credit, simul_emprunt_max, simul_credit_immo,
        simul_dat, simul_car8, simul_credimatic, simul_sogeprimo, simul_pel
    ]
    tool_map = {tool.name: tool for tool in tools}
    return tools, tool_map


@st.cache_resource
def _get_memory():
    """Ouvre la connexion SQLite et retourne le checkpointer."""
    conn = sqlite3.connect("database/checkpoints.db", check_same_thread=False)
    return SqliteSaver(conn)


@st.cache_resource
def _get_retriever():
    """Charge les index FAISS une seule fois."""
    embeddings = initialize_embeddings()
    return setup_retriever(embeddings)


@st.cache_resource
def _build_chain():
    """Assemble le prompt + modèle + tools."""
    model = _get_llm()
    tools, _ = _get_tools()
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    model_with_tools = model.bind_tools(tools)
    return prompt | model_with_tools


# Initialize the Gemini model (using st.cache_resource for efficiency)
@st.cache_resource
def initialize_model(_chain, _tool_map, _memory, _retriever):
    """Assemble le graph Langchain à partir des composants cachés."""

    def should_continue(state: State):
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    call_node = partial(
        call_model,
        chain=_chain
    )

    retrieve_node = partial(
        retrieve,
        retriever=_retriever
    )

    tools_node = partial(
        execute_tools,
        tool_map=_tool_map
    )

    workflow = StateGraph(State)
    workflow.add_node("model", call_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("tools", tools_node)
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "model")
    workflow.add_conditional_edges("model", should_continue, {"tools": "tools",
                                                              END: END})
    workflow.add_edge("tools", "model")

    app = workflow.compile(checkpointer=_memory)

    return app


def call_model(state: State, chain):
    # On extrait le contexte récupéré par le nœud précédent
    context_docs = state.get("context", [])
    context_text = "\n\n".join([doc.page_content for doc in context_docs])

    profile = state.get("user_profile", {})
    revenus = (profile.get("revenus")
               if profile.get("revenus") is not None else 0)
    solde = (profile.get("solde")
             if profile.get("solde") is not None else 0)

    # On injecte explicitement ce texte dans l'appel de la chaîne
    # La chaîne utilisera alors context_text pour remplir {context}
    produits = profile.get("produits", [])
    produits_str = (", ".join(produits) if produits
                    else "Aucun")
    response = chain.invoke({
        "messages": state["messages"],
        "context": context_text,
        "nom": profile.get("nom"),
        "prénom": profile.get("prénom"),
        "segment": profile.get("segment"),
        "revenus": str(revenus),
        "solde": str(solde),
        "produits": produits_str
        })
    return {"messages": response}


def execute_tools(state: State, tool_map):
    last_message = state["messages"][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:  # type: ignore
        tool_func = tool_map[tool_call["name"]]
        output = tool_func.invoke(tool_call["args"])
        tool_messages.append(ToolMessage(content=str(output),
                                         tool_call_id=tool_call["id"]))
    return {"messages": tool_messages}


def generate_conv_title(first_human_msg, first_ai_msg):
    """Génère un titre de conversation à partir du premier échange."""
    try:
        model = _get_title_llm()
        prompt = (
            "En te basant sur cet échange, génère un titre de conversation "
            "très court (5 mots maximum), en français, sans guillemets, "
            "sans ponctuation finale.\n\n"
            f"Client : {first_human_msg[:500]}\n"
            f"Conseiller : {first_ai_msg[:500]}\n\n"
            "Titre :"
        )
        response = model.invoke(prompt)
        title = response.content.strip().strip('"').strip("'")  # type: ignore
        return title[:60]  # Sécurité : tronque si trop long
    except Exception:
        return f"Discussion du {
            datetime.now().strftime('%d/%m %H:%M')}"
