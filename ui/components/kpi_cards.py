# ui/components/kpi_cards.py 

# pyrefly: ignore [missing-import]
import streamlit as st

def kpi_card(titulo, valor, delta, estado="ok"):
    color = {
        "ok"     : "#22c55e",
        "warning": "#f59e0b",
        "risk"   : "#ef4444"
    }.get(estado, "#22c55e")

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

def kpi_card_desde_datos(titulo, valor_num, referencia_num=None, formato="%", umbral_ok=0.80, umbral_warning=0.70):
    """
    KPI dinámico que calcula su propio estado según umbrales.
    valor_num: float (ej: 0.91 para 91%)
    referencia_num: float opcional para calcular delta
    """
    if formato == "%":
        valor_str = f"{valor_num*100:.1f}%"
    else:
        valor_str = f"{valor_num:.1f}"

    if referencia_num is not None:
        diff = (valor_num - referencia_num) * 100
        delta_str = f"{diff:+.1f}% vs período anterior"
    else:
        delta_str = "Sin referencia previa"

    if valor_num >= umbral_ok:
        estado = "ok"
    elif valor_num >= umbral_warning:
        estado = "warning"
    else:
        estado = "risk"

    kpi_card(titulo, valor_str, delta_str, estado)