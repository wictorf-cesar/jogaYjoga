# SR2 — Relatório de Processo

Documento de entrega do Status Report 2, cobrindo os três tópicos técnicos
apresentados: **Modelagem** (T1), **Avaliação** (T2) e **Deployment** (T3).
Cada afirmação abaixo corresponde ao que está efetivamente implementado no
repositório e em produção em `https://jogayjoga.onrender.com`.

---

## T1 — Modelagem

### Arquitetura geral

O Joga & Joga é organizado em três camadas isoladas, com responsabilidades
claras e pastas separadas:

- **Backend** — API em FastAPI (`app/backend/`).
- **Frontend** — aplicação Streamlit (`app/frontend/`).
- **Inteligência Artificial** — chatbot RAG (`app/backend/services/rag_service.py`).

A separação interna do backend inclui `repositories/` (acesso ao banco),
`domain/` (regras de negócio por contexto) e `routes/` (rotas isoladas), o que
favorece manutenção e evolução.

### Stack e justificativas

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy | APIs assíncronas com validação automática (Pydantic); ORM que suporta SQLite (local) e PostgreSQL (prod) |
| Frontend | Streamlit + Folium | Mapa de quadras com *MarkerCluster*; dashboards do dono com `st.metric` e `st.bar_chart` |
| Auth | Token bearer próprio + HMAC-SHA256 | Sem dependência de JWT; senhas com `pbkdf2_hmac`; assinatura comparada com `hmac.compare_digest` (evita *timing attack*) |
| IA | RAG (Groq + fastembed/ONNX) | Geração aumentada por recuperação; embeddings locais leves + LLM na nuvem |

> **Plotly** está declarado nas dependências, porém os dashboards atuais usam
> componentes nativos do Streamlit (`st.bar_chart`). A Plotly permanece
> disponível para visualizações futuras.

### Regras de negócio

Implementadas e verificáveis no código:

- Dono de quadra **não pode reservar** como jogador (`403` em `get_current_player`).
- Reserva precisa estar **dentro do horário de funcionamento** do dia
  (`ensure_reservation_inside_business_hours`).
- Reserva **não sobrepõe bloqueio** do dono (`ensure_reservation_not_blocked` → `409`).
- **Capacidade respeitada**: conta reservas sobrepostas vs. `qtd_quadras` (`409`).
- **Avaliação só após reserva concluída** (`status_reserva == "concluido"` → `409`).

### Inteligência Artificial — RAG

O chatbot usa **RAG** (Retrieval-Augmented Generation), não LLM puro. Dois
modelos com papéis distintos:

- **`all-MiniLM-L6-v2`** (embeddings) — converte texto em vetor de 384
  dimensões; roda **local** via **fastembed/ONNX**.
- **`llama-3.3-70b-versatile`** (LLM) — lê o contexto e redige a resposta em
  pt-BR; roda na **Groq** via API.

Fluxo em 3 passos:

1. **Retrieve** — a pergunta é embutida e comparada por **similaridade de
   cosseno** contra o índice de quadras; retorna as top-5 mais relevantes
   (`TOP_K = 5`, `MIN_SIMILARITY = 0.15`).
2. **Augment** — as quadras recuperadas viram um bloco de contexto injetado num
   *system prompt* rígido ("use **apenas** o contexto, não invente dados").
3. **Generate** — o Llama 3.3 70B (via Groq) redige a resposta em pt-BR, com
   `temperature=0.3` para priorizar factualidade.

**Decisão de engenharia:** os embeddings rodam em **fastembed/ONNX**, não em
`sentence-transformers`/torch. Mesmo modelo base, mas footprint de ~150 MB em
vez de ~500 MB — o que cabe no *free tier* do Render (512 MB) sem *out-of-memory*.

### Resultados observados

Chamada real ao `POST /ai/chat` (pergunta: *"onde posso jogar volei em recife
amanha?"*):

```json
{
  "reply": "Olá! 🏐 Encontrei algumas opções de quadras para jogar volei em Recife ...",
  "provider": "rag",
  "courts_used": 5,
  "model": "llama-3.3-70b-versatile",
  "latency_ms": 1763.82
}
```

O campo `"provider": "rag"` confirma a execução do fluxo de recuperação +
geração. A resposta cita **fatos do catálogo** (nomes, bairros, preços) que só
existem no banco, comprovando o *grounding*.

---

## T2 — Avaliação

### KPIs e evidências

| KPI | Tipo | Evidência atual |
|---|---|---|
| **Tempo de resposta do sistema** | Técnico | `/ai/chat` mede e retorna `latency_ms` por chamada (~1,2–1,8 s em prod). Rotas `/health` e `/health/groq` para disponibilidade |
| **Prontidão do RAG** | Técnico | `GET /ai/rag/health` → `{"ready": true, "courts_indexed": 33}`. Enquanto carrega, `/ai/chat` degrada para `provider: "loading"` |
| **Taxa de conflito de reservas** | Negócio | Regra existe (overlap + capacidade via `qtd_quadras` → `409`), mas a métrica ainda não é computada/agregada |
| **Taxa de conversão do uso da IA** | Negócio | O `/ai/chat` expõe `courts_used` e `latency_ms`, mas não há rastreamento ponta-a-ponta chat→reserva |
| **Cobertura de testes** | Técnico | 2 suítes `unittest` (`tests/`); o CI executa apenas `ruff` — não roda `pytest` nem mede cobertura |

### Resiliência e tratamento de erros

- `/ai/chat` **nunca devolve 500**: fallback gracioso para chave ausente,
  índice carregando, *rate limit*, *timeout*, erro de autenticação e outros
  (classificação por `type(exc).__name__`).
- Carregamento dos embeddings em **thread daemon** no startup — não bloqueia o
  *bind* da porta dentro da janela de health-check do Render.
- `init_db` com **retry** para tolerar o *cold start* do PostgreSQL no *free
  tier* do Render.

### Limitações identificadas (análise crítica)

- As regras de reserva (`ensure_reservation_*`, `calculate_reservation_value`)
  ainda vivem em `app/backend/main.py`; a camada `domain/reservations/` está
  apenas esboçada.
- Sem **Alembic** — migração de schema feita manualmente via
  `ensure_sqlite_columns` (válido apenas para SQLite).
- `app/frontend/streamlit_app.py` com ~2.484 linhas — precisa ser quebrado em
  páginas menores.
- O índice em produção reporta `courts_indexed: 33` (o seed tem 34 quadras) —
  uma quadra não foi indexada (em investigação).
- O RAG recupera por similaridade semântica; **não filtra por disponibilidade
  real** de horário. O "amanhã" na resposta do LLM é eco conversacional, não
  checagem de agenda.

### Plano de melhorias futuras

- Implementar **Alembic** para migrações automatizadas.
- Quebrar `streamlit_app.py` em páginas com `st.navigation`/`pages/`.
- Adicionar **testes de API com `httpx`** (TestClient do FastAPI) e incluir
  `pytest` + `coverage` no CI.
- Migrar as regras de reservas/quadras do `main.py` para a camada de domínio.
- Computar efetivamente os KPIs de "taxa de conflito" e "conversão da IA"
  (logs estruturados / tabela de eventos).
- Investigar a quadra não indexada.

---

## T3 — Deployment

### Ambientes em produção

| Componente | Plataforma | URL |
|---|---|---|
| Backend / API | Render (web service) | `https://jogayjoga.onrender.com` |
| Frontend | Streamlit Community Cloud | `https://jogayjoga.streamlit.app/` |
| Banco (prod) | PostgreSQL (fornecido pelo Render via `DATABASE_URL`) | — |
| Banco (local) | SQLite (arquivo local) | — |
| Código | GitHub | `wictorf-cesar/jogaYjoga` |
| CI | GitHub Actions + Ruff | lint/format automático a cada PR |

- Start do backend: `uvicorn app.backend.main:app --host 0.0.0.0 --port $PORT`.
- O frontend lê `requirements.txt` (não `pyproject.toml`).

### Segurança em produção

- Variáveis de ambiente protegem dados sensíveis:
  - `GROQ_API_KEY` — chave do LLM.
  - `JOGAYJOGA_SECRET_KEY` — chave de assinatura dos tokens.
- Defaults inseguros (`dev-secret-change-me`) existem apenas para
  desenvolvimento local.

### Evidências de operação (verificáveis ao vivo)

| Verificação | Endpoint | Resultado observado |
|---|---|---|
| Backend no ar | `GET /health` | `{"status":"ok"}` (HTTP 200) |
| RAG pronto | `GET /ai/rag/health` | `{"ready":true,"courts_indexed":33}` |
| Chatbot RAG | `POST /ai/chat` | `provider:"rag"`, `courts_used:5`, `latency_ms` ~1,2–1,8 s |
| Catálogo de quadras | `GET /espacos` | Lista de quadras reais (Recife, Olinda, Jaboatão, Paulista, Abreu e Lima) |
| Frontend navegável | `https://jogayjoga.streamlit.app/` | Aplicação Streamlit |

### Lições operacionais já resolvidas

| Problema | Causa | Solução |
|---|---|---|
| OOM a cada 2–5 min no Render | `torch` + MiniLM > 512 MB | Troca por **fastembed/ONNX** (~150 MB) — PR #21 |
| Deploy "no open ports detected" | Startup síncrono de embeddings travava o *bind* da porta | Embeddings em **thread daemon** no startup — PR #20 |
| `POST /ai/chat` 500 com `groq.AuthenticationError` | `except` só cobria `GroqServiceError`; chave inválida vazava como 500 | `except Exception` final classificando os erros nativos do SDK — PR #19 |

---

## Síntese

O projeto entrega, de ponta a ponta, uma plataforma web com backend em FastAPI,
frontend em Streamlit e um chatbot RAG em produção. A **modelagem** é modular,
com regras de negócio verificáveis no código; a **avaliação** dispõe de métricas
reais para tempo de resposta e prontidão do RAG (e reconhece honestamente os
KPIs ainda não computados); e o **deployment** é operacional e publicamente
demonstrável. As limitações listadas compõem o plano de evolução imediato.
