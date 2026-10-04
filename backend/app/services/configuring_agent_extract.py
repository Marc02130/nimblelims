"""Text extract for lab files. PDF uses pypdf; docx uses python-docx. CSV and txt are text."""

from __future__ import annotations

import io
import zipfile


class UnsupportedFileType(ValueError):
    pass


def detect_kind(data: bytes, filename: str = "") -> str:
    lower = (filename or "").lower()
    if data.startswith(b"%PDF") or lower.endswith(".pdf"):
        if data.startswith(b"%PDF"):
            return "pdf"
    if data.startswith(b"PK\x03\x04") and _zip_has_word_document(data):
        return "docx"
    if lower.endswith(".docx"):
        return "docx"
    if _looks_like_text(data) or lower.endswith((".txt", ".csv", ".md", ".json")):
        return "txt"
    raise UnsupportedFileType("Unsupported file type. Use PDF, DOCX, TXT, CSV, MD, or JSON.")


def extract_text(data: bytes, kind: str) -> str:
    if kind == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if kind == "docx":
        from docx import Document

        document = Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs).strip()
    if kind == "txt":
        if data.startswith(b"\xef\xbb\xbf"):
            return data.decode("utf-8-sig")
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("cp1252")
    raise UnsupportedFileType("Unsupported file type")


def _zip_has_word_document(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return "word/document.xml" in zf.namelist()
    except zipfile.BadZipFile:
        return False


def _looks_like_text(data: bytes) -> bool:
    if not data or data.count(b"\x00") / len(data) > 0.01:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False
