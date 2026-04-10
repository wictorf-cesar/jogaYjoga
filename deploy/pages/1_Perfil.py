import streamlit as st
import pandas as pd
import plotly.express as px
import random
from datetime import date, timedelta

# A configuração da página deve ser o primeiro comando do Streamlit
st.set_page_config(page_title="Perfil | Joga y Joga", page_icon="👤", layout="wide")

# --- Inicializa estado da página ---
if "perfil_view" not in st.session_state:
    st.session_state["perfil_view"] = "select"

def voltar():
    st.session_state["perfil_view"] = "select"

# ══════════════════════════════════════════════════════════════════════════════
# TELA 1: SELEÇÃO DE PERFIL
# ══════════════════════════════════════════════════════════════════════════════
def tela_selecao():
    st.title("👤 Perfil")
    st.write("Selecione como você vai usar o **Joga y Joga**:")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style='text-align: center; padding: 1rem;'>
                <h1 style='font-size: 3rem;'>⚽</h1>
                <h3>Atleta</h3>
                <p style='color: gray; font-size: 0.9rem;'>
                    Encontre e alugue quadras perto de você
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Entrar como Atleta", use_container_width=True):
            st.session_state["perfil_view"] = "atleta"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div style='text-align: center; padding: 1rem;'>
                <h1 style='font-size: 3rem;'>🏟️</h1>
                <h3>Administrador</h3>
                <p style='color: gray; font-size: 0.9rem;'>
                    Gerencie suas quadras e acompanhe resultados
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Entrar como Administrador", use_container_width=True):
            st.session_state["perfil_view"] = "admin"
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TELA 2: ATLETA (DASHBOARD)
# ══════════════════════════════════════════════════════════════════════════════
def tela_atleta():
    # 1º: A ÂNCORA INVISÍVEL
    st.markdown('<span id="ancora-voltar-atleta"></span>', unsafe_allow_html=True)
    
    # 2º: O BOTÃO (Fica logo abaixo da âncora)
    if st.button("← Voltar", key="btn_atleta"):
        voltar()
        st.rerun()

    # 3º: O CSS QUE LÊ A ÂNCORA
    st.markdown("""
    <style>
    /* Oculta o container da âncora para não gerar espaço vazio na tela */
    div.element-container:has(#ancora-voltar-atleta) {
        display: none !important;
    }
    
    /* Pega o container do botão (que é o irmão imediato '+' da âncora) e faz flutuar no TOPO DIREITO */
    div.element-container:has(#ancora-voltar-atleta) + div.element-container {
        position: fixed;
        top: 65px;  /* <--- MUDAMOS DE BOTTOM PARA TOP AQUI */
        right: 40px;
        z-index: 9999;
        width: auto !important;
    }
    
    /* Estiliza o botão para ficar bonitão */
    div.element-container:has(#ancora-voltar-atleta) + div.element-container button {
        border-radius: 30px;
        box-shadow: 0 4px 15px rgba(255, 107, 0, 0.4);
        border: 1px solid #FF6B00;
        background-color: #1a1a2e;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    div.element-container:has(#ancora-voltar-atleta) + div.element-container button:hover {
        background-color: #FF6B00;
        color: white;
    }
    
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
    """, unsafe_allow_html=True)

    # ── MOCK DATA Atleta ──
    ATLETA = { "nome": "João Silva", "membro_desde": "março de 2024", "esportes": ["⚽ Futebol", "🏐 Vôlei", "🎾 Tênis"], "quadra_fav": "Arena Boa Vista", "nivel": "Intermediário" }
    KPI = { "partidas_mes": 12, "horas_mes": 18.5, "quadras_visitadas": 7, "sequencia_dias": 5, "gasto_mes": 420, "media_avaliacao": 4.8 }
    
    semanas = [f"S{i}" for i in range(1, 9)]
    random.seed(42)
    historico = pd.DataFrame({"Semana": semanas * 3, "Esporte": ["Futebol"]*8 + ["Vôlei"]*8 + ["Tênis"]*8, "Partidas": [random.randint(0, 4) for _ in range(24)]})
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun"]
    gastos = pd.DataFrame({"Mês": meses * 3, "Esporte": ["Futebol"]*6 + ["Vôlei"]*6 + ["Tênis"]*6, "Gasto": [random.randint(80,200) for _ in range(18)]})
    hoje = date.today()
    proximas_reservas = [
        {"quadra": "Arena Boa Vista",    "esporte": "⚽ Futebol", "data": hoje + timedelta(days=1), "hora": "19:00", "status": "confirmado"},
        {"quadra": "Quadra do Derby",    "esporte": "🏐 Vôlei",  "data": hoje + timedelta(days=3), "hora": "08:30", "status": "confirmado"},
        {"quadra": "Arena Aflitos",      "esporte": "🎾 Tênis",  "data": hoje + timedelta(days=7), "hora": "07:00", "status": "pendente"},
    ]
    historico_partidas = pd.DataFrame({
        "Data":      [(hoje - timedelta(days=d)).strftime("%d/%m") for d in [2,4,6,9,11,14]],
        "Quadra":  ["Arena Boa Vista","Quadra do Derby","Arena Aflitos","Arena Boa Vista","Pina Beach","Quadra do Derby"],
        "Esporte": ["⚽ Futebol","🏐 Vôlei","🎾 Tênis","⚽ Futebol","🏐 Vôlei","⚽ Futebol"],
        "Duração": ["1h","1h30","1h","2h","1h","1h30"],
        "Gasto":   ["R$ 90","R$ 75","R$ 95","R$ 110","R$ 80","R$ 75"],
        "Avaliação":["⭐⭐⭐⭐⭐","⭐⭐⭐⭐","⭐⭐⭐⭐⭐","⭐⭐⭐⭐","⭐⭐⭐⭐⭐","⭐⭐⭐⭐"],
    })

    CORES_ESPORTE = {"Futebol": "#FF6B00", "Vôlei": "#ff9a00", "Tênis": "#ffb347"}

    # ── RENDERIZAÇÃO ATLETA ──
    tags_html = "".join(f"<span class='sport-tag'>{e}</span>" for e in ATLETA["esportes"])
    st.markdown(f"""
    <div class="hero">
      <div class="hero-avatar">🏃</div>
      <div>
        <p class="hero-name">{ATLETA['nome']}</p>
        <p class="hero-sub">Membro desde {ATLETA['membro_desde']} &nbsp;·&nbsp; Nível: {ATLETA['nivel']} &nbsp;·&nbsp; Quadra favorita: {ATLETA['quadra_fav']}</p>
        {tags_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec-title">📊 Resumo do Mês</div>', unsafe_allow_html=True)
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("🏟️ Partidas",          KPI["partidas_mes"],        "+3 vs mês anterior")
    k2.metric("⏱️ Horas jogadas",      f"{KPI['horas_mes']}h",     "+2.5h vs mês anterior")
    k3.metric("📍 Quadras visitadas",  KPI["quadras_visitadas"],   "+2 novas")
    k4.metric("🔥 Sequência atual",    f"{KPI['sequencia_dias']}d","recorde pessoal!")
    k5.metric("💸 Gasto no mês",       f"R$ {KPI['gasto_mes']}",  "-R$ 30 vs mês anterior")
    k6.metric("⭐ Avaliação média",    KPI["media_avaliacao"],     "top 10% da plataforma")

    col_res, col_ativ = st.columns([2, 3])
    with col_res:
        st.markdown('<div class="sec-title">🗓️ Próximas Reservas</div>', unsafe_allow_html=True)
        for r in proximas_reservas:
            cor_status = "#22c55e" if r["status"] == "confirmado" else "#f59e0b"
            st.markdown(f"""
            <div class="reserva-card">
              <h4>{r['esporte']} — {r['quadra']}</h4>
              <p>📅 {r['data'].strftime('%d/%m/%Y')} às {r['hora']} &nbsp;
                 <span style='color:{cor_status}; font-weight:600;'>● {r['status'].capitalize()}</span>
              </p>
            </div>
            """, unsafe_allow_html=True)
        st.button("+ Nova Reserva", use_container_width=True)

    with col_ativ:
        st.markdown('<div class="sec-title">📈 Partidas por Semana</div>', unsafe_allow_html=True)
        fig_hist = px.bar(historico, x="Semana", y="Partidas", color="Esporte", barmode="group", color_discrete_map=CORES_ESPORTE)
        fig_hist.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=0), legend=dict(font=dict(color="#a0aec0")), xaxis=dict(gridcolor="#2a2a4a"), yaxis=dict(gridcolor="#2a2a4a"))
        st.plotly_chart(fig_hist, use_container_width=True)

    col_g1, col_g2 = st.columns([3, 2])
    with col_g1:
        st.markdown('<div class="sec-title">💸 Gastos Mensais por Esporte</div>', unsafe_allow_html=True)
        fig_gas = px.line(gastos, x="Mês", y="Gasto", color="Esporte", markers=True, color_discrete_map=CORES_ESPORTE, labels={"Gasto": "R$"})
        fig_gas.update_traces(line_width=2.5, marker_size=7)
        fig_gas.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=0), legend=dict(font=dict(color="#a0aec0")), xaxis=dict(gridcolor="#2a2a4a"), yaxis=dict(gridcolor="#2a2a4a", tickprefix="R$ "))
        st.plotly_chart(fig_gas, use_container_width=True)

    with col_g2:
        st.markdown('<div class="sec-title">🏅 Tempo por Esporte</div>', unsafe_allow_html=True)
        df_tempo = pd.DataFrame({"Esporte": ["Futebol","Vôlei","Tênis"], "Horas":  [9.5, 5.5, 3.5]})
        fig_pie = px.pie(df_tempo, names="Esporte", values="Horas", hole=0.5, color_discrete_map=CORES_ESPORTE)
        fig_pie.update_traces(textfont_color="#fff")
        fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=0), legend=dict(font=dict(color="#a0aec0")), annotations=[dict(text="18.5h", x=0.5, y=0.5, font_size=18, font_color="#FF6B00", showarrow=False, font=dict(family="Syne"))])
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown('<div class="sec-title">📋 Histórico de Partidas</div>', unsafe_allow_html=True)
    st.dataframe(historico_partidas, use_container_width=True, hide_index=True)




# ══════════════════════════════════════════════════════════════════════════════
# TELA 3: ADMINISTRADOR (DASHBOARD)
# ══════════════════════════════════════════════════════════════════════════════
def tela_admin():
    # 1º: A ÂNCORA INVISÍVEL
    st.markdown('<span id="ancora-voltar-admin"></span>', unsafe_allow_html=True)
    
    # 2º: O BOTÃO
    if st.button("← Voltar", key="btn_admin"):
        voltar()
        st.rerun()
        
    # 3º: O CSS QUE LÊ A ÂNCORA
    st.markdown("""
    <style>
    /* Oculta o container da âncora */
    div.element-container:has(#ancora-voltar-admin) {
        display: none !important;
    }
    
    /* Pega o container do botão e faz flutuar no TOPO DIREITO */
    div.element-container:has(#ancora-voltar-admin) + div.element-container {
        position: fixed;
        top: 65px;  /* <--- MUDAMOS DE BOTTOM PARA TOP AQUI */
        right: 40px;
        z-index: 9999;
        width: auto !important;
    }
    
    /* Estiliza o botão */
    div.element-container:has(#ancora-voltar-admin) + div.element-container button {
        border-radius: 30px;
        box-shadow: 0 4px 15px rgba(255, 107, 0, 0.4);
        border: 1px solid #FF6B00;
        background-color: #1a1a2e;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    div.element-container:has(#ancora-voltar-admin) + div.element-container button:hover {
        background-color: #FF6B00;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("📊 Dashboard do Administrador")
    st.caption("Visão geral — Abril 2026")
    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="💰 Lucro total (mês)", value="R$ 18.640", delta="+12% vs março")
    with col2:
        st.metric(label="📅 Aluguéis realizados", value="214", delta="+8% vs março")
    with col3:
        st.metric(label="🏟️ Quadras cadastradas", value="6", delta="2 com alta demanda")
    with col4:
        st.metric(label="📈 Taxa de ocupação", value="74%", delta="Meta: 80%", delta_color="inverse")

    st.divider()

    st.subheader("💵 Lucro por quadra (R$)")
    lucro_data = pd.DataFrame(
        {"Lucro (R$)": [5220, 3690, 2880, 2640, 2610, 1600]},
        index=["Arena Norte", "Cais do Apolo", "Boa Viagem", "Derby", "Graças", "Olinda"]
    )
    st.bar_chart(lucro_data, use_container_width=True)

    st.divider()

    st.subheader("📆 Aluguéis por dia da semana (média mensal)")
    semana_data = pd.DataFrame(
        {"Aluguéis": [18, 22, 20, 25, 34, 48, 47]},
        index=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    )
    st.line_chart(semana_data, use_container_width=True)

    st.divider()

    st.subheader("📋 Detalhamento por quadra")
    quadras_df = pd.DataFrame({
        "Quadra": ["Arena Norte", "Cais do Apolo", "Boa Viagem", "Derby", "Graças", "Olinda"],
        "Esporte": ["Futebol", "Futsal", "Vôlei", "Basquete", "Futebol", "Tênis"],
        "Aluguéis": [58, 41, 36, 33, 29, 17],
        "Lucro (R$)": [5220, 3690, 2880, 2640, 2610, 1600],
        "Ocupação (%)": [89, 76, 68, 62, 55, 40],
        "Status": ["Alta demanda", "Regular", "Regular", "Regular", "Baixa", "Baixa"],
    })

    st.dataframe(
        quadras_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Lucro (R$)": st.column_config.NumberColumn("Lucro (R$)", format="R$ %d"),
            "Ocupação (%)": st.column_config.ProgressColumn("Ocupação (%)", min_value=0, max_value=100, format="%d%%"),
            "Status": st.column_config.TextColumn("Status"),
        },
    )

# ══════════════════════════════════════════════════════════════════════════════
# O CORAÇÃO DO CÓDIGO
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["perfil_view"] == "select":
    tela_selecao()
elif st.session_state["perfil_view"] == "atleta":
    tela_atleta()
elif st.session_state["perfil_view"] == "admin":
    tela_admin()