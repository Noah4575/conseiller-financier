# migrate.py — à lancer une fois puis supprimer
from tinydb import TinyDB
from database.database import _hash_password, init_db, SessionLocal, User, Conversation
import bcrypt, datetime, uuid

init_db()
old_db = TinyDB("database/sgci_data.json")

with SessionLocal() as db:
    for u in old_db.table("users").all():
        if db.query(User).filter(User.id == u["id"]).first():
            continue
        db.add(User(
            id=u["id"], password=_hash_password(u["password"]) if not u["password"].startswith("$2b$") else u["password"],  # déjà hashé → on ne retouche pas,  # déjà hashé si fait avant
            nom=u["nom"], prenom=u.get("prénom", ""),
            role=u.get("role", "client"), segment=u.get("segment", ""),
            solde=u.get("solde", 0), revenus=u.get("revenus", 0),
            produits=u.get("produits") or []
        ))
    for c in old_db.table("conversations").all():
        db.add(Conversation(
            id=c["id"], user_id=c["user_id"], title=c["title"],
            messages=c.get("messages", []),
            updated_at=datetime.datetime.now()
        ))
    db.commit()
print("Migration terminée.")