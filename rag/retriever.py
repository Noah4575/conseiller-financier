from langchain_cohere import CohereEmbeddings, CohereRerank  # type: ignore
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_transformers import LongContextReorder
from langchain.retrievers import EnsembleRetriever  # Changed from langchain_classic
from llm.core import State
import pickle
from langchain_community.vectorstores import FAISS
import os


def initialize_embeddings():
    embeddings = CohereEmbeddings(model="embed-multilingual-light-v3.0")
    return embeddings


def load_stores(embeddings, FAISS_INDEX_PATH, BM25_RETRIEVER_PATH):
    dense_store = FAISS.load_local(FAISS_INDEX_PATH, embeddings,
                                   allow_dangerous_deserialization=True)
    '''Chargement des retrievers précédemment sauvegardés'''

    with open(BM25_RETRIEVER_PATH, "rb") as f:
        sparse_retriever = pickle.load(f)

    return dense_store, sparse_retriever


def setup_hybrid_retriever(embeddings):
    FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH")
    BM25_RETRIEVER_PATH = os.environ.get("BM25_RETRIEVER_PATH")

    dense_store, sparse_retriever = load_stores(embeddings, FAISS_INDEX_PATH,
                                                BM25_RETRIEVER_PATH)

    hybrid_retriever = EnsembleRetriever(
        retrievers=[dense_store.as_retriever(search_kwargs={"k": 10}),
                    sparse_retriever],
        weights=[0.6, 0.4],
    )
    base_retriever = hybrid_retriever

    compressor = CohereRerank(model="rerank-multilingual-v3.0", top_n=8)

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever
    )
    return compression_retriever


def retrieve(state: State, hybrid_retriever):

    messages = state["messages"]
    last_message = messages[-1]

    # Si le contenu est une liste (multimodal), on extrait uniquement le texte
    if isinstance(last_message.content, list):
        # On cherche l'élément qui a le type "text"
        question = next(
            (item["text"] for item in last_message.content if item["type"] == "text"),  # type: ignore
            ""
        )
    else:
        # C'est déjà une chaîne de caractères (cas classique)
        question = last_message.content

    # Préparer les tâches de recherche
    retrieved_docs = hybrid_retriever.invoke(question)

    # Traiter les résultats
    reordering = LongContextReorder()
    docs = reordering.transform_documents(retrieved_docs)

    return {
        "context": docs,
        "question": question
    }
