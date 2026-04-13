import re
from datetime import date, datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Nominatim
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from database import SessionLocal, init_db
from models import Avaliacao, Endereco, Espaco, Esporte, Proprietario, Reserva, Usuario

app = Flask(__name__)
CORS(app)

geocoder = Nominatim(user_agent="jogayjoga-mvp", timeout=10)


# ── Helpers ──────────────────────────────────────────────────────────────────


def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def limpar_endereco(endereco: str) -> str:
    limpo = re.sub(r"\d{5}-?\d{3}", "", endereco)
    limpo = limpo.replace(" - ", ", ")
    limpo = re.sub(r",\s*,", ",", limpo)
    limpo = re.sub(r"\s+", " ", limpo).strip().rstrip(",")
    return limpo


def gerar_tentativas(endereco: str) -> list[str]:
    limpo = limpar_endereco(endereco)
    tentativas = [
        f"{limpo}, Recife, Pernambuco, Brasil",
        f"{limpo}, Recife, PE",
        limpo,
    ]
    partes = [p.strip() for p in limpo.split(",") if p.strip()]
    while len(partes) > 2:
        partes.pop(0)
        simplificado = ", ".join(partes)
        tentativas.append(f"{simplificado}, Recife, Pernambuco, Brasil")
        tentativas.append(simplificado)
    return tentativas


def geocode_endereco(endereco: str):
    for tentativa in gerar_tentativas(endereco):
        try:
            location = geocoder.geocode(tentativa)
            if location:
                return location.latitude, location.longitude
        except GeocoderTimedOut:
            continue
    return None, None


# ── Auth ─────────────────────────────────────────────────────────────────────


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Body JSON obrigatório"}), 400

    campos = ["nome", "email", "senha"]
    faltando = [c for c in campos if not data.get(c)]
    if faltando:
        return jsonify({"erro": f"Campos faltando: {faltando}"}), 400

    db = get_db()
    try:
        if db.query(Usuario).filter(Usuario.email == data["email"]).first():
            return jsonify({"erro": "Email já cadastrado"}), 409

        usuario = Usuario(
            nome_completo=data["nome"],
            email=data["email"],
            senha_hash=generate_password_hash(data["senha"]),
            cpf=data.get("cpf"),
            telefone=data.get("telefone"),
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return jsonify(usuario.to_dict()), 201
    finally:
        db.close()


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("senha"):
        return jsonify({"erro": "Email e senha obrigatórios"}), 400

    db = get_db()
    try:
        usuario = db.query(Usuario).filter(Usuario.email == data["email"]).first()
        if not usuario or not check_password_hash(usuario.senha_hash, data["senha"]):
            return jsonify({"erro": "Credenciais inválidas"}), 401

        return jsonify(usuario.to_dict()), 200
    finally:
        db.close()


# ── Usuários / Perfil ────────────────────────────────────────────────────────


@app.route("/usuarios/<int:user_id>", methods=["GET"])
def get_usuario(user_id):
    db = get_db()
    try:
        usuario = db.query(Usuario).get(user_id)
        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404
        return jsonify(usuario.to_dict())
    finally:
        db.close()


@app.route("/usuarios/<int:user_id>/reservas", methods=["GET"])
def get_reservas_usuario(user_id):
    db = get_db()
    try:
        tipo = request.args.get("tipo", "todas")  # proximas | historico | todas

        query = db.query(Reserva).filter(Reserva.id_usuario == user_id)

        if tipo == "proximas":
            query = query.filter(Reserva.data_reserva >= date.today())
            query = query.order_by(Reserva.data_reserva.asc())
        elif tipo == "historico":
            query = query.filter(Reserva.data_reserva < date.today())
            query = query.order_by(Reserva.data_reserva.desc())
        else:
            query = query.order_by(Reserva.data_reserva.desc())

        reservas = query.all()
        return jsonify([r.to_dict() for r in reservas])
    finally:
        db.close()


@app.route("/usuarios/<int:user_id>/estatisticas", methods=["GET"])
def get_estatisticas_usuario(user_id):
    db = get_db()
    try:
        inicio_mes = date.today().replace(day=1)

        # Reservas do mês
        reservas_mes = (
            db.query(Reserva)
            .filter(
                Reserva.id_usuario == user_id,
                Reserva.data_reserva >= inicio_mes,
            )
            .all()
        )

        partidas = len(reservas_mes)

        # Horas jogadas
        horas = 0.0
        for r in reservas_mes:
            if r.hora_inicio and r.hora_fim:
                inicio = datetime.combine(date.today(), r.hora_inicio)
                fim = datetime.combine(date.today(), r.hora_fim)
                horas += (fim - inicio).seconds / 3600

        # Gasto no mês
        gasto = sum(float(r.valor_total or 0) for r in reservas_mes)

        # Quadras visitadas no mês
        quadras_visitadas = len(set(r.id_espaco for r in reservas_mes))

        # Avaliação média
        avg = (
            db.query(func.avg(Avaliacao.nota))
            .filter(Avaliacao.id_usuario == user_id)
            .scalar()
        )

        # Quadra mais frequente (favorita)
        todas_reservas = db.query(Reserva).filter(Reserva.id_usuario == user_id).all()
        freq: dict[int, int] = {}
        for r in todas_reservas:
            freq[r.id_espaco] = freq.get(r.id_espaco, 0) + 1

        quadra_fav = None
        if freq:
            fav_id = max(freq, key=freq.get)
            espaco = db.query(Espaco).get(fav_id)
            quadra_fav = espaco.nome_espaco if espaco else None

        # Sequência de dias consecutivos jogando
        datas = sorted(set(r.data_reserva for r in todas_reservas), reverse=True)
        sequencia = 0
        hoje = date.today()
        for d in datas:
            if d == hoje - timedelta(days=sequencia):
                sequencia += 1
            else:
                break

        return jsonify(
            {
                "partidas_mes": partidas,
                "horas_mes": round(horas, 1),
                "gasto_mes": round(gasto, 2),
                "quadras_visitadas": quadras_visitadas,
                "media_avaliacao": round(float(avg), 1) if avg else None,
                "quadra_favorita": quadra_fav,
                "sequencia_dias": sequencia,
            }
        )
    finally:
        db.close()


# ── Espaços (ex-quadras) ────────────────────────────────────────────────────


@app.route("/espacos", methods=["GET"])
def listar_espacos():
    db = get_db()
    try:
        query = db.query(Espaco)

        esporte = request.args.get("esporte")
        if esporte:
            query = query.filter(
                Espaco.esportes.any(Esporte.nome_esporte.ilike(f"%{esporte}%"))
            )

        espacos = query.all()
        return jsonify([e.to_dict() for e in espacos])
    finally:
        db.close()


@app.route("/espacos/<int:espaco_id>", methods=["GET"])
def get_espaco(espaco_id):
    db = get_db()
    try:
        espaco = db.query(Espaco).get(espaco_id)
        if not espaco:
            return jsonify({"erro": "Espaço não encontrado"}), 404
        return jsonify(espaco.to_dict())
    finally:
        db.close()


@app.route("/espacos", methods=["POST"])
def criar_espaco():
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Body JSON obrigatório"}), 400

    campos = ["nome", "endereco"]
    faltando = [c for c in campos if not data.get(c)]
    if faltando:
        return jsonify({"erro": f"Campos faltando: {faltando}"}), 400

    db = get_db()
    try:
        # Geocoding
        lat, lng = geocode_endereco(data["endereco"])

        # Endereço simples (string completa no logradouro)
        endereco = Endereco(logradouro=data["endereco"])
        db.add(endereco)
        db.flush()

        # Esportes
        esportes = []
        for nome in data.get("esportes", []):
            esporte = (
                db.query(Esporte)
                .filter(Esporte.nome_esporte.ilike(nome.strip()))
                .first()
            )
            if not esporte:
                esporte = Esporte(nome_esporte=nome.strip().title())
                db.add(esporte)
                db.flush()
            esportes.append(esporte)

        espaco = Espaco(
            nome_espaco=data["nome"],
            id_endereco=endereco.id_endereco,
            latitude=lat,
            longitude=lng,
            cobertura=data.get("cobertura"),
            preco_hora=data.get("preco_hora"),
            capacidade_pessoas=data.get("capacidade"),
            qtd_quadras=data.get("qtd_quadras", 1),
            esportes=esportes,
        )
        db.add(espaco)
        db.commit()
        db.refresh(espaco)
        return jsonify(espaco.to_dict()), 201
    finally:
        db.close()


@app.route("/espacos/<int:espaco_id>", methods=["DELETE"])
def deletar_espaco(espaco_id):
    db = get_db()
    try:
        espaco = db.query(Espaco).get(espaco_id)
        if not espaco:
            return jsonify({"erro": "Espaço não encontrado"}), 404
        nome = espaco.nome_espaco
        db.delete(espaco)
        db.commit()
        return jsonify({"mensagem": f"Espaço '{nome}' deletado"})
    finally:
        db.close()


# ── Esportes ─────────────────────────────────────────────────────────────────


@app.route("/esportes", methods=["GET"])
def listar_esportes():
    db = get_db()
    try:
        esportes = db.query(Esporte).order_by(Esporte.nome_esporte).all()
        return jsonify([e.to_dict() for e in esportes])
    finally:
        db.close()


# ── Reservas ─────────────────────────────────────────────────────────────────


@app.route("/reservas", methods=["POST"])
def criar_reserva():
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Body JSON obrigatório"}), 400

    campos = ["id_usuario", "id_espaco", "data", "hora_inicio", "hora_fim"]
    faltando = [c for c in campos if not data.get(c)]
    if faltando:
        return jsonify({"erro": f"Campos faltando: {faltando}"}), 400

    db = get_db()
    try:
        # Verifica conflito de horário
        conflito = (
            db.query(Reserva)
            .filter(
                Reserva.id_espaco == data["id_espaco"],
                Reserva.data_reserva == data["data"],
                Reserva.status_reserva != "cancelado",
                Reserva.hora_inicio < data["hora_fim"],
                Reserva.hora_fim > data["hora_inicio"],
            )
            .first()
        )
        if conflito:
            return jsonify({"erro": "Horário indisponível"}), 409

        # Calcula valor
        espaco = db.query(Espaco).get(data["id_espaco"])
        valor = None
        if espaco and espaco.preco_hora:
            h_ini = datetime.strptime(data["hora_inicio"], "%H:%M")
            h_fim = datetime.strptime(data["hora_fim"], "%H:%M")
            horas = (h_fim - h_ini).seconds / 3600
            valor = round(float(espaco.preco_hora) * horas, 2)

        reserva = Reserva(
            id_usuario=data["id_usuario"],
            id_espaco=data["id_espaco"],
            data_reserva=data["data"],
            hora_inicio=data["hora_inicio"],
            hora_fim=data["hora_fim"],
            valor_total=valor,
        )
        db.add(reserva)
        db.commit()
        db.refresh(reserva)
        return jsonify(reserva.to_dict()), 201
    finally:
        db.close()


@app.route("/reservas/<int:reserva_id>", methods=["PATCH"])
def atualizar_reserva(reserva_id):
    data = request.get_json()
    if not data or "status" not in data:
        return jsonify({"erro": "Campo 'status' obrigatório"}), 400

    if data["status"] not in ("confirmado", "cancelado"):
        return jsonify({"erro": "Status inválido (confirmado/cancelado)"}), 400

    db = get_db()
    try:
        reserva = db.query(Reserva).get(reserva_id)
        if not reserva:
            return jsonify({"erro": "Reserva não encontrada"}), 404

        reserva.status_reserva = data["status"]
        db.commit()
        db.refresh(reserva)
        return jsonify(reserva.to_dict())
    finally:
        db.close()


# ── Avaliações ───────────────────────────────────────────────────────────────


@app.route("/avaliacoes", methods=["POST"])
def criar_avaliacao():
    data = request.get_json()
    if not data:
        return jsonify({"erro": "Body JSON obrigatório"}), 400

    campos = ["id_usuario", "id_espaco", "nota"]
    faltando = [c for c in campos if not data.get(c)]
    if faltando:
        return jsonify({"erro": f"Campos faltando: {faltando}"}), 400

    if not 1 <= data["nota"] <= 5:
        return jsonify({"erro": "Nota deve ser entre 1 e 5"}), 400

    db = get_db()
    try:
        avaliacao = Avaliacao(
            id_usuario=data["id_usuario"],
            id_espaco=data["id_espaco"],
            id_reserva=data.get("id_reserva"),
            nota=data["nota"],
            comentario=data.get("comentario"),
        )
        db.add(avaliacao)
        db.commit()
        db.refresh(avaliacao)
        return jsonify(avaliacao.to_dict()), 201
    finally:
        db.close()


@app.route("/espacos/<int:espaco_id>/avaliacoes", methods=["GET"])
def listar_avaliacoes_espaco(espaco_id):
    db = get_db()
    try:
        avaliacoes = (
            db.query(Avaliacao)
            .filter(Avaliacao.id_espaco == espaco_id)
            .order_by(Avaliacao.criado_em.desc())
            .all()
        )
        return jsonify([a.to_dict() for a in avaliacoes])
    finally:
        db.close()


# ── Admin Dashboard ──────────────────────────────────────────────────────────


@app.route("/admin/<int:user_id>/dashboard", methods=["GET"])
def admin_dashboard(user_id):
    db = get_db()
    try:
        # Verifica se é proprietário
        prop = db.query(Proprietario).filter(Proprietario.id_usuario == user_id).first()
        if not prop:
            return jsonify({"erro": "Usuário não é proprietário"}), 403

        # Espaços do proprietário
        espacos = (
            db.query(Espaco)
            .filter(Espaco.id_proprietario == prop.id_proprietario)
            .all()
        )
        espaco_ids = [e.id_espaco for e in espacos]

        inicio_mes = date.today().replace(day=1)

        # Reservas do mês nos espaços do proprietário
        reservas_mes = (
            db.query(Reserva)
            .filter(
                Reserva.id_espaco.in_(espaco_ids),
                Reserva.data_reserva >= inicio_mes,
            )
            .all()
        )

        # Lucro total
        lucro = sum(float(r.valor_total or 0) for r in reservas_mes)

        # Aluguéis por espaço
        por_espaco = []
        for esp in espacos:
            res_esp = [r for r in reservas_mes if r.id_espaco == esp.id_espaco]
            lucro_esp = sum(float(r.valor_total or 0) for r in res_esp)
            por_espaco.append(
                {
                    "id": esp.id_espaco,
                    "nome": esp.nome_espaco,
                    "alugueis": len(res_esp),
                    "lucro": round(lucro_esp, 2),
                    "esportes": [e.nome_esporte for e in esp.esportes],
                }
            )

        # Aluguéis por dia da semana
        dias = {i: 0 for i in range(7)}  # 0=seg, 6=dom
        for r in reservas_mes:
            dias[r.data_reserva.weekday()] += 1

        nomes_dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        por_dia = {nomes_dias[i]: dias[i] for i in range(7)}

        return jsonify(
            {
                "total_espacos": len(espacos),
                "alugueis_mes": len(reservas_mes),
                "lucro_mes": round(lucro, 2),
                "por_espaco": por_espaco,
                "por_dia_semana": por_dia,
            }
        )
    finally:
        db.close()


# ── Compatibilidade (endpoint antigo /quadras redireciona) ───────────────────


@app.route("/quadras", methods=["GET"])
def listar_quadras_compat():
    """Mantém compatibilidade com frontend antigo."""
    db = get_db()
    try:
        query = db.query(Espaco)
        esporte = request.args.get("esporte")
        if esporte:
            query = query.filter(
                Espaco.esportes.any(Esporte.nome_esporte.ilike(f"%{esporte}%"))
            )
        espacos = query.all()

        # Retorna no formato antigo que o frontend espera
        result = []
        for e in espacos:
            endereco_str = ""
            if e.endereco:
                parts = [
                    e.endereco.logradouro,
                    e.endereco.bairro,
                    e.endereco.nome_municipio,
                ]
                endereco_str = ", ".join(p for p in parts if p)
            result.append(
                {
                    "id": e.id_espaco,
                    "nome": e.nome_espaco,
                    "endereco": endereco_str,
                    "esporte": ", ".join(esp.nome_esporte for esp in e.esportes),
                    "latitude": float(e.latitude) if e.latitude else None,
                    "longitude": float(e.longitude) if e.longitude else None,
                }
            )
        return jsonify(result)
    finally:
        db.close()


# ── Health ───────────────────────────────────────────────────────────────────


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
