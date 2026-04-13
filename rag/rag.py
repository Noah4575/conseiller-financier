from langchain_cohere import CohereEmbeddings  # type: ignore
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import WebBaseLoader, DataFrameLoader
from langchain_experimental.text_splitter import SemanticChunker  # type:ignore
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import faiss
import nltk
import bs4
import os
import re


# Pages du Site Web SGCI
urls = {
        "https://institutionnel.societegenerale.ci/fr/votre-banque/historique/":{"class_":"col-md-9 mainCol"},
        "https://particuliers.societegenerale.ci/fr/devenir-client/ouvrir-compte/":{"class_":"dce dce-accordeon"},
        "https://particuliers.societegenerale.ci/fr/devenir-client/nous-contacter/":{"id":"c16077"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/comptes/compte-cheque/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/comptes/compte-eco/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/comptes/compte-euro/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/packages/pack-premier/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/packages/pack-classic/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/packages/pack-infinite/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/packages/pack-diaspora/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/services-connexes/change-manuel/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/services-connexes/coffre-fort/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/emprunter/decouvert-compte/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/emprunter/pret-consommation/pret-scolaire/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/emprunter/pret-consommation/pret-personnel-ordinaire/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/emprunter/pret-consommation/pret-personnel-ordinaire-installation-plus/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/emprunter/pret-consommation/avance-conventionnelle-tresorerie/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/emprunter/prets-immobiliers/pret-personnel-immobilier/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/produits-banque-distance/messalia/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/produits-banque-distance/vocalia-plus/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/produits-banque-distance/connect-lappli-mobile-web-societe-generale-cote-divoire/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/produits-banque-distance/politique-confidentialite/":{"id":"c16130"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/produits-banque-distance/yeri/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/cartes-bancaires/carte-eclair/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/cartes-bancaires/carte-visa-horizon/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/cartes-bancaires/carte-visa-classic/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/cartes-bancaires/carte-visa-premier/":{"class_git ":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/cartes-bancaires/carte-visa-platinum/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/banque-quotidien/cartes-bancaires/carte-visa-infinite/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-vie/soge-invest-premium/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-vie/plan-retraite-zenith-performance/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-vie/yaconfort-premium/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-vie/yaconfort/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-vie/certicompte/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-vie/sogetudes/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-non-vie/assurance-voyage/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-non-vie/assurance-multirisques-habitation/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/assurer/assurance-non-vie/quietis-plus/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/epargne/plan-epargne-taux-progressif/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/epargne/compte-epargne/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/epargne/credimatic/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/epargne/plan-epargne-logement/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/epargne/sogeprimo/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/placements/depots-terme/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/placements/bourse/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/placements/car/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/placements/compte-titres/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/epargner/placements/fonds-communs-placement/":{"class_":"dce_tabs_content"},
        "https://particuliers.societegenerale.ci/fr/faq/":{"class_":"col-md-9 mainCol"}
        }


def clean_text(text: str) -> str:
    """Réinsère des espaces après la ponctuation et nettoie le texte."""
    # Espace après ponctuation collée
    text = re.sub(r'([.!?:])([A-ZÀ-Ü])', r'\1 \2', text)
    # Supprime les espaces multiples
    text = re.sub(r' +', ' ', text)
    return text.strip()


def load_docs(urls):
    '''Chargement du contenu des URLs dans des documents'''
    all_docs = []
    for url, parse_class in urls.items():
        try:
            print(url)
            strainer = bs4.SoupStrainer(**parse_class)
            loader = WebBaseLoader(
                web_paths=[url],
                bs_kwargs={"parse_only": strainer}
                )
            docs = loader.load()
            for doc in docs:
                doc.page_content = clean_text(doc.page_content)
                doc.metadata["source"] = url
                doc.metadata["loaded_at"] = str(pd.Timestamp.now())
            all_docs.extend(docs)

        except Exception as e:
            print(f"✗ Error loading {url}: {e}")
            continue

    return all_docs


def load_excel(file_path):
    '''Charge et nettoie les documents depuis le fichier CSV des produits.'''

    print(f"Chargement du fichier excel produits : {file_path}")

    try:
        # 1. Charger avec pandas, en sautant les 2 premières lignes
        #    Les vrais en-têtes sont à la ligne 3 (index 2)
        df = pd.read_excel(file_path, header=2)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du CSV : {e}")
        return []

    # 2. Renommer les colonnes (basé sur l'inspection)
    df = df.rename(columns={
        df.columns[0]: "Produit",
        df.columns[1]: "Cible",
        df.columns[2]: "Descriptif",
        df.columns[3]: "Tarif"
    })

    # 3. Nettoyer les lignes vides (où 'Produit' est manquant)
    df = df.dropna()
    # Supprimer la première ligne
    df = df.iloc[1:]

    # Supprimer les \n dans les colonnes texte
    df['Produit'] = df['Produit'].str.replace('\n', ' ', regex=False)
    df['Cible'] = df['Cible'].str.replace('\n', ' ', regex=False)
    df['Descriptif'] = df['Descriptif'].str.replace('\n', ' ', regex=False)
    df['Tarif'] = df['Tarif'].str.replace('\n', ' ', regex=False)

    # 4. CRÉER LE CONTENU DU RAG
    # Nous combinons les colonnes en un seul 'page_content'
    # C'est ce qui sera vectorisé.
    df['page_content'] = (
        "Produit: " + df['Produit'].astype(str) + "; "
        "Description: " + df['Descriptif'].astype(str) + "; "
        "Cible: " + df['Cible'].astype(str) + "; "
        "Tarif: " + df['Tarif'].astype(str)
    )

    # 5. Utiliser DataFrameLoader pour convertir en Documents
    loader = DataFrameLoader(df, page_content_column="page_content")
    docs = loader.load()

    # 6. Ajouter la source (le nom du fichier) aux métadonnées
    for doc in docs:
        doc.metadata["source"] = file_path

    print(f"✅ {len(docs)} documents produits chargés depuis le CSV.")
    return docs


def split_docs(all_docs, embeddings):
    '''Split les documents en chunks'''
    text_splitter = SemanticChunker(embeddings)
    all_splits = text_splitter.split_documents(all_docs)
    return all_splits


def extract_topic_from_url(url: str) -> str:
    """
    Transforme une URL en un sujet lisible.
    Ex: .../pret-consommation/pret-scolaire/ -> "pret consommation
      pret scolaire"
    """
    try:
        # Enlève la base et la fin
        parts = url.strip('/').split('/')
        # Garde les 3 dernières parties (ex: 'emprunter', 'pret-consommation',
        #  'pret-scolaire')
        relevant_parts = parts[-3:]
        # Remplace les tirets par des espaces
        topic = " ".join(part.replace('-', ':') for part in relevant_parts)

        return topic
    except Exception:
        # Fallback si l'URL est étrange
        return "information generale"


def create_dense_store(all_splits, embeddings):
    '''Création d'un vector store FAISS optimisé (IndexIVFFlat)'''
    # 1. Crée la base de données FAISS initiale (LangChain wrapper).
    dense_store = FAISS.from_documents(
        documents=all_splits,
        embedding=embeddings,
    )
    # Prépare les vecteurs NumPy pour FAISS
    texts = [doc.page_content for doc in all_splits]
    vectors = embeddings.embed_documents(texts)
    vectors_np = np.array(vectors).astype("float32")

    # 2. Configure l'Index Inverted File (IVF)
    embedding_dim = vectors_np.shape[1]
    # Définit l'index de base (quantificateur) pour le clustering.
    quantizer = faiss.IndexFlatL2(embedding_dim)
    # Calcule le nombre de clusters (listes) pour l'index IVF.
    nlist = min(20, (len(all_splits) // 10))
    # Crée l'objet IndexIVFFlat (optimisation majeure pour la vitesse).
    index = faiss.IndexIVFFlat(quantizer, embedding_dim, nlist,
                               faiss.METRIC_L2)

    # 3. Entraînement et Ajout
    # Entraîne l'index à partitionner l'espace en 'nlist' clusters.
    index.train(vectors_np)
    # Définit le nombre de clusters à explorer lors d'une recherche
    index.nprobe = min(10, (nlist//2))
    index.add(vectors_np)

    # 4. Finalisation
    dense_store.index = index

    return dense_store


def load_stores(embeddings, FAISS_INDEX_PATH):
    pc_retriever = FAISS.load_local(FAISS_INDEX_PATH, embeddings,
                                    allow_dangerous_deserialization=True)
    '''Chargement des retrievers précédemment sauvegardés'''

    return pc_retriever


def extract_product_name(url: str) -> str:
    # Prend uniquement le dernier segment non vide de l'URL
    last_segment = [p for p in url.strip("/").split("/") if p][-1]
    # Remplace les tirets par des espaces et met en titre
    return last_segment.replace("-", " ").title()


def main():
    # Setup
    load_dotenv()
    embeddings = CohereEmbeddings(model="embed-multilingual-light-v3.0",
                                  cohere_api_key=os.environ.get(
                                      "COHERE_API_KEY"))  # type: ignore

    FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH")
    PRODUCTS_PATH = os.environ.get("PRODUCTS_PATH")

    nltk.download("punkt_tab")
    # Load, split, create and save stores
    all_docs = load_docs(urls)
    xls_docs = load_excel(PRODUCTS_PATH)
    all_docs.extend(xls_docs)
    # all_splits = split_docs(all_docs, embeddings)

    print("Enrichissement des chunks avec les métadonnées de source...")
    for doc in all_docs:
        source_url = doc.metadata.get("source")

        if source_url:
            # Extraire un sujet lisible de l'URL
            topic = extract_topic_from_url(source_url)

            # Préfixer le contenu original avec le sujet
            original_content = doc.page_content
            product_name = extract_product_name(source_url)

            doc.page_content = (
                f"Produit: {product_name}\n"
                f"Sujet de la page: {topic}\n\n"
                f"Contenu: {original_content}"
            )
    print("✅ Chunks enrichis.")

    dense_store = create_dense_store(all_docs, embeddings)

    dense_store.save_local(FAISS_INDEX_PATH)


if __name__ == "__main__":
    main()
