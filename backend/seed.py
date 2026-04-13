"""
Seed script — popula o banco a partir do Quadras.csv
Uso: python3 seed.py
"""

import csv
import re
import sys
from pathlib import Path

from database import Base, SessionLocal, engine
from models import Endereco, Espaco, Esporte, espaco_esportes  # noqa: F401

CSV_PATH = Path(__file__).resolve().parent.parent / "Quadras.csv"


def parse_endereco(raw: str) -> dict:
    """
    Parseia string tipo:
    'Av. Afonso Olindense, 797 - Várzea, Recife - PE, 50810-000'
    """
    # Extrai CEP
    cep_match = re.search(r"(\d{5}-?\d{3})", raw)
    cep = cep_match.group(1) if cep_match else None

    # Remove CEP da string
    limpo = re.sub(r",?\s*\d{5}-?\d{3}", "", raw).strip().rstrip(",")

    # Tenta extrair estado (2 letras após " - ")
    estado_match = re.search(r"-\s*([A-Z]{2})\s*$", limpo)
    estado = estado_match.group(1) if estado_match else None
    if estado:
        limpo = limpo[: estado_match.start()].strip().rstrip("-").strip()

    # Tenta extrair município (última parte após vírgula)
    partes = [p.strip() for p in limpo.split(",")]

    municipio = None
    bairro = None
    logradouro = None

    if len(partes) >= 3:
        logradouro = partes[0]
        # Parte do meio pode ter "797 - Várzea" → número + bairro
        meio = ", ".join(partes[1:-1])
        if " - " in meio:
            _, bairro = meio.rsplit(" - ", 1)
            bairro = bairro.strip()
        else:
            bairro = meio.strip()
        municipio = partes[-1].strip()
    elif len(partes) == 2:
        logradouro = partes[0]
        municipio = partes[1].strip()
    else:
        logradouro = partes[0]

    return {
        "cep": cep,
        "logradouro": logradouro,
        "bairro": bairro,
        "nome_municipio": municipio,
        "nome_estado": estado,
    }


def parse_latlong(raw: str) -> tuple[float | None, float | None]:
    """Parseia '-8.037761, -34.956766' → (lat, lng)"""
    try:
        parts = raw.split(",")
        return float(parts[0].strip()), float(parts[1].strip())
    except (ValueError, IndexError):
        return None, None


def parse_cobertura(raw: str) -> str:
    """Mapeia cobertura do CSV pro ENUM do model."""
    raw = raw.strip().lower()
    if "telhado" in raw:
        return "Telhado"
    if "tela" in raw:
        return "Tela"
    return "Nenhuma"


def seed():
    # Recria tabelas
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    esportes_cache: dict[str, Esporte] = {}

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0

        for row in reader:
            # 1. Endereco
            end_data = parse_endereco(row["ENDEREÇO"])
            endereco = Endereco(**end_data)
            db.add(endereco)
            db.flush()  # gera id

            # 2. Esportes (deduplica)
            nomes_esporte = [e.strip().title() for e in row["ESPORTES"].split(",")]
            esportes_row = []
            for nome in nomes_esporte:
                if nome not in esportes_cache:
                    esporte = Esporte(nome_esporte=nome)
                    db.add(esporte)
                    db.flush()
                    esportes_cache[nome] = esporte
                esportes_row.append(esportes_cache[nome])

            # 3. Lat/Long
            lat, lng = parse_latlong(row["LAT LONG"])

            # 4. Espaco
            espaco = Espaco(
                nome_espaco=row["NOME"].strip(),
                id_endereco=endereco.id_endereco,
                latitude=lat,
                longitude=lng,
                cobertura=parse_cobertura(row["COBERTURA"]),
                qtd_quadras=int(row["QTD QUADRAS"]) if row["QTD QUADRAS"].strip() else 1,
                esportes=esportes_row,
            )
            db.add(espaco)
            count += 1

    db.commit()
    db.close()
    print(f"✅ Seed concluído: {count} espaços, {len(esportes_cache)} esportes")
    print(f"   Esportes: {', '.join(sorted(esportes_cache.keys()))}")


if __name__ == "__main__":
    seed()
