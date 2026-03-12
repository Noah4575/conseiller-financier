import datetime

import streamlit as st

from langchain_core.messages import HumanMessage, AIMessage
from streamlit_mic_recorder import mic_recorder  # type: ignore
import base64
import tempfile
import os
import whisper  # type: ignore
import torch
import pypdf
from llm.llm import initialize_model

from database.database import (init_db, get_user_data,
                               update_conversation_messages,
                               create_new_conversation, get_user_conversations,
                               create_user, get_all_users, delete_user)

init_db()  # Initialize the database with default users

if "authentified" not in st.session_state:
    st.session_state.authentified = False

if not st.session_state.authentified:
    st.title("🔐 Connexion SGCI conseiller financier")

    tab_login, tab_register = st.tabs(["Connexion", "Inscription"])

    with tab_login:
        user_id = st.text_input("ID Client")
        password = st.text_input("Mot de passe", type="password")

        if st.button("Se connecter"):
            user_data = get_user_data(user_id)
            if user_data and user_data["password"] == password:
                st.session_state.authentified = True
                st.session_state.user_id = user_id
                st.session_state.user_info = user_data
                st.success(f"Bienvenue {user_data['prénom']} {user_data['nom']} !")
                st.rerun()
            else:
                st.error("ID ou mot de passe incorrect. Veuillez réessayer.")

    with tab_register:
        st.subheader("Créer un nouveau compte client")
        col1, col2 = st.columns(2)

        with col1:
            new_id = st.text_input("Choisissez un ID Client")
            new_pswd = st.text_input("Choisissez un mot de passe", type="password")
            new_prenom = st.text_input("Prénom")
            new_nom = st.text_input("Nom")

        with col2:
            new_solde = st.number_input("Solde actuel (FCFA)", min_value=0,
                                        step=100000)
            new_revenus = st.number_input("Revenus mensuels (FCFA)",
                                          min_value=0, step=100000)
            # Dans app.py, au moment de l'inscription
            with st.expander("Lire les Conditions Générales d'Utilisation"):
                try:
                    with open("cgu.txt", "r", encoding="utf-8") as f:
                        cgu_text = f.read()
                    st.write(cgu_text)
                except FileNotFoundError:
                    st.error("Le fichier cgu.txt est introuvable à la racine du projet.")
            cgu = st.checkbox("J'accepte les CGU", key="accept_cgu")


        if new_solde > 10000000:
            new_segment = "High Net Worth"
        elif new_solde > 1000000 and new_solde <= 10000000:
            new_segment = "Affluent"
        else:
            new_segment = "Mass Market"

        if st.button("S'inscrire", disabled=not cgu):
            if new_id and new_nom and new_prenom and new_pswd:
                success, message = create_user(new_id, new_pswd, new_nom,
                                               new_prenom, new_segment, new_solde,
                                               new_revenus)
                if success:
                    st.success(message + "Vous pouvez vous connecter.")
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Veuillez remplir tous les champs pour créer un compte.")
        if not cgu:
            st.caption("⚠️ Vous devez accepter les CGU pour créer un compte.")

else:
    user = st.session_state.user_info
    # GESTION CONVERSATIONS
    st.sidebar.title(f"👤 Bonjour {user['prénom']} {user['nom']}")
    st.sidebar.info(f"Segment : {str(user['segment'])}\n"
                    f"\nSolde : {int(user['solde']):,} FCFA\n"
                    f"\nRevenus : {int(user['revenus']):,} FCFA")
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        # On réinitialise les variables de session
        st.session_state.authentified = False
        st.session_state.user_id = None
        st.session_state.user_info = None
        # Optionnel : vider l'historique des messages pour le prochain utilisateur
        st.session_state.messages = []
        st.rerun()

    if st.session_state.user_info.get("role") == "admin":
        st.sidebar.divider()
        st.sidebar.subheader("🛠️ Administration")

        users = get_all_users()
        user_list = [f"{u['id']} - {u['prénom']} {u['nom']}" for u in users]

        selected_user_str = st.sidebar.selectbox("Sélectionner un compte à supprimer", user_list)

        if st.sidebar.button("❌ Supprimer ce compte", type="primary",
                             use_container_width=True):
            target_id = selected_user_str.split(" - ")[0]
            if delete_user(target_id):
                st.sidebar.success(f"Compte {target_id} supprimé.")
                st.rerun() 

    st.sidebar.divider()
    st.sidebar.subheader("Historique des conversations")

    if st.sidebar.button("➕ Nouvelle conversation"):
        new_conv_id = create_new_conversation(st.session_state.user_id,
                                              title=f"Discussion du {datetime.datetime.now().strftime('%d/%m %H:%M')}")
        st.session_state.thread_id = new_conv_id
        st.session_state.messages = [AIMessage(content="Bonjour! Je suis votre conseiller financier expert."
                                     " Comment puis-je vous aider avec vos projets financiers ?")]
        st.rerun()

    user_convs = get_user_conversations(st.session_state.user_id)

    for conv in user_convs:
        # Affiche les titres des conversations dans la barre latérale
        if st.sidebar.button(f"💬 {conv['title']}", key=conv['id'],
                             use_container_width=True):
            st.session_state.thread_id = conv['id']
            loaded_messages = []
            for m in conv['messages']:
                if m['type'] == 'human':
                    loaded_messages.append(HumanMessage(content=m['content']))
                else:
                    loaded_messages.append(AIMessage(content=m['content']))

            st.session_state.messages = loaded_messages
            st.rerun()

    # --- 1. Core Setup and Initialization ---
    st.set_page_config(page_title="Conseiller Financier IA", layout="wide")
    st.title("👨‍💼 Conseiller Financier IA")


    @st.cache_resource
    def load_whisper_model():
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(device)
        return whisper.load_model("turbo").to(device)


    # Initialize the LangGraph application
    app = initialize_model()
    model = load_whisper_model()

    # --- 2. Chat History Management (State) ---
    if "messages" not in st.session_state:
        st.session_state.messages = [
            AIMessage(content="Bonjour! Je suis votre conseiller financier expert."
                    " Comment puis-je vous aider avec vos projets financiers ?")
        ]
    if "thread_id" not in st.session_state:
        # Si aucune conv n'existe, on la crée, sinon on prend la plus récente
        if user_convs:
            st.session_state.thread_id = user_convs[0]['id']
            # Logique de chargement identique ici...
        else:
            st.session_state.thread_id = create_new_conversation(user['id'])

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    # On place le micro dans une colonne pour ne pas encombrer l'interface
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
        if st.sidebar.button("🗑️ Effacer les documents joints"):
            st.rerun()

    def process_file(uploaded_file):
        # 1. Cas des fichiers TEXTE (.txt)
        if uploaded_file.type == "text/plain":
            text_content = uploaded_file.getvalue().decode("utf-8")
            return {
                "type": "text",
                "text": (
                    f"\n[Document texte: {uploaded_file.name}]\n"
                    f"{text_content}"
                ),
            }

        # 2. Cas des IMAGES (.png, .jpg)
        elif uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
            file_bytes = uploaded_file.getvalue()
            base64_file = base64.b64encode(file_bytes).decode("utf-8")
            image_url = f"data:{uploaded_file.type};base64,{base64_file}"
            return {
                "type": "image_url",
                "image_url": {"url": image_url}
            }

        # 3. Cas des PDF (.pdf)
        elif uploaded_file.type == "application/pdf":
            try:
                # On extrait le texte du PDF
                pdf_reader = pypdf.PdfReader(uploaded_file)
                pdf_text = f"\n[Contenu du PDF: {uploaded_file.name}]\n"
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
                return {"type": "text", "text": pdf_text}
            except Exception:
                return {
                    "type": "text",
                    "text": f"Erreur de lecture du PDF {uploaded_file.name}"
                    }

        return None


    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(message.content)

    query = st.chat_input("Votre demande...")
    transcribed_text = None

    if audio_data:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data['bytes'])
            tmp_file_path = tmp_file.name

        try:
            # 2. Passer le CHEMIN du fichier à Whisper, pas le dictionnaire
            with st.spinner("Transcription en cours..."):
                result = model.transcribe(tmp_file_path)
                transcribed_text = result["text"].strip()

        finally:
            # 3. Nettoyer le fichier temporaire après usage
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

    final_input = query or transcribed_text

    if final_input:
        # 1. Display User Message
        st.chat_message("user").write(final_input)

        multimodal_content = [{"type": "text", "text": final_input}]
        files_info = ""
        if files:
            for f in files:
                processed = process_file(f)  # Votre fonction de traitement
                if processed:
                    multimodal_content.append(processed)
                    files_info += f"\n- Document joint : {f.name}"

        history_message = HumanMessage(content=final_input + files_info)
        st.session_state.messages.append(history_message)  # type: ignore

        # 2. Run the AI (Synchronously)
        with st.chat_message("assistant"):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            inputs = {"messages": st.session_state.messages[-5:],  # type: ignore
                      "language": "Français",
                      "user_profile": st.session_state.user_info
                      }

            # Container for the text stream
            message_placeholder = st.empty()
            full_response = ""

            for event in app.stream(inputs, config, stream_mode="values"):
                if "messages" in event:
                    msg = event["messages"][-1]

                    # Check if it's a final response (not a tool call)
                    if (isinstance(msg, AIMessage) and msg.content
                       and not msg.tool_calls):
                        full_response = msg.content
                        message_placeholder.markdown(full_response)

            # Save final response to history
            st.session_state.messages.append(AIMessage(content=full_response))

            if files:
                st.session_state.uploader_key += 1
                st.rerun()

            serializable_messages = []
            for m in st.session_state.messages:
                m_type = "human" if isinstance(m, HumanMessage) else "ai"
                serializable_messages.append({"type": m_type, "content": m.content})

            update_conversation_messages(st.session_state.thread_id,
                                         serializable_messages)

            st.rerun()
