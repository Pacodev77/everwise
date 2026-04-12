# ui/components/kpi_cards.py 

import streamlit as st


def estado_por_valor(valor, umbral_ok, umbral_warning):
    """
    Determina el estado visual del KPI según umbrales.
    
    - ok: valor >= umbral_ok
    - warning: valor >= umbral_warning
    - risk: valor < umbral_warning
    """
    if valor >= umbral_ok:
        return "ok"
    elif valor >= umbral_warning:
        return "warning"
    else:
        return "risk"


def kpi_card(titulo, valor, delta, estado="ok"):
    color = {
        "ok": "#22c55e",
        "warning": "#f59e0b",
        "risk": "#ef4444"
    }[estado]

    st.markdown(
        f"""
        <div style="
            background:white;
            padding:20px;
            border-radius:18px;
            border-left:6px solid {color};
            box-shadow:0 8px 24px rgba(15,23,42,.05)">
            <div style="font-size:.85rem;color:#64748b">{titulo}</div>
            <div style="font-size:2rem;font-weight:800">{valor}</div>
            <div style="font-size:.8rem;color:#64748b">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
