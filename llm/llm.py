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
from tools.simul_credit import (simul_credit, simul_emprunt_max,
                                simul_credit_immo)
from tools.simul_placements import (simul_credimatic, simul_dat, simul_car8,
                                    simul_sogeprimo, simul_pel)
from rag.retriever import retrieve, setup_hybrid_retriever
from rag.retriever import initialize_embeddings

# --- 1. Core Setup and Initialization ---
# Load environment variables
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = os.environ.get(  # type: ignore
    "LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_API_KEY"] = os.environ.get(  # type: ignore
    "LANGCHAIN_API_KEY")


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

    SIMULATOR_URL = "https://sgci-perso-cred.onrender.com/"

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Tu es un conseiller financier expert de la Société "
            "Générale Côte d'Ivoire (SGCI),pour {prénom} {nom}."
            "Commence ton message avec une salutation personnalisée en "
            "utilisant le prénom ({prénom}) du client."
            "Ton ton est prestigieux, précis et proactif."
            "INFOS CLIENT CONNUES :"
            "- Segment : {segment}"
            "- Revenus : {revenus} FCFA"
            "- Solde : {solde} FCFA"
            "- Produits détenus : {produits}"
            "RÈGLE D'OR : Tu connais déjà les revenus du client ({revenus} "
            "FCFA)"
            "Ne redemande JAMAIS le nom ou le revenu du client "
            "si tu les as déjà ci-dessus. "
            "Si le client demande un crédit, injecte automatiquement la valeur"
            " {revenus} FCFA dans l'argument `revenus` de l'outil "
            "`simul_credit`."
            "Et pareil pour les autres outils 'simul_credit_immo', 'simul_dat'"
            " et 'simul_car8'."
            "MISSIONS :"
            "1. Analyse patrimoniale (Banque, Épargne, Placements BRVM, "
            "Assurances)."
            "2. Crédits (Immobilier & Consommation)."
            "RÈGLES D'EXTRACTION DE DONNÉES (CRUCIAL) :"
            "- Avant de poser une question, ANALYSE l'historique et les "
            "documents fournis dans le contexte."
            "- Si une information (revenu, montant, durée) est présente dans "
            "un document (ex: fiche de paie) "
            "ou dans un message précédent, CONSIDÈRE-LA COMME ACQUISE."
            "- L'envoi d'un document par le client vaut consentement implicite"
            "pour l'analyse de ce document spécifique. "
            "Ne redemande pas de consentement pour les données déjà transmises"
            "LOGIQUE DE SIMULATION :"
            "1. Identifie les variables nécessaires : montant, durée, "
            "fréquence."
            "2. UTILISATION DES DONNÉES IMPLICITES (CRUCIAL) : "
            "- Si le produit choisi a une durée fixe (ex: CAR 8 = 8 ans), "
            "considère que la durée est ACQUISE. "
            "- NE DEMANDE PAS au client de confirmer une durée imposée par le "
            "contrat."
            "- Dis plutôt : 'Comme il s'agit d'un CAR 8, nous partons sur la "
            "durée contractuelle de 8 ans.'"
            "3. UTILISATION DU PROFIL :"
            "- Si le client dit 'mon solde', utilise la valeur {solde} FCFA "
            "sans redemander le montant."
            "- Si tu as les infos pour `simul_emprunt_max`, 'simul_epargne',"
            " 'simul_dat', 'simul_credit_immo', 'simul_car8','simul_sogeprimo'"
            ", 'simul_credimatic', ou 'simul_pel' applique la "
            "même logique : identifie les données nécessaires, vérifie si tu "
            "les as déjà, et appelle l'outil sans délai."
            "- Si un produit mentionné dans le contexte (RAG) impose une durée"
            "fixe (ex: CAR 8 ans), ne demande pas de confirmation de durée au "
            "client. Utilise la durée imposée par le produit pour tes calculs."
            "- Dès que l'utilisateur demande 'ce qu'il peut faire' ou exprime "
            "une déception suite à un refus de crédit, lance IMMÉDIATEMENT "
            "l'outil simul_emprunt_max avec les revenus du profil et la durée "
            "mentionnée précédemment sans poser de question."
            "4. Outil simulateur de crédit :"
            "Lorsqu'un client demande une simulation de crédit, de prêt ou de"
            " financement :"
            "- Effectue d'abord la simulation avec tes outils."
            "- Termine systématiquement ta réponse par cette phrase (en "
            "Markdown) : 📊 Pour aller plus loin, explorez notre simulateur "
            f"interactif : [Simulateur de crédit]({SIMULATOR_URL})"
            "STYLE ET DEONTOLOGIE :"
            "- La monnaie est le FCFA."
            "- Sois un partenaire de confiance : si tu vois un revenu élevé "
            "sur une fiche de paie, "
            "adapte ton discours au standing 'High-Net-Worth'."
            "- Base-toi sur ce contexte : {context}."),
        MessagesPlaceholder(variable_name="messages"),
    ])

    tools = [simul_credit, simul_emprunt_max, simul_credit_immo, simul_dat,
             simul_car8, simul_credimatic, simul_sogeprimo, simul_pel]
    tool_map = {tool.name: tool for tool in tools}
    model_with_tools = model.bind_tools(tools)
    chain = prompt | model_with_tools

    def call_model(state: State):
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

    def execute_tools(state: State):
        last_message = state["messages"][-1]
        tool_messages = []
        for tool_call in last_message.tool_calls:  # type: ignore
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

    conn = sqlite3.connect("database/checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    app = workflow.compile(checkpointer=memory)

    return app


def generate_conv_title(first_human_msg, first_ai_msg):
    """Génère un titre de conversation à partir du premier échange."""
    try:
        model = init_chat_model("gemini-2.5-flash-lite",
                                model_provider="google_genai")
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
            datetime.datetime.now().strftime('%d/%m %H:%M')}"  # type: ignore
