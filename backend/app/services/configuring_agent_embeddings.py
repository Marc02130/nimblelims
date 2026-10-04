"""Local MiniLM embeddings, the same model and width RAGged uses.

``EMBEDDING_PROVIDER=stub`` returns a fixed 384-d vector and does not load the model.
"""

from __future__ import annotations

import os

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
_EMBED_BATCH = 32
_model = None


def embedding_provider() -> str:
    return (os.getenv("EMBEDDING_PROVIDER") or "local").strip().lower()


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if embedding_provider() == "stub":
        return [[0.01] * EMBEDDING_DIM for _ in texts]
    model = _get_model()
    out: list[list[float]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        batch = texts[start : start + _EMBED_BATCH]
        out.extend(list(map(float, vec)) for vec in model.embed(batch))
    return out


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _model
