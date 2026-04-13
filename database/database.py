import uuid
import bcrypt
import datetime
from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# --- Setup ---

engine = create_engine(
    "sqlite:///database/sgci_data.db",
    connect_args={"check_same_thread": False}
)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)


# --- Modèles ---

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    password = Column(String, nullable=False)
    nom = Column(String)
    prenom = Column(String)
    role = Column(String, default="client")
    segment = Column(String)
    solde = Column(Integer, default=0)
    revenus = Column(Integer, default=0)
    produits = Column(JSON, default=list)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    title = Column(String, default="Nouvelle discussion")
    messages = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.datetime.now,
                        onupdate=datetime.datetime.now)


# --- Helpers internes ---
def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# --- Init ---

def init_db():
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        if db.query(User).count() > 0:
            return

        db.add_all([
            User(id="admin", password=_hash_password("admin"),
                 nom="Système", prenom="Admin", role="admin",
                 segment="interne", solde=0, revenus=0, produits=[]),
            User(id="0001", password=_hash_password("123"),
                 nom="Traoré", prenom="Alassane", segment="High Net Worth",
                 solde=7500000, revenus=2500000,
                 produits=["Crédit Immobilier", "Dépôt à Terme"]),
            User(id="0002", password=_hash_password("123"),
                 nom="Koffi", prenom="Jean", segment="High Net Worth",
                 solde=1500000, revenus=900000, produits=[]),
        ])
        db.commit()
        print("Base de données initialisée avec succès !")


# --- Users ---

def get_user_data(user_id: str) -> dict | None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        return _user_to_dict(user) if user else None


def create_user(user_id, password, nom, prenom, segment, solde, revenus):
    with SessionLocal() as db:
        if db.query(User).filter(User.id == user_id).first():
            return False, "Cet identifiant existe déjà."
        db.add(User(
            id=user_id, password=_hash_password(password),
            nom=nom, prenom=prenom, segment=segment,
            solde=solde, revenus=revenus, produits=[]
        ))
        db.commit()
    return True, "Compte créé avec succès !"


def update_user(user_id: str, solde: int, revenus: int, segment: str):
    with SessionLocal() as db:
        db.query(User).filter(User.id == user_id).update(
            {"solde": solde, "revenus": revenus, "segment": segment}
        )
        db.commit()


def delete_user(user_id: str) -> bool:
    if user_id == "admin":
        return False
    with SessionLocal() as db:
        db.query(User).filter(User.id == user_id).delete()
        db.query(Conversation).filter(Conversation.user_id == user_id).delete()
        db.commit()
    return True


def get_all_users() -> list[dict]:
    with SessionLocal() as db:
        users = db.query(User).filter(User.id != "admin").all()
        return [_user_to_dict(u) for u in users]


def verify_user(user_id: str, password: str) -> dict | None:
    """Vérifie les credentials et retourne l'utilisateur si valide."""
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user and _check_password(password, user.password):  # type: ignore
            return _user_to_dict(user)
    return None


# --- Conversations ---

def create_new_conversation(user_id: str, title="Nouvelle discussion") -> str:
    conv_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(Conversation(id=conv_id, user_id=user_id, title=title))
        db.commit()
    return conv_id


def get_user_conversations(user_id: str) -> list[dict]:
    with SessionLocal() as db:
        convs = (db.query(Conversation)
                 .filter(Conversation.user_id == user_id)
                 .order_by(Conversation.updated_at.desc())
                 .all())
        return [_conv_to_dict(c) for c in convs]


def update_conversation_messages(conv_id: str, messages: list):
    with SessionLocal() as db:
        db.query(Conversation).filter(Conversation.id == conv_id).update(
            {"messages": messages, "updated_at": datetime.datetime.now()}
        )
        db.commit()


def update_conv_title(conv_id: str, new_title: str):
    with SessionLocal() as db:
        db.query(Conversation).filter(Conversation.id == conv_id).update(
            {"title": new_title}
        )
        db.commit()


def delete_conversation(conv_id: str):
    with SessionLocal() as db:
        db.query(Conversation).filter(Conversation.id == conv_id).delete()
        db.commit()


# --- Utils ---

def get_segment(solde: int) -> str:
    if solde > 10_000_000:
        return "High Net Worth"
    elif solde > 1_000_000:
        return "Affluent"
    return "Mass Market"


def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id, "password": u.password,
        "nom": u.nom, "prénom": u.prenom,
        "role": u.role, "segment": u.segment,
        "solde": u.solde, "revenus": u.revenus,
        "produits": u.produits or [],
    }


def _conv_to_dict(c: Conversation) -> dict:
    return {
        "id": c.id, "user_id": c.user_id,
        "title": c.title, "messages": c.messages or [],
        "updated_at": str(c.updated_at),
    }
