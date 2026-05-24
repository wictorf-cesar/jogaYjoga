from __future__ import annotations


def format_currency(value: float | int | None) -> str:
    if value is None:
        return "Nao informado"
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def normalize_text(value: str | None) -> str:
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    normalized = (value or "").lower().strip()
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized

