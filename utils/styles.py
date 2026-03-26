import streamlit as st


def inject_styles():
    with open("assets/style.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
