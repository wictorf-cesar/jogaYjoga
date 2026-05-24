from __future__ import annotations

import os
from typing import Any

import requests

API_URL = os.getenv("JOGAYJOGA_API_URL", "http://localhost:8000").rstrip("/")
DEFAULT_TIMEOUT_SECONDS = 10


def auth_headers(token: str | None = None) -> dict[str, str] | None:
    return {"Authorization": f"Bearer {token}"} if token else None


def request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[Any | None, str | None]:
    try:
        response = requests.request(
            method,
            f"{API_URL}{path}",
            json=payload,
            headers=auth_headers(token),
            timeout=timeout,
        )
    except requests.RequestException:
        return None, "Nao foi possivel conectar ao backend."

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        return None, detail or "Erro na requisicao."

    if response.status_code == 204:
        return {}, None
    return response.json(), None

