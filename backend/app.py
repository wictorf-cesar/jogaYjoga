import re

from flask import Flask, jsonify, request
from flask_cors import CORS
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

from database import init_db, SessionLocal
from models import Quadra

app = Flask(__name__)
CORS(app)

geocoder = Nominatim(user_agent="jogayjoga-mvp", timeout=10)


def limpar_endereco(endereco: str) -> str:
    """Remove CEP, traços decorativos e espaços extras."""
    limpo = re.sub(r"\d{5}-?\d{3}", "", endereco)  # remove CEP
    limpo = limpo.replace(" - ", ", ")  # "Recife - PE" → "Recife, PE"
    limpo = re.sub(r",\s*,", ",", limpo)  # vírgulas duplas
    limpo = re.sub(r"\s+", " ", limpo).strip().rstrip(",")
    return limpo


def gerar_tentativas(endereco: str) -> list[str]:
    """Gera variações do endereço para tentar geocodificar."""
    limpo = limpar_endereco(endereco)
    tentativas = [
        f"{limpo}, Recife, Pernambuco, Brasil",
        f"{limpo}, Recife, PE",
        limpo,
    ]

    # Simplificação progressiva: remove o primeiro trecho antes da vírgula
    # Ex: "Avenida, Cais do Apolo, 77, Recife, PE" → "Cais do Apolo, 77, Recife, PE"
    partes = [p.strip() for p in limpo.split(",") if p.strip()]
    while len(partes) > 2:
        partes.pop(0)
        simplificado = ", ".join(partes)
        tentativas.append(f"{simplificado}, Recife, Pernambuco, Brasil")
        tentativas.append(simplificado)

    return tentativas


def geocode_endereco(endereco: str):
    """Converte endereço em lat/lng via Nominatim. Tenta variações do endereço."""
    for tentativa in gerar_tentativas(endereco):
        try:
            location = geocoder.geocode(tentativa)
            if location:
                return location.latitude, location.longitude
        except GeocoderTimedOut:
            continue
    return None, None


@app.route("/quadras", methods=["POST"])
def criar_quadra():
    data = request.get_json()

    if not data:
        return jsonify({"erro": "Body JSON é obrigatório"}), 400

    campos_obrigatorios = ["nome", "endereco", "esporte"]
    faltando = [c for c in campos_obrigatorios if not data.get(c)]
    if faltando:
        return jsonify({"erro": f"Campos obrigatórios faltando: {faltando}"}), 400

    lat, lng = geocode_endereco(data["endereco"])

    db = SessionLocal()
    try:
        quadra = Quadra(
            nome=data["nome"],
            endereco=data["endereco"],
            esporte=data["esporte"].lower(),
            latitude=lat,
            longitude=lng,
        )
        db.add(quadra)
        db.commit()
        db.refresh(quadra)
        return jsonify(quadra.to_dict()), 201
    finally:
        db.close()


@app.route("/quadras", methods=["GET"])
def listar_quadras():
    db = SessionLocal()
    try:
        query = db.query(Quadra)

        esporte = request.args.get("esporte")
        if esporte:
            query = query.filter(Quadra.esporte == esporte.lower())

        quadras = query.all()
        return jsonify([q.to_dict() for q in quadras])
    finally:
        db.close()


@app.route("/quadras/<int:quadra_id>", methods=["DELETE"])
def deletar_quadra(quadra_id):
    db = SessionLocal()
    try:
        quadra = db.query(Quadra).get(quadra_id)
        if not quadra:
            return jsonify({"erro": "Quadra não encontrada"}), 404
        db.delete(quadra)
        db.commit()
        return jsonify({"mensagem": f"Quadra '{quadra.nome}' deletada"})
    finally:
        db.close()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
