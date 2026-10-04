"""Chunk lab files the way RAGged does: heading-aware splits, 1000 chars, 200 overlap.

Copied from RAGged ``api/app/services/chunk.py`` (split_text / split_with_headings only).
"""

from __future__ import annotations

import re

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
_NUMBERED = re.compile(r"^\d+(\.\d+)*\.?\s+\S")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    separators: list[str] | None = None,
) -> list[str]:
    separators = separators if separators is not None else DEFAULT_SEPARATORS
    text = text.strip()
    if not text:
        return []
    chunks = _split(text, chunk_size, separators)
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    merged: list[str] = []
    for chunk in chunks:
        if not merged:
            merged.append(chunk)
            continue
        prev = merged[-1]
        prefix = prev[-overlap:] if len(prev) > overlap else prev
        combined = prefix + chunk if not chunk.startswith(prefix) else chunk
        if len(combined) <= chunk_size + overlap:
            merged.append(combined)
        else:
            merged.append(chunk)
    return merged


def _split(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    if not separators:
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
    sep, rest = separators[0], separators[1:]
    if sep == "":
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
    pieces = text.split(sep)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = piece if current == "" else current + sep + piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.extend(_split(current, chunk_size, rest))
        current = piece
    if current:
        chunks.extend(_split(current, chunk_size, rest))
    return [c for c in chunks if c]


def looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 3 or len(stripped) > 90:
        return False
    if stripped.endswith((",", ";", ":")):
        return False
    words = stripped.split()
    if len(words) > 14:
        return False
    if _NUMBERED.match(stripped):
        return True
    letters = [w for w in words if re.search(r"[A-Za-z]", w)]
    if not letters:
        return False
    if stripped.isupper() and len(words) <= 10:
        return True
    titled = sum(1 for w in letters if w[:1].isupper())
    if titled >= max(1, int(0.6 * len(letters))) and not stripped.endswith((".", "?", "!")):
        return True
    return False


def split_with_headings(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[tuple[str, str]]:
    heading = ""
    buf = ""
    out: list[tuple[str, str]] = []
    for line in text.splitlines(keepends=True):
        if looks_like_heading(line):
            if buf.strip():
                for piece in split_text(buf, chunk_size, overlap):
                    out.append((piece, heading))
                buf = ""
            heading = line.strip()
            continue
        buf += line
    if buf.strip():
        for piece in split_text(buf, chunk_size, overlap):
            out.append((piece, heading))
    return out or [(piece, "") for piece in split_text(text, chunk_size, overlap)]
