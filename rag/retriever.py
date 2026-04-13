from langchain_cohere import CohereEmbeddings  # type: ignore
from langchain_community.document_transformers import LongContextReorder
from llm.core import State
import os
from rag.rag import load_stores
import streamlit as st


def initialize_embeddings():
    embeddings = CohereEmbeddings(
        model="embed-multilingual-light-v3.0")  # type: ignore
    return embeddings


@st.cache_resource
def setup_retriever(_embeddings):
    FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH")

    dense_store = load_stores(_embeddings, FAISS_INDEX_PATH)  # type: ignore

    retriever = dense_store.as_retriever(search_kwargs={"k": 6})

    return retriever


def retrieve(state: State, retriever):

    messages = state["messages"]
    last_message = messages[-1]

    # Si le contenu est une liste (multimodal), on extrait uniquement le texte
    if isinstance(last_message.content, list):
        # On cherche l'élément qui a le type "text"
        question = next(
            (item["text"]  # type: ignore
             for item in last_message.content
             if item["type"] == "text"),  # type: ignore
            ""
        )
    else:
        # C'est déjà une chaîne de caractères (cas classique)
        question = last_message.content

    # Préparer les tâches de recherche
    retrieved_docs = retriever.invoke(question)

    # Traiter les résultats
    reordering = LongContextReorder()
    docs = reordering.transform_documents(retrieved_docs)

    return {
        "context": docs,
        "question": question
    }
