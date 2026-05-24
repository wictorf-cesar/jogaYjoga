# Joga & Joga

Sistema web para busca, reserva e gestao de quadras esportivas.

## Visao Geral

O Joga & Joga conecta usuarios que querem reservar quadras com donos de espacos esportivos. O projeto combina uma API FastAPI, uma interface Streamlit, banco SQLite local, mapas com Folium e um chatbot de reservas integrado a Groq.

O app permite ao usuario buscar quadras por cidade/esporte, consultar horarios, criar reservas, favoritar espacos, acompanhar pagamentos Pix e avaliar reservas concluidas. Donos de quadra podem cadastrar espacos, acompanhar reservas, definir horarios, bloquear periodos e consultar indicadores de faturamento.

## Funcionalidades Principais

- Cadastro e login de usuarios.
- Separacao entre usuario comum e dono de quadra.
- Listagem publica de quadras.
- Filtros por cidade, esporte, cobertura e preco.
- Mapa interativo com marcadores das quadras.
- Cadastro de quadra pelo dono com geocodificacao.
- Relacao entre quadra, endereco, proprietario e esportes.
- Consulta de disponibilidade por data.
- Criacao e cancelamento de reservas.
- Pagamento Pix por link de comprovante.
- Favoritos.
- Avaliacoes apos reserva concluida.
- Dashboard do dono com reservas e faturamento.
- Agenda diaria, horarios de funcionamento e bloqueios.
- Chatbot para interpretar mensagens livres e estruturar intencoes de reserva.

## Stack Utilizada

- Python 3.12
- FastAPI
- Streamlit
- SQLAlchemy
- SQLite
- Pydantic
- Requests
- Groq SDK
- Folium
- streamlit-folium
- Pandas
- Plotly
- Geopy
- uv
- unittest

## Arquitetura

O projeto foi organizado em camadas:

- `backend`: API, rotas, dependencias, dominio, repositorios, servicos, integracoes e utilitarios.
- `frontend`: app Streamlit e estrutura auxiliar para componentes, paginas, servicos, estilos e utilitarios.
- `database`: sessao SQLAlchemy, inicializacao e compatibilidade do banco.
- `models`: entidades SQLAlchemy.
- `schemas`: contratos Pydantic da API.
- `data`: seed, CSV e scripts de geocodificacao.
- `tests`: testes automatizados de regras de chatbot e integracao Groq isolada.

O entrypoint historico continua funcionando:

```bash
uvicorn app.backend.main:app --reload
streamlit run app/frontend/streamlit_app.py
```

Tambem existe um entrypoint compatível com a estrutura profissional:

```bash
uvicorn backend.app.main:app --reload
```

## Estrutura de Pastas

```text
jogayjoga/
  app/
    backend/
      api/
        deps.py
      core/
        config.py
        exceptions.py
        logging.py
      domain/
        chat/
        favorites/
        payments/
        reservations/
        users/
        venues/
      integrations/
        groq.py
      repositories/
        reservations.py
        users.py
        venues.py
      routes/
        chat.py
      services/
        groq_service.py
      utils/
        logger.py
      main.py
      security.py
    chatbot/
      engine.py
    core/
      config.py
    data/
      Quadras.csv
      geocode_quadras.py
      seed.py
    database/
      handler.py
      session.py
    frontend/
      assets/
        logo.png
      src/
        components/
        hooks/
        pages/
        services/
        styles/
        types/
        utils/
      streamlit_app.py
    models/
      entities.py
    schemas/
      api.py
  backend/
    app/
      main.py
  db/
    jogayjoga.db
  logs/
  tests/
  .env.example
  context.md
  pyproject.toml
  uv.lock
```

## Backend

O backend principal esta em `app/backend/main.py`. Ele expoe a API FastAPI, registra middleware, inicializa o banco e mantem os endpoints existentes.

Camadas auxiliares:

- `app/backend/core`: configuracao, logging e tratamento de erros.
- `app/backend/api`: dependencias compartilhadas.
- `app/backend/repositories`: acesso direto ao banco.
- `app/backend/domain`: regras de negocio por contexto.
- `app/backend/services`: servicos aplicacionais e integracoes mais complexas.
- `app/backend/integrations`: wrappers de integracoes externas.
- `app/backend/routes`: rotas novas isoladas.
- `app/backend/utils`: utilitarios internos.

### Autenticacao

A autenticacao usa token bearer proprio assinado com HMAC-SHA256:

- `create_access_token(user_id)`
- `decode_access_token(token)`
- `hash_password(password)`
- `verify_password(password, password_hash)`

Configuracoes:

- `JOGAYJOGA_SECRET_KEY`
- `JOGAYJOGA_TOKEN_TTL_HOURS`

## Frontend

O frontend e um app Streamlit em `app/frontend/streamlit_app.py`.

Ele contem:

- Tela de login/cadastro.
- Navegacao de usuario.
- Navegacao de dono.
- Mapas e filtros.
- Formularios de reserva.
- Paginas de reservas, favoritos, agenda, horarios e bloqueios.
- Chatbot.

A pasta `app/frontend/src` concentra a organizacao nova para evoluir o frontend:

- `components`: componentes reutilizaveis.
- `pages`: telas.
- `hooks`: helpers de estado.
- `services`: cliente de API.
- `utils`: formatadores e normalizadores.
- `types`: contratos/aliases.
- `styles`: estilos e constantes visuais.

## Fluxo Principal da Aplicacao

1. Usuario abre o Streamlit.
2. Faz login ou cadastro.
3. O frontend salva `access_token` em `st.session_state`.
4. Chamadas autenticadas usam header `Authorization: Bearer <token>`.
5. Usuario comum acessa mapa, reserva, favoritos, assistente e minhas reservas.
6. Dono de quadra acessa dashboard, minhas quadras, reservas, agenda, horarios, bloqueios e cadastro de quadra.
7. Backend valida permissao por dependencia FastAPI.
8. SQLAlchemy persiste dados no SQLite.

## Fluxo do Chatbot e Reservas

O chatbot usa dois niveis:

1. Parser Groq em `app/backend/services/groq_service.py`.
2. Motor conversacional em `app/chatbot/engine.py`.

O parser transforma texto livre em JSON:

```json
{
  "intent": "CREATE_RESERVATION",
  "sport": "futebol",
  "city": "Recife",
  "date_relative": "amanha",
  "in_scope": true
}
```

Intents suportadas:

- `CREATE_RESERVATION`
- `ASK_AVAILABLE_VENUES`
- `SELECT_VENUE`
- `ASK_AVAILABLE_TIMES`
- `SELECT_TIME`
- `CONFIRM_RESERVATION`
- `CANCEL_RESERVATION`
- `OUT_OF_SCOPE`
- `CHANGE_RESERVATION_CONTEXT`

Estados conversacionais:

- `IDLE`
- `WAITING_CITY`
- `WAITING_VENUE_SELECTION`
- `WAITING_DATE`
- `WAITING_TIME_SELECTION`
- `WAITING_CONFIRMATION`

Regras importantes:

- O bot nunca escolhe quadra automaticamente.
- Perguntas como "horarios?" nao sao tratadas como escolha de quadra.
- Mudanca de esporte, cidade ou data limpa quadra/horario selecionados.
- Reserva so pode ser confirmada com quadra e horario explicitamente escolhidos.
- Fora de escopo retorna mensagem controlada.

## Regras de Negocio

- Dono de quadra nao pode criar reserva como jogador.
- Reserva nao pode ser criada em data passada.
- Hora final deve ser maior que hora inicial.
- Disponibilidade respeita horarios cadastrados, bloqueios e capacidade da quadra.
- Se nao houver horario cadastrado, o padrao e 06:00 a 23:00.
- Slots tem duracao de 1 hora e avancam de 30 em 30 minutos.
- Reservas canceladas nao contam como ocupacao.
- Avaliacao so fica disponivel para reserva concluida.
- Quadra precisa ter pelo menos um esporte.
- Cidade/bairro sao normalizados ao cadastrar endereco.
- Filtros de cidade sao case-insensitive.

## Variaveis de Ambiente

Arquivo exemplo: `.env.example`.

Crie um arquivo local chamado `.env` na raiz do projeto. Esse arquivo guarda segredos da sua maquina e nao deve ser versionado no Git.

```env
GROQ_API_KEY=coloque_sua_chave_groq_aqui
JOGAYJOGA_AI_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT_SECONDS=12
GROQ_BASE_URL=https://api.groq.com
JOGAYJOGA_API_URL=http://127.0.0.1:8001
JOGAYJOGA_SECRET_KEY=troque-em-producao
JOGAYJOGA_TOKEN_TTL_HOURS=24
```

### Configurando a Groq

Links oficiais:

- Console da Groq: https://console.groq.com/
- Quickstart da Groq: https://console.groq.com/docs/quickstart
- Documentacao de modelos: https://console.groq.com/docs/models
- Modelo usado neste projeto: https://console.groq.com/docs/model/llama-3.3-70b-versatile

Passo a passo:

1. Acesse o Console da Groq.
2. Crie ou entre na sua conta.
3. Abra a area de API keys.
4. Gere uma nova chave.
5. Copie a chave e coloque somente no `.env` local:

```env
GROQ_API_KEY=sua_chave_groq_aqui
```

O modelo base configurado no projeto e:

```env
JOGAYJOGA_AI_MODEL=llama-3.3-70b-versatile
```

A URL base usada pelo SDK da Groq e:

```env
GROQ_BASE_URL=https://api.groq.com
```

### Onde a API key entra no codigo

Nao coloque a API key diretamente em arquivos `.py`.

O codigo que le a chave fica em `app/backend/services/groq_service.py`, na funcao `get_groq_api_key()`:

```python
def get_groq_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY")
```

Se o dev precisar mudar como a integracao com Groq funciona, o lugar correto e `app/backend/services/groq_service.py`. Se precisar trocar a chave, o lugar correto e o arquivo `.env`, nao o codigo.

## Como Instalar

1. Instale Python 3.12.
2. Instale `uv`.
3. Sincronize as dependencias:

```bash
uv sync
```

## Como Rodar Localmente

Use dois terminais: um para backend e outro para frontend.

Ou use o script unico:

```bash
python run.py
```

Ele inicia o backend em `http://127.0.0.1:8001` e o frontend em `http://127.0.0.1:8501`.
Se alguma porta estiver indisponivel no Windows, o script escolhe uma porta livre e mostra a URL correta no terminal.

## Como Rodar Backend

Porta recomendada atual:

```bash
uvicorn app.backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Alternativa com entrypoint compatível:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```

Healthcheck:

```bash
curl http://127.0.0.1:8001/health
```

Healthcheck Groq:

```bash
curl http://127.0.0.1:8001/health/groq
```

## Como Rodar Frontend

```bash
$env:JOGAYJOGA_API_URL="http://127.0.0.1:8001"
streamlit run app/frontend/streamlit_app.py
```

URL:

```text
http://127.0.0.1:8501
```

## Como Rodar Testes

```bash
python -m unittest discover -s tests
```

Checagem de sintaxe:

```bash
python -m compileall app tests
```

## Banco e Seed

O banco local fica em:

```text
db/jogayjoga.db
```

Para recriar tabelas e importar quadras do CSV:

```bash
python -m app.data.seed
```

O backend tambem cria tabelas no startup e roda seed se nao houver espacos.

## Endpoints Principais

Saude:

- `GET /health`
- `GET /health/groq`
- `GET /chat/health/groq`

Autenticacao:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Quadras:

- `GET /espacos`
- `GET /espacos/{espaco_id}`
- `GET /espacos/{espaco_id}/disponibilidade?data=YYYY-MM-DD`

Reservas:

- `POST /reservas`
- `GET /me/reservas`
- `PATCH /me/reservas/{reserva_id}/cancelar`

Pagamentos:

- `PATCH /me/reservas/{reserva_id}/pagamento`

Favoritos:

- `GET /me/favoritos`
- `POST /me/favoritos/{espaco_id}`
- `DELETE /me/favoritos/{espaco_id}`

Dono:

- `GET /owner/dashboard`
- `GET /owner/espacos`
- `POST /owner/espacos`
- `GET /owner/reservas`
- `PATCH /owner/reservas/{reserva_id}/status`
- `GET /owner/horarios`
- `POST /owner/espacos/{espaco_id}/horarios`
- `GET /owner/bloqueios`
- `POST /owner/bloqueios`

Chat:

- `POST /ai/parse`
- `POST /chat/parse`

## Exemplos de Uso

Login:

```bash
curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"usuario@email.com\",\"senha\":\"123456\"}"
```

Listar quadras:

```bash
curl http://127.0.0.1:8001/espacos
```

Consultar disponibilidade:

```bash
curl "http://127.0.0.1:8001/espacos/34/disponibilidade?data=2026-05-24"
```

Testar Groq:

```bash
curl http://127.0.0.1:8001/health/groq
```

## Logs e Debug

Logs do backend e frontend podem ser redirecionados para `logs/`.

O chatbot possui logs estruturados com tags:

- `[ENV]`
- `[CHAT]`
- `[VALIDATOR]`
- `[INTENT]`
- `[STATE BEFORE]`
- `[STATE AFTER]`
- `[ACTION]`
- `[GROQ REQUEST]`
- `[GROQ RESPONSE]`
- `[GROQ PARSED]`
- `[GROQ ERROR]`
- `[HTTP]`

Exemplo:

```text
2026-05-23 10:34:27.020 INFO [GROQ REQUEST] Request iniciado {"model":"llama-3.3-70b-versatile"}
2026-05-23 10:34:28.616 INFO [GROQ RESPONSE] Resposta recebida {"latency_ms":1597.24}
2026-05-23 10:34:28.616 INFO [GROQ PARSED] JSON parseado {"parsed":{"intent":"CREATE_RESERVATION"}}
```

## Tratamento de Erros

- Erros de autenticacao retornam 401.
- Acesso de usuario errado retorna 403.
- Recursos inexistentes retornam 404.
- Conflitos de reserva retornam 409.
- Falhas Groq sao logadas e podem cair para parser local por regras.
- `GroqServiceError` padroniza erros da integracao.
- `AppError` existe para erros controlados novos.

## Boas Praticas Adotadas

- Camadas de dominio, repositorio e servico.
- Entry points mantidos para compatibilidade.
- Logs estruturados com timestamps.
- Testes automatizados para regras do chatbot.
- Normalizacao de cidade e esporte.
- Chave Groq carregada apenas por variavel de ambiente.
- Separacao gradual do frontend em `src`.
- README como guia operacional do projeto.

## Troubleshooting

### Groq nao aparece no dashboard

Verifique:

- `/health/groq`
- logs `[ENV]`
- logs `[GROQ REQUEST]`
- se a chave foi carregada
- se o modelo e `llama-3.3-70b-versatile`

### Quadra cadastrada nao aparece para usuario

Verifique:

- se existe em `espacos`
- se tem `id_endereco`
- se tem relacao em `espaco_esportes`
- se a cidade esta normalizada
- se o frontend esta apontando para a API correta
- se o cache `get_espacos` foi limpo

### Frontend nao conecta

Confirme:

```bash
$env:JOGAYJOGA_API_URL="http://127.0.0.1:8001"
```

### Porta ocupada

Use outra porta ou finalize o processo que esta usando a porta.

## Roadmap

- Migrar rotas restantes de `app/backend/main.py` para `app/backend/routes`.
- Migrar regras de reserva para `domain/reservations`.
- Migrar regras de quadras para `domain/venues`.
- Quebrar `streamlit_app.py` em paginas menores.
- Adicionar migrations com Alembic.
- Trocar SQLite por PostgreSQL em ambiente real.
- Adicionar testes de API com `httpx`.
- Criar pipeline de CI.

## Checklist Antes de Produção

- Definir `GROQ_API_KEY` somente por variavel de ambiente.
- Definir `JOGAYJOGA_SECRET_KEY` forte.
- Usar banco gerenciado ou PostgreSQL.
- Configurar migrations.
- Restringir CORS.
- Configurar HTTPS.
- Adicionar rate limit.
- Revisar logs para nao expor dados sensiveis.
- Configurar monitoramento.
- Rodar testes automatizados.
- Validar backup do banco.
- Criar usuarios e dados iniciais controlados.
