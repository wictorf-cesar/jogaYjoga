# Joga y Joga — Como rodar e como funciona

## Como rodar

Precisa de dois terminais abertos ao mesmo tempo.

**Terminal 1 — Backend (API):**
```bash
cd ~/Documents/study/jogaYjoga
source venv/bin/activate
cd backend && python app.py
```
Isso sobe a API Flask em `http://localhost:5000`.

**Terminal 2 — Frontend (Interface):**
```bash
cd ~/Documents/study/jogaYjoga
source venv/bin/activate
cd frontend && streamlit run app.py
```
Isso abre a interface no browser em `http://localhost:8501`.

---

## Como funciona (fluxo completo)

### Cadastro de quadra

1. O usuário abre o Streamlit no browser e preenche o formulário na sidebar: **nome**, **endereço** e **esporte**.
2. O Streamlit envia esses dados via HTTP POST para a API Flask (`POST /quadras`).
3. A API recebe o endereço e chama o **Nominatim** (serviço gratuito do OpenStreetMap) para converter o endereço em **latitude e longitude**.
4. A API salva tudo no banco de dados **SQLite** — um arquivo chamado `jogayjoga.db` dentro da pasta `backend/`.
5. O Streamlit recarrega a lista de quadras e mostra o novo marcador no mapa.

### Visualização no mapa

1. Ao abrir a página, o Streamlit faz um `GET /quadras` na API.
2. A API consulta o SQLite e retorna todas as quadras com suas coordenadas.
3. O Streamlit usa a biblioteca **Folium** para renderizar um mapa do OpenStreetMap centrado em Recife, com um marcador verde para cada quadra.
4. Ao clicar no marcador, aparece o nome, esporte e endereço da quadra.

### Filtro por esporte

1. O usuário seleciona um esporte no dropdown (ex: "futebol").
2. O Streamlit faz `GET /quadras?esporte=futebol`.
3. A API filtra no banco e retorna só as quadras daquele esporte.
4. O mapa atualiza mostrando apenas os marcadores filtrados.

---

## Onde os dados ficam salvos

| O quê | Onde |
|---|---|
| Banco de dados | `backend/jogayjoga.db` (arquivo SQLite, criado automaticamente ao rodar o backend pela primeira vez) |
| Tabela | `quadras` — campos: id, nome, endereco, esporte, latitude, longitude, created_at |

O SQLite é um banco de dados em arquivo único. Não precisa instalar nada. Se quiser resetar os dados, basta deletar o arquivo `jogayjoga.db` e reiniciar o backend.

---

## Diagrama resumido

```
[ Browser ]
     │
     ▼
[ Streamlit :8501 ]  ──HTTP──▶  [ Flask API :5000 ]  ──▶  [ SQLite jogayjoga.db ]
     │                                │
     ▼                                ▼
[ Folium/Mapa ]               [ Nominatim (geocoding) ]
```
