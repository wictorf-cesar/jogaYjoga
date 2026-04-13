import os
from pathlib import Path

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

# --- Config ---
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
API_URL = os.environ.get("API_URL", "https://jogayjoga.onrender.com")
RECIFE_CENTER = [-8.0476, -34.877]

st.set_page_config(page_title="Joga y Joga", page_icon="⚽", layout="wide")


# --- API helpers ---
def api_get(path, params=None):
    try:
        resp = requests.get(f"{API_URL}{path}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        st.error("❌ Não foi possível conectar à API. Tente novamente em instantes.")
        return []
    except requests.Timeout:
        st.warning(
            "⏳ API demorando para responder (pode estar hibernando). Tente novamente."
        )
        return []
    except Exception as e:
        st.error(f"Erro na API: {e}")
        return []


def api_post(path, data):
    try:
        resp = requests.post(f"{API_URL}{path}", json=data, timeout=15)
        return resp.json(), resp.status_code
    except requests.ConnectionError:
        return {"erro": "Sem conexão com a API"}, 503
    except Exception as e:
        return {"erro": str(e)}, 500


def api_delete(path):
    try:
        resp = requests.delete(f"{API_URL}{path}", timeout=15)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"erro": str(e)}, 500


# --- Funções de dados ---
def listar_espacos(esporte=None):
    params = {}
    if esporte and esporte != "todos":
        params["esporte"] = esporte
    return api_get("/espacos", params=params)


def listar_esportes():
    data = api_get("/esportes")
    return [e["nome"] for e in data] if data else []


def criar_espaco(nome, endereco, esportes):
    return api_post(
        "/espacos",
        {
            "nome": nome,
            "endereco": endereco,
            "esportes": esportes,
        },
    )


# --- UI ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    st.image(str(BASE_DIR / "logo.png"), width=300)
    st.caption("Encontre e cadastre quadras esportivas em Recife")

st.divider()

# --- Sidebar: cadastro ---
st.sidebar.header("📋 Cadastrar novo espaço")

# Busca esportes disponíveis da API
esportes_disponiveis = listar_esportes()
if not esportes_disponiveis:
    esportes_disponiveis = [
        "Futebol Society",
        "Vôlei De Praia",
        "Futevôlei",
        "Beach Tênnis",
        "Futsal",
    ]

with st.sidebar.form("form_espaco"):
    nome = st.text_input("Nome do espaço")
    endereco = st.text_input(
        "Endereço", placeholder="Ex: Rua da Aurora, 500, Boa Vista"
    )
    esportes_selecionados = st.multiselect("Esportes", esportes_disponiveis)
    submitted = st.form_submit_button("Cadastrar", use_container_width=True)

    if submitted:
        if not nome or not endereco:
            st.error("Preencha nome e endereço.")
        elif not esportes_selecionados:
            st.error("Selecione pelo menos um esporte.")
        else:
            result, status = criar_espaco(nome, endereco, esportes_selecionados)
            if status == 201:
                st.success(f"Espaço '{nome}' cadastrado!")
            else:
                st.warning(f"Cadastrado com ressalva: {result.get('erro', '')}")

# --- Filtro + Mapa ---
col_filtro, col_mapa = st.columns([1, 3])

with col_filtro:
    st.subheader("🔍 Filtros")
    opcoes_filtro = ["todos"] + esportes_disponiveis
    filtro_esporte = st.selectbox("Esporte", opcoes_filtro)

espacos = listar_espacos(filtro_esporte)

with col_mapa:
    mapa = folium.Map(location=RECIFE_CENTER, zoom_start=13)

    for e in espacos:
        lat = e.get("latitude")
        lng = e.get("longitude")
        if lat and lng:
            esportes_str = ", ".join(e.get("esportes", []))
            endereco_str = ""
            if e.get("endereco"):
                end = e["endereco"]
                parts = [end.get("logradouro"), end.get("bairro"), end.get("municipio")]
                endereco_str = ", ".join(p for p in parts if p)

            folium.Marker(
                location=[lat, lng],
                popup=f"<b>{e['nome']}</b><br>🏅 {esportes_str}<br>📍 {endereco_str}",
                tooltip=e["nome"],
                icon=folium.Icon(color="orange", icon="futbol", prefix="fa"),
            ).add_to(mapa)

    st_folium(mapa, width=None, height=500, use_container_width=True)

# --- Lista ---
st.divider()

if espacos:
    st.subheader(f"📋 {len(espacos)} espaço(s) encontrado(s)")
    cols = st.columns(3)
    for i, e in enumerate(espacos):
        with cols[i % 3]:
            lat = e.get("latitude")
            geo = "📍" if lat else "⚠️ sem localização"
            esportes_str = ", ".join(e.get("esportes", []))
            endereco_str = ""
            if e.get("endereco"):
                end = e["endereco"]
                parts = [end.get("logradouro"), end.get("bairro"), end.get("municipio")]
                endereco_str = ", ".join(p for p in parts if p)

            st.markdown(
                f"""
                **{e["nome"]}**  
                🏅 {esportes_str}  
                {geo} {endereco_str}
                """
            )
else:
    st.info("Nenhum espaço encontrado. Use o formulário na sidebar para cadastrar.")
