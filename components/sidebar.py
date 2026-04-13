import datetime
import os

from dotenv import load_dotenv
import streamlit as st

from database.database import (
    delete_conversation, get_user_conversations, create_new_conversation,
    get_all_users, delete_user, update_user, get_segment
)
from components.notifs import get_notif_solde
# from utils.session import clear_session_cookie
from config import get_welcome_message
from utils.session import switch_conversation, reset_session

load_dotenv()

WELCOME_MESSAGE = get_welcome_message()


def show_popups(user_info):
    """Affiche la cloche de notifications en haut à droite."""
    notifs = get_notif_solde(user_info)
    count = len(notifs)

    SIMULATOR_URL = os.getenv("SIMULATOR_URL")

    _, col_notif, col_sim = st.columns([0.8, 0.1, 0.1])

    with col_sim:
        st.link_button("Sim crédit", url=SIMULATOR_URL)  # type: ignore
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
        reset_session()
        st.session_state.authentified = False
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
            reset_session()
            st.session_state.authentified = False
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
        switch_conversation()
        st.rerun()

    user_convs = get_user_conversations(st.session_state.user_id)

    for conv in user_convs:
        col_title, col_del = st.sidebar.columns([0.8, 0.2])
        with col_title:
            if st.button(f"💬 {conv['title']}", key=conv['id'],
                         use_container_width=True):
                switch_conversation(conv)
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{conv['id']}",
                         help="Supprimer cette conversation",
                         use_container_width=False):
                _confirm_delete_conv(conv)

    return user_convs


@st.dialog("Supprimer la conversation")
def _confirm_delete_conv(conv):
    st.write(f"Supprimer **{conv['title']}** ?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirmer", type="primary", use_container_width=True):
            delete_conversation(conv['id'])
            # Si on supprime la conv active, on réinitialise
            if st.session_state.get("thread_id") == conv['id']:
                reset_session()
            st.rerun()
    with col2:
        if st.button("Annuler", use_container_width=True):
            st.rerun()
