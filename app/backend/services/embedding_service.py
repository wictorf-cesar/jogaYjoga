"""Embedding service using sentence-transformers (all-MiniLM-L6-v2).

Loads the model once on first use (lazy singleton) and provides:
- text embedding
- cosine similarity search against a corpus
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

logger = logging.getLogger("jogayjoga.embeddings")

MODEL_NAME = "all-MiniLM-L6-v2"

_model: Any = None


def _get_model() -> Any:
    """Lazy-load the SentenceTransformer model (singleton)."""
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Carregando modelo %s ...", MODEL_NAME)
        started = time.perf_counter()
        _model = SentenceTransformer(MODEL_NAME)
        elapsed = round(time.perf_counter() - started, 2)
        logger.info("Modelo %s carregado em %.2fs", MODEL_NAME, elapsed)
        return _model
    except ImportError:
        logger.error(
            "sentence-transformers nao instalado — RAG desabilitado. "
            "Instale com: pip install sentence-transformers"
        )
        raise


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string. Returns a 1-D numpy array."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed multiple texts. Returns a 2-D numpy array (n_texts, dim)."""
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def cosine_similarity_search(
    query_embedding: np.ndarray,
    corpus_embeddings: np.ndarray,
    top_k: int = 5,
) -> list[tuple[int, float]]:
    """Return top-k (index, score) pairs sorted by descending similarity.

    Both query and corpus embeddings are expected to be L2-normalized,
    so dot product == cosine similarity.
    """
    scores = corpus_embeddings @ query_embedding
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_indices]
