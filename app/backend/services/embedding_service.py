"""Embedding service using fastembed (ONNX runtime) — all-MiniLM-L6-v2.

Loads the model once on first use (lazy singleton) and provides:
- text embedding
- cosine similarity search against a corpus

Uses fastembed's ONNX backend instead of sentence-transformers+torch, which
keeps the runtime memory footprint at ~120-180MB instead of ~500MB. This is
the difference between fitting in the Render free tier (512MB) and OOMing.
The model is the same (sentence-transformers/all-MiniLM-L6-v2) and fastembed
L2-normalizes the output by default (PooledNormalizedEmbedding), so the
embeddings are compatible with what rag_service expects.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("jogayjoga.embeddings")

# fastembed model id — same underlying model as sentence-transformers, ONNX build
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: Any = None


def _resolve_cache_dir() -> str:
    """Pick a persistent cache dir for the model download.

    Priority:
    1. SENTENCE_TRANSFORMERS_HOME env var (if set by the operator)
    2. FASTEMBED_CACHE_DIR env var (fastembed-native)
    3. A project-local ``.cache/fastembed`` dir inside the repo

    The project-local fallback matters on PaaS like Render, where the repo
    dir (/opt/render/project) persists between deploys but the default
    ~/.cache lives on the ephemeral filesystem and is lost on every spin-up.
    Pinning the cache here means the model is downloaded once and reused
    across cold starts instead of being refetched every time.
    """
    for env_var in ("SENTENCE_TRANSFORMERS_HOME", "FASTEMBED_CACHE_DIR"):
        env_home = os.getenv(env_var)
        if env_home:
            Path(env_home).mkdir(parents=True, exist_ok=True)
            return env_home

    # Project-local fallback: <repo>/.cache/fastembed
    repo_root = Path(__file__).resolve().parents[3]
    cache_dir = repo_root / ".cache" / "fastembed"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return str(cache_dir)


def _get_model() -> Any:
    """Lazy-load the fastembed TextEmbedding model (singleton)."""
    global _model
    if _model is not None:
        return _model

    try:
        from fastembed import TextEmbedding

        cache_dir = _resolve_cache_dir()
        logger.info("Carregando modelo %s (cache=%s) ...", MODEL_NAME, cache_dir)
        started = time.perf_counter()
        _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=cache_dir)
        elapsed = round(time.perf_counter() - started, 2)
        logger.info("Modelo %s carregado em %.2fs", MODEL_NAME, elapsed)
        return _model
    except ImportError:
        logger.error(
            "fastembed nao instalado — RAG desabilitado. "
            "Instale com: pip install fastembed"
        )
        raise


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string. Returns a 1-D numpy array (L2-normalized)."""
    model = _get_model()
    # fastembed.embed yields one array per input; take the first.
    return list(model.embed([text]))[0]


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed multiple texts. Returns a 2-D numpy array (n_texts, dim).

    Output is L2-normalized (fastembed PooledNormalizedEmbedding), matching
    the previous sentence-transformers(normalize_embeddings=True) behavior.
    """
    model = _get_model()
    vectors = list(model.passage_embed(texts))
    return np.vstack(vectors)


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
