import base64
import pypdf


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
            pdf_name = f"\n[Contenu du PDF: {uploaded_file.name}]\n"
            pdf_text = pdf_name
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() + "\n"
            return {"type": "text",
                    "text": pdf_text,
                    "display_text": pdf_name}
        except Exception:
            return {
                "type": "text",
                "text": f"Erreur de lecture du PDF {uploaded_file.name}"
                }

    return None
