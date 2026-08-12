# cycle_comparison.py

# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
import altair as alt
import pandas as pd
from src.logic.comparative_engine import generar_recomendaciones_ciclo

ORDEN_BIMESTRES = ["B1", "B2", "B3", "B4", "B5"]
ETIQUETAS = {"B1": "Bimestre 1", "B2": "Bimestre 2", "B3": "Bimestre 3",
             "B4": "Bimestre 4", "B5": "Bimestre 5"}
COLORES = {"B1": "#94a3b8", "B2": "#60a5fa", "B3": "#3b82f6",
           "B4": "#2563eb", "B5": "#1d4ed8"}

def render_cycle_comparison(df_asistencia_actual, df_academico_actual,
                             df_asistencia_previo, df_academico_previo,
                             sede_actual: str | None = None):
    st.markdown("---")
    st.markdown("### Análisis Histórico y Plan de Acción Ejecutivo")
    st.caption("Comparativa de Dominio Académico por Bimestre")

    # ── Leer historial real acumulado ───────────────────────────────
    if sede_actual == "Global":
        campus_keys = ["Misiones", "Nuevo Sur", "San Agustín"]
        historial = {}
        for bim in ORDEN_BIMESTRES:
            b_vals = []
            for c in campus_keys:
                c_hist = st.session_state.get(f"historial_bimestres_{c}", {})
                if bim in c_hist:
                    b_vals.append(c_hist[bim])
            if b_vals:
                historial[bim] = sum(b_vals) / len(b_vals)
    else:
        clave_hist = f"historial_bimestres_{sede_actual}" if sede_actual else None
        historial  = st.session_state.get(clave_hist, {}) if clave_hist else {}

    if historial:
        # Construir DataFrame desde datos reales subidos
        filas = []
        for bim in ORDEN_BIMESTRES:
            if bim in historial:
                filas.append({
                    "Bimestre" : ETIQUETAS[bim],
                    "Dominio"  : historial[bim],
                    "Color"    : COLORES[bim],
                    "Tipo"     : "Real"
                })
        df_chart = pd.DataFrame(filas)
        st.caption(f"Bimestres con datos reales: {', '.join(historial.keys())}")
    else:
        # Fallback simulado mientras no hay archivos subidos
        df_actual = pd.merge(df_asistencia_actual, df_academico_actual, on="campus")
        avg_dominio = df_actual["dominio"].mean()
        df_chart = pd.DataFrame([
            {"Bimestre": "Bimestre 1", "Dominio": avg_dominio - 0.08, "Color": "#94a3b8", "Tipo": "Simulado"},
            {"Bimestre": "Bimestre 2", "Dominio": avg_dominio - 0.04, "Color": "#60a5fa", "Tipo": "Simulado"},
            {"Bimestre": "Bimestre 3", "Dominio": avg_dominio,        "Color": "#3b82f6", "Tipo": "Simulado"},
            {"Bimestre": "Bimestre 4", "Dominio": avg_dominio + 0.02, "Color": "#2563eb", "Tipo": "Simulado"},
            {"Bimestre": "Bimestre 5", "Dominio": avg_dominio + 0.05, "Color": "#1d4ed8", "Tipo": "Simulado"},
        ])
        st.caption("Mostrando proyección estimada. Sube archivos por bimestre para ver datos reales.")

    # ── Gráfica con color por bimestre ──────────────────────────────
    chart = alt.Chart(df_chart).mark_bar(
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X("Bimestre:O", title=None, axis=alt.Axis(labelAngle=0),
                sort=[ETIQUETAS[b] for b in ORDEN_BIMESTRES]),
        y=alt.Y("Dominio:Q", title="Porcentaje (%)",
                axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("Color:N", scale=None),  # usa el color directo del DataFrame
        tooltip=[
            alt.Tooltip("Bimestre:O"),
            alt.Tooltip("Dominio:Q", format=".1%", title="Dominio"),
            alt.Tooltip("Tipo:N", title="Fuente")
        ]
    ).properties(height=260).configure_view(stroke="transparent")

    st.altair_chart(chart, use_container_width=True)

    # ── Retrospectiva ────────────────────────────────────────────────
    df_actual_ret = pd.merge(df_asistencia_actual, df_academico_actual, on="campus")
    df_previo_ret = pd.merge(df_asistencia_previo, df_academico_previo, on="campus")
    recomendaciones = generar_recomendaciones_ciclo(df_actual_ret, df_previo_ret)

    st.markdown("---")
    st.markdown("#### Retrospectiva")

    col_mantener, col_mejorar, col_modificar = st.columns(3)

    with col_mantener:
        st.markdown("<h5 style='color:#22c55e;'>Qué Mantener</h5>", unsafe_allow_html=True)
        if not recomendaciones["mantener"]:
            st.write("Sin hallazgos principales.")
        for msg in recomendaciones["mantener"]:
            st.info(msg)

    with col_mejorar:
        st.markdown("<h5 style='color:#f59e0b;'>Qué Mejorar</h5>", unsafe_allow_html=True)
        if not recomendaciones["mejorar"]:
            st.write("Sin hallazgos principales.")
        for msg in recomendaciones["mejorar"]:
            st.warning(msg)

    with col_modificar:
        st.markdown("<h5 style='color:#ef4444;'>Qué Modificar</h5>", unsafe_allow_html=True)
        if not recomendaciones["modificar"]:
            st.write("Sin hallazgos principales.")
        for msg in recomendaciones["modificar"]:
            st.error(msg)

    st.markdown("<br>", unsafe_allow_html=True)