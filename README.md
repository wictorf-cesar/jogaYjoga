# ⚽ Joga y Joga

Plataforma para descoberta, cadastro e reserva de quadras esportivas na região metropolitana de Recife.

> **Live:** [jogayjoga.streamlit.app](https://jogayjoga.streamlit.app) · **API:** [jogayjoga.onrender.com](https://jogayjoga.onrender.com/health)

## Arquitetura

```
Streamlit Cloud (frontend) → HTTP requests → Flask API (Render) → PostgreSQL (Render)
```

| Camada | Tecnologia | Hospedagem |
|--------|-----------|------------|
| Frontend | Streamlit + Folium + Plotly | Streamlit Cloud |
| Backend | Flask + SQLAlchemy | Render (free tier) |
| Banco de dados | PostgreSQL | Render (free tier) |
| Geocoding | Nominatim | API pública (sem key) |

## Funcionalidades

- 🗺️ **Mapa interativo** com 29 quadras reais de Recife/Olinda
- 🔍 **Filtro por esporte** (Futebol Society, Vôlei de Praia, Futevôlei, Beach Tênis, Futsal)
- ➕ **Cadastro de espaços** com geocoding automático e múltiplos esportes
- 👤 **Login e cadastro** de usuários com autenticação
- 📊 **Dashboard do atleta** — KPIs, próximas reservas, histórico de partidas
- 📈 **Dashboard do administrador** — lucro, aluguéis por espaço e por dia da semana
- 📅 **Sistema de reservas** com detecção de conflito de horário
- ⭐ **Avaliações** de espaços

## Banco de dados

8 tabelas baseadas no DER do projeto:

`usuarios` · `proprietarios` · `enderecos` · `espacos` · `esportes` · `espaco_esportes` (N:N) · `reservas` · `avaliacoes`

## API — Principais endpoints

| Rota | Método | Descrição |
|------|--------|-----------|
| `/register` | POST | Cadastro de usuário |
| `/login` | POST | Login (email + senha) |
| `/espacos` | GET | Listar espaços (filtro por esporte) |
| `/espacos` | POST | Cadastrar novo espaço |
| `/esportes` | GET | Listar esportes disponíveis |
| `/reservas` | POST | Criar reserva |
| `/usuarios/:id/estatisticas` | GET | KPIs do dashboard atleta |
| `/admin/:id/dashboard` | GET | Métricas do proprietário |
| `/health` | GET | Health check |

## Como rodar localmente

**1. Backend (terminal 1):**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 seed.py   # popula o banco com dados demo
python3 app.py    # roda em localhost:5000
```

**2. Frontend (terminal 2):**
```bash
cd frontend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run Quadras.py   # roda em localhost:8501
```

## Estrutura do projeto

```
├── backend/
│   ├── app.py              # Flask API (endpoints)
│   ├── models.py           # SQLAlchemy models (8 tabelas)
│   ├── database.py         # Conexão (SQLite local / PostgreSQL no Render)
│   ├── seed.py             # Popula banco com CSV + dados demo
│   └── requirements.txt
├── frontend/               # Streamlit (desenvolvimento local)
│   ├── Quadras.py          # Página principal (mapa + cadastro)
│   └── pages/
│       └── 1_Perfil.py     # Login + dashboards (atleta/admin)
├── deploy/                 # Streamlit Cloud (produção)
│   ├── Quadras.py
│   └── pages/
│       └── 1_Perfil.py
├── Quadras.csv             # 29 quadras reais de Recife/Olinda
└── README.md
```

## Grupo 4 — CESAR School

Projeto acadêmico desenvolvido para a disciplina de Projetos (SR1).
