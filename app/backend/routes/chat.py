from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.backend.services.groq_service import (
    GroqServiceError,
    generate_chat_completion,
    test_groq_connection,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatCompletionRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    current_step: str | None = Field(default=None, max_length=50)


@router.get("/health/groq")
def groq_health() -> dict:
    return test_groq_connection()


@router.post("/parse")
def parse_chat_message(payload: ChatCompletionRequest) -> dict:
    try:
        return generate_chat_completion(
            [
                {
                    "role": "user",
                    "content": (
                        f"Etapa atual: {payload.current_step or 'IDLE'}\n"
                        f"Mensagem: {payload.message}"
                    ),
                }
            ]
        )
    except GroqServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": str(exc), "details": exc.details},
        ) from exc

