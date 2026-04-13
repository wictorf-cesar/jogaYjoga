"""
Seed script — popula o banco a partir do Quadras.csv + dados demo
Uso: python3 seed.py
"""

import csv
import random
import re
from datetime import date, time, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

from database import Base, SessionLocal, engine
from models import (
    Avaliacao,
    Endereco,
    Espaco,
    Esporte,
    Proprietario,
    Reserva,
    Usuario,
    espaco_esportes,  # noqa: F401
)

CSV_PATH = Path(__file__).resolve().parent.parent / "Quadras.csv"


# ── Parsing helpers ──────────────────────────────────────────────────────────


def parse_endereco(raw: str) -> dict:
    cep_match = re.search(r"(\d{5}-?\d{3})", raw)
    cep = cep_match.group(1) if cep_match else None
    limpo = re.sub(r",?\s*\d{5}-?\d{3}", "", raw).strip().rstrip(",")
    estado_match = re.search(r"-\s*([A-Z]{2})\s*$", limpo)
    estado = estado_match.group(1) if estado_match else None
    if estado:
        limpo = limpo[: estado_match.start()].strip().rstrip("-").strip()
    partes = [p.strip() for p in limpo.split(",")]
    municipio = bairro = logradouro = None
    if len(partes) >= 3:
        logradouro = partes[0]
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
    try:
        parts = raw.split(",")
        return float(parts[0].strip()), float(parts[1].strip())
    except (ValueError, IndexError):
        return None, None


def parse_cobertura(raw: str) -> str:
    raw = raw.strip().lower()
    if "telhado" in raw:
        return "Telhado"
    if "tela" in raw:
        return "Tela"
    return "Nenhuma"


# ── Seed principal ───────────────────────────────────────────────────────────


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("📦 Tabelas recriadas")

    db = SessionLocal()
    random.seed(42)

    # ── 1. Espaços do CSV ────────────────────────────────────────────────────

    esportes_cache: dict[str, Esporte] = {}
    espacos_criados: list[Espaco] = []

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            end_data = parse_endereco(row["ENDEREÇO"])
            endereco = Endereco(**end_data)
            db.add(endereco)
            db.flush()

            nomes_esporte = [e.strip().title() for e in row["ESPORTES"].split(",")]
            esportes_row = []
            for nome in nomes_esporte:
                if nome not in esportes_cache:
                    esporte = Esporte(nome_esporte=nome)
                    db.add(esporte)
                    db.flush()
                    esportes_cache[nome] = esporte
                esportes_row.append(esportes_cache[nome])

            lat, lng = parse_latlong(row["LAT LONG"])

            espaco = Espaco(
                nome_espaco=row["NOME"].strip(),
                id_endereco=endereco.id_endereco,
                latitude=lat,
                longitude=lng,
                cobertura=parse_cobertura(row["COBERTURA"]),
                qtd_quadras=int(row["QTD QUADRAS"]) if row["QTD QUADRAS"].strip() else 1,
                preco_hora=random.choice([80, 90, 100, 120, 150]),
                esportes=esportes_row,
            )
            db.add(espaco)
            espacos_criados.append(espaco)

    db.flush()
    print(f"✅ {len(espacos_criados)} espaços, {len(esportes_cache)} esportes")

    # ── 2. Usuários demo ─────────────────────────────────────────────────────

    atleta = Usuario(
        nome_completo="João Silva",
        email="atleta@demo.com",
        senha_hash=generate_password_hash("123456"),
        cpf="111.222.333-44",
        telefone="(81) 99999-0001",
    )
    db.add(atleta)

    admin_user = Usuario(
        nome_completo="Maria Proprietária",
        email="admin@demo.com",
        senha_hash=generate_password_hash("123456"),
        cpf="555.666.777-88",
        telefone="(81) 99999-0002",
    )
    db.add(admin_user)
    db.flush()

    # ── 3. Proprietário (admin é dono de 6 espaços) ──────────────────────────

    prop = Proprietario(
        id_usuario=admin_user.id_usuario,
        cnpj="12.345.678/0001-90",
        razao_social="JogaYJoga Esportes LTDA",
        chave_pix="admin@demo.com",
    )
    db.add(prop)
    db.flush()

    # Vincula os 6 primeiros espaços ao proprietário
    for esp in espacos_criados[:6]:
        esp.id_proprietario = prop.id_proprietario

    db.flush()

    print(f"👤 Usuários: atleta@demo.com / admin@demo.com (senha: 123456)")
    print(f"🏟️ Proprietário vinculado a {min(6, len(espacos_criados))} espaços")

    # ── 4. Reservas do atleta (últimos 30 dias + próximas) ───────────────────

    hoje = date.today()
    horarios = [
        (time(7, 0), time(8, 0)),
        (time(8, 0), time(9, 30)),
        (time(17, 0), time(18, 30)),
        (time(19, 0), time(20, 0)),
        (time(19, 0), time(21, 0)),
        (time(20, 0), time(21, 30)),
    ]

    reservas_criadas = 0

    # Reservas passadas (últimos 30 dias)
    for dias_atras in [2, 4, 6, 8, 10, 13, 15, 18, 20, 23, 25, 28]:
        esp = random.choice(espacos_criados[:10])
        h_ini, h_fim = random.choice(horarios)
        horas = (
            (h_fim.hour * 60 + h_fim.minute) - (h_ini.hour * 60 + h_ini.minute)
        ) / 60
        valor = round(float(esp.preco_hora or 100) * horas, 2)

        reserva = Reserva(
            id_usuario=atleta.id_usuario,
            id_espaco=esp.id_espaco,
            data_reserva=hoje - timedelta(days=dias_atras),
            hora_inicio=h_ini,
            hora_fim=h_fim,
            status_reserva="confirmado",
            valor_total=valor,
        )
        db.add(reserva)
        reservas_criadas += 1

    # Reservas futuras
    for dias_frente in [1, 3, 5, 7]:
        esp = random.choice(espacos_criados[:10])
        h_ini, h_fim = random.choice(horarios)
        horas = (
            (h_fim.hour * 60 + h_fim.minute) - (h_ini.hour * 60 + h_ini.minute)
        ) / 60
        valor = round(float(esp.preco_hora or 100) * horas, 2)
        status = "confirmado" if dias_frente <= 3 else "pendente"

        reserva = Reserva(
            id_usuario=atleta.id_usuario,
            id_espaco=esp.id_espaco,
            data_reserva=hoje + timedelta(days=dias_frente),
            hora_inicio=h_ini,
            hora_fim=h_fim,
            status_reserva=status,
            valor_total=valor,
        )
        db.add(reserva)
        reservas_criadas += 1

    # Reservas nos espaços do admin (de outros "usuários" fictícios)
    for _ in range(40):
        esp = random.choice(espacos_criados[:6])
        h_ini, h_fim = random.choice(horarios)
        horas = (
            (h_fim.hour * 60 + h_fim.minute) - (h_ini.hour * 60 + h_ini.minute)
        ) / 60
        valor = round(float(esp.preco_hora or 100) * horas, 2)
        dia = hoje - timedelta(days=random.randint(0, 28))

        reserva = Reserva(
            id_usuario=atleta.id_usuario,  # simplificado: atleta faz todas
            id_espaco=esp.id_espaco,
            data_reserva=dia,
            hora_inicio=h_ini,
            hora_fim=h_fim,
            status_reserva="confirmado",
            valor_total=valor,
        )
        db.add(reserva)
        reservas_criadas += 1

    db.flush()
    print(f"📅 {reservas_criadas} reservas criadas")

    # ── 5. Avaliações do atleta ──────────────────────────────────────────────

    avaliacoes_criadas = 0
    for esp in espacos_criados[:8]:
        avaliacao = Avaliacao(
            id_usuario=atleta.id_usuario,
            id_espaco=esp.id_espaco,
            nota=random.choice([4, 4, 5, 5, 5]),
            comentario=random.choice([
                "Ótima quadra, bem cuidada!",
                "Gostei muito, vou voltar.",
                "Boa estrutura, recomendo.",
                "Excelente localização.",
                "Quadra em bom estado, preço justo.",
                "Muito boa, iluminação top.",
                "Areia limpa, atendimento nota 10.",
                "Ambiente agradável, voltarei com certeza.",
            ]),
        )
        db.add(avaliacao)
        avaliacoes_criadas += 1

    db.commit()
    db.close()
    print(f"⭐ {avaliacoes_criadas} avaliações criadas")
    print("🎉 Seed completo!")
    print()
    print("  Logins demo:")
    print("  📧 atleta@demo.com  / 123456  (dashboard atleta)")
    print("  📧 admin@demo.com   / 123456  (dashboard admin)")


if __name__ == "__main__":
    seed()
