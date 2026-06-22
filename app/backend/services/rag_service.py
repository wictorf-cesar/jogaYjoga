"""RAG (Retrieval-Augmented Generation) service for jogaYjoga.

Builds an in-memory embedding index of all courts on startup, then:
1. Embeds the user query
2. Retrieves the top-k most relevant courts via cosine similarity
3. Builds a context string with court details
4. Sends context + query to Groq with a structured system prompt
5. Returns the LLM-generated answer
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.backend.services.embedding_service import (
    cosine_similarity_search,
    embed_text,
    embed_texts,
)
from app.backend.services.groq_service import (
    GroqServiceError,
    get_groq_api_key,
)
from app.models.entities import Avaliacao, Espaco

logger = logging.getLogger("jogayjoga.rag")

# ── System prompt for RAG chatbot ──

SYSTEM_PROMPT = """\
Voce e o assistente virtual do jogaYjoga, um app de busca e reserva de quadras \
esportivas na regiao metropolitana do Recife.

## Regras
- Responda SEMPRE em portugues brasileiro (pt-BR).
- Use APENAS as informacoes do CONTEXTO abaixo para responder. Nao invente dados.
- Se o contexto nao tiver informacao suficiente, diga que nao encontrou e sugira \
  que o usuario reformule a pergunta.
- Quando recomendar quadras, inclua: nome, bairro/cidade, esportes, cobertura, \
  preco por hora e numero de quadras.
- Se o usuario parecer pronto para reservar, sugira que use o menu "Reservar quadra" \
  ou diga "quero reservar [nome da quadra]".
- Seja conciso, amigavel e direto. Use emojis com moderacao (1-2 por mensagem).
- Nunca responda perguntas fora do escopo (receitas, politica, etc). Diga educadamente \
  que so pode ajudar com quadras esportivas.
- Se o usuario perguntar por comparativos (mais barata, melhor avaliada, mais perto), \
  analise os dados do contexto e responda factualmente.
- Formate precos como R$ XX,XX.

## Contexto das quadras
{context}
""".strip()

# ── In-memory embedding store ──

TOP_K = 5
MIN_SIMILARITY = 0.15


@dataclass
class EmbeddingStore:
    """Holds court embeddings in memory."""

    texts: list[str] = field(default_factory=list)
    espaco_ids: list[int] = field(default_factory=list)
    espaco_data: list[dict[str, Any]] = field(default_factory=list)
    embeddings: np.ndarray | None = None
    ready: bool = False


_store = EmbeddingStore()


def _build_court_text(espaco: dict[str, Any]) -> str:
    """Build a rich text chunk for a single court for embedding."""
    parts = [f"Quadra: {espaco['nome']}"]

    endereco = espaco.get("endereco") or {}
    location_parts = [
        endereco.get("bairro"),
        endereco.get("municipio"),
        endereco.get("estado"),
    ]
    location = ", ".join(p for p in location_parts if p)
    if location:
        parts.append(f"Local: {location}")

    esportes = espaco.get("esportes") or []
    if esportes:
        parts.append(f"Esportes: {', '.join(esportes)}")

    cobertura = espaco.get("cobertura")
    if cobertura:
        parts.append(f"Cobertura: {cobertura}")

    preco = espaco.get("preco_hora")
    if preco is not None:
        parts.append(f"Preco: R$ {preco:.2f}/hora")

    qtd = espaco.get("qtd_quadras")
    if qtd:
        parts.append(f"Quantidade de quadras: {qtd}")

    nota = espaco.get("media_avaliacoes")
    if nota:
        parts.append(f"Avaliacao media: {nota:.1f}/5")

    return ". ".join(parts)


def _build_context_block(espaco_data: dict[str, Any]) -> str:
    """Build a context block for a single court to inject into the prompt."""
    lines = [f"🏟️ {espaco_data['nome']}"]

    endereco = espaco_data.get("endereco") or {}
    location_parts = [
        endereco.get("logradouro"),
        endereco.get("bairro"),
        endereco.get("municipio"),
        endereco.get("estado"),
    ]
    location = ", ".join(p for p in location_parts if p)
    if location:
        lines.append(f"   Endereco: {location}")

    esportes = espaco_data.get("esportes") or []
    if esportes:
        lines.append(f"   Esportes: {', '.join(esportes)}")

    cobertura = espaco_data.get("cobertura")
    if cobertura:
        lines.append(f"   Cobertura: {cobertura}")

    preco = espaco_data.get("preco_hora")
    if preco is not None:
        lines.append(f"   Preco: R$ {preco:.2f}/hora")
    else:
        lines.append("   Preco: nao informado")

    qtd = espaco_data.get("qtd_quadras")
    if qtd:
        lines.append(f"   Quadras disponiveis: {qtd}")

    nota = espaco_data.get("media_avaliacoes")
    if nota:
        lines.append(f"   Avaliacao media: {nota:.1f}/5")

    return "\n".join(lines)


def build_embeddings(db: Session) -> None:
    """Load all courts from DB, generate embeddings, and store in memory."""
    global _store

    logger.info("Gerando embeddings das quadras...")
    started = time.perf_counter()

    espacos = db.scalars(select(Espaco).order_by(Espaco.id_espaco)).unique().all()
    if not espacos:
        logger.warning("Nenhuma quadra encontrada — embeddings vazios.")
        _store = EmbeddingStore()
        return

    texts: list[str] = []
    ids: list[int] = []
    data: list[dict[str, Any]] = []

    for espaco in espacos:
        espaco_dict = espaco.to_dict()

        # Enrich with average rating
        avg_nota = db.scalar(
            select(func.avg(Avaliacao.nota)).where(
                Avaliacao.id_espaco == espaco.id_espaco
            )
        )
        if avg_nota is not None:
            espaco_dict["media_avaliacoes"] = round(float(avg_nota), 1)

        text = _build_court_text(espaco_dict)
        texts.append(text)
        ids.append(espaco.id_espaco)
        data.append(espaco_dict)

    embeddings = embed_texts(texts)

    _store = EmbeddingStore(
        texts=texts,
        espaco_ids=ids,
        espaco_data=data,
        embeddings=embeddings,
        ready=True,
    )

    elapsed = round(time.perf_counter() - started, 2)
    logger.info(
        "Embeddings gerados: %d quadras em %.2fs (dim=%d)",
        len(texts),
        elapsed,
        embeddings.shape[1] if embeddings is not None else 0,
    )


def is_ready() -> bool:
    """Check if the embedding store is loaded and ready."""
    return _store.ready and _store.embeddings is not None


def retrieve(query: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
    """Retrieve the top-k most relevant courts for a query."""
    if not is_ready():
        logger.warning("Embedding store nao esta pronto — retornando vazio.")
        return []

    query_embedding = embed_text(query)
    results = cosine_similarity_search(query_embedding, _store.embeddings, top_k=top_k)

    retrieved = []
    for idx, score in results:
        if score < MIN_SIMILARITY:
            continue
        court = _store.espaco_data[idx].copy()
        court["_similarity"] = round(score, 4)
        retrieved.append(court)

    logger.info(
        "Retrieve: query=%r, results=%d, scores=%s",
        query[:80],
        len(retrieved),
        [r["_similarity"] for r in retrieved],
    )
    return retrieved


def build_context(courts: list[dict[str, Any]]) -> str:
    """Build the context string to inject into the system prompt."""
    if not courts:
        return "Nenhuma quadra encontrada para essa busca."
    blocks = [_build_context_block(court) for court in courts]
    return "\n\n".join(blocks)


def chat(query: str, db: Session | None = None) -> dict[str, Any]:
    """Full RAG pipeline: retrieve → build context → call LLM → return response.

    Returns a dict with: reply, provider, courts_used, model.
    """
    if not get_groq_api_key():
        return {
            "reply": (
                "O assistente de IA esta temporariamente indisponivel "
                "(GROQ_API_KEY ausente). Tente novamente mais tarde."
            ),
            "provider": "fallback",
            "courts_used": 0,
        }

    if not is_ready():
        # Try to build embeddings on the fly if DB session provided.
        # build_embeddings can raise ImportError if sentence-transformers
        # is not installed (startup may have swallowed it) — absorb it here
        # so we degrade to the loading fallback instead of a 500.
        if db is not None:
            try:
                build_embeddings(db)
            except ImportError as exc:
                logger.warning(
                    "Nao foi possivel gerar embeddings (%s). "
                    "RAG indisponivel ate instalar sentence-transformers.",
                    exc,
                )
        if not is_ready():
            return {
                "reply": (
                    "O sistema de busca ainda esta carregando. "
                    "Tente novamente em alguns segundos."
                ),
                "provider": "loading",
                "courts_used": 0,
            }

    # 1. Retrieve relevant courts
    courts = retrieve(query)

    # 2. Build context
    context = build_context(courts)

    # 3. Build messages with system prompt
    system_prompt = SYSTEM_PROMPT.format(context=context)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    # 4. Call Groq (reuse the existing service, but for free-form generation)
    try:
        from app.backend.services.groq_service import (
            GROQ_MODEL,
            get_groq_client,
        )

        logger.info(
            "RAG chat: query=%r, courts=%d, model=%s",
            query[:80],
            len(courts),
            GROQ_MODEL,
        )

        started = time.perf_counter()
        client = get_groq_client()
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
            stream=False,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        reply = (
            completion.choices[0].message.content
            if completion.choices
            else "Desculpe, nao consegui gerar uma resposta."
        )

        logger.info(
            "RAG response: latency=%.2fms, reply_len=%d", latency_ms, len(reply)
        )

        return {
            "reply": reply,
            "provider": "rag",
            "model": GROQ_MODEL,
            "courts_used": len(courts),
            "latency_ms": latency_ms,
        }

    except GroqServiceError as exc:
        logger.error("RAG Groq error: %s (code=%s)", exc, exc.code)
        return {
            "reply": (
                "Desculpe, o assistente esta com dificuldades no momento. "
                "Tente novamente em instantes."
            ),
            "provider": "error",
            "error": str(exc),
            "courts_used": len(courts),
        }

    except Exception as exc:
        # Catch native groq SDK errors (groq.AuthenticationError,
        # RateLimitError, APITimeoutError, APIConnectionError, APIStatusError)
        # and any other failure from the create() call. These are NOT
        # subclasses of GroqServiceError, so without this they would escape
        # as an unhandled 500 with a full stacktrace in the response.
        name = type(exc).__name__
        if name == "AuthenticationError":
            logger.error("RAG Groq auth error: %s", exc)
            reply = (
                "O assistente de IA esta temporariamente indisponivel. "
                "Tente novamente mais tarde."
            )
        elif name == "RateLimitError":
            logger.warning("RAG Groq rate limit: %s", exc)
            reply = (
                "O assistente recebeu muitas requisicoes agora. "
                "Aguarde alguns segundos e tente novamente."
            )
        elif name in ("APITimeoutError", "APIConnectionError"):
            logger.warning("RAG Groq connection/timeout: %s", exc)
            reply = (
                "Tive dificuldade para falar com o servico de IA. "
                "Tente novamente em instantes."
            )
        else:
            logger.error("RAG Groq unexpected error (%s): %s", name, exc)
            reply = (
                "Desculpe, o assistente esta com dificuldades no momento. "
                "Tente novamente em instantes."
            )
        return {
            "reply": reply,
            "provider": "error",
            "error": f"{name}: {exc}",
            "courts_used": len(courts),
        }
