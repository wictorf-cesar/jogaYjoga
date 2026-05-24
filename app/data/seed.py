"""
Seed script for the local SQLite database.

Run from the project root:
    python -m app.data.seed
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DBConfig
from app.database.handler import DBHandler
from app.models.entities import (
    Base,
    Endereco,
    Espaco,
    Esporte,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
CSV_CANDIDATES = (
    ROOT_DIR / "Quadras.csv",
    ROOT_DIR / "app" / "Quadras.csv",
    ROOT_DIR / "app" / "data" / "Quadras.csv",
)

def find_csv_path() -> Path | None:
    return next((path for path in CSV_CANDIDATES if path.exists()), None)


def parse_endereco(raw: str) -> dict:
    cep_match = re.search(r"(\d{5}-?\d{3})", raw)
    cep = cep_match.group(1) if cep_match else None
    clean = re.sub(r",?\s*\d{5}-?\d{3}", "", raw).strip().rstrip(",")

    state_match = re.search(r"-\s*([A-Z]{2})\s*$", clean)
    state = state_match.group(1) if state_match else None
    if state_match:
        clean = clean[: state_match.start()].strip().rstrip("-").strip()

    parts = [part.strip() for part in clean.split(",") if part.strip()]
    street = parts[0] if parts else None
    city = parts[-1] if len(parts) >= 2 else None
    neighborhood = ", ".join(parts[1:-1]) if len(parts) >= 3 else None

    if neighborhood and " - " in neighborhood:
        neighborhood = neighborhood.rsplit(" - ", 1)[-1].strip()

    return {
        "cep": cep,
        "logradouro": street,
        "bairro": neighborhood,
        "nome_municipio": city,
        "nome_estado": state,
    }


def parse_latlong(raw: str) -> tuple[float | None, float | None]:
    try:
        latitude, longitude = raw.split(",", maxsplit=1)
        return float(latitude.strip()), float(longitude.strip())
    except (AttributeError, ValueError):
        return None, None


def parse_cobertura(raw: str) -> str:
    normalized = (raw or "").strip().lower()
    if "telhado" in normalized:
        return "Telhado"
    if "tela" in normalized:
        return "Tela"
    return "Nenhuma"


def load_space_rows() -> list[dict[str, str]]:
    csv_path = find_csv_path()
    if not csv_path:
        expected = ", ".join(str(path) for path in CSV_CANDIDATES)
        raise FileNotFoundError(f"Quadras.csv nao encontrado. Locais esperados: {expected}")

    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def get_row_value(row: dict[str, str], *names: str, default: str = "") -> str:
    normalized = {key.strip().upper(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.upper())
        if value is not None:
            return value
    return default


def parse_float(value: str) -> float | None:
    value = (value or "").strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def reset_database() -> None:
    Base.metadata.drop_all(bind=DBConfig.engine)
    Base.metadata.create_all(bind=DBConfig.engine)


def seed(reset: bool = True) -> None:
    if reset:
        reset_database()
        print("Tabelas recriadas.")
    else:
        DBHandler()

    with Session(DBConfig.engine) as db:
        esportes_cache: dict[str, Esporte] = {}
        espacos_criados: list[Espaco] = []

        for row in load_space_rows():
            endereco = Endereco(
                **parse_endereco(get_row_value(row, "ENDERECO", "ENDEREÇO"))
            )
            db.add(endereco)
            db.flush()

            nomes_esportes = [
                esporte.strip().title()
                for esporte in get_row_value(row, "ESPORTES").split(",")
                if esporte.strip()
            ]

            esportes_row = []
            for nome in nomes_esportes:
                esporte = esportes_cache.get(nome)
                if not esporte:
                    esporte = db.scalar(
                        select(Esporte).where(Esporte.nome_esporte == nome)
                    )
                if not esporte:
                    esporte = Esporte(nome_esporte=nome)
                    db.add(esporte)
                    db.flush()
                esportes_cache[nome] = esporte
                esportes_row.append(esporte)

            latitude, longitude = parse_latlong(get_row_value(row, "LAT LONG"))
            qtd_quadras = get_row_value(row, "QTD QUADRAS", default="1").strip()

            espaco = Espaco(
                nome_espaco=get_row_value(row, "NOME").strip(),
                id_endereco=endereco.id_endereco,
                latitude=latitude,
                longitude=longitude,
                cobertura=parse_cobertura(get_row_value(row, "COBERTURA")),
                qtd_quadras=int(qtd_quadras) if qtd_quadras else 1,
                preco_hora=parse_float(get_row_value(row, "PRECO_HORA")) or 120,
                esportes=esportes_row,
            )
            db.add(espaco)
            espacos_criados.append(espaco)

        db.flush()

        db.commit()

    print(f"{len(espacos_criados)} espacos criados.")
    print(f"{len(esportes_cache)} esportes criados ou reutilizados.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Popula o banco local com locais do CSV.")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Nao apaga as tabelas antes de inserir os dados.",
    )
    args = parser.parse_args()
    seed(reset=not args.no_reset)


if __name__ == "__main__":
    main()
