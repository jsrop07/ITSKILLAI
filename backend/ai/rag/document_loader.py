import os
import fitz  # PyMuPDF
from docx import Document


def load_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return load_pdf_text(file_path)

    if ext == ".docx":
        return load_docx_text(file_path)

    if ext == ".txt":
        return load_txt_text(file_path)

    raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")


def load_pdf_text(file_path: str) -> str:
    texts = []

    with fitz.open(file_path) as doc:
        for page in doc:
            text = page.get_text()
            if text:
                texts.append(text)

    return "\n".join(texts)


def load_docx_text(file_path: str) -> str:
    document = Document(file_path)
    texts = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            texts.append(paragraph.text.strip())

    return "\n".join(texts)


def load_txt_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()