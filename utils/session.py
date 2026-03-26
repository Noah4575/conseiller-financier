import streamlit as st
import extra_streamlit_components as stx
from database.database import get_user_data

COOKIE_NAME = "sgci_user_id"
COOKIE_EXPIRY_DAYS = 7


def get_cookie_manager():
    """Retourne toujours la même instance du CookieManager."""
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="cookie_manager")
    return st.session_state.cookie_manager


def restore_session_from_cookie():
    if st.session_state.get("authentified"):
        return

    cookie_manager = get_cookie_manager()
    user_id = cookie_manager.get(COOKIE_NAME)

    if user_id:
        user_data = get_user_data(user_id)
        if user_data:
            st.session_state.authentified = True
            st.session_state.user_id = user_id
            st.session_state.user_info = user_data


def save_session_to_cookie(user_id: str):
    cookie_manager = get_cookie_manager()
    cookie_manager.set(COOKIE_NAME, user_id, max_age=COOKIE_EXPIRY_DAYS * 86400)


def clear_session_cookie():
    cookie_manager = get_cookie_manager()
    cookie_manager.delete(COOKIE_NAME)