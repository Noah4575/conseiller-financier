from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END  # type: ignore
from langgraph.checkpoint.memory import MemorySaver  # type: ignore
from functools import partial

import os
import streamlit as st
from dotenv import load_dotenv
from llm.core import State
from tools.simul_credit import simul_credit
from rag.retriever import retrieve, setup_hybrid_retriever, initialize_embeddings

# --- 1. Core Setup and Initialization ---
# Load environment variables
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = os.environ.get("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_API_KEY"] = os.environ.get("LANGCHAIN_API_KEY")

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
        ("system", "Tu es un conseiller financier expert et dédié de Société "
            "Générale Côte d'Ivoire (SGCI). Ta clientèle est 'High-Net-Worth' "
            "(Haut de gamme). Tu dois être courtois, précis et professionnel. "
            "Ton périmètre d'expertise couvre TOUS les produits SGCI : "
            "1. **Banque au quotidien** : Gestion de comptes courants, "
            "cartes Visa (Gold, Infinite), virements internationaux. "
            "2. **Épargne & Placements** : DAT (Dépôts à Terme), Comptes "
            "Épargne, FCP (Fonds Communs de Placement sur la BRVM). "
            "3. **Assurances** : Assurance vie, protection des moyens "
            "de paiement, assurance voyage. "
            "4. **Crédits** : Immobilier et Consommation. "
            "RÈGLES IMPORTANTES : "
            "- Soit précis et explique bien les produits SGCI adaptés aux "
            "besoins exprimés par l'utilisateur. "
            "- Si l'utilisateur te demande explicitement une simulation de "
            "crédit, utilise l'outil `simul_credit` UNIQUEMENT si "
            "tu as les 3 infos : revenus mensuels, montant, durée. "
            "- Si l'utilisateur pose une question vague, "
            "demande des précisions sur ses objectifs (rendement, sécurité, "
            " horizon de temps) avant de proposer des produits SGCI. "
            "- La monnaie de référence est le FCFA (Franc CFA). "
            "Ne force pas la vente. Agis comme un partenaire de confiance pour"
            " la gestion de leur patrimoine en Côte d'Ivoire. "
            "- Base-toi sur le contexte suivant pour les infos concernant la "
            "SGCI : {context}."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    tools = [simul_credit]
    tool_map = {tool.name: tool for tool in tools}
    model_with_tools = model.bind_tools(tools)
    chain = prompt | model_with_tools

    def call_model(state: State):
        # On extrait le contexte récupéré par le nœud précédent
        context_docs = state.get("context", [])

        # On transforme les documents en une seule chaîne de texte
        context_text = "\n\n".join([doc.page_content for doc in context_docs])

        # On injecte explicitement ce texte dans l'appel de la chaîne
        # La chaîne utilisera alors context_text pour remplir {context} 
        response = chain.invoke({
            "messages": state["messages"],
            "context": context_text
        })
        return {"messages": response}

    def execute_tools(state: State):
        last_message = state["messages"][-1]
        tool_messages = []
        for tool_call in last_message.tool_calls:
            tool_func = tool_map[tool_call["name"]]
            output = tool_func.invoke(tool_call["args"])
            tool_messages.append(ToolMessage(content=str(output),
                                             tool_call_id=tool_call["id"]))
        return {"messages": tool_messages}

    def should_continue(state: State):
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    embeddings = initialize_embeddings()
    hybrid_retriever = setup_hybrid_retriever(embeddings)

    retrieve_node = partial(
        retrieve,
        hybrid_retriever=hybrid_retriever
    )

    workflow = StateGraph(State)
    workflow.add_node("model", call_model)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("tools", execute_tools)
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "model")
    workflow.add_conditional_edges("model", should_continue, {"tools": "tools",
                                                              END: END})
    workflow.add_edge("tools", "model")

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    return app
