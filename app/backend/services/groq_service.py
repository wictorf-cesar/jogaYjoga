from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.backend.utils.logger import log_error, log_event, mask_secret

def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


try:
    from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq, RateLimitError
except ImportError:  # pragma: no cover - exercised only when dependency is missing locally.
    class RateLimitError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    class APIStatusError(Exception):
        pass

    Groq = None


GROQ_MODEL = os.getenv("JOGAYJOGA_AI_MODEL", "llama-3.3-70b-versatile")
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS", "12"))
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com")

SYSTEM_PROMPT = """
Voce e um parser de reservas esportivas.
Voce deve retornar SOMENTE JSON valido.
Nunca explique nada.
Nunca responda texto normal.

Domínio permitido: reservas esportivas, busca de quadras, horários, cancelamento,
favoritos, pagamentos e reservas do usuário.

Intents permitidas:
- CREATE_RESERVATION
- ASK_AVAILABLE_VENUES
- SELECT_VENUE
- ASK_AVAILABLE_TIMES
- SELECT_TIME
- CONFIRM_RESERVATION
- CANCEL_RESERVATION
- OUT_OF_SCOPE
- CHANGE_RESERVATION_CONTEXT

Campos esperados:
{
  "intent": "CREATE_RESERVATION",
  "sport": "futebol | beach_tennis | tenis | volei | futevolei | null",
  "city": "Recife | Olinda | null",
  "date_relative": "hoje | amanha | null",
  "date_text": "texto original de data ou null",
  "time_text": "HH:MM ou null",
  "venue_text": "nome da quadra ou null",
  "venue_number": 1,
  "slot_number": 1,
  "reservation_id": 123,
  "confirmation": false,
  "in_scope": true
}

Regras:
- "pelada", "bater bola" e "jogar bola" significam futebol.
- "marcar", "agendar" e "reservar" indicam CREATE_RESERVATION.
- "horarios?", "tem horario?" e "quais horarios?" indicam ASK_AVAILABLE_TIMES, nao SELECT_VENUE.
- Se o usuario mudar esporte, cidade ou data, use CHANGE_RESERVATION_CONTEXT.
- Se estiver fora do dominio, use OUT_OF_SCOPE e in_scope=false.
""".strip()


class GroqServiceError(RuntimeError):
    def __init__(self, message: str, *, code: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True)
class GroqHealth:
    status: str
    latency_ms: float | None
    model: str
    key_loaded: bool
    sdk_loaded: bool
    detail: str | None = None


def validate_groq_environment() -> None:
    api_key = get_groq_api_key()
    log_event("ENV", "GROQ_API_KEY carregada", loaded=bool(api_key))
    log_event("ENV", "GROQ_API_KEY length", length=len(api_key or ""))
    log_event("ENV", "GROQ_API_KEY masked", key=mask_secret(api_key))
    log_event(
        "ENV",
        "Groq SDK/config",
        sdk_loaded=Groq is not None,
        model=GROQ_MODEL,
        base_url=GROQ_BASE_URL,
        timeout_seconds=GROQ_TIMEOUT_SECONDS,
        source="env",
    )
    if not api_key:
        log_event("GROQ BLOCKED", "GROQ_API_KEY ausente; nenhuma request sera enviada")
    if Groq is None:
        log_event("GROQ BLOCKED", "Pacote groq nao instalado; nenhuma request sera enviada")


def get_groq_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY")


def get_groq_client() -> Any:
    api_key = get_groq_api_key()
    if Groq is None:
        raise GroqServiceError(
            "Pacote groq nao instalado.",
            code="missing_groq_sdk",
            details={"install": "uv add groq"},
        )
    if not api_key:
        raise GroqServiceError(
            "GROQ_API_KEY nao configurada.",
            code="missing_api_key",
        )
    return Groq(api_key=api_key, base_url=GROQ_BASE_URL, timeout=GROQ_TIMEOUT_SECONDS)


def sanitize_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    sanitized = []
    for message in messages:
        content = message.get("content", "")
        sanitized.append(
            {
                "role": message.get("role", ""),
                "content": content[:1500] + "...[truncated]" if len(content) > 1500 else content,
            }
        )
    return sanitized


def extract_json_object(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise GroqServiceError("Resposta vazia da Groq.", code="empty_response")

    cleaned = text.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fenced_match:
        try:
            return json.loads(fenced_match.group(1))
        except json.JSONDecodeError:
            pass

    object_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if object_match:
        try:
            return json.loads(object_match.group(0))
        except json.JSONDecodeError as exc:
            raise GroqServiceError(
                "Resposta da Groq nao e JSON valido mesmo apos tentativa de correcao.",
                code="invalid_json",
                details={"raw_response": cleaned[:2000]},
            ) from exc

    raise GroqServiceError(
        "Resposta da Groq nao contem objeto JSON.",
        code="invalid_json",
        details={"raw_response": cleaned[:2000]},
    )


def generate_chat_completion(messages: list[dict[str, str]]) -> dict[str, Any]:
    request_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    log_event(
        "GROQ REQUEST",
        "Request iniciado",
        model=GROQ_MODEL,
        timeout_seconds=GROQ_TIMEOUT_SECONDS,
        stream=False,
        messages=sanitize_messages(request_messages),
    )

    started_at = time.perf_counter()
    try:
        client = get_groq_client()
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=request_messages,
            temperature=0,
            response_format={"type": "json_object"},
            stream=False,
        )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        content = completion.choices[0].message.content if completion.choices else None
        log_event(
            "GROQ RESPONSE",
            "Resposta recebida",
            latency_ms=latency_ms,
            model=GROQ_MODEL,
            raw_response=(content or "")[:2000],
        )
        parsed = extract_json_object(content or "")
        log_event("GROQ PARSED", "JSON parseado", parsed=parsed)
        return parsed
    except RateLimitError as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_error("GROQ ERROR", "Rate limit da Groq", exc, latency_ms=latency_ms)
        raise GroqServiceError("Rate limit da Groq.", code="rate_limit") from exc
    except APITimeoutError as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_error("GROQ ERROR", "Timeout na Groq", exc, latency_ms=latency_ms, timeout_seconds=GROQ_TIMEOUT_SECONDS)
        raise GroqServiceError("Timeout na Groq.", code="timeout") from exc
    except APIConnectionError as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_error("GROQ ERROR", "Erro de conexao com Groq", exc, latency_ms=latency_ms)
        raise GroqServiceError("Erro de conexao com Groq.", code="connection_error") from exc
    except APIStatusError as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_error(
            "GROQ ERROR",
            "Erro HTTP da Groq",
            exc,
            latency_ms=latency_ms,
            status_code=getattr(exc, "status_code", None),
            response=getattr(exc, "response", None),
        )
        raise GroqServiceError("Erro HTTP da Groq.", code="api_status_error") from exc
    except GroqServiceError:
        raise
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_error("GROQ ERROR", "Erro inesperado chamando Groq", exc, latency_ms=latency_ms)
        raise GroqServiceError("Erro inesperado chamando Groq.", code="unexpected_error") from exc


def test_groq_connection() -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        parsed = generate_chat_completion(
            [{"role": "user", "content": "quero marcar futebol amanha no Recife"}]
        )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "model": GROQ_MODEL,
            "parsed": parsed,
        }
    except GroqServiceError as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "model": GROQ_MODEL,
            "error_code": exc.code,
            "error": str(exc),
            "details": exc.details,
        }


if __name__ == "__main__":
    validate_groq_environment()
    result = test_groq_connection()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
