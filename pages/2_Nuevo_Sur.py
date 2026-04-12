# pages/2_Nuevo_Sur.py
# ======================================================
# Everwise Dashboard 2026 · Sede Nuevo Sur
# ======================================================

import streamlit as st
import pandas as pd
import altair as alt

from config.campus import CAMPUS
from ui.components.kpi_cards import kpi_card, estado_por_valor
from ui.sections.sidebar import render_sidebar
from ui.sections.footer import render_footer
from src.logic.data_loader import load_global_data, load_apps_data, load_academico_bloques, load_clima_heatmap, load_disciplina_data
from ui.components.cycle_comparison import render_cycle_comparison
from ui.charts.apps_charts import chart_comparativa_apps, chart_correlacion_practica
from ui.charts.nuevos_graficos import chart_academico_bloques, chart_clima_heatmap, chart_clima_barras
from ui.components.data_uploader import render_campus_dynamic_view
from ui.components.asistencia_seccion import render_asistencia_section

st.set_page_config(
    page_title="Everwise | Sede Nuevo Sur",
    page_icon="assets/letra-e_blue.png",
    layout="wide"
)

try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

from src.logic.auth import require_login
require_login("Nuevo Sur")

campus = CAMPUS["nuevo_sur"]

# Sidebar
render_sidebar(sede_name="Nuevo Sur")

# Header
st.markdown(
    f"""
    <div class="header-container">
        <div class="dashboard-title">{campus['nombre']}</div>
        <div class="dashboard-subtitle">
            {campus['subtitulo']}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

sede_actual = "Nuevo Sur"

# Carga de datos localizados
df_asistencia, df_academico, df_asistencia_prev, df_academico_prev = load_global_data()
df_apps_kpis, df_correlacion = load_apps_data()
df_acad_hist = load_academico_bloques()
df_clima_global = load_clima_heatmap()
df_casos_global, df_cartas_global = load_disciplina_data()

df_ast = df_asistencia[df_asistencia['campus'] == sede_actual]
df_aca = df_academico[df_academico['campus'] == sede_actual]
df_ast_prev = df_asistencia_prev[df_asistencia_prev['campus'] == sede_actual]
df_aca_prev = df_academico_prev[df_academico_prev['campus'] == sede_actual]

df_apps_kpis_sede = df_apps_kpis[df_apps_kpis['campus'] == sede_actual]
df_corr_sede = df_correlacion[df_correlacion['campus'] == sede_actual]

df_acad_sede = df_acad_hist[df_acad_hist['campus'] == sede_actual]
df_clima = df_clima_global[df_clima_global['campus'] == sede_actual]
df_casos = df_casos_global[df_casos_global['campus'] == sede_actual]
df_cartas = df_cartas_global[df_cartas_global['campus'] == sede_actual]

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Resumen Ejecutivo", 
    "Desempeño Académico", 
    "Clima Escolar", 
    "Disciplina", 
    "Práctica Docente"
])

with tab1:
    estado_asistencia = estado_por_valor(94, 90, 80)
    
    # Dinámica de métricas académicas (Mates y Español) para la sede local
    bloques_ordenados = sorted(df_acad_sede['Bloque'].unique())
    b_actual = bloques_ordenados[-1]
    b_previo = bloques_ordenados[-2] if len(bloques_ordenados) > 1 else b_actual
    
    math_actual = df_acad_sede[df_acad_sede['Bloque'] == b_actual]['Matemáticas'].mean()
    math_previo = df_acad_sede[df_acad_sede['Bloque'] == b_previo]['Matemáticas'].mean()
    math_delta = (math_actual - math_previo) * 100
    
    esp_actual = df_acad_sede[df_acad_sede['Bloque'] == b_actual]['Español'].mean()
    esp_previo = df_acad_sede[df_acad_sede['Bloque'] == b_previo]['Español'].mean()
    esp_delta = (esp_actual - esp_previo) * 100

    k1, k2, k3 = st.columns(3, gap="large")
    with k1:
        kpi_card("Asistencia Promedio", "94%", "+3% vs mes anterior", estado=estado_asistencia)
    with k2:
        kpi_card(f"Matemáticas ({b_actual})", f"{math_actual*100:.1f}%", f"{math_delta:+.1f}% vs {b_previo}", estado="ok" if math_delta >= 0 else "warning")
    with k3:
        kpi_card(f"Español ({b_actual})", f"{esp_actual*100:.1f}%", f"{esp_delta:+.1f}% vs {b_previo}", estado="ok" if esp_delta >= 0 else "warning")
        
    render_asistencia_section(sede_actual, mostrar_uploader=True)
    
    render_cycle_comparison(df_ast, df_aca, df_ast_prev, df_aca_prev)

with tab2:
    st.markdown("### Seguimiento Académico y Trazabilidad")
    if not render_campus_dynamic_view("acad", sede_actual):
        st.altair_chart(chart_academico_bloques(df_acad_sede), use_container_width=True)
        st.info("**Aviso:** Evaluando hasta B3, el área de oportunidad crítica sigue siendo el refuerzo académico en Matemáticas.")

with tab3:
    st.markdown("### Mapa de Calor - Indicador de Clima Escolar (ICE)")
    if not render_campus_dynamic_view("clima", sede_actual):
        st.altair_chart(chart_clima_heatmap(df_clima), use_container_width=True)
        st.markdown("### Distribución de Respuestas")
        st.altair_chart(chart_clima_barras(df_clima), use_container_width=True)
        st.info("**Lectura ejecutiva:** Nuevo Sur presenta altos índices de satisfacción. Se recomienda mantener prácticas actuales, pero reforzar matematicas.")

with tab4:
    st.markdown("### Panel de Control de Disciplina e Inclusión")
    if not render_campus_dynamic_view("disc", sede_actual):
        cd1, cd2 = st.columns(2)
        with cd1:
            st.markdown("**Radar de Casos Especiales (Activos)**")
            st.dataframe(df_casos, hide_index=True, use_container_width=True)
        with cd2:
            st.markdown("**Alertas por Cartas Compromiso**")
            st.dataframe(df_cartas, hide_index=True, use_container_width=True)

with tab5:
    st.markdown("### Herramientas y Acompañamiento Docente")
    if not render_campus_dynamic_view("prac", sede_actual):
        st.markdown(f"### Uso de Aplicaciones: IXL vs Progrentis en {sede_actual}")
        colr1, colr2 = st.columns(2, gap="large")
        with colr1:
            st.markdown("**Métricas de Adopción**")
            st.altair_chart(chart_comparativa_apps(df_apps_kpis_sede), use_container_width=True)
        with colr2:
            st.markdown("**Relación Académica: Práctica vs Resultados (Dominio)**")
            st.altair_chart(chart_correlacion_practica(df_corr_sede), use_container_width=True)



# Footer
render_footer()