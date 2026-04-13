import os
import tempfile

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from streamlit_mic_recorder import mic_recorder  # type: ignore

from llm.llm import (_build_chain, _get_memory, _get_retriever, _get_tools,
                     initialize_model, generate_conv_title)
from database.database import (update_conversation_messages, update_conv_title)
from components.sidebar import show_popups, show_sidebar
from components.file_processor import process_file
from services.audio import load_whisper_model
from config import get_welcome_message
from utils.session import init_session

WELCOME_MESSAGE = get_welcome_message()


def show_chat_page():
    user = st.session_state.user_info

    show_popups(user)
    user_convs = show_sidebar(user)

    st.title("👨‍💼 Conseiller Financier IA")

    chain = _build_chain()
    _, tool_map = _get_tools()
    memory = _get_memory()
    retriever = _get_retriever()

    app = initialize_model(chain, tool_map, memory, retriever)
    model = load_whisper_model()

    init_session(user_convs)

    audio_data, files = _show_media_inputs()
    _display_chat_history()

    if "pending_edit" in st.session_state and st.session_state.pending_edit:
        pending = st.session_state.pop("pending_edit")
        _handle_user_input(pending, [], app)
        return

    query = st.chat_input("Votre demande...")
    transcribed_text = _transcribe_audio(audio_data, model)
    final_input = query or transcribed_text

    if final_input:
        _handle_user_input(final_input, files, app)


# --- Fonctions internes ---

def _show_media_inputs():
    """Affiche les widgets audio et upload dans la sidebar."""
    with st.sidebar:
        st.write("### Entrée Vocale")
        audio_data = mic_recorder(
            start_prompt="Démarrer l'enregistrement 🎤",
            stop_prompt="Arrêter & Envoyer 🛑",
            key='recorder'
        )
        st.write("### Pièce Jointe (PDF, DOCX)")
        files = st.file_uploader(
            "Téléchargez un document financier pour analyse",
            accept_multiple_files=True,
            key=f"file_uploader_{st.session_state.uploader_key}"
        )
        if st.button("🗑️ Effacer les documents joints"):
            st.rerun()

    return audio_data, files


def _display_chat_history():
    for i, message in enumerate(st.session_state.messages):
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                # Extraire le texte brut selon le format du contenu
                if isinstance(message.content, list):
                    display_text = next(
                        (b.get("display_text") or b.get("text", "")
                         for b in message.content if b.get("type") == "text"),
                        ""
                    )
                    for block in message.content:
                        if block.get("type") == "image_url":
                            st.image(block["image_url"]["url"])
                else:
                    display_text = message.content

                # Mode édition actif sur ce message
                if st.session_state.editing_index == i:
                    new_text = st.text_area(
                        "Modifier votre message :",
                        value=st.session_state.edit_text,
                        key=f"edit_area_{i}"
                    )
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("✅ Valider", key=f"confirm_{i}"):
                            # Tronquer l'historique à partir de ce message (exclu)
                            st.session_state.messages = st.session_state.messages[:i]
                            st.session_state.editing_index = None
                            st.session_state.pending_edit = new_text
                            st.rerun()
                    with col2:
                        if st.button("❌ Annuler", key=f"cancel_{i}"):
                            st.session_state.editing_index = None
                            st.rerun()
                else:
                    col_msg, col_btn = st.columns([0.95, 0.05])
                    with col_msg:
                        st.markdown(display_text)
                    with col_btn:
                        if st.button("✏️", key=f"edit_{i}", help="Modifier ce message"):
                            st.session_state.editing_index = i
                            st.session_state.edit_text = display_text
                            st.rerun()

        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(message.content)


def _transcribe_audio(audio_data, model) -> str | None:
    if not audio_data:
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_data['bytes'])
        tmp_file_path = tmp_file.name

    try:
        with st.spinner("Transcription en cours..."):
            result = model.transcribe(tmp_file_path)
            return result["text"].strip()
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


def _handle_user_input(final_input: str, files, app):
    st.chat_message("user").write(final_input)

    # Construction du message multimodal
    multimodal_content = [{"type": "text", "text": final_input}]
    if files:
        for f in files:
            processed = process_file(f)
            if processed:
                multimodal_content.append(processed)

    st.session_state.messages.append(HumanMessage(
        content=multimodal_content))  # type: ignore

    # Appel au modèle et streaming de la réponse
    full_response = _stream_ai_response(app)

    _save_conversation(full_response)

    if files:
        st.session_state.uploader_key += 1

    st.rerun()


def _stream_ai_response(app) -> str:
    """Stream la réponse du modèle et retourne le texte complet."""
    with st.chat_message("assistant"):
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {
            "messages": st.session_state.messages[-1],
            "language": "Français",
            "user_profile": st.session_state.user_info,
        }

        message_placeholder = st.empty()
        full_response = ""

        with st.spinner("Génération de la réponse..."):
            for chunk, metadata in app.stream(inputs, config, stream_mode="messages"):
                if (metadata.get("langgraph_node") == "model"
                    and hasattr(chunk, "content")
                    and isinstance(chunk.content, str)
                    and chunk.content):
                    full_response += chunk.content
                    message_placeholder.markdown(full_response)

    if (not st.session_state.messages
            or st.session_state.messages[-1].content != full_response):
        st.session_state.messages.append(AIMessage(content=full_response))

    if not full_response:
        full_response = ("⚠️ Je n'ai pas pu générer de réponse. Veuillez"
                         "réessayer.")
        message_placeholder.markdown(full_response)

    return full_response  # type: ignore


def _save_conversation(full_response: str):
    """Sérialise et persiste la conversation en base de données."""
    serializable_messages = [
        {"type": "human" if isinstance(m, HumanMessage) else "ai",
         "content": m.content}
        for m in st.session_state.messages
    ]

    human_msgs = [m for m in st.session_state.messages if isinstance(
        m, HumanMessage)]
    ai_msgs = [m for m in st.session_state.messages if isinstance(
        m, AIMessage) and m.content]

    # Génération automatique du titre à la première réponse
    if len(human_msgs) == 1 and len(ai_msgs) == 2:
        first_human = human_msgs[0].content
        if isinstance(first_human, list):
            first_human = next(
                (b["text"] for b in first_human  # type: ignore
                 if b["type"] == "text"),  # type: ignore
                ""
            )
        title = generate_conv_title(first_human, full_response)
        update_conv_title(st.session_state.thread_id, title)

    update_conversation_messages(st.session_state.thread_id,
                                 serializable_messages)
