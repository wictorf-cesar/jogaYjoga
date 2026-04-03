# Joga y Joga — Contexto do Projeto

> Referência rápida para início de sessão com o agente.

## O que é

Plataforma web para descoberta e cadastro de quadras esportivas na região metropolitana de Recife. Projeto acadêmico (SR1) com entrega em formato pitch.

## Equipe e responsabilidades

- **Wictor + Guilherme**: Arquitetura e Backend (API REST, models, rotas) — deadline domingo 05/04
- **Douglas W. + Davi Paiva**: Entendimento de dados, amostra inicial de quadras — até sexta 03/04
- **Jonathan + Alexandre**: Frontend e integração, telas — até sexta 03/04
- **Talita**: Drive, cronograma, site

## Stack definida

- **API**: Flask (Python)
- **BD**: SQLite + SQLAlchemy
- **Frontend/Demo**: Streamlit
- **Mapa**: Folium + streamlit-folium (OpenStreetMap)
- **Geocoding**: Nominatim (grátis, sem API key)

## Funcionalidades do MVP

1. Cadastro de quadras (nome, endereço, esporte) — geocoding automático
2. Visualização das quadras no mapa
3. Filtro por esporte

## Fora do MVP

- Cadastro/autenticação de usuários
- Reserva/agendamento
- Chatbot
- Pagamento
- Dashboard de donos

## Arquitetura

```
Streamlit (frontend) → requests HTTP → Flask API (backend) → SQLite
                                              ↓
                                      Nominatim (geocoding)
```

## Endpoints

- `POST /quadras` — cadastra quadra
- `GET /quadras` — lista todas
- `GET /quadras?esporte=X` — filtra por esporte

## Arquivos importantes

- `DECISOES_ARQUITETURA.md` — registro detalhado de todas as decisões técnicas e justificativas
- `jogaYjoga contexto.docx` — contexto de negócio original
- `requisitos do projeto/` — prints dos requisitos da SR1
- `rascunho da ideia do app/` — prints do brainstorm

## Entregáveis da SR1

1. Repositório GitHub/GitLab
2. Documentação (PPT/PDF) com roteiro e metodologias
3. Cronograma atualizado
4. Google Sites
