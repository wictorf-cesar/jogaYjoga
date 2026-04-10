import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

import folium
import streamlit as st

# Diretório deste arquivo (funciona local e no Streamlit Cloud)
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


# --- Config ---
DB_PATH = str(BASE_DIR / "quadras.db")
RECIFE_CENTER = [-8.0476, -34.877]

st.set_page_config(page_title="Joga y Joga", page_icon="⚽", layout="wide")

geocoder = Nominatim(user_agent="jogayjoga-mvp", timeout=10)


# --- Database ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quadras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            endereco TEXT NOT NULL,
            esporte TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


# --- Geocoding ---
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


# --- CRUD ---
def criar_quadra(nome, endereco, esporte):
    lat, lng = geocode_endereco(endereco)
    conn = get_db()
    conn.execute(
        "INSERT INTO quadras (nome, endereco, esporte, latitude, longitude, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (nome, endereco, esporte.lower(), lat, lng, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return lat is not None


def listar_quadras(esporte=None):
    conn = get_db()
    if esporte and esporte != "todos":
        rows = conn.execute(
            "SELECT * FROM quadras WHERE esporte = ?", (esporte.lower(),)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM quadras").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deletar_quadra(quadra_id):
    conn = get_db()
    conn.execute("DELETE FROM quadras WHERE id = ?", (quadra_id,))
    conn.commit()
    conn.close()


# --- UI ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    st.image(str(BASE_DIR / "logo.png"), width=300)
    st.caption("Encontre e cadastre quadras esportivas em Recife")

st.divider()

# --- Sidebar: cadastro ---
st.sidebar.header("📋 Cadastrar nova quadra")

with st.sidebar.form("form_quadra"):
    nome = st.text_input("Nome da quadra")
    endereco = st.text_input(
        "Endereço", placeholder="Ex: Rua da Aurora, 500, Boa Vista"
    )
    esporte = st.selectbox(
        "Esporte", ["futebol", "vôlei", "basquete", "tênis", "futsal", "outro"]
    )
    submitted = st.form_submit_button("Cadastrar", use_container_width=True)

    if submitted:
        if not nome or not endereco:
            st.error("Preencha nome e endereço.")
        else:
            com_geo = criar_quadra(nome, endereco, esporte)
            if com_geo:
                st.success(f"Quadra '{nome}' cadastrada!")
            else:
                st.warning(f"Quadra '{nome}' cadastrada, mas sem localização no mapa.")

# --- Filtro + Mapa ---
col_filtro, col_mapa = st.columns([1, 3])

with col_filtro:
    st.subheader("🔍 Filtros")
    filtro_esporte = st.selectbox(
        "Esporte",
        ["todos", "futebol", "vôlei", "basquete", "tênis", "futsal", "outro"],
    )

quadras = listar_quadras(filtro_esporte)

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

# --- Lista ---
st.divider()

if quadras:
    st.subheader(f"📋 {len(quadras)} quadra(s) encontrada(s)")
    cols = st.columns(3)
    for i, q in enumerate(quadras):
        with cols[i % 3]:
            geo = "📍" if q.get("latitude") else "⚠️ sem localização"
            st.markdown(
                f"""
                **{q["nome"]}**  
                🏅 {q["esporte"]}  
                {geo} {q["endereco"]}
                """
            )
else:
    st.info("Nenhuma quadra cadastrada ainda. Use o formulário na sidebar.")
