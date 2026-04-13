import streamlit as st
from database.database import (create_user, get_segment,
                               verify_user)
# from utils.session import save_session_to_cookie


def show_auth_page():
    st.title("🔐 Connexion SGCI conseiller financier")

    tab_login, tab_register = st.tabs(["Connexion", "Inscription"])

    with tab_login:
        _show_login_form()

    with tab_register:
        _show_register_form()


def _show_login_form():
    user_id = st.text_input("ID Client")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        user_data = verify_user(user_id, password)
        if user_data:
            st.session_state.authentified = True
            st.session_state.user_id = user_id
            st.session_state.user_info = user_data
            # save_session_to_cookie(user_id)
            st.success(f"Bienvenue {user_data['prénom']} {user_data['nom']} !")
            st.rerun()
        else:
            st.error("ID ou mot de passe incorrect. Veuillez réessayer.")


def _show_register_form():
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
        new_revenus = st.number_input("Revenus mensuels (FCFA)", min_value=0,
                                      step=100000)
        with st.expander("Lire les Conditions Générales d'Utilisation"):
            try:
                with open("cgu.txt", "r", encoding="utf-8") as f:
                    st.write(f.read())
            except FileNotFoundError:
                st.error("Le fichier cgu.txt est introuvable à la racine "
                         "du projet.")
        cgu = st.checkbox("J'accepte les CGU", key="accept_cgu")

    new_segment = get_segment(new_solde)

    if st.button("S'inscrire", disabled=not cgu):
        if not new_pswd.strip():
            st.warning("Le mot de passe ne peut pas être vide.")
            return False
        if new_id and new_nom and new_prenom and new_pswd:
            success, message = create_user(
                new_id, new_pswd, new_nom, new_prenom,
                new_segment, new_solde, new_revenus
            )
            if success:
                st.success(message + " Vous pouvez vous connecter.")
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Veuillez remplir tous les champs pour "
                       "créer un compte.")

    if not cgu:
        st.caption("⚠️ Vous devez accepter les CGU pour créer un compte.")
