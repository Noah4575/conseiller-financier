from dataclasses import dataclass, field
from langchain_core.messages import AIMessage
from config import get_welcome_message
import streamlit as st
from database.database import create_new_conversation

WELCOME_MESSAGE = get_welcome_message()


@dataclass
class AppSession:
    """Représente l'état complet d'une session utilisateur."""
    thread_id: str = ""
    messages: list = field(default_factory=list)
    uploader_key: int = 0
    editing_index: int | None = None
    edit_text: str = ""
    pending_edit: str | None = None


def init_session(user_convs: list) -> None:
    """
    Initialise le session_state une seule fois par session.
    À appeler en début de show_chat_page(), avant tout le reste.
    """

    # Si déjà initialisé, on ne touche à rien
    if st.session_state.get("_session_ready"):
        return

    # Détermine le thread_id et les messages initiaux
    if user_convs:
        first_conv = user_convs[0]
        thread_id = first_conv["id"]
        messages = _deserialize_messages(first_conv.get("messages", []))
    else:
        thread_id = create_new_conversation(st.session_state.user_info["id"])
        messages = [AIMessage(content=WELCOME_MESSAGE)]

    # Initialise tous les champs d'un coup
    session = AppSession(
        thread_id=thread_id,
        messages=messages or [AIMessage(content=WELCOME_MESSAGE)],
    )
    _apply_to_state(session)

    # Flag pour ne jamais réexécuter ce bloc
    st.session_state._session_ready = True


def reset_session() -> None:
    """Réinitialise complètement la session (changement de conversation)."""
    keys_to_clear = list(vars(AppSession()).keys()) + ["_session_ready"]
    for key in keys_to_clear:
        st.session_state.pop(key, None)


def switch_conversation(conv: dict | None = None) -> None:
    """Change la conversation active sans recharger toute la page."""
    if conv is None:
        thread_id = create_new_conversation(st.session_state.user_info["id"])
        messages = [AIMessage(content=WELCOME_MESSAGE)]

    else:
        thread_id = conv["id"]
        messages = _deserialize_messages(conv.get("messages", []))

    session = AppSession(thread_id=thread_id,
                         messages=messages)

    _apply_to_state(session)
    st.session_state._session_ready = True


# --- Helpers privés ---

def _deserialize_messages(raw: list) -> list:
    from langchain_core.messages import HumanMessage
    return [
        HumanMessage(content=m["content"]) if m["type"] == "human"
        else AIMessage(content=m["content"])
        for m in raw
    ]


def _apply_to_state(session: AppSession) -> None:
    """Écrit tous les champs de la dataclass dans st.session_state."""
    for key, value in vars(session).items():
        st.session_state[key] = value
