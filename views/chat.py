import os
import tempfile

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from streamlit_mic_recorder import mic_recorder  # type: ignore

from llm.llm import initialize_model, generate_conv_title
from database.database import (create_new_conversation,
                               update_conversation_messages, update_conv_title)
from components.sidebar import show_popups, show_sidebar
from components.file_processor import process_file
from services.audio import load_whisper_model
from config import get_welcome_message

WELCOME_MESSAGE = get_welcome_message()


def show_chat_page():
    user = st.session_state.user_info

    show_popups(user)
    user_convs = show_sidebar(user)

    st.title("👨‍💼 Conseiller Financier IA")

    app = initialize_model()
    model = load_whisper_model()

    _init_session_state(user, user_convs)

    audio_data, files = _show_media_inputs()
    _display_chat_history()

    query = st.chat_input("Votre demande...")
    transcribed_text = _transcribe_audio(audio_data, model)
    final_input = query or transcribed_text

    if final_input:
        _handle_user_input(final_input, files, app)


# --- Fonctions internes ---

def _init_session_state(user, user_convs):
    if "messages" not in st.session_state:
        st.session_state.messages = [AIMessage(content=WELCOME_MESSAGE)]

    if "thread_id" not in st.session_state:
        if user_convs:
            st.session_state.thread_id = user_convs[0]['id']
        else:
            st.session_state.thread_id = create_new_conversation(user['id'])

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0


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
    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                if isinstance(message.content, list):
                    for block in message.content:
                        if block.get("type") == "text":  # type: ignore
                            text = block.get("display_text") or block.get("text")  # type: ignore
                            st.markdown(text)  # type: ignore
                        elif block.get("type") == "image_url":  # type: ignore
                            st.image(block["image_url"]["url"])  # type: ignore
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
            for event in app.stream(inputs, config, stream_mode="values"):
                if "messages" in event:
                    msg = event["messages"][-1]
                    if (isinstance(msg, AIMessage) and msg.content
                            and not msg.tool_calls):
                        full_response = msg.content
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
    if len(human_msgs) == 1 and len(ai_msgs) == 1:
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
