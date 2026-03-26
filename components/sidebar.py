import datetime

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from database.database import (
    get_user_conversations, create_new_conversation,
    get_all_users, delete_user, update_user, get_segment
)
from components.notifs import get_notif_solde
from utils.session import clear_session_cookie
from config import get_welcome_message

WELCOME_MESSAGE = get_welcome_message()


def show_popups(user_info):
    """Affiche la cloche de notifications en haut à droite."""
    notifs = get_notif_solde(user_info)
    count = len(notifs)

    SIMULATOR_URL = "https://sgci-perso-cred.onrender.com/"

    _, col_notif, col_sim = st.columns([0.8, 0.1, 0.1])

    with col_sim:
        st.link_button("Sim crédit", url=SIMULATOR_URL)
    with col_notif:
        label = f"🔔 ({count})" if count > 0 else "🔔"
        with st.popover(label):
            st.markdown("### Notifications")
            if count > 0:
                for n in notifs:
                    st.info(f"**{n['type']}** : {n['message']}")
            else:
                st.write("Aucune notification")


def show_sidebar(user) -> list:
    """Affiche la sidebar complète et retourne la liste des conversations."""
    st.sidebar.title(f"👤 Bonjour {user['prénom']} {user['nom']}")
    st.sidebar.info(
        f"Segment : {str(user['segment'])}\n"
        f"\nSolde : {int(user['solde']):,} FCFA\n"
        f"\nRevenus : {int(user['revenus']):,} FCFA"
    )

    _show_profile_update(user)
    _show_logout_button()
    _show_admin_panel(user)
    _show_delete_account(user)

    return _show_conversation_history()


# --- Sections internes (non exportées) ---

def _show_profile_update(user):
    with st.sidebar.expander("✏️ Mettre à jour mon profil"):
        new_solde = st.number_input(
            "Mettre à jour mon solde (FCFA)",
            min_value=0, value=int(user['solde']),
            step=100000, key="update_solde"
        )
        new_revenus = st.number_input(
            "Mettre à jour mes revenus (FCFA)",
            min_value=0, value=int(user['revenus']),
            step=100000, key="update_revenus"
        )
        if st.button("💾 Sauvegarder", use_container_width=True):
            new_segment = get_segment(new_solde)
            update_user(st.session_state.user_id, new_solde, new_revenus,
                        new_segment)
            st.session_state.user_info["solde"] = new_solde
            st.session_state.user_info["revenus"] = new_revenus
            st.session_state.user_info["segment"] = new_segment
            st.success("Profil mis à jour !")
            st.rerun()


def _show_logout_button():
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        # clear_session_cookie()
        st.session_state.authentified = False
        st.session_state.user_id = None
        st.session_state.user_info = None
        st.session_state.messages = []
        st.rerun()


@st.dialog("Supprimer mon compte")
def _confirm_delete_dialog(user):
    st.warning("⚠️ Cette action est irréversible. Toutes vos conversations"
               " seront supprimées.")
    st.write(f"Voulez-vous vraiment supprimer le compte **{user['prénom']} "
             f"{user['nom']}** ?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Oui, supprimer", type="primary",
                     use_container_width=True):
            delete_user(user['id'])
            # clear_session_cookie()
            st.session_state.authentified = False
            st.session_state.user_id = None
            st.session_state.user_info = None
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("Annuler", use_container_width=True):
            st.rerun()


def _show_delete_account(user):
    if st.sidebar.button("❌ Supprimer mon compte", use_container_width=True):
        _confirm_delete_dialog(user)


def _show_admin_panel(user):
    if user.get("role") != "admin":
        return

    st.sidebar.divider()
    st.sidebar.subheader("🛠️ Administration")

    users = get_all_users()
    user_list = [f"{u['id']} - {u['prénom']} {u['nom']}" for u in users]
    selected_user_str = st.sidebar.selectbox(
            "Sélectionner un compte à supprimer", user_list)

    if st.sidebar.button("❌ Supprimer ce compte", type="primary",
                         use_container_width=True):
        target_id = selected_user_str.split(" - ")[0]
        if delete_user(target_id):
            st.sidebar.success(f"Compte {target_id} supprimé.")
            st.rerun()


def _show_conversation_history() -> list:
    st.sidebar.divider()
    st.sidebar.subheader("Historique des conversations")

    if st.sidebar.button("➕ Nouvelle conversation"):
        timestamp = datetime.datetime.now().strftime('%d/%m %H:%M')
        new_conv_id = create_new_conversation(
            st.session_state.user_id,
            title=f"Discussion du {timestamp}"
        )
        st.session_state.thread_id = new_conv_id
        st.session_state.messages = [AIMessage(content=WELCOME_MESSAGE)]
        st.rerun()

    user_convs = get_user_conversations(st.session_state.user_id)

    for conv in user_convs:
        if st.sidebar.button(f"💬 {conv['title']}", key=conv['id'],
                             use_container_width=True):
            st.session_state.thread_id = conv['id']
            loaded_messages = [
                HumanMessage(content=m['content']) if m['type'] == 'human'
                else AIMessage(content=m['content'])
                for m in conv['messages']
            ]
            st.session_state.messages = loaded_messages
            st.rerun()

    return user_convs
