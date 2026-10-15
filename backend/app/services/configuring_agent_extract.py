"""Text extract for lab files. PDF uses pypdf; docx uses python-docx. CSV and txt are text."""

from __future__ import annotations

import io
import zipfile


class UnsupportedFileType(ValueError):
    pass


class NoTextInFile(ValueError):
    pass


def file_text(data: bytes, filename: str = "") -> str:
    """Text only; see file_kind_and_text."""
    return file_kind_and_text(data, filename)[1]


def file_kind_and_text(data: bytes, filename: str = "") -> tuple[str, str]:
    """(kind, text) of an uploaded lab file; kind is pdf, docx, or txt. One path for the configuring agent and SOP parse.

    UnsupportedFileType: not PDF/DOCX/text, or a PDF/DOCX that can't be read.
    NoTextInFile: readable but no extractable text (e.g. a scanned PDF).
    """
    if not data:
        raise NoTextInFile("That file is empty.")
    kind = detect_kind(data, filename)
    try:
        text = extract_text(data, kind)
    except UnsupportedFileType:
        raise
    except Exception as exc:  # noqa: BLE001 - corrupt PDF/DOCX
        raise UnsupportedFileType(f"Could not read that {kind.upper()} file.") from exc
    if not text.strip():
        if kind == "pdf":
            raise NoTextInFile("That PDF has no extractable text (it may be a scanned image). Upload a text PDF, DOCX, or TXT.")
        raise NoTextInFile("That file has no text.")
    return kind, text


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
