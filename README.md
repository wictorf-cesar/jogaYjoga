# Joga & Joga

Sistema web para busca, reserva e gestao de quadras esportivas na regiao metropolitana do Recife.

Conecta usuarios que querem reservar quadras com donos de espacos esportivos. O usuario busca quadras por cidade/esporte, consulta horarios, cria reservas, favorita espacos, acompanha pagamentos Pix e avalia reservas concluidas. Donos de quadra cadastram espacos, acompanham reservas, definem horarios, bloqueiam periodos e consultam faturamento.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite (local) / PostgreSQL (prod via `DATABASE_URL`)
- **Frontend:** Streamlit + Folium (mapas) + Plotly (dashboard)
- **IA:** Groq (LLM) + sentence-transformers `all-MiniLM-L6-v2` (embeddings) para o chatbot RAG
- **Auth:** token bearer proprio assinado com HMAC-SHA256

## Arquitetura

```
app/
  backend/        API FastAPI, rotas, dominio, repositorios, servicos, integracoes
    routes/       rotas isoladas (chat, rag_chat)
    services/     groq_service, embedding_service, rag_service
    domain/       regras de negocio por contexto (reservations, venues, users, ...)
    repositories/ acesso direto ao banco
  chatbot/        motor conversacional legado (intent classifier)
  frontend/       app Streamlit + estrutura src/ (components, pages, services, ...)
  models/         entidades SQLAlchemy
  schemas/        contratos Pydantic da API
  database/       sessao SQLAlchemy, init
  data/           seed, CSV de quadras, geocodificacao
backend/app/      entrypoint compativel (alias para app.backend.main)
```

Entrypoints:

```bash
uvicorn app.backend.main:app --reload          # principal
uvicorn backend.app.main:app --reload          # alias compativel
streamlit run app/frontend/streamlit_app.py    # frontend
```

## Variaveis de Ambiente

Copie `.env.example` para `.env` (nao versionado). Em producao, sete no painel do PaaS.

| Variavel | Obrig. | Default | Uso |
|---|---|---|---|
| `GROQ_API_KEY` | sim | — | Chave da Groq (console.groq.com). Sem ela o chatbot responde fallback. |
| `JOGAYJOGA_AI_MODEL` | nao | `llama-3.3-70b-versatile` | Modelo Groq usado no RAG |
| `GROQ_BASE_URL` | nao | `https://api.groq.com` | Base URL do SDK Groq |
| `GROQ_TIMEOUT_SECONDS` | nao | `12` | Timeout das chamadas Groq |
| `JOGAYJOGA_API_URL` | nao | `https://jogayjoga.onrender.com` | URL da API (usada pelo frontend Streamlit) |
| `JOGAYJOGA_SECRET_KEY` | sim (prod) | `dev-secret-change-me` | Chave HMAC do token de auth |
| `JOGAYJOGA_TOKEN_TTL_HOURS` | nao | `24` | Validade do token |
| `DATABASE_URL` | nao | SQLite local | Em prod, URL do Postgres (Render ja fornece) |
| `SENTENCE_TRANSFORMERS_HOME` | nao | `./.cache/sentence-transformers` | Cache do modelo de embeddings (persistir em PaaS) |
| `HF_HOME` | nao | default do HF | Cache do HuggingFace |

> Nao coloque a chave Groq no codigo. Ela e lida em `app/backend/services/groq_service.py:get_groq_api_key()` via `os.getenv`.

## Como Rodar Localmente

```bash
# 1. Instalar dependencias
uv sync                         # dev local (pyproject.toml, pega wheel nativa do SO)

# 2. Backend + frontend juntos
python run.py                   # backend em :8001, frontend em :8501

# OU separado:
uvicorn app.backend.main:app --host 127.0.0.1 --port 8001 --reload
streamlit run app/frontend/streamlit_app.py
```

Healthcheck:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/health/groq
```

O backend cria as tabelas e roda o seed no startup se nao houver quadras. Para recriar tudo a partir do CSV:

```bash
python -m app.data.seed
```

## Testes

```bash
python -m unittest discover -s tests
python -m compileall app tests    # checagem de sintaxe
```

## Endpoints

**Saude:** `GET /health`, `GET /health/groq`

**Auth:** `POST /auth/register`, `POST /auth/login`, `GET /auth/me`

**Quadras:** `GET /espacos`, `GET /espacos/{id}`, `GET /espacos/{id}/disponibilidade?data=YYYY-MM-DD`

**Reservas:** `POST /reservas`, `GET /me/reservas`, `PATCH /me/reservas/{id}/cancelar`

**Pagamentos:** `PATCH /me/reservas/{id}/pagamento`

**Favoritos:** `GET /me/favoritos`, `POST /me/favoritos/{espaco_id}`, `DELETE /me/favoritos/{espaco_id}`

**Dono:** `GET /owner/dashboard`, `GET|POST /owner/espacos`, `GET /owner/reservas`, `PATCH /owner/reservas/{id}/status`, `GET|POST /owner/horarios`, `GET|POST /owner/bloqueios`

**Chatbot (RAG):**
- `POST /ai/chat` — pergunta livre em linguagem natural; retorna resposta gerada pelo LLM com base nas quadras recuperadas por similaridade semantica
- `GET /ai/rag/health` — readiness do indice de embeddings (`{"ready": bool, "courts_indexed": N}`)

**Chatbot legado (intent classifier):** `POST /ai/parse`, `POST /chat/parse` — ainda disponiveis, usados pelo motor conversacional em `app/chatbot/engine.py`.

### Exemplo

```bash
# Listar quadras
curl http://127.0.0.1:8001/espacos

# Pergunta ao RAG
curl -X POST http://127.0.0.1:8001/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "qual a quadra mais barata para futebol em Recife?"}'
```

## Como o Chatbot Funciona (RAG)

Fluxo da mensagem do usuario ate a resposta:

```
pergunta → embedding (all-MiniLM-L6-v2) → busca semantica nas quadras
        → top-k quadras mais relevantes → contexto + system prompt → Groq LLM → resposta natural
```

- Os embeddings de todas as quadras sao gerados no startup (em background, sem bloquear o bind da porta) e mantidos em memoria.
- O system prompt forca respostas em pt-BR, escopo so sobre quadras, e usar apenas o contexto recuperado (nao inventa dados).
- Se o indice ainda nao esta pronto, `POST /ai/chat` responde `"loading"` ate ficar disponivel.
- Comparativos ("mais barata", "melhor avaliada") sao respondidos factualmente a partir do contexto.

## Regras de Negocio

- Dono de quadra nao pode criar reserva como jogador.
- Reserva nao pode ser em data passada; hora final > hora inicial.
- Disponibilidade respeita horarios cadastrados, bloqueios e capacidade.
- Sem horario cadastrado, o padrao e 06:00–23:00. Slots de 1h, avancando de 30 em 30 min.
- Reservas canceladas nao contam como ocupacao.
- Avaliacao so fica disponivel para reserva concluida.
- Quadra precisa ter pelo menos um esporte.
- Cidade/bairro normalizados ao cadastrar; filtros de cidade sao case-insensitive.

## Logs e Debug

Logs estruturados com tags: `[ENV]`, `[CHAT]`, `[GROQ REQUEST/RESPONSE/PARSED/ERROR]`, `[HTTP]`. Redirecione para `logs/` se necessario.

## Troubleshooting

- **Chatbot responde "loading" / `rag/health` retorna `ready: false`**: indice de embeddings ainda carregando. Aguarde ~30–60s apos o startup. Se persistir, cheque os logs por `Erro ao gerar embeddings RAG` ou `sentence-transformers nao instalado`.
- **Groq nao aparece no dashboard**: verifique `/health/groq` e os logs `[ENV]` (chave carregada? modelo correto?).
- **Quadra cadastrada nao aparece**: confira `id_endereco`, relacao em `espaco_esportes`, normalizacao da cidade, e se o frontend aponta para a API correta (`JOGAYJOGA_API_URL`).
- **Frontend nao conecta**: confirme `JOGAYJOGA_API_URL` apontando para a URL da API.
- **Deploy no Render falha com "no open ports"**: o startup travou. Os embeddings rodam em background thread exatamente pra evitar isso; se voltar a acontecer, cheque se `_build_rag_embeddings` ainda esta em thread.

## Roadmap

- Migrar rotas restantes de `app/backend/main.py` para `app/backend/routes`.
- Migrar regras de reserva/quadras para `domain/`.
- Quebrar `streamlit_app.py` em paginas menores.
- Adicionar migrations com Alembic.
- Adicionar testes de API com `httpx`.

## Checklist Antes de Producao

- `GROQ_API_KEY` definida por variavel de ambiente.
- `JOGAYJOGA_SECRET_KEY` forte.
- Banco gerenciado/PostgreSQL + migrations.
- CORS restrito (hoje esta `*`).
- HTTPS, rate limit, monitoramento.
- Backup do banco.
