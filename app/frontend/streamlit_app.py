import json
import logging
import os
import sys
import traceback
from datetime import date, time
from pathlib import Path

import folium
import pandas as pd
import requests
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

API_URL = os.getenv("JOGAYJOGA_API_URL", "http://localhost:8000").rstrip("/")
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"
MAP_CENTER = [-8.0200, -34.9300]


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{super().format(record)}{self.RESET}"


chat_logger = logging.getLogger("jogayjoga.frontend.chat")
if not chat_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColorFormatter(
            "%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    chat_logger.addHandler(handler)
chat_logger.setLevel(logging.DEBUG)
chat_logger.propagate = False


def chat_debug_log(tag: str, message: str, **data: object) -> None:
    payload = f" {json.dumps(data, ensure_ascii=False, default=str)}" if data else ""
    chat_logger.info(f"[{tag}] {message}{payload}")


def chat_debug_error(tag: str, message: str, exc: Exception | None = None, **data: object) -> None:
    if exc:
        data["error_type"] = type(exc).__name__
        data["error"] = str(exc)
        data["stacktrace"] = traceback.format_exc()
    payload = f" {json.dumps(data, ensure_ascii=False, default=str)}" if data else ""
    chat_logger.error(f"[{tag}] {message}{payload}")


def debugChatFlow(message: str, state: dict, action: dict | str | None = None) -> None:
    chat_debug_log("DEBUG CHAT FLOW", "Snapshot do fluxo", message=message, state=state, action=action or "NONE")

st.set_page_config(page_title="Joga & Joga", page_icon=str(LOGO_PATH), layout="wide")


def apply_design_system() -> None:
    st.markdown(
        """
        <style>
        :root {
            --jj-navy: #10233f;
            --jj-blue: #1769aa;
            --jj-orange: #e86a10;
            --jj-mint: #16a085;
            --jj-bg: #f5f8fb;
            --jj-panel: #ffffff;
            --jj-line: #dbe5ee;
            --jj-muted: #66788a;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(232, 106, 16, 0.08), transparent 28rem),
                linear-gradient(180deg, #f7fbfd 0%, var(--jj-bg) 38%, #eef4f8 100%);
            color: var(--jj-navy);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #10233f 0%, #14345d 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        section[data-testid="stSidebar"] * {
            color: #f8fbff !important;
        }

        section[data-testid="stSidebar"] img {
            background: #ffffff;
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
        }

        section[data-testid="stSidebar"] .stButton > button {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 10px;
            color: #ffffff !important;
            font-weight: 700;
            min-height: 42px;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: var(--jj-orange);
            border-color: var(--jj-orange);
        }

        .main .block-container {
            max-width: 1280px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            color: var(--jj-navy);
            letter-spacing: 0;
        }

        h1 {
            font-size: 2rem;
            font-weight: 850;
            margin-bottom: 0.35rem;
        }

        h2, h3 {
            font-weight: 800;
        }

        div[data-testid="stMetric"] {
            background: var(--jj-panel);
            border: 1px solid var(--jj-line);
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 10px 28px rgba(16, 35, 63, 0.07);
        }

        div[data-testid="stMetric"] label {
            color: var(--jj-muted) !important;
            font-weight: 700;
        }

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--jj-navy);
            font-weight: 850;
        }

        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px !important;
        }

        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input,
        textarea,
        div[data-baseweb="select"] > div {
            border-radius: 10px !important;
            border-color: var(--jj-line) !important;
            background-color: #ffffff !important;
        }

        .stButton > button {
            border-radius: 10px;
            border: 1px solid var(--jj-line);
            font-weight: 750;
            min-height: 42px;
        }

        .stButton > button[kind="primary"] {
            background: var(--jj-orange);
            border-color: var(--jj-orange);
            color: #ffffff;
        }

        .jj-page-header {
            background: linear-gradient(135deg, #10233f 0%, #1769aa 100%);
            color: #ffffff;
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 22px;
            box-shadow: 0 18px 42px rgba(16, 35, 63, 0.18);
        }

        .jj-page-header h1 {
            color: #ffffff;
            margin: 0;
        }

        .jj-page-header p {
            color: rgba(255, 255, 255, 0.78);
            margin: 6px 0 0;
            font-size: 1rem;
        }

        .jj-card {
            background: var(--jj-panel);
            border: 1px solid var(--jj-line);
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 10px 28px rgba(16, 35, 63, 0.07);
            margin-bottom: 14px;
        }

        .jj-card-title {
            font-weight: 850;
            color: var(--jj-navy);
            font-size: 1.05rem;
            margin-bottom: 4px;
        }

        .jj-muted {
            color: var(--jj-muted);
            font-size: 0.92rem;
        }

        .jj-pill {
            display: inline-block;
            background: #eef6fb;
            color: var(--jj-blue);
            border: 1px solid #d8e9f5;
            border-radius: 999px;
            padding: 4px 10px;
            margin: 3px 4px 3px 0;
            font-size: 0.82rem;
            font-weight: 750;
        }

        iframe {
            border-radius: 14px !important;
            border: 1px solid var(--jj-line) !important;
            box-shadow: 0 14px 34px rgba(16, 35, 63, 0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def info_card(title: str, body: str, chips: list[str] | None = None) -> None:
    chips_html = "".join(f'<span class="jj-pill">{chip}</span>' for chip in chips or [])
    st.markdown(
        f"""
        <div class="jj-card">
            <div class="jj-card-title">{title}</div>
            <div class="jj-muted">{body}</div>
            <div>{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


apply_design_system()


def post_api(
    path: str,
    payload: dict,
    token: str | None = None,
) -> tuple[dict | None, str | None]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    try:
        response = requests.post(
            f"{API_URL}{path}",
            json=payload,
            headers=headers,
            timeout=10,
        )
    except requests.RequestException:
        return None, "Nao foi possivel conectar ao backend."

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        return None, detail or "Erro na requisicao."

    return response.json(), None


def patch_api(
    path: str,
    payload: dict | None = None,
    token: str | None = None,
) -> tuple[dict | None, str | None]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    try:
        response = requests.patch(
            f"{API_URL}{path}",
            json=payload or {},
            headers=headers,
            timeout=10,
        )
    except requests.RequestException:
        return None, "Nao foi possivel conectar ao backend."

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        return None, detail or "Erro na requisicao."

    return response.json(), None


def delete_api(path: str, token: str | None = None) -> tuple[bool, str | None]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    try:
        response = requests.delete(f"{API_URL}{path}", headers=headers, timeout=10)
    except requests.RequestException:
        return False, "Nao foi possivel conectar ao backend."

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        return False, detail or "Erro na requisicao."
    return True, None


def get_api(path: str, token: str | None = None) -> tuple[dict | list | None, str | None]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    try:
        response = requests.get(f"{API_URL}{path}", headers=headers, timeout=10)
    except requests.RequestException:
        return None, "Nao foi possivel conectar ao backend."

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        return None, detail or "Erro na requisicao."

    return response.json(), None


@st.cache_data(ttl=60)
def get_espacos() -> tuple[list[dict], str | None]:
    data, error = get_api("/espacos")
    if error:
        return [], error
    return data or [], None


def get_owner_espacos(token: str) -> tuple[list[dict], str | None]:
    data, error = get_api("/owner/espacos", token=token)
    if error:
        return [], error
    return data or [], None


def get_owner_dashboard(token: str) -> tuple[dict, str | None]:
    data, error = get_api("/owner/dashboard", token=token)
    if error:
        return {}, error
    return data or {}, None


def get_owner_reservas(
    token: str,
    data_reserva: date | None = None,
) -> tuple[list[dict], str | None]:
    path = "/owner/reservas"
    if data_reserva:
        path += f"?data={data_reserva.isoformat()}"
    data, error = get_api(path, token=token)
    if error:
        return [], error
    return data or [], None


def update_owner_reserva_status(
    token: str,
    reserva_id: int,
    status: str,
) -> tuple[dict | None, str | None]:
    return patch_api(
        f"/owner/reservas/{reserva_id}/status",
        {"status": status},
        token=token,
    )


def create_owner_espaco(token: str, payload: dict) -> tuple[dict | None, str | None]:
    return post_api("/owner/espacos", payload, token=token)


def create_reserva(token: str, payload: dict) -> tuple[dict | None, str | None]:
    return post_api("/reservas", payload, token=token)


def parse_message_with_ai(
    token: str,
    message: str,
    current_step: str | None,
) -> tuple[dict | None, str | None]:
    return post_api(
        "/ai/parse",
        {"message": message, "current_step": current_step},
        token=token,
    )


def get_my_reservas(token: str) -> tuple[list[dict], str | None]:
    data, error = get_api("/me/reservas", token=token)
    if error:
        return [], error
    return data or [], None


def cancel_my_reserva(token: str, reserva_id: int) -> tuple[dict | None, str | None]:
    return patch_api(f"/me/reservas/{reserva_id}/cancelar", token=token)


def update_my_pagamento(
    token: str,
    reserva_id: int,
    comprovante_url: str | None,
) -> tuple[dict | None, str | None]:
    return patch_api(
        f"/me/reservas/{reserva_id}/pagamento",
        {"metodo": "pix", "comprovante_url": comprovante_url},
        token=token,
    )


def create_avaliacao(token: str, payload: dict) -> tuple[dict | None, str | None]:
    return post_api("/me/avaliacoes", payload, token=token)


def get_espaco_detail(token: str, espaco_id: int) -> tuple[dict, str | None]:
    data, error = get_api(f"/espacos/{espaco_id}", token=token)
    if error:
        return {}, error
    return data or {}, None


def get_availability(espaco_id: int, data_reserva: date) -> tuple[list[dict], str | None]:
    data, error = get_api(
        f"/espacos/{espaco_id}/disponibilidade?data={data_reserva.isoformat()}"
    )
    if error:
        return [], error
    return data or [], None


def add_favorito(token: str, espaco_id: int) -> tuple[dict | None, str | None]:
    return post_api(f"/me/favoritos/{espaco_id}", {}, token=token)


def remove_favorito(token: str, espaco_id: int) -> tuple[bool, str | None]:
    return delete_api(f"/me/favoritos/{espaco_id}", token=token)


def get_favoritos(token: str) -> tuple[list[dict], str | None]:
    data, error = get_api("/me/favoritos", token=token)
    if error:
        return [], error
    return data or [], None


def get_owner_horarios(token: str) -> tuple[list[dict], str | None]:
    data, error = get_api("/owner/horarios", token=token)
    if error:
        return [], error
    return data or [], None


def create_owner_horario(
    token: str,
    espaco_id: int,
    payload: dict,
) -> tuple[dict | None, str | None]:
    return post_api(f"/owner/espacos/{espaco_id}/horarios", payload, token=token)


def get_owner_bloqueios(token: str) -> tuple[list[dict], str | None]:
    data, error = get_api("/owner/bloqueios", token=token)
    if error:
        return [], error
    return data or [], None


def create_owner_bloqueio(token: str, payload: dict) -> tuple[dict | None, str | None]:
    return post_api("/owner/bloqueios", payload, token=token)


def show_flash_message() -> None:
    message = st.session_state.pop("flash_message", None)
    if not message:
        return

    message_type = message.get("type", "info")
    text = message.get("text", "")
    st.toast(text)
    if message_type == "success":
        st.success(text)
    elif message_type == "warning":
        st.warning(text)
    elif message_type == "error":
        st.error(text)
    else:
        st.info(text)


def format_endereco(endereco: dict) -> str:
    parts = [
        endereco.get("logradouro"),
        endereco.get("bairro"),
        endereco.get("municipio"),
        endereco.get("estado"),
    ]
    label = ", ".join(part for part in parts if part)
    return f"#{endereco['id']} - {label}" if label else f"#{endereco['id']}"


def same_text(left: str | None, right: str | None) -> bool:
    return normalize_text(left or "") == normalize_text(right or "")


def set_auth(data: dict) -> None:
    st.session_state["access_token"] = data["access_token"]
    st.session_state["user"] = data["user"]


def endereco_label(endereco: dict | None) -> str:
    if not endereco:
        return "Endereco nao informado"

    parts = [
        endereco.get("logradouro"),
        endereco.get("bairro"),
        endereco.get("municipio"),
        endereco.get("estado"),
    ]
    return ", ".join(part for part in parts if part) or "Endereco nao informado"


def marker_popup(espaco: dict) -> str:
    esportes = ", ".join(espaco.get("esportes") or ["Esportes nao informados"])
    endereco = endereco_label(espaco.get("endereco"))
    qtd_quadras = espaco.get("qtd_quadras") or 1
    cobertura = espaco.get("cobertura") or "Nao informada"

    return f"""
    <div style="width: 240px; font-family: Arial, sans-serif;">
        <h4 style="margin: 0 0 8px; color: #1B2A4A;">{espaco["nome"]}</h4>
        <div style="color: #E86A10; font-weight: 700; margin-bottom: 6px;">
            {esportes}
        </div>
        <div style="font-size: 13px; color: #1B2A4A; line-height: 1.35;">
            <b>Endereco:</b> {endereco}<br>
            <b>Quadras:</b> {qtd_quadras}<br>
            <b>Cobertura:</b> {cobertura}
        </div>
    </div>
    """


def render_espacos_map(
    title: str,
    owner_view: bool = False,
    espacos_data: list[dict] | None = None,
    error: str | None = None,
    show_title: bool = True,
) -> None:
    espacos = espacos_data
    if espacos is None:
        espacos, error = get_espacos()

    if show_title:
        st.subheader(title)
    if error:
        st.warning(error)
        return

    if not espacos:
        st.info("Nenhuma quadra encontrada.")
        return

    mapa = folium.Map(
        location=MAP_CENTER,
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
    )
    cluster = MarkerCluster(name="Quadras").add_to(mapa)

    sem_coordenada = 0
    for espaco in espacos:
        lat = espaco.get("latitude")
        lng = espaco.get("longitude")
        if lat is None or lng is None:
            sem_coordenada += 1
            continue

        icon_color = "orange" if not owner_view else "darkblue"

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(marker_popup(espaco), max_width=280),
            tooltip=espaco["nome"],
            icon=folium.Icon(color=icon_color, icon="futbol", prefix="fa"),
        ).add_to(cluster)

    st_folium(mapa, width=None, height=500, use_container_width=True)
    if sem_coordenada:
        st.caption(f"{sem_coordenada} locais ainda nao possuem latitude/longitude.")


def filter_espacos(
    espacos: list[dict],
    search: str = "",
    cidade: str = "Todas",
    esporte: str = "Todos",
    cobertura: str = "Todas",
    preco_max: float | None = None,
) -> list[dict]:
    search = search.strip().lower()
    filtered = []
    for espaco in espacos:
        endereco = espaco.get("endereco") or {}
        esportes = espaco.get("esportes") or []
        preco = espaco.get("preco_hora")
        if search and search not in espaco.get("nome", "").lower():
            continue
        if cidade != "Todas" and not same_text(endereco.get("municipio"), cidade):
            continue
        if esporte != "Todos" and esporte not in esportes:
            continue
        if cobertura != "Todas" and espaco.get("cobertura") != cobertura:
            continue
        if preco_max is not None and preco is not None and preco > preco_max:
            continue
        filtered.append(espaco)
    return filtered


def render_espacos_filters(espacos: list[dict], key_prefix: str) -> list[dict]:
    cidades_by_key = {}
    for espaco in espacos:
        cidade = (espaco.get("endereco") or {}).get("municipio")
        if cidade:
            cidades_by_key.setdefault(normalize_text(cidade), cidade.title())
    cidades = sorted(cidades_by_key.values())
    esportes = sorted(
        {esporte for espaco in espacos for esporte in (espaco.get("esportes") or [])}
    )
    coberturas = sorted(
        {espaco.get("cobertura") for espaco in espacos if espaco.get("cobertura")}
    )
    prices = [espaco.get("preco_hora") for espaco in espacos if espaco.get("preco_hora")]

    with st.expander("Filtros", expanded=True):
        col_1, col_2, col_3, col_4 = st.columns([0.34, 0.22, 0.22, 0.22])
        with col_1:
            search = st.text_input("Buscar", key=f"{key_prefix}_search")
        with col_2:
            cidade = st.selectbox("Cidade", ["Todas", *cidades], key=f"{key_prefix}_cidade")
        with col_3:
            esporte = st.selectbox("Esporte", ["Todos", *esportes], key=f"{key_prefix}_esporte")
        with col_4:
            cobertura = st.selectbox(
                "Cobertura",
                ["Todas", *coberturas],
                key=f"{key_prefix}_cobertura",
            )

        preco_max = None
        if prices:
            preco_max = st.slider(
                "Preco maximo por hora",
                min_value=0,
                max_value=int(max(prices) + 50),
                value=int(max(prices) + 50),
                step=10,
                key=f"{key_prefix}_preco",
            )

    return filter_espacos(espacos, search, cidade, esporte, cobertura, preco_max)


def render_auth_brand_panel() -> None:
    with st.container(border=True):
        st.image(str(LOGO_PATH), use_container_width=True)
        st.header("Reserve quadras com poucos cliques.")
        st.write(
            "Encontre espacos esportivos, escolha horarios disponiveis e acompanhe "
            "suas reservas em um so lugar."
        )
        st.caption("Recife, Olinda, Paulista, Abreu e Lima e Jaboatao")


def render_auth_metrics() -> None:
    col_1, col_2, col_3 = st.columns(3, gap="small")
    with col_1:
        with st.container(border=True):
            st.caption("Locais")
            st.subheader("33")
    with col_2:
        with st.container(border=True):
            st.caption("Cidades")
            st.subheader("5")
    with col_3:
        with st.container(border=True):
            st.caption("Esportes")
            st.subheader("15")


def render_profile_preview(tipo_usuario: str) -> None:
    with st.container(border=True):
        if tipo_usuario == "Dono de quadra":
            st.caption(
                "Perfil dono de quadra: painel para gerenciar quadras e reservas."
            )
        else:
            st.caption("Perfil usuario: busca de quadras por cidade e esporte.")


def login_page() -> None:
    left, right = st.columns([0.95, 1.05], gap="large", vertical_alignment="top")

    with left:
        render_auth_brand_panel()

    with right:
        render_auth_metrics()
        st.header("Acesse sua conta")
        st.caption("Entre para jogar ou cadastre seu espaco esportivo.")

        login_tab, register_tab = st.tabs(["Entrar", "Criar conta"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                data, error = post_api("/auth/login", {"email": email, "senha": senha})
                if error:
                    st.error(error)
                else:
                    set_auth(data)
                    st.rerun()

        with register_tab:
            with st.form("register_form"):
                account_col_1, account_col_2 = st.columns(2)
                with account_col_1:
                    nome = st.text_input("Nome completo")
                with account_col_2:
                    email = st.text_input("Email", key="register_email")
                tipo_usuario = st.radio(
                    "Tipo de conta",
                    options=[
                        "Usuario",
                        "Dono de quadra",
                    ],
                    horizontal=True,
                )
                render_profile_preview(tipo_usuario)
                form_col_1, form_col_2 = st.columns(2)
                with form_col_1:
                    telefone = st.text_input("Telefone")
                with form_col_2:
                    cpf = st.text_input("CPF")
                data_nascimento = st.date_input(
                    "Data de nascimento",
                    value=date(2000, 1, 1),
                    min_value=date(1900, 1, 1),
                    max_value=date.today(),
                    format="DD/MM/YYYY",
                )
                st.caption("Endereco residencial")
                address_col_1, address_col_2 = st.columns([0.7, 0.3])
                with address_col_1:
                    logradouro = st.text_input("Rua / avenida")
                with address_col_2:
                    cep = st.text_input("CEP")
                address_col_3, address_col_4, address_col_5 = st.columns([0.4, 0.4, 0.2])
                with address_col_3:
                    bairro = st.text_input("Bairro")
                with address_col_4:
                    municipio = st.text_input("Cidade")
                with address_col_5:
                    estado = st.text_input("UF", value="PE", max_chars=2)
                senha = st.text_input("Senha", type="password", key="register_password")
                submitted = st.form_submit_button("Criar conta", use_container_width=True)

            if submitted:
                payload = {
                    "nome_completo": nome,
                    "email": email,
                    "telefone": telefone or None,
                    "cpf": cpf or None,
                    "data_nascimento": data_nascimento.isoformat()
                    if data_nascimento
                    else None,
                    "endereco_residencia": {
                        "cep": cep or None,
                        "logradouro": logradouro or None,
                        "bairro": bairro or None,
                        "municipio": municipio or None,
                        "estado": estado or None,
                    },
                    "is_dono_quadra": tipo_usuario == "Dono de quadra",
                    "senha": senha,
                }
                data, error = post_api("/auth/register", payload)
                if error:
                    st.error(error)
                else:
                    set_auth(data)
                    st.rerun()


def render_sidebar(user: dict, show_logout: bool = True) -> None:
    with st.sidebar:
        st.image(str(LOGO_PATH), use_container_width=True)
        st.divider()
        st.markdown(f"**{user.get('nome', 'Usuario')}**")
        st.caption("Dono de quadra" if user.get("is_dono_quadra") else "Usuario")
        if show_logout and st.button("Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def render_logout_button() -> None:
    with st.sidebar:
        if st.button("Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def format_currency(value: float | int | None) -> str:
    amount = float(value or 0)
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_user_navigation() -> str:
    current_page = st.session_state.get("user_page", "Mapa")
    with st.sidebar:
        st.caption("Navegacao")
        if st.button("Mapa", use_container_width=True, type="primary" if current_page == "Mapa" else "secondary"):
            st.session_state["user_page"] = "Mapa"
            st.rerun()
        if st.button(
            "Reservar quadra",
            use_container_width=True,
            type="primary" if current_page == "Reservar quadra" else "secondary",
        ):
            st.session_state["user_page"] = "Reservar quadra"
            st.rerun()
        if st.button(
            "Minhas reservas",
            use_container_width=True,
            type="primary" if current_page == "Minhas reservas" else "secondary",
        ):
            st.session_state["user_page"] = "Minhas reservas"
            st.rerun()
        if st.button(
            "Assistente",
            use_container_width=True,
            type="primary" if current_page == "Assistente" else "secondary",
        ):
            st.session_state["user_page"] = "Assistente"
            st.rerun()
        if st.button(
            "Favoritos",
            use_container_width=True,
            type="primary" if current_page == "Favoritos" else "secondary",
        ):
            st.session_state["user_page"] = "Favoritos"
            st.rerun()
    return st.session_state.get("user_page", "Mapa")


def init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "Oi. Eu posso ajudar com reservas, quadras, horarios, "
                    "favoritos, pagamentos e suas reservas."
                ),
            }
        ]
    if "chat_flow" not in st.session_state:
        st.session_state["chat_flow"] = {"intent": None, "step": "idle"}


def add_chat_message(role: str, content: str) -> None:
    st.session_state["chat_messages"].append({"role": role, "content": content})


def reset_chat_flow() -> None:
    st.session_state["chat_flow"] = {"intent": None, "step": "idle"}


def clear_chat_flow_selection(flow: dict) -> None:
    for key in ["candidates", "selected_space", "date", "date_hint", "time_hint", "slots", "slot"]:
        flow.pop(key, None)


def normalize_text(value: str) -> str:
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
    normalized = value.lower().strip()
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized


def chat_first_number(value: str) -> int | None:
    for raw_token in normalize_text(value).replace("#", " ").split():
        token = raw_token.strip(".,;:")
        if token.isdigit():
            return int(token)
    return None


def chat_option_selection(value: str) -> int | None:
    text = normalize_text(value)
    compact = text.replace("#", " ").strip()
    if compact.isdigit():
        return int(compact)

    words = compact.split()
    option_terms = {"opcao", "opção", "numero", "n", "quadra", "horario"}
    if len(words) <= 3 and any(word in option_terms for word in words):
        for word in words:
            token = word.strip(".,;:")
            if token.isdigit():
                return int(token)
    return None


def is_new_chat_search(message: str, parsed: dict) -> bool:
    text = normalize_text(message)
    if chat_option_selection(message) is not None:
        return False
    if parsed.get("intent") in {"criar_reserva", "buscar_quadras", "ver_disponibilidade"}:
        return True
    search_terms = [
        "marcar",
        "reservar",
        "bater bola",
        "jogar",
        "pelada",
        "quadra",
        "disponivel",
        "horario",
        "o que tem",
    ]
    return any(term in text for term in search_terms)


def parse_chat_date(message: str) -> date | None:
    text = normalize_text(message)
    if "hoje" in text:
        return date.today()
    if "amanha" in text:
        return date.fromordinal(date.today().toordinal() + 1)

    for separator in ["/", "-"]:
        parts = text.split()
        for part in parts:
            if separator not in part:
                continue
            values = part.strip(".,;").split(separator)
            try:
                if len(values) == 2:
                    day, month = [int(item) for item in values]
                    return date(date.today().year, month, day)
                if len(values) == 3:
                    if len(values[0]) == 4:
                        year, month, day = [int(item) for item in values]
                    else:
                        day, month, year = [int(item) for item in values]
                    return date(year, month, day)
            except ValueError:
                continue
    return None


def parse_chat_time(message: str | None) -> time | None:
    if not message:
        return None
    text = normalize_text(message).replace("as ", " ")
    for raw_token in text.split():
        token = raw_token.strip(".,;")
        if "h" in token:
            hour_text, minute_text = token.split("h", maxsplit=1)
            minute_text = minute_text or "00"
        elif ":" in token:
            hour_text, minute_text = token.split(":", maxsplit=1)
        else:
            continue
        try:
            hour = int(hour_text)
            minute = int(minute_text)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return time(hour, minute)
        except ValueError:
            continue
    return None


def match_chat_option(value: str | None, options: list[str]) -> str | None:
    if not value:
        return None
    normalized_value = normalize_text(value)
    for option in sorted(options, key=len, reverse=True):
        normalized_option = normalize_text(option)
        if (
            normalized_value == normalized_option
            or normalized_option in normalized_value
            or normalized_value in normalized_option
        ):
            return option
    return None


def chat_sport_matches(requested_sport: str, espaco: dict) -> bool:
    requested = normalize_text(requested_sport)
    for sport in espaco.get("esportes") or []:
        current = normalize_text(sport)
        if requested == current or requested in current or current in requested:
            return True
    return False


def detect_chat_sport(message: str, espacos: list[dict]) -> str | None:
    text = normalize_text(message)
    sport_synonyms = {
        "futebol": ["pelada", "bater bola", "jogar bola", "futebol", "society"],
        "beach tennis": ["beach tennis", "beachtennis"],
        "tenis": ["tenis", "tennis"],
        "volei": ["volei", "voley", "volley", "voleibol"],
        "futevolei": ["futevolei", "fute volei"],
    }
    sports = sorted(
        {sport for espaco in espacos for sport in (espaco.get("esportes") or [])},
        key=len,
        reverse=True,
    )
    for canonical, aliases in sport_synonyms.items():
        if any(alias in text for alias in aliases):
            matched = match_chat_option(canonical, sports)
            if matched:
                return matched
    for sport in sports:
        if normalize_text(sport) in text:
            return sport
    return None


def resolve_chat_sport(value: str | None, message: str, espacos: list[dict]) -> str | None:
    sports = sorted({sport for espaco in espacos for sport in (espaco.get("esportes") or [])})
    return match_chat_option(value, sports) or detect_chat_sport(message, espacos)


def detect_chat_city(message: str, espacos: list[dict]) -> str | None:
    text = normalize_text(message)
    cities = sorted(
        {
            (espaco.get("endereco") or {}).get("municipio")
            for espaco in espacos
            if (espaco.get("endereco") or {}).get("municipio")
        },
        key=len,
        reverse=True,
    )
    for city in cities:
        if normalize_text(city) in text:
            return city
    return None


def resolve_chat_city(value: str | None, message: str, espacos: list[dict]) -> str | None:
    cities = sorted(
        {
            (espaco.get("endereco") or {}).get("municipio")
            for espaco in espacos
            if (espaco.get("endereco") or {}).get("municipio")
        }
    )
    return match_chat_option(value, cities) or detect_chat_city(message, espacos)


def is_chat_in_scope(message: str) -> bool:
    text = normalize_text(message)
    allowed_terms = [
        "quadra",
        "reserva",
        "reservar",
        "marcar",
        "pelada",
        "jogar",
        "cancelar",
        "horario",
        "agenda",
        "pagamento",
        "pix",
        "favorito",
        "favoritar",
        "esporte",
        "futebol",
        "tenis",
        "beach",
        "volei",
        "futevolei",
        "preco",
        "cidade",
        "mapa",
        "minhas reservas",
    ]
    return any(term in text for term in allowed_terms)


def classify_chat_intent(message: str) -> str:
    text = normalize_text(message)
    if any(term in text for term in ["cancelar", "desmarcar"]):
        return "cancelar_reserva"
    if any(term in text for term in ["minhas reservas", "ver reservas", "historico"]):
        return "ver_reservas"
    if any(term in text for term in ["pix", "pagamento", "comprovante"]):
        return "pagamento"
    if any(term in text for term in ["favorito", "favoritar"]):
        return "favoritos"
    if any(term in text for term in ["reservar", "reserva", "marcar", "pelada", "jogar", "horario"]):
        return "criar_reserva"
    if any(term in text for term in ["quadra", "buscar", "encontrar", "esporte"]):
        return "buscar_quadras"
    return "fora_do_escopo"


def build_chat_candidates(flow: dict, espacos: list[dict]) -> list[dict]:
    candidates = espacos
    if flow.get("sport"):
        candidates = [
            espaco
            for espaco in candidates
            if chat_sport_matches(flow["sport"], espaco)
        ]
    if flow.get("city"):
        candidates = [
            espaco
            for espaco in candidates
            if same_text((espaco.get("endereco") or {}).get("municipio"), flow["city"])
        ]
    return candidates[:5]


def format_chat_candidates(candidates: list[dict]) -> str:
    if not candidates:
        return "Nao encontrei quadras com esses filtros."
    lines = ["Encontrei estas opcoes:"]
    for index, espaco in enumerate(candidates, start=1):
        lines.append(
            f"{index}. {espaco['nome']} - {endereco_label(espaco.get('endereco'))} - "
            f"{format_currency(espaco.get('preco_hora'))}/h"
        )
    lines.append("Digite o numero da quadra que voce quer reservar.")
    return "\n".join(lines)


def format_chat_slots(slots: list[dict], heading: str = "Horarios disponiveis:") -> str:
    lines = [heading]
    for index, slot in enumerate(slots, start=1):
        lines.append(
            f"{index}. {slot['hora_inicio'][:5]} - {slot['hora_fim'][:5]} "
            f"({slot['vagas']} vaga(s))"
        )
    lines.append("Digite o numero do horario desejado.")
    return "\n".join(lines)


def slot_start_time(slot: dict) -> time:
    return time.fromisoformat(slot["hora_inicio"])


def load_chat_slots(flow: dict, reservation_date: date) -> str | None:
    flow["date"] = reservation_date.isoformat()
    slots, error = get_availability(flow["selected_space"]["id"], reservation_date)
    if error:
        reset_chat_flow()
        return error
    available_slots = [slot for slot in slots if slot.get("disponivel")]
    if not available_slots:
        reset_chat_flow()
        return "Nao ha horarios disponiveis nessa data. Tente outra data."
    requested_time = parse_chat_time(flow.get("time_hint"))
    if requested_time:
        filtered_slots = [
            slot for slot in available_slots if slot_start_time(slot) >= requested_time
        ]
        if filtered_slots:
            available_slots = filtered_slots
    flow["slots"] = available_slots[:8]
    flow["step"] = "choose_slot"
    return None


def find_chat_slot_by_time(slots: list[dict], requested_time: time | None) -> dict | None:
    if not requested_time:
        return None
    requested = requested_time.strftime("%H:%M")
    for slot in slots:
        if slot["hora_inicio"][:5] == requested:
            return slot
    return None


def confirm_chat_slot(flow: dict, selected_slot: dict) -> str:
    flow["slot"] = selected_slot
    flow["step"] = "confirm"
    space = flow["selected_space"]
    return (
        f"Confirmar reserva em {space['nome']} no dia {flow['date']} "
        f"das {selected_slot['hora_inicio'][:5]} as {selected_slot['hora_fim'][:5]} "
        f"por {format_currency(space.get('preco_hora'))}? Responda 'confirmar' ou 'cancelar'."
    )


def format_cancelable_reservas(reservas: list[dict]) -> str:
    lines = ["Qual reserva voce quer cancelar?"]
    for index, reserva in enumerate(reservas[:5], start=1):
        lines.append(
            f"{index}. #{reserva['id']} - {reserva['espaco']} - "
            f"{reserva['data']} {reserva['hora_inicio'][:5]} - {reserva['status']}"
        )
    lines.append("Digite o numero da lista ou o ID da reserva.")
    return "\n".join(lines)


def handle_chat_cancel_flow(token: str, message: str) -> str:
    flow = st.session_state["chat_flow"]
    text = normalize_text(message)
    parsed = st.session_state.get("last_ai_parse") or {}

    if flow.get("step", "").startswith("cancel_") and (
        parsed.get("cancel_flow") or text in {"sair", "reiniciar", "nao"}
    ):
        reset_chat_flow()
        return "Cancelamento interrompido. Posso ajudar com outra coisa."

    reservas, error = get_my_reservas(token)
    if error:
        reset_chat_flow()
        return error
    cancelable = [reserva for reserva in reservas if reserva.get("status") != "cancelado"]
    if not cancelable:
        reset_chat_flow()
        return "Voce nao tem reservas ativas para cancelar."

    if flow.get("step") == "cancel_choose":
        selected_number = parsed.get("reservation_id") or chat_first_number(message)
        selected = None
        if selected_number:
            selected = next(
                (reserva for reserva in cancelable if reserva["id"] == selected_number),
                None,
            )
            if not selected and 1 <= selected_number <= len(flow.get("cancel_options", [])):
                selected = flow["cancel_options"][selected_number - 1]
        if not selected:
            return "Nao encontrei essa reserva. Digite o numero da lista ou o ID da reserva."
        flow["cancel_reservation"] = selected
        flow["step"] = "cancel_confirm"
        return (
            f"Confirmar cancelamento da reserva #{selected['id']} em {selected['espaco']} "
            f"no dia {selected['data']} as {selected['hora_inicio'][:5]}? "
            "Responda 'confirmar' ou 'nao'."
        )

    if flow.get("step") == "cancel_confirm":
        if not parsed.get("confirmation") and text not in {"confirmar", "sim", "ok", "pode"}:
            reset_chat_flow()
            return "Reserva mantida. Posso ajudar com outra coisa."
        selected = flow.get("cancel_reservation")
        data, error = cancel_my_reserva(token, selected["id"])
        reset_chat_flow()
        if error:
            return error
        return f"Reserva #{data['id']} cancelada."

    selected_id = parsed.get("reservation_id") or chat_first_number(message)
    if selected_id:
        selected = next((reserva for reserva in cancelable if reserva["id"] == selected_id), None)
        if selected:
            flow.update(
                {
                    "intent": "cancelar_reserva",
                    "step": "cancel_confirm",
                    "cancel_reservation": selected,
                }
            )
            return (
                f"Confirmar cancelamento da reserva #{selected['id']} em {selected['espaco']} "
                f"no dia {selected['data']} as {selected['hora_inicio'][:5]}? "
                "Responda 'confirmar' ou 'nao'."
            )

    flow.update(
        {
            "intent": "cancelar_reserva",
            "step": "cancel_choose",
            "cancel_options": cancelable[:5],
        }
    )
    return format_cancelable_reservas(cancelable)


def handle_chat_reservation_flow(token: str, message: str, espacos: list[dict]) -> str:
    flow = st.session_state["chat_flow"]
    text = normalize_text(message)
    parsed = st.session_state.get("last_ai_parse") or {}

    if parsed.get("cancel_flow") or text in {"cancelar", "sair", "reiniciar"}:
        reset_chat_flow()
        return "Fluxo reiniciado. Me diga o esporte, cidade ou quadra que voce quer reservar."

    if flow.get("step") == "ask_sport":
        sport = resolve_chat_sport(parsed.get("sport"), message, espacos)
        if not sport:
            return "Qual esporte voce quer jogar? Exemplos: Beach Tennis, Futebol, Tenis."
        flow["sport"] = sport
        flow["step"] = "ask_city"
        return "Em qual cidade voce quer jogar?"

    if flow.get("step") == "ask_city":
        city = resolve_chat_city(parsed.get("city"), message, espacos)
        if not city:
            cities = sorted(
                {
                    (espaco.get("endereco") or {}).get("municipio")
                    for espaco in espacos
                    if (espaco.get("endereco") or {}).get("municipio")
                }
            )
            examples = ", ".join(cities[:5]) or "Recife"
            return f"Nao reconheci a cidade. Tente uma destas: {examples}."
        flow["city"] = city
        candidates = build_chat_candidates(flow, espacos)
        if not candidates:
            clear_chat_flow_selection(flow)
            return "Nao encontrei quadras com esse esporte nessa cidade. Me diga outra cidade."
        flow["candidates"] = candidates
        flow["step"] = "choose_space"
        return format_chat_candidates(candidates)

    if flow.get("step") == "choose_space":
        if is_new_chat_search(message, parsed):
            reset_chat_flow()
            return handle_chat_reservation_flow(token, message, espacos)
        try:
            selected_index = int(chat_option_selection(message) or parsed.get("space_number") or 0) - 1
            selected = flow["candidates"][selected_index]
        except (ValueError, IndexError, KeyError):
            return "Digite o numero de uma das quadras listadas."
        flow["selected_space"] = selected
        if flow.get("date_hint"):
            reservation_date = date.fromisoformat(flow["date_hint"])
            error = load_chat_slots(flow, reservation_date)
            if error:
                return error
            selected_slot = find_chat_slot_by_time(
                flow["slots"],
                parse_chat_time(flow.get("time_hint")),
            )
            if selected_slot:
                return confirm_chat_slot(flow, selected_slot)
            return format_chat_slots(
                flow["slots"],
                f"Horarios disponiveis em {reservation_date.isoformat()}:",
            )
        flow["step"] = "ask_date"
        return f"Boa escolha: {selected['nome']}. Para qual data? Pode responder 'hoje', 'amanha' ou '25/05'."

    if flow.get("step") == "ask_date":
        reservation_date = parse_chat_date(parsed.get("date_text") or message)
        if not reservation_date or reservation_date < date.today():
            return "Informe uma data valida futura. Exemplos: hoje, amanha ou 25/05."
        requested_time = parse_chat_time(parsed.get("time_text") or message)
        if requested_time:
            flow["time_hint"] = requested_time.strftime("%H:%M")
        error = load_chat_slots(flow, reservation_date)
        if error:
            return error
        selected_slot = find_chat_slot_by_time(flow["slots"], requested_time)
        if selected_slot:
            return confirm_chat_slot(flow, selected_slot)
        return format_chat_slots(flow["slots"])

    if flow.get("step") == "choose_slot":
        if is_new_chat_search(message, parsed):
            reset_chat_flow()
            return handle_chat_reservation_flow(token, message, espacos)
        try:
            selected_index = int(chat_option_selection(message) or parsed.get("slot_number") or 0) - 1
            selected_slot = flow["slots"][selected_index]
        except (ValueError, IndexError, KeyError):
            return "Digite o numero de um dos horarios listados."
        return confirm_chat_slot(flow, selected_slot)

    if flow.get("step") == "confirm":
        if not parsed.get("confirmation") and text not in {"confirmar", "sim", "ok", "pode"}:
            reset_chat_flow()
            return "Reserva cancelada. Posso ajudar com outra busca."
        payload = {
            "id_espaco": flow["selected_space"]["id"],
            "data_reserva": flow["date"],
            "hora_inicio": flow["slot"]["hora_inicio"],
            "hora_fim": flow["slot"]["hora_fim"],
        }
        data, error = create_reserva(token, payload)
        reset_chat_flow()
        if error:
            return error
        return f"Reserva confirmada: {data['espaco']} em {data['data']} as {data['hora_inicio'][:5]}."

    sport = resolve_chat_sport(parsed.get("sport"), message, espacos)
    city = resolve_chat_city(parsed.get("city"), message, espacos)
    reservation_date = parse_chat_date(parsed.get("date_text") or message)
    requested_time = parse_chat_time(parsed.get("time_text") or message)
    flow.update({"intent": "criar_reserva", "sport": sport, "city": city})
    if reservation_date:
        flow["date_hint"] = reservation_date.isoformat()
    if requested_time:
        flow["time_hint"] = requested_time.strftime("%H:%M")

    if not flow.get("sport"):
        flow["step"] = "ask_sport"
        return "Qual esporte voce quer jogar?"
    if not flow.get("city"):
        flow["step"] = "ask_city"
        return "Em qual cidade voce quer jogar?"

    candidates = build_chat_candidates(flow, espacos)
    flow["candidates"] = candidates
    if not candidates:
        reset_chat_flow()
        return "Nao encontrei quadras com esse esporte e cidade. Tente outros filtros."
    flow["step"] = "choose_space"
    return format_chat_candidates(candidates)


def handle_chat_message(token: str, message: str) -> str:
    espacos, error = get_espacos()
    if error:
        return error

    flow = st.session_state["chat_flow"]
    parsed, parse_error = parse_message_with_ai(token, message, flow.get("step"))
    if parse_error:
        parsed = None
    st.session_state["last_ai_parse"] = parsed or {}

    if flow.get("step", "").startswith("cancel_"):
        return handle_chat_cancel_flow(token, message)

    if flow.get("step") != "idle":
        return handle_chat_reservation_flow(token, message, espacos)

    if parsed:
        in_scope = bool(parsed.get("in_scope"))
        intent = parsed.get("intent", "fora_do_escopo")
    else:
        in_scope = is_chat_in_scope(message)
        intent = classify_chat_intent(message)

    if not in_scope:
        return (
            "Eu so consigo ajudar com reservas de quadras, horarios, favoritos, "
            "pagamentos e informacoes do Joga & Joga."
        )

    if intent in {"criar_reserva", "ver_disponibilidade"}:
        return handle_chat_reservation_flow(token, message, espacos)
    if intent == "buscar_quadras":
        sport = resolve_chat_sport((parsed or {}).get("sport"), message, espacos)
        city = resolve_chat_city((parsed or {}).get("city"), message, espacos)
        flow.update({"intent": "buscar_quadras", "sport": sport, "city": city})
        candidates = build_chat_candidates(flow, espacos)
        reset_chat_flow()
        return format_chat_candidates(candidates).replace(
            "Digite o numero da quadra que voce quer reservar.",
            "Para reservar alguma delas, diga: quero reservar.",
        )
    if intent == "ver_reservas":
        reservas, error = get_my_reservas(token)
        if error:
            return error
        if not reservas:
            return "Voce ainda nao possui reservas."
        lines = ["Suas reservas:"]
        for reserva in reservas[:5]:
            lines.append(
                f"#{reserva['id']} - {reserva['espaco']} - {reserva['data']} "
                f"{reserva['hora_inicio'][:5]} - {reserva['status']}"
            )
        return "\n".join(lines)
    if intent == "cancelar_reserva":
        return handle_chat_cancel_flow(token, message)
    if intent == "pagamento":
        return "Pagamentos Pix ficam em Minhas reservas. Selecione a reserva e salve o link do comprovante."
    if intent == "favoritos":
        return "Voce pode favoritar uma quadra na tela Reservar quadra, dentro dos detalhes da quadra."

    return "Posso ajudar a buscar quadras, ver horarios, reservar, cancelar, favoritar ou explicar pagamento Pix."


def render_chatbot_page(token: str) -> None:
    page_header(
        "Assistente de reservas",
        "Converse de forma guiada para encontrar quadras e reservar horarios.",
    )
    init_chat_state()

    with st.container(border=True):
        st.caption("Escopo: reservas, quadras, horarios, favoritos e pagamentos do app.")
        provider = (st.session_state.get("last_ai_parse") or {}).get("provider", "aguardando mensagem")
        st.caption(f"Parser ativo: {provider}")
        for message in st.session_state["chat_messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        prompt = st.chat_input("Ex: Quero reservar Beach Tennis em Recife amanha")
        if prompt:
            add_chat_message("user", prompt)
            answer = handle_chat_message(token, prompt)
            add_chat_message("assistant", answer)
            st.rerun()


def espaco_option_label(espaco: dict) -> str:
    endereco = endereco_label(espaco.get("endereco"))
    preco = format_currency(espaco.get("preco_hora"))
    return f"{espaco['nome']} | {endereco} | {preco}/h"


def render_reservation_form(token: str) -> None:
    espacos, error = get_espacos()
    page_header(
        "Reservar quadra",
        "Escolha uma quadra, confira os detalhes e reserve um horario disponivel.",
    )
    if error:
        st.warning(error)
        return
    if not espacos:
        st.info("Nenhuma quadra disponivel para reserva.")
        return

    filtered_espacos = render_espacos_filters(espacos, "reserve_filters")
    if not filtered_espacos:
        st.info("Nenhuma quadra encontrada com esses filtros.")
        return

    selected = st.selectbox(
        "Quadra",
        options=filtered_espacos,
        format_func=espaco_option_label,
        key="reservation_selected_space",
    )
    detail, detail_error = get_espaco_detail(token, selected["id"])
    with st.expander("Detalhes da quadra", expanded=True):
        info_card(
            selected["nome"],
            endereco_label(selected.get("endereco")),
            selected.get("esportes") or [],
        )
        details_col_1, details_col_2, details_col_3 = st.columns(3)
        details_col_1.metric("Preco/hora", format_currency(selected.get("preco_hora")))
        details_col_2.metric("Quadras", selected.get("qtd_quadras") or 1)
        details_col_3.metric("Cobertura", selected.get("cobertura") or "Nao informada")
        if detail and not detail_error:
            st.caption(
                f"Avaliacao media: {detail.get('media_avaliacoes') or 'Sem notas'} "
                f"({detail.get('total_avaliacoes', 0)} avaliacoes)"
            )
            if detail.get("favorito"):
                if st.button("Remover dos favoritos", use_container_width=True):
                    _, error = remove_favorito(token, selected["id"])
                    st.toast(error or "Removido dos favoritos.")
                    st.rerun()
            else:
                if st.button("Favoritar quadra", use_container_width=True):
                    _, error = add_favorito(token, selected["id"])
                    st.toast(error or "Quadra favoritada.")
                    st.rerun()
            for avaliacao in detail.get("avaliacoes", [])[:3]:
                st.caption(
                    f"{avaliacao.get('usuario') or 'Usuario'}: "
                    f"{avaliacao.get('nota')} estrelas - {avaliacao.get('comentario') or ''}"
                )

    data_reserva = st.date_input(
        "Data",
        min_value=date.today(),
        value=date.today(),
        format="DD/MM/YYYY",
        key="reservation_date",
    )
    slots, slots_error = get_availability(selected["id"], data_reserva)
    available_slots = [slot for slot in slots if slot.get("disponivel")]
    if slots_error:
        st.warning(slots_error)
        return
    if not available_slots:
        st.info("Nao ha horarios disponiveis para essa data.")
        return

    selected_slot = st.selectbox(
        "Horario disponivel",
        options=available_slots,
        format_func=lambda slot: (
            f"{slot['hora_inicio'][:5]} - {slot['hora_fim'][:5]} "
            f"({slot['vagas']} vaga(s))"
        ),
    )
    st.caption(f"Valor estimado: {format_currency(selected.get('preco_hora'))}")

    if not st.button("Confirmar reserva", use_container_width=True):
        return

    payload = {
        "id_espaco": selected["id"],
        "data_reserva": data_reserva.isoformat(),
        "hora_inicio": selected_slot["hora_inicio"],
        "hora_fim": selected_slot["hora_fim"],
    }
    data, error = create_reserva(token, payload)
    if error:
        st.toast(error)
        st.error(error)
        return

    st.session_state["user_page"] = "Minhas reservas"
    st.session_state["flash_message"] = {
        "type": "success",
        "text": f"Reserva confirmada em {data['espaco']} no dia {data['data']}.",
    }
    st.rerun()


def render_my_reservas(token: str) -> None:
    page_header(
        "Minhas reservas",
        "Acompanhe seus horarios, envie comprovante Pix, cancele ou avalie reservas concluidas.",
    )
    reservas, error = get_my_reservas(token)
    if error:
        st.warning(error)
        return
    if not reservas:
        st.info("Voce ainda nao possui reservas.")
        return

    rows = []
    for reserva in reservas:
        rows.append(
            {
                "Quadra": reserva.get("espaco"),
                "Data": reserva.get("data"),
                "Inicio": reserva.get("hora_inicio"),
                "Fim": reserva.get("hora_fim"),
                "Status": reserva.get("status"),
                "Valor": format_currency(reserva.get("valor_total")),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    payable = [reserva for reserva in reservas if reserva.get("status") != "cancelado"]
    if payable:
        st.subheader("Pagamento Pix")
        selected_payment = st.selectbox(
            "Reserva para pagamento",
            options=payable,
            format_func=lambda reserva: (
                f"#{reserva['id']} - {reserva['espaco']} - "
                f"{format_currency(reserva.get('valor_total'))}"
            ),
            key="payment_reserva",
        )
        comprovante_url = st.text_input(
            "Link do comprovante Pix",
            value=selected_payment.get("comprovante_url") or "",
        )
        if st.button("Salvar comprovante", use_container_width=True):
            data, error = update_my_pagamento(token, selected_payment["id"], comprovante_url or None)
            if error:
                st.toast(error)
                st.error(error)
                return
            st.session_state["flash_message"] = {
                "type": "success",
                "text": f"Pagamento da reserva #{data['id']} atualizado.",
            }
            st.rerun()

    concluded = [reserva for reserva in reservas if reserva.get("status") == "concluido"]
    if concluded:
        st.subheader("Avaliar quadra")
        selected_review = st.selectbox(
            "Reserva concluida",
            options=concluded,
            format_func=lambda reserva: f"#{reserva['id']} - {reserva['espaco']} - {reserva['data']}",
        )
        nota = st.slider("Nota", 1, 5, 5)
        comentario = st.text_area("Comentario", max_chars=500)
        if st.button("Enviar avaliacao", use_container_width=True):
            data, error = create_avaliacao(
                token,
                {
                    "id_reserva": selected_review["id"],
                    "nota": nota,
                    "comentario": comentario or None,
                },
            )
            if error:
                st.toast(error)
                st.error(error)
                return
            st.session_state["flash_message"] = {
                "type": "success",
                "text": f"Avaliacao enviada para {data['espaco']}.",
            }
            st.rerun()

    cancelable = [reserva for reserva in reservas if reserva.get("status") != "cancelado"]
    if not cancelable:
        return

    st.subheader("Cancelar reserva")
    selected = st.selectbox(
        "Reserva",
        options=cancelable,
        format_func=lambda reserva: (
            f"#{reserva['id']} - {reserva['espaco']} - "
            f"{reserva['data']} {reserva['hora_inicio']}"
        ),
    )
    if st.button("Cancelar reserva", use_container_width=True):
        data, error = cancel_my_reserva(token, selected["id"])
        if error:
            st.toast(error)
            st.error(error)
            return
        st.toast("Reserva cancelada.")
        st.session_state["flash_message"] = {
            "type": "success",
            "text": f"Reserva #{data['id']} cancelada.",
        }
        st.rerun()


def render_favoritos_page(token: str) -> None:
    page_header("Favoritos", "Suas quadras salvas para reservar mais rapido.")
    favoritos, error = get_favoritos(token)
    if error:
        st.warning(error)
        return
    if not favoritos:
        st.info("Voce ainda nao favoritou nenhuma quadra.")
        return

    rows = [
        {
            "Nome": espaco.get("nome"),
            "Endereco": endereco_label(espaco.get("endereco")),
            "Esportes": ", ".join(espaco.get("esportes") or []),
            "Preco/hora": format_currency(espaco.get("preco_hora")),
        }
        for espaco in favoritos
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def usuario_home_page(user: dict) -> None:
    render_sidebar(user, show_logout=False)
    token = st.session_state.get("access_token")
    page = render_user_navigation()
    render_logout_button()
    show_flash_message()

    if page == "Reservar quadra":
        render_reservation_form(token)
        return

    if page == "Minhas reservas":
        render_my_reservas(token)
        return

    if page == "Assistente":
        render_chatbot_page(token)
        return

    if page == "Favoritos":
        render_favoritos_page(token)
        return

    espacos, error = get_espacos()
    page_header(
        "Quadras disponiveis",
        "Explore quadras por cidade, esporte, cobertura e preco antes de reservar.",
    )
    if error:
        st.warning(error)
        return
    cities_count = len(
        {
            (espaco.get("endereco") or {}).get("municipio")
            for espaco in espacos
            if (espaco.get("endereco") or {}).get("municipio")
        }
    )
    sports_count = len({sport for espaco in espacos for sport in (espaco.get("esportes") or [])})
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Quadras", len(espacos))
    metric_2.metric("Cidades", cities_count)
    metric_3.metric("Esportes", sports_count)
    filtered_espacos = render_espacos_filters(espacos, "map_filters")
    render_espacos_map(
        "Mapa",
        espacos_data=filtered_espacos,
        error=None,
        show_title=False,
    )


def render_owner_metrics(dashboard: dict) -> None:
    col_1, col_2, col_3, col_4 = st.columns(4, gap="small")
    with col_1:
        st.metric("Espacos", dashboard.get("total_espacos", 0))
    with col_2:
        st.metric("Quadras", dashboard.get("total_quadras", 0))
    with col_3:
        st.metric("Reservas no mes", dashboard.get("reservas_mes", 0))
    with col_4:
        st.metric("Faturamento no mes", format_currency(dashboard.get("faturamento_mes")))
    st.caption(
        f"Ticket medio no mes: {format_currency(dashboard.get('ticket_medio_mes'))}"
    )


def render_owner_revenue(dashboard: dict) -> None:
    st.subheader("Faturamento por mes")
    monthly = dashboard.get("faturamento_por_mes") or []
    if not monthly:
        st.info("Ainda nao ha reservas faturadas para montar o historico mensal.")
        return

    revenue_df = pd.DataFrame(monthly).rename(
        columns={
            "mes": "Mes",
            "faturamento": "Faturamento",
            "reservas": "Reservas",
        }
    )
    st.bar_chart(revenue_df.set_index("Mes")[["Faturamento"]], use_container_width=True)
    st.dataframe(
        revenue_df.assign(
            Faturamento=revenue_df["Faturamento"].apply(format_currency),
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_owner_reservas(token: str) -> None:
    page_header(
        "Reservas recebidas",
        "Veja quem reservou, acompanhe pagamentos e atualize o status operacional.",
    )
    reservas, error = get_owner_reservas(token)
    if error:
        st.warning(error)
        return
    if not reservas:
        st.info("Suas quadras ainda nao possuem reservas.")
        return

    rows = [
        {
            "ID": reserva.get("id"),
            "Usuario": reserva.get("usuario") or f"Usuario #{reserva.get('id_usuario')}",
            "Quadra": reserva.get("espaco"),
            "Data": reserva.get("data"),
            "Inicio": reserva.get("hora_inicio"),
            "Fim": reserva.get("hora_fim"),
            "Status": reserva.get("status"),
            "Valor": format_currency(reserva.get("valor_total")),
        }
        for reserva in reservas
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Atualizar status")
    selected = st.selectbox(
        "Reserva",
        options=reservas,
        format_func=lambda reserva: (
            f"#{reserva['id']} - {reserva['espaco']} - "
            f"{reserva['data']} {reserva['hora_inicio']}"
        ),
    )
    new_status = st.selectbox("Status", ["confirmado", "concluido", "cancelado"])
    if st.button("Salvar status", use_container_width=True):
        data, error = update_owner_reserva_status(token, selected["id"], new_status)
        if error:
            st.toast(error)
            st.error(error)
            return
        st.session_state["flash_message"] = {
            "type": "success",
            "text": f"Reserva #{data['id']} atualizada para {data['status']}.",
        }
        st.rerun()


def render_owner_agenda(token: str) -> None:
    page_header("Agenda do dia", "Visao diaria das reservas das suas quadras.")
    data_agenda = st.date_input("Data da agenda", value=date.today(), format="DD/MM/YYYY")
    reservas, error = get_owner_reservas(token, data_agenda)
    if error:
        st.warning(error)
        return
    if not reservas:
        st.info("Nenhuma reserva nessa data.")
        return

    agenda_df = pd.DataFrame(
        [
            {
                "Hora": f"{reserva['hora_inicio'][:5]} - {reserva['hora_fim'][:5]}",
                "Quadra": reserva.get("espaco"),
                "Usuario": reserva.get("usuario"),
                "Status": reserva.get("status"),
                "Pagamento": reserva.get("pagamento_status") or "sem registro",
                "Valor": format_currency(reserva.get("valor_total")),
            }
            for reserva in reservas
        ]
    )
    st.dataframe(agenda_df, use_container_width=True, hide_index=True)


def weekday_label(index: int) -> str:
    labels = [
        "Segunda",
        "Terca",
        "Quarta",
        "Quinta",
        "Sexta",
        "Sabado",
        "Domingo",
    ]
    return labels[index]


def render_owner_horarios(token: str, espacos: list[dict]) -> None:
    page_header(
        "Horarios de funcionamento",
        "Defina quando cada quadra pode receber reservas.",
    )
    horarios, error = get_owner_horarios(token)
    if error:
        st.warning(error)
        return

    if horarios:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Quadra ID": h["id_espaco"],
                        "Dia": weekday_label(h["dia_semana"]),
                        "Abertura": h["hora_abertura"],
                        "Fechamento": h["hora_fechamento"],
                        "Ativo": h["ativo"],
                    }
                    for h in horarios
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Sem horarios cadastrados. O sistema usa 06:00-23:00 como padrao.")

    if not espacos:
        st.info("Cadastre uma quadra antes de definir horarios.")
        return

    st.subheader("Adicionar horario")
    selected = st.selectbox("Quadra", options=espacos, format_func=lambda e: e["nome"])
    dia = st.selectbox("Dia da semana", options=list(range(7)), format_func=weekday_label)
    col_1, col_2 = st.columns(2)
    with col_1:
        abertura = st.time_input("Abertura", value=time(6, 0), step=1800)
    with col_2:
        fechamento = st.time_input("Fechamento", value=time(23, 0), step=1800)
    if st.button("Salvar horario", use_container_width=True):
        data, error = create_owner_horario(
            token,
            selected["id"],
            {
                "dia_semana": dia,
                "hora_abertura": abertura.isoformat(),
                "hora_fechamento": fechamento.isoformat(),
            },
        )
        if error:
            st.toast(error)
            st.error(error)
            return
        st.session_state["flash_message"] = {
            "type": "success",
            "text": "Horario cadastrado.",
        }
        st.rerun()


def render_owner_bloqueios(token: str, espacos: list[dict]) -> None:
    page_header(
        "Bloqueios de horario",
        "Reserve periodos para manutencao, eventos ou indisponibilidades.",
    )
    bloqueios, error = get_owner_bloqueios(token)
    if error:
        st.warning(error)
        return
    if bloqueios:
        st.dataframe(pd.DataFrame(bloqueios), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum bloqueio cadastrado.")

    if not espacos:
        st.info("Cadastre uma quadra antes de bloquear horarios.")
        return

    st.subheader("Adicionar bloqueio")
    selected = st.selectbox("Quadra", options=espacos, format_func=lambda e: e["nome"], key="bloqueio_espaco")
    data_bloqueio = st.date_input("Data", value=date.today(), min_value=date.today(), format="DD/MM/YYYY")
    col_1, col_2 = st.columns(2)
    with col_1:
        inicio = st.time_input("Inicio", value=time(12, 0), step=1800, key="bloqueio_inicio")
    with col_2:
        fim = st.time_input("Fim", value=time(13, 0), step=1800, key="bloqueio_fim")
    motivo = st.text_input("Motivo")
    if st.button("Bloquear horario", use_container_width=True):
        data, error = create_owner_bloqueio(
            token,
            {
                "id_espaco": selected["id"],
                "data_bloqueio": data_bloqueio.isoformat(),
                "hora_inicio": inicio.isoformat(),
                "hora_fim": fim.isoformat(),
                "motivo": motivo or None,
            },
        )
        if error:
            st.toast(error)
            st.error(error)
            return
        st.session_state["flash_message"] = {
            "type": "success",
            "text": "Bloqueio cadastrado.",
        }
        st.rerun()


def render_owner_spaces(espacos: list[dict]) -> None:
    st.subheader("Minhas quadras")
    if not espacos:
        st.info("Voce ainda nao possui quadras vinculadas ao seu perfil.")
        return

    rows = []
    for espaco in espacos:
        rows.append(
            {
                "Nome": espaco.get("nome"),
                "Endereco": endereco_label(espaco.get("endereco")),
                "Esportes": ", ".join(espaco.get("esportes") or []),
                "Quadras": espaco.get("qtd_quadras") or 1,
                "Cobertura": espaco.get("cobertura") or "Nao informada",
                "Preco/hora": format_currency(espaco.get("preco_hora")),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def parse_optional_money(value: str) -> float | None:
    normalized = value.strip().replace(",", ".")
    if not normalized:
        return None
    return float(normalized)


def render_owner_create_space(token: str) -> None:
    page_header(
        "Cadastrar quadra",
        "Cadastre um espaco com endereco validado por coordenadas para aparecer no mapa.",
    )
    with st.form("owner_create_space_form"):
        nome = st.text_input("Nome do espaco")
        esportes_raw = st.text_input(
            "Esportes",
            placeholder="Beach Tennis, Futebol, Volei",
        )

        address_col_1, address_col_2 = st.columns([0.7, 0.3])
        with address_col_1:
            logradouro = st.text_input("Rua / avenida")
        with address_col_2:
            cep = st.text_input("CEP")

        address_col_3, address_col_4, address_col_5 = st.columns([0.4, 0.4, 0.2])
        with address_col_3:
            bairro = st.text_input("Bairro")
        with address_col_4:
            municipio = st.text_input("Cidade")
        with address_col_5:
            estado = st.text_input("UF", value="PE", max_chars=2)

        details_col_1, details_col_2, details_col_3 = st.columns(3)
        with details_col_1:
            qtd_quadras = st.number_input("Quantidade de quadras", min_value=1, value=1)
        with details_col_2:
            preco_hora = st.text_input("Preco por hora", placeholder="120,00")
        with details_col_3:
            cobertura = st.selectbox("Cobertura", ["Nenhuma", "Tela", "Telhado"])

        submitted = st.form_submit_button("Cadastrar quadra", use_container_width=True)

    if not submitted:
        return

    try:
        payload = {
            "nome": nome,
            "endereco": {
                "cep": cep or None,
                "logradouro": logradouro or None,
                "bairro": bairro or None,
                "municipio": municipio or None,
                "estado": estado or None,
            },
            "esportes": [
                esporte.strip()
                for esporte in esportes_raw.split(",")
                if esporte.strip()
            ],
            "cobertura": cobertura,
            "preco_hora": parse_optional_money(preco_hora),
            "qtd_quadras": int(qtd_quadras),
        }
    except ValueError:
        st.error("Confira o preco. Use apenas numeros.")
        return

    data, error = create_owner_espaco(token, payload)
    if error:
        st.toast(error)
        st.error(error)
        return

    get_espacos.clear()
    st.session_state["owner_page"] = "Minhas quadras"
    success_text = (
        f"Quadra cadastrada: {data['nome']}. "
        "Ela ja aparece em Minhas quadras e nos mapas."
    )
    st.session_state["flash_message"] = {
        "type": "success",
        "text": success_text,
    }
    st.rerun()


def render_owner_navigation() -> str:
    current_page = st.session_state.get("owner_page", "Mapa")
    with st.sidebar:
        st.caption("Navegacao")
        if st.button("Mapa", use_container_width=True, type="primary" if current_page == "Mapa" else "secondary"):
            st.session_state["owner_page"] = "Mapa"
            st.rerun()
        if st.button(
            "Minhas quadras",
            use_container_width=True,
            type="primary" if current_page == "Minhas quadras" else "secondary",
        ):
            st.session_state["owner_page"] = "Minhas quadras"
            st.rerun()
        if st.button(
            "Reservas",
            use_container_width=True,
            type="primary" if current_page == "Reservas" else "secondary",
        ):
            st.session_state["owner_page"] = "Reservas"
            st.rerun()
        if st.button(
            "Agenda",
            use_container_width=True,
            type="primary" if current_page == "Agenda" else "secondary",
        ):
            st.session_state["owner_page"] = "Agenda"
            st.rerun()
        if st.button(
            "Horarios",
            use_container_width=True,
            type="primary" if current_page == "Horarios" else "secondary",
        ):
            st.session_state["owner_page"] = "Horarios"
            st.rerun()
        if st.button(
            "Bloqueios",
            use_container_width=True,
            type="primary" if current_page == "Bloqueios" else "secondary",
        ):
            st.session_state["owner_page"] = "Bloqueios"
            st.rerun()
        if st.button(
            "Cadastrar quadra",
            use_container_width=True,
            type="primary" if current_page == "Cadastrar quadra" else "secondary",
        ):
            st.session_state["owner_page"] = "Cadastrar quadra"
            st.rerun()
    return st.session_state.get("owner_page", "Mapa")


def dono_quadra_home_page(user: dict) -> None:
    render_sidebar(user, show_logout=False)
    token = st.session_state.get("access_token")
    dashboard, dashboard_error = get_owner_dashboard(token)
    espacos, espacos_error = get_owner_espacos(token)

    page = render_owner_navigation()
    render_logout_button()
    show_flash_message()

    if page == "Mapa":
        page_header(
            "Mapa das quadras",
            "Acompanhe todos os espacos cadastrados na plataforma.",
        )
        render_espacos_map("Mapa das quadras", owner_view=True, show_title=False)
        return

    if page == "Cadastrar quadra":
        render_owner_create_space(token)
        return

    if page == "Reservas":
        render_owner_reservas(token)
        return

    if page == "Agenda":
        render_owner_agenda(token)
        return

    if page == "Horarios":
        render_owner_horarios(token, espacos)
        return

    if page == "Bloqueios":
        render_owner_bloqueios(token, espacos)
        return

    page_header(
        "Minhas quadras",
        "Acompanhe suas quadras, reservas e faturamento mensal.",
    )

    if dashboard_error:
        st.warning(dashboard_error)
    else:
        render_owner_metrics(dashboard)
        render_owner_revenue(dashboard)

    render_owner_spaces(espacos)
    render_espacos_map(
        "Mapa dos meus espacos",
        owner_view=True,
        espacos_data=espacos,
        error=espacos_error,
    )

    if not dashboard_error:
        st.caption(
            "O faturamento considera reservas nao canceladas vinculadas as suas quadras."
        )


def home_page() -> None:
    user = st.session_state.get("user", {})
    if user.get("is_dono_quadra"):
        dono_quadra_home_page(user)
    else:
        usuario_home_page(user)


if st.session_state.get("access_token"):
    home_page()
else:
    login_page()
