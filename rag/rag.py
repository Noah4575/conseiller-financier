from langchain_cohere import CohereEmbeddings
from langchain.chat_models import init_chat_model
from langchain_community.document_transformers import LongContextReorder
# from langchain_core.documents import Document
from langchain.retrievers import EnsembleRetriever
from Agent.core import State
import pickle
import FAISS
import os


def initialize_embeddings():
    embeddings = CohereEmbeddings(model="embed-multilingual-light-v3.0")
    return embeddings


def setup_hybrid_retriever(embeddings):
    FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH")
    BM25_RETRIEVER_PATH = os.environ.get("BM25_RETRIEVER_PATH")

    dense_store, sparse_retriever = load_stores(embeddings, FAISS_INDEX_PATH,
                                                BM25_RETRIEVER_PATH)

    hybrid_retriever = EnsembleRetriever(
        retrievers=[dense_store.as_retriever(search_kwargs={"k": 6}),
                    sparse_retriever],
        weights=[0.6, 0.4],
    )
    return hybrid_retriever


async def retrieve(state: State, hybrid_retriever: EnsembleRetriever,
                   FAISS2_INDEX_PATH, embeddings):

    question = state["messages"][-1].content

    # Préparer les tâches de recherche
    task_rag = hybrid_retriever.ainvoke(question)

    # Lancer les deux recherches en parallèle
    retrieved_docs = await task_rag

    # Traiter les résultats
    reordering = LongContextReorder()
    docs = reordering.transform_documents(retrieved_docs)

    return {
        "context": docs,
        "question": question
    }


def load_stores(embeddings, FAISS_INDEX_PATH, BM25_RETRIEVER_PATH):
    dense_store = FAISS.load_local(FAISS_INDEX_PATH, embeddings,
                                   allow_dangerous_deserialization=True)
    '''Chargement des retrievers précédemment sauvegardés'''

    with open(BM25_RETRIEVER_PATH, "rb") as f:
        sparse_retriever = pickle.load(f)

    return dense_store, sparse_retriever
