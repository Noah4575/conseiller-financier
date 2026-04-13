import streamlit as st
import torch
import tempfile
import os
import whisper  # type: ignore


@st.cache_resource
def load_whisper_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(device)
    return whisper.load_model("turbo").to(device)


def transcribe_audio(audio_data):

    model = load_whisper_model()

    with tempfile.NamedTemporaryFile(
            delete=False, suffix=".wav") as tmp_file:
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

    return transcribed_text
