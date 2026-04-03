# ⚽ Joga y Joga

Plataforma para descoberta e cadastro de quadras esportivas na região metropolitana de Recife.

## Stack

- **Backend:** Flask + SQLAlchemy + SQLite
- **Frontend:** Streamlit + Folium (OpenStreetMap)
- **Geocoding:** Nominatim

## Como rodar

**1. Instalar dependências:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt -r frontend/requirements.txt
```

**2. Subir o backend (terminal 1):**
```bash
cd backend && python app.py
```

**3. Subir o frontend (terminal 2):**
```bash
cd frontend && streamlit run app.py
```

Acesse `http://localhost:8501` no browser.

## Grupo 4 — CESAR School
