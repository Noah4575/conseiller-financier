from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph.message import add_messages  # type: ignore
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

import os
import streamlit as st
from typing import Sequence, Annotated, TypedDict
from dotenv import load_dotenv
from llm.core import State
from tools.simul_credit import simul_credit
# --- 1. Core Setup and Initialization ---

# Load environment variables
load_dotenv()
# Required for tracing and API access
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")


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

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Tu es un conseiller financier expert et dédié d'une banque de Côte d'Ivoire.
            Ta clientèle est "High-Net-Worth" (Haut de gamme). Tu dois être courtois, précis et professionnel.

            Ton périmètre d'expertise couvre TOUS les produits SGCI :
            1. **Banque au quotidien** : Gestion de comptes courants, cartes Visa (Gold, Infinite), virements internationaux.
            2. **Épargne & Placements** : DAT (Dépôts à Terme), Comptes Épargne, FCP (Fonds Communs de Placement sur la BRVM).
            3. **Assurances** : Assurance vie, protection des moyens de paiement, assurance voyage.
            4. **Crédits** : Immobilier et Consommation.

            RÈGLES IMPORTANTES :
            - Si l'utilisateur parle de crédit, propose de faire une simulation.
            - Pour la simulation, utilise l'outil `simul_credit` UNIQUEMENT si tu as les 3 infos : revenus mensuels, montant, durée.
            - Si l'utilisateur pose une question vague (ex: "Je veux investir"), demande des précisions sur ses objectifs (rendement, sécurité, horizon de temps) avant de proposer des produits SGCI.
            - La monnaie de référence est le FCFA (Franc CFA).

            Ne force pas la vente. Agis comme un partenaire de confiance pour la gestion de leur patrimoine en Côte d'Ivoire.
            """),
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