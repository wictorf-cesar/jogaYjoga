import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Perfil | Joga y Joga", page_icon="👤", layout="wide")

API_URL = os.environ.get("API_URL", "http://localhost:5000")

CORES_ESPORTE = {
    "Futebol Society": "#FF6B00",
    "Vôlei De Praia": "#ff9a00",
    "Futevôlei": "#ffb347",
    "Beach Tênnis": "#ffd166",
    "Futsal": "#06d6a0",
}


# ── API helpers ──────────────────────────────────────────────────────────────

def api_get(path, params=None):
    try:
        resp = requests.get(f"{API_URL}{path}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def api_post(path, data):
    try:
        resp = requests.post(f"{API_URL}{path}", json=data, timeout=15)
        return resp.json(), resp.status_code
    except Exception:
        return None, 503


# ── Session state ────────────────────────────────────────────────────────────

if "perfil_view" not in st.session_state:
    st.session_state["perfil_view"] = "select"
if "user" not in st.session_state:
    st.session_state["user"] = None


def voltar():
    st.session_state["perfil_view"] = "select"
    st.session_state["user"] = None


# ── CSS compartilhado ────────────────────────────────────────────────────────

SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap');

.hero { background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 60%, #16213e 100%); border: 1px solid rgba(255,107,0,0.25); border-radius: 24px; padding: 2rem 2.2rem; display: flex; align-items: center; gap: 1.5rem; margin-bottom: 0.5rem; position: relative; overflow: hidden; }
.hero::before { content: ''; position: absolute; top: -40px; right: -40px; width: 180px; height: 180px; background: radial-gradient(circle, rgba(255,107,0,0.18) 0%, transparent 70%); border-radius: 50%; }
.hero-avatar { width: 72px; height: 72px; background: linear-gradient(135deg, #FF6B00, #ff9a00); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2rem; flex-shrink: 0; }
.hero-name { font-family: 'Syne', sans-serif; font-size: 1.7rem; color: #fff; margin: 0 0 0.1rem; }
.hero-sub { color: #a0aec0; font-size: 0.88rem; margin: 0; }
.sport-tag { display: inline-block; background: rgba(255,107,0,0.15); border: 1px solid rgba(255,107,0,0.35); color: #FF6B00; border-radius: 20px; padding: 0.15rem 0.75rem; font-size: 0.75rem; font-weight: 600; margin: 0.3rem 0.2rem 0 0; }
.sec-title { font-family: 'Syne', sans-serif; font-size: 1.1rem; color: #FF6B00; border-left: 3px solid #FF6B00; padding-left: 0.6rem; margin: 1.6rem 0 0.8rem; }
.reserva-card { background: linear-gradient(145deg, #1a1a2e, #16213e); border: 1px solid #2a2a4a; border-left: 4px solid #FF6B00; border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: 0.7rem; }
.reserva-card h4 { font-family:'Syne',sans-serif; color:#fff; margin:0 0 0.2rem; font-size:0.98rem; }
.reserva-card p  { color:#a0aec0; font-size:0.82rem; margin:0; }
</style>
"""

VOLTAR_CSS = """
<style>
div.element-container:has(#{anchor_id}) {{ display: none !important; }}
div.element-container:has(#{anchor_id}) + div.element-container {{
    position: fixed; top: 65px; right: 40px; z-index: 9999; width: auto !important;
}}
div.element-container:has(#{anchor_id}) + div.element-container button {{
    border-radius: 30px; box-shadow: 0 4px 15px rgba(255,107,0,0.4);
    border: 1px solid #FF6B00; background-color: #1a1a2e;
    padding: 0.5rem 1.5rem; transition: all 0.3s ease;
}}
div.element-container:has(#{anchor_id}) + div.element-container button:hover {{
    background-color: #FF6B00; color: white;
}}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# TELA 1: SELEÇÃO — LOGIN / CADASTRO
# ══════════════════════════════════════════════════════════════════════════════

def tela_selecao():
    st.title("👤 Perfil")
    st.write("Faça login ou crie sua conta para acessar o **Joga y Joga**:")
    st.divider()

    tab_login, tab_cadastro = st.tabs(["🔑 Login", "📝 Cadastro"])

    with tab_login:
        with st.form("form_login"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                if not email or not senha:
                    st.error("Preencha email e senha.")
                else:
                    result, status = api_post("/login", {"email": email, "senha": senha})
                    if status == 200 and result:
                        st.session_state["user"] = result
                        if result.get("is_proprietario"):
                            st.session_state["perfil_view"] = "admin"
                        else:
                            st.session_state["perfil_view"] = "atleta"
                        st.rerun()
                    else:
                        st.error("Email ou senha incorretos.")

    with tab_cadastro:
        with st.form("form_cadastro"):
            nome = st.text_input("Nome completo")
            email_c = st.text_input("Email", key="email_cadastro")
            senha_c = st.text_input("Senha", type="password", key="senha_cadastro")
            telefone = st.text_input("Telefone (opcional)")
            submitted_c = st.form_submit_button("Criar conta", use_container_width=True)

            if submitted_c:
                if not nome or not email_c or not senha_c:
                    st.error("Preencha nome, email e senha.")
                else:
                    data = {"nome": nome, "email": email_c, "senha": senha_c}
                    if telefone:
                        data["telefone"] = telefone
                    result, status = api_post("/register", data)
                    if status == 201 and result:
                        st.session_state["user"] = result
                        st.session_state["perfil_view"] = "atleta"
                        st.rerun()
                    elif status == 409:
                        st.error("Email já cadastrado.")
                    else:
                        st.error("Erro ao criar conta.")


# ══════════════════════════════════════════════════════════════════════════════
# TELA 2: ATLETA (DASHBOARD COM DADOS REAIS)
# ══════════════════════════════════════════════════════════════════════════════

def tela_atleta():
    user = st.session_state.get("user")
    if not user:
        st.session_state["perfil_view"] = "select"
        st.rerun()
        return

    user_id = user["id"]

    # Botão voltar
    st.markdown('<span id="ancora-voltar-atleta"></span>', unsafe_allow_html=True)
    if st.button("← Sair", key="btn_atleta"):
        voltar()
        st.rerun()

    st.markdown(SHARED_CSS, unsafe_allow_html=True)
    st.markdown(VOLTAR_CSS.format(anchor_id="ancora-voltar-atleta"), unsafe_allow_html=True)

    # Busca dados da API
    stats = api_get(f"/usuarios/{user_id}/estatisticas") or {}
    reservas_prox = api_get(f"/usuarios/{user_id}/reservas", {"tipo": "proximas"}) or []
    reservas_hist = api_get(f"/usuarios/{user_id}/reservas", {"tipo": "historico"}) or []

    # ── Hero ──
    membro_desde = user.get("data_cadastro", "")[:7] if user.get("data_cadastro") else "recém-chegado"
    quadra_fav = stats.get("quadra_favorita", "—")

    st.markdown(
        f"""
    <div class="hero">
      <div class="hero-avatar">🏃</div>
      <div>
        <p class="hero-name">{user["nome"]}</p>
        <p class="hero-sub">Membro desde {membro_desde} &nbsp;·&nbsp; Quadra favorita: {quadra_fav}</p>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── KPIs ──
    st.markdown('<div class="sec-title">📊 Resumo do Mês</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🏟️ Partidas", stats.get("partidas_mes", 0))
    k2.metric("⏱️ Horas", f"{stats.get('horas_mes', 0)}h")
    k3.metric("📍 Quadras", stats.get("quadras_visitadas", 0))
    k4.metric("🔥 Sequência", f"{stats.get('sequencia_dias', 0)}d")
    avg = stats.get("media_avaliacao")
    k5.metric("⭐ Avaliação", avg if avg else "—")

    # ── Próximas reservas ──
    col_res, col_hist = st.columns([2, 3])

    with col_res:
        st.markdown(
            '<div class="sec-title">🗓️ Próximas Reservas</div>', unsafe_allow_html=True
        )
        if reservas_prox:
            for r in reservas_prox:
                cor = "#22c55e" if r.get("status") == "confirmado" else "#f59e0b"
                st.markdown(
                    f"""
                <div class="reserva-card">
                  <h4>{r.get("espaco", "—")}</h4>
                  <p>📅 {r.get("data", "—")} às {r.get("hora_inicio", "—")} &nbsp;
                     <span style='color:{cor}; font-weight:600;'>● {r.get("status", "pendente").capitalize()}</span>
                  </p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Nenhuma reserva futura.")

    with col_hist:
        st.markdown(
            '<div class="sec-title">📋 Histórico de Partidas</div>', unsafe_allow_html=True
        )
        if reservas_hist:
            df = pd.DataFrame(
                {
                    "Data": [r.get("data", "") for r in reservas_hist],
                    "Espaço": [r.get("espaco", "") for r in reservas_hist],
                    "Horário": [f"{r.get('hora_inicio', '')} - {r.get('hora_fim', '')}" for r in reservas_hist],
                    "Valor": [f"R$ {r.get('valor_total', 0)}" for r in reservas_hist],
                    "Status": [r.get("status", "").capitalize() for r in reservas_hist],
                }
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma partida registrada ainda. Faça sua primeira reserva!")


# ══════════════════════════════════════════════════════════════════════════════
# TELA 3: ADMINISTRADOR (DASHBOARD COM DADOS REAIS)
# ══════════════════════════════════════════════════════════════════════════════

def tela_admin():
    user = st.session_state.get("user")
    if not user:
        st.session_state["perfil_view"] = "select"
        st.rerun()
        return

    user_id = user["id"]

    # Botão voltar
    st.markdown('<span id="ancora-voltar-admin"></span>', unsafe_allow_html=True)
    if st.button("← Sair", key="btn_admin"):
        voltar()
        st.rerun()

    st.markdown(SHARED_CSS, unsafe_allow_html=True)
    st.markdown(VOLTAR_CSS.format(anchor_id="ancora-voltar-admin"), unsafe_allow_html=True)

    st.title("📊 Dashboard do Administrador")
    st.divider()

    # Busca dados da API
    dashboard = api_get(f"/admin/{user_id}/dashboard")

    if not dashboard:
        st.warning("Não foi possível carregar os dados do dashboard. Verifique se você é proprietário de espaços.")
        return

    # ── KPIs ──
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Lucro do mês", f"R$ {dashboard.get('lucro_mes', 0):,.2f}")
    with col2:
        st.metric("📅 Aluguéis no mês", dashboard.get("alugueis_mes", 0))
    with col3:
        st.metric("🏟️ Espaços cadastrados", dashboard.get("total_espacos", 0))

    st.divider()

    # ── Lucro por espaço ──
    por_espaco = dashboard.get("por_espaco", [])
    if por_espaco:
        st.subheader("💵 Lucro por espaço (R$)")
        df_lucro = pd.DataFrame(
            {"Lucro (R$)": [e["lucro"] for e in por_espaco]},
            index=[e["nome"] for e in por_espaco],
        )
        st.bar_chart(df_lucro, use_container_width=True)

        st.divider()

    # ── Aluguéis por dia da semana ──
    por_dia = dashboard.get("por_dia_semana", {})
    if por_dia:
        st.subheader("📆 Aluguéis por dia da semana")
        df_dia = pd.DataFrame(
            {"Aluguéis": list(por_dia.values())},
            index=list(por_dia.keys()),
        )
        st.line_chart(df_dia, use_container_width=True)

        st.divider()

    # ── Detalhamento ──
    if por_espaco:
        st.subheader("📋 Detalhamento por espaço")
        df_detalhe = pd.DataFrame(
            {
                "Espaço": [e["nome"] for e in por_espaco],
                "Esportes": [", ".join(e.get("esportes", [])) for e in por_espaco],
                "Aluguéis": [e["alugueis"] for e in por_espaco],
                "Lucro (R$)": [e["lucro"] for e in por_espaco],
            }
        )
        st.dataframe(
            df_detalhe,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Lucro (R$)": st.column_config.NumberColumn("Lucro (R$)", format="R$ %d"),
            },
        )


# ══════════════════════════════════════════════════════════════════════════════
# ROTEAMENTO
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state["perfil_view"] == "select":
    tela_selecao()
elif st.session_state["perfil_view"] == "atleta":
    tela_atleta()
elif st.session_state["perfil_view"] == "admin":
    tela_admin()
