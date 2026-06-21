"""RAG chatbot endpoint — POST /ai/chat."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.services import rag_service
from app.database.session import get_db

router = APIRouter(prefix="/ai", tags=["ai"])


class RagChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class RagChatResponse(BaseModel):
    reply: str
    provider: str = "rag"
    courts_used: int = 0
    model: str | None = None
    latency_ms: float | None = None


@router.post("/chat", response_model=RagChatResponse)
def rag_chat(
    payload: RagChatRequest,
    db: Session = Depends(get_db),
) -> RagChatResponse:
    """Conversational RAG endpoint.

    Embeds the user message, retrieves relevant courts,
    builds a context, and generates a natural-language response via Groq.
    """
    result = rag_service.chat(payload.message, db=db)
    return RagChatResponse(**result)


@router.get("/rag/health")
def rag_health() -> dict:
    """Check if the RAG embedding store is ready."""
    return {
        "ready": rag_service.is_ready(),
        "courts_indexed": len(rag_service._store.espaco_ids),
    }
