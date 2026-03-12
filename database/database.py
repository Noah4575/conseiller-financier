import uuid
from tinydb import TinyDB, Query
import datetime

db = TinyDB('sgci_data.json')
users_table = db.table('users')
conversations_table = db.table('conversations')


def init_db():
    if not users_table.all():
        # On crée un client "VIP" pour tes tests
        users_table.insert({
            "id": "admin",
            "password": "admin",
            "nom": "Système",
            "prénom": "Admin",
            "role": "admin",
            "segment": "interne",
            "solde": 0,
            "revenus": 0,
            "produits": [],
            "documents": None
        })

        users_table.insert({
            "id": "0001",
            "password": "123",
            "nom": "Traoré",
            "prénom": "Alassane",
            "segment": "High Net Worth",
            "solde": 7500000,
            "revenus": 2500000,
            "produits": ["Crédit Immobilier", "Dépôt à Terme"],
            "documents": None
            })

        users_table.insert({
            "id": "0002",
            "password": "123",
            "nom": "Koffi",
            "prénom": "Jean",
            "segment": "High Net Worth",
            "solde": 1500000,
            "revenus": 900000,
            "produits": None,
            "documents": None
            })

        print("Base de données initialisée avec succès !")


def get_user_data(user_id):
    """Récupère les infos d'un utilisateur par son ID."""
    User = Query()
    result = users_table.search(User.id == user_id)
    return result[0] if result else None


def create_new_conversation(user_id, title="Nouvelle discussion"):
    conv_id = str(uuid.uuid4())
    conversations_table.insert({
        "id": conv_id,
        "user_id": user_id,
        "title": title,
        "messages": [],  # Liste vide au départ
        "updated_at": str(datetime.datetime.now())
    })
    return conv_id


def get_user_conversations(user_id):
    """Récupère la liste des titres pour la barre latérale."""
    Q = Query()
    convs = conversations_table.search(Q.user_id == user_id)
    return sorted(convs, key=lambda x: x['updated_at'], reverse=True)


def update_conversation_messages(conv_id, messages):
    """Sauvegarde l'intégralité du chat en cours."""
    Q = Query()
    conversations_table.update(
        {"messages": messages, "updated_at": str(datetime.datetime.now())},
        Q.id == conv_id
    )


def create_user(user_id, password, nom, prenom, segment, solde, revenus):
    """Crée un nouvel utilisateur s'il n'existe pas déjà."""
    User = Query()
    # On vérifie si l'ID existe déjà
    if users_table.search(User.id == user_id):
        return False, "Cet identifiant existe déjà."

    users_table.insert({
        "id": user_id,
        "password": password,
        "nom": nom,
        "prénom": prenom,
        "segment": segment,
        "solde": solde,
        "revenus": revenus,
        "produits": [],
        "documents": None
    })
    return True, "Compte créé avec succès !"


def get_all_users():
    """Récupère tous les utilisateurs (sauf l'admin actuel pour éviter l'auto-suppression)."""
    return [u for u in users_table.all() if u['id'] != 'admin']


def delete_user(user_id):
    """Supprime un utilisateur et ses conversations associées."""
    User = Query()
    # Supprimer l'utilisateur
    users_table.remove(User.id == user_id)
    # Supprimer ses conversations
    Conv = Query()
    conversations_table.remove(Conv.user_id == user_id)
    return True
