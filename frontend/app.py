import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

API_URL = "http://localhost:5000"

# Centro de Recife
RECIFE_CENTER = [-8.0476, -34.877]

st.set_page_config(page_title="Joga y Joga", page_icon="⚽", layout="wide")

# --- Header com logo centralizada ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    st.image("logo.png", width=300)
    st.caption("Encontre e cadastre quadras esportivas em Recife")

st.divider()

# --- Sidebar: cadastro de quadra ---
st.sidebar.header("📋 Cadastrar nova quadra")

with st.sidebar.form("form_quadra"):
    nome = st.text_input("Nome da quadra")
    endereco = st.text_input("Endereço", placeholder="Ex: Rua da Aurora, 500, Boa Vista")
    esporte = st.selectbox("Esporte", ["futebol", "vôlei", "basquete", "tênis", "futsal", "outro"])
    submitted = st.form_submit_button("Cadastrar", use_container_width=True)

    if submitted:
        if not nome or not endereco:
            st.error("Preencha nome e endereço.")
        else:
            try:
                resp = requests.post(
                    f"{API_URL}/quadras",
                    json={"nome": nome, "endereco": endereco, "esporte": esporte},
                    timeout=15,
                )
                if resp.status_code == 201:
                    st.success(f"Quadra '{nome}' cadastrada!")
                else:
                    st.error(f"Erro: {resp.json().get('erro', 'desconhecido')}")
            except requests.ConnectionError:
                st.error("Não consegui conectar na API. O backend tá rodando?")

# --- Filtro + Mapa ---
col_filtro, col_mapa = st.columns([1, 3])

with col_filtro:
    st.subheader("🔍 Filtros")
    filtro_esporte = st.selectbox(
        "Esporte",
        ["todos", "futebol", "vôlei", "basquete", "tênis", "futsal", "outro"],
    )

# --- Buscar quadras ---
try:
    params = {}
    if filtro_esporte != "todos":
        params["esporte"] = filtro_esporte

    resp = requests.get(f"{API_URL}/quadras", params=params, timeout=5)
    quadras = resp.json() if resp.status_code == 200 else []
except requests.ConnectionError:
    quadras = []
    st.warning("Backend offline — mostrando mapa vazio.")

# --- Mapa ---
with col_mapa:
    mapa = folium.Map(location=RECIFE_CENTER, zoom_start=13)

    for q in quadras:
        if q.get("latitude") and q.get("longitude"):
            folium.Marker(
                location=[q["latitude"], q["longitude"]],
                popup=f"<b>{q['nome']}</b><br>🏅 {q['esporte']}<br>📍 {q['endereco']}",
                tooltip=q["nome"],
                icon=folium.Icon(color="orange", icon="futbol", prefix="fa"),
            ).add_to(mapa)

    st_folium(mapa, width=None, height=500, use_container_width=True)

# --- Lista de quadras ---
st.divider()

if quadras:
    st.subheader(f"📋 {len(quadras)} quadra(s) encontrada(s)")
    cols = st.columns(3)
    for i, q in enumerate(quadras):
        with cols[i % 3]:
            geo = "📍" if q.get("latitude") else "⚠️ sem localização"
            st.markdown(
                f"""
                **{q['nome']}**  
                🏅 {q['esporte']}  
                {geo} {q['endereco']}
                """)
else:
    st.info("Nenhuma quadra cadastrada ainda. Use o formulário na sidebar.")
