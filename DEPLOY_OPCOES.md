# Joga y Joga — Opções de Deploy

> Ponderação sobre como colocar o app público na internet para o professor acessar.

---

## Opção 1: Streamlit Community Cloud (recomendada pra demo)

- **Custo**: grátis
- **Como funciona**: conecta o repo GitHub no [share.streamlit.io](https://share.streamlit.io), ele deploya automaticamente e gera uma URL pública
- **Ajuste necessário**: unificar tudo num Streamlit único — o Streamlit acessa o SQLite direto, sem Flask separado
- **Esforço**: ~15 minutos de refactor
- **Prós**: zero config de infra, professor acessa por link, deploy automático a cada push
- **Contras**: perde a separação frontend/backend no deploy (mas mantém no código do repo pra avaliação)

## Opção 2: Flask no Render + Streamlit no Community Cloud

- **Custo**: grátis (free tier)
- **Como funciona**: sobe o Flask no [render.com](https://render.com) (gera URL tipo `https://jogayjoga-api.onrender.com`), o Streamlit aponta pra essa URL
- **Esforço**: ~30 minutos de config
- **Prós**: mantém a arquitetura separada igual ao local
- **Contras**: free tier do Render dorme após 15min sem uso — primeira requisição demora ~30s pra acordar

## Opção 3: Railway.app

- **Mesma ideia do Render**, alternativa caso Render dê problema
- **Free tier** tem limite de horas/mês

---

## Decisão

**Para a apresentação SR1**: ir com Opção 1 (Streamlit Community Cloud unificado). É o mais rápido e confiável pra demo ao vivo.

**No repositório**: manter o código com Flask + Streamlit separados. A arquitetura correta fica documentada e avaliável no código — o deploy simplificado é só pra conveniência da apresentação.

Isso cobre os dois requisitos:
- ✅ Proposta de arquitetura da solução (nota pela separação backend/frontend no repo)
- ✅ Demo funcional acessível por link (Streamlit Cloud)
