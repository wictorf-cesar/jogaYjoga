# Joga y Joga — Decisões de Arquitetura

> Registro das decisões técnicas tomadas durante o desenvolvimento do MVP.
> Última atualização: 2026-04-02

---

## 1. Stack escolhida

| Camada | Tecnologia | Justificativa |
|---|---|---|
| API REST | **Flask** | Leve, sem boilerplate excessivo, experiência prévia do time |
| Banco de dados | **SQLite** | Zero configuração, arquivo único, ideal pra demo acadêmica |
| ORM | **SQLAlchemy** | Modela tabelas em Python, facilita evolução do schema |
| Frontend/Demo | **Streamlit** | Prototipagem rápida de UI, grátis, suficiente pra apresentação ao professor |
| Mapa | **Folium + streamlit-folium** | Mapa interativo baseado em OpenStreetMap, sem custo |
| Geocoding | **Nominatim (OpenStreetMap)** | Gratuito, converte endereço → lat/lng sem precisar de API key |

### Alternativas descartadas

- **FastAPI**: tecnicamente superior (async, tipagem, docs automáticas), mas Flask já é conhecido pelo time e suficiente pro escopo.
- **Django**: muito boilerplate (apps, settings, admin, migrations obrigatórias) — overkill pra um MVP acadêmico.
- **Google Maps**: requer billing account e API key paga. Folium/OpenStreetMap entrega o mesmo resultado pra esse escopo, sem custo.
- **PostgreSQL / MySQL**: exigem instalação e configuração de servidor. SQLite é um arquivo `.db` que roda em qualquer máquina.

---

## 2. Arquitetura geral

```
Flask API (backend)  ←→  SQLite (.db)
      ↑
      | HTTP (requests)
      ↓
Streamlit (frontend/demo)  →  Folium (mapa)
```

- **Streamlit consome a API Flask via `requests`**, não acessa o banco diretamente.
- Essa separação foi intencional: o requisito da SR1 pede explicitamente "implementação de API REST".
- Facilita evolução futura (trocar frontend sem mexer no backend).

---

## 3. Decisões sobre funcionalidades do MVP

### Incluído no MVP
- **Cadastro de quadras**: usuário informa nome, endereço e esporte. O backend geocodifica o endereço (Nominatim) e salva lat/lng.
- **Visualização no mapa**: todas as quadras cadastradas aparecem como marcadores no mapa (Folium).
- **Filtro por esporte**: endpoint aceita query param `?esporte=futebol`.

### Fora do MVP (próximas iterações)
- Cadastro/autenticação de usuários — por ora qualquer pessoa pode cadastrar quadras.
- Sistema de reserva/agendamento.
- Chatbot.
- Pagamento (Pix, split).
- Dashboard do dono da quadra.

---

## 4. Modelo de dados (MVP)

### Tabela `quadras`

| Campo | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | Identificador único |
| nome | TEXT NOT NULL | Nome da quadra |
| endereco | TEXT NOT NULL | Endereço informado pelo usuário |
| esporte | TEXT NOT NULL | Esporte praticado (futebol, vôlei, etc.) |
| latitude | REAL | Obtido via geocoding (Nominatim) |
| longitude | REAL | Obtido via geocoding (Nominatim) |
| created_at | DATETIME | Data de cadastro |

---

## 5. Endpoints da API (MVP)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/quadras` | Cadastra nova quadra (geocodifica endereço automaticamente) |
| `GET` | `/quadras` | Lista todas as quadras |
| `GET` | `/quadras?esporte=X` | Lista quadras filtradas por esporte |

---

## 6. Limitações conhecidas

- **Nominatim** tem rate limit de 1 request/segundo — aceitável pro MVP, inviável em produção com muitos usuários simultâneos.
- **SQLite** não suporta escrita concorrente — ok pra demo, precisaria migrar pra PostgreSQL em produção.
- **Sem autenticação** — qualquer pessoa pode cadastrar/ver quadras. Risco aceitável pra um MVP acadêmico.

---

## 7. Estrutura de pastas

```
jogaYjoga/
├── backend/
│   ├── app.py              # Flask app + rotas
│   ├── models.py           # SQLAlchemy models
│   ├── database.py         # Config SQLite + session
│   └── requirements.txt
├── frontend/
│   ├── app.py              # Streamlit app (mapa + formulário)
│   └── requirements.txt
├── DECISOES_ARQUITETURA.md  # Este arquivo
└── README.md
```
