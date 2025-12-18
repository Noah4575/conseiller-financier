from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_agent
# from services.socgenai_models import llm_model

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

# Initialize the Gemini model (using st.cache_resource for efficiency)
@st.cache_resource
def initialize_model():
    """Initializes the LLM and the LangGraph application."""
    model = init_chat_model("gemini-2.5-flash-lite",
                            model_provider="google_genai")

    prompt = ("system", """Tu es un conseiller financier expert et dédié d'une banque de Côte d'Ivoire.
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
            """)
    tools = [simul_credit]

    agent = create_agent(model=model, tools=tools, system_prompt=prompt)

    return agent
