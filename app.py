import streamlit as st
from database.database import init_db
# from utils.session import restore_session_from_cookie
from views.auth import show_auth_page
from views.chat import show_chat_page
from utils.styles import inject_styles

st.set_page_config(page_title="Conseiller Financier IA", layout="wide",
                   initial_sidebar_state="expanded")

inject_styles()
init_db()
# restore_session_from_cookie()

if "authentified" not in st.session_state:
    st.session_state.authentified = False

if not st.session_state.authentified:
    show_auth_page()
else:
    show_chat_page()
