# pages/1_Misiones.py
# ======================================================
# Everwise Dashboard 2026 · Sede Misiones
# ======================================================

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore [missing-import]
import altair as alt

from config.campus import CAMPUS
from ui.components.kpi_cards import kpi_card, kpi_card_desde_datos
from ui.sections.sidebar import render_sidebar
from ui.sections.footer import render_footer
from src.logic.data_loader import load_global_data, load_apps_data, load_academico_bloques, load_clima_heatmap, load_disciplina_data
from ui.components.cycle_comparison import render_cycle_comparison
from ui.charts.apps_charts import chart_comparativa_apps, chart_correlacion_practica
from ui.charts.nuevos_graficos import chart_academico_bloques, chart_clima_heatmap, chart_clima_barras
from ui.components.data_uploader import render_campus_dynamic_view, render_campus_uploader
from ui.components.asistencia_seccion import render_asistencia_section
from src.logic.academic_processor import calcular_kpis_ejecutivos
from ui.components.ixl_seccion import render_ixl_section, render_adopcion_y_correlacion
from ui.components.academico_seccion import render_academico_section


st.set_page_config(
    page_title="Everwise | Sede Misiones",
    page_icon="assets/letra-e_blue.png",
    layout="wide"
)

try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

from src.logic.auth import require_login
require_login("Misiones")

from src.logic.data_loader import init_session_state
init_session_state()

campus = CAMPUS["misiones"]

# Sidebar
ciclo_seleccionado = render_sidebar(sede_name="Misiones")

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

# Carga de datos localizados
df_asistencia, df_academico, df_asistencia_prev, df_academico_prev = load_global_data()
df_acad_hist = load_academico_bloques()

# Integrar datos reales de session_state si existen
df_clima_global = st.session_state.get("clima_data_global", load_clima_heatmap())

df_casos_global, df_cartas_global = load_disciplina_data()
df_casos_global = st.session_state.get("disciplina_casos", df_casos_global)
df_cartas_global = st.session_state.get("disciplina_cartas", df_cartas_global)

df_apps_kpis, df_correlacion = load_apps_data()
df_apps_kpis = st.session_state.get("practica_apps_kpis", df_apps_kpis)
df_correlacion = st.session_state.get("practica_correlacion", df_correlacion)

sede_actual = "Misiones"

# Override with real data if available in session_state
clave_acad = f"academico_propio_{sede_actual}"
if clave_acad in st.session_state:
    res_acad = st.session_state[clave_acad]
    df_raw = res_acad["df_raw"]
    real_dom = (df_raw["Language Arts"].mean() + df_raw["Matemáticas"].mean() + df_raw["Español"].mean()) / 30
    df_academico.loc[df_academico["campus"] == sede_actual, "dominio"] = real_dom

clave_asis = f"asistencia_data_{sede_actual}"
df_asistencia["staff_asistencia"] = None
if clave_asis in st.session_state:
    res_ast = st.session_state[clave_asis]
    real_asis = res_ast["niveles"]["Asistencia"].mean() if not res_ast["niveles"].empty else 0.0
    df_asistencia.loc[df_asistencia["campus"] == sede_actual, "asistencia"] = real_asis
    df_asistencia.loc[df_asistencia["campus"] == sede_actual, "staff_asistencia"] = res_ast["staff"]

# Ajuste dinámico de ciclo escolar
def obtener_datos_por_ciclo(ciclo: str, df_ast_25_26, df_aca_25_26, df_ast_24_25, df_aca_24_25):
    if ciclo == "2025 - 2026":
        return df_ast_25_26, df_aca_25_26, df_ast_24_25, df_aca_24_25
    elif ciclo == "2024 - 2025":
        df_ast_23_24 = df_ast_24_25.copy()
        df_ast_23_24["asistencia"] = (df_ast_23_24["asistencia"] - 0.02).clip(0, 1)
        df_aca_23_24 = df_aca_24_25.copy()
        df_aca_23_24["dominio"] = (df_aca_23_24["dominio"] - 0.03).clip(0, 1)
        return df_ast_24_25, df_aca_24_25, df_ast_23_24, df_aca_23_24
    else: # "2023 - 2024"
        df_ast_23_24 = df_ast_24_25.copy()
        df_ast_23_24["asistencia"] = (df_ast_23_24["asistencia"] - 0.02).clip(0, 1)
        df_aca_23_24 = df_aca_24_25.copy()
        df_aca_23_24["dominio"] = (df_aca_23_24["dominio"] - 0.03).clip(0, 1)
        
        df_ast_22_23 = df_ast_23_24.copy()
        df_ast_22_23["asistencia"] = (df_ast_22_23["asistencia"] - 0.01).clip(0, 1)
        df_aca_22_23 = df_aca_23_24.copy()
        df_aca_22_23["dominio"] = (df_aca_22_23["dominio"] - 0.02).clip(0, 1)
        return df_ast_23_24, df_aca_23_24, df_ast_22_23, df_aca_22_23

df_ast_cycle, df_aca_cycle, df_ast_prev_cycle, df_aca_prev_cycle = obtener_datos_por_ciclo(
    ciclo_seleccionado, df_asistencia, df_academico, df_asistencia_prev, df_academico_prev
)

df_ast = df_ast_cycle[df_ast_cycle['campus'] == sede_actual]
df_aca = df_aca_cycle[df_aca_cycle['campus'] == sede_actual]
df_ast_prev = df_ast_prev_cycle[df_ast_prev_cycle['campus'] == sede_actual]
df_aca_prev = df_aca_prev_cycle[df_aca_prev_cycle['campus'] == sede_actual]

df_apps_kpis_sede = df_apps_kpis[df_apps_kpis['campus'] == sede_actual]
df_corr_sede = df_correlacion[df_correlacion['campus'] == sede_actual]

df_acad_sede = df_acad_hist[df_acad_hist['campus'] == sede_actual]
df_clima = df_clima_global[df_clima_global['campus'] == sede_actual]
df_casos = df_casos_global[df_casos_global['campus'] == sede_actual]
df_cartas = df_cartas_global[df_cartas_global['campus'] == sede_actual]

# ====
clave_datos  = f"academico_propio_{sede_actual}"
kpis_reales  = None

if clave_datos in st.session_state:
    kpis_reales = calcular_kpis_ejecutivos(st.session_state[clave_datos])
# ===

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Resumen Ejecutivo", 
    "Desempeño Académico", 
    "Clima Escolar", 
    "Disciplina", 
    "Práctica Docente"
])

# ==============================
with tab1:
    # ── Intentar leer datos reales del archivo subido o SQLite ──
    clave_datos = f"academico_propio_{sede_actual}"
    kpis_reales = None

    if clave_datos in st.session_state:
        from src.logic.academic_processor import calcular_kpis_ejecutivos
        kpis_reales = calcular_kpis_ejecutivos(st.session_state[clave_datos])
    else:
        from src.logic.data_loader import get_academic_history_catalog
        catalog = get_academic_history_catalog()
        if sede_actual in catalog and catalog[sede_actual]:
            def _sort_b(b):
                s = str(b).upper().strip()
                return int(s[1:]) if s.startswith('B') and s[1:].isdigit() else 99
            latest_b = sorted(catalog[sede_actual].keys(), key=_sort_b)[-1]
            res_latest = catalog[sede_actual][latest_b]
            st.session_state[clave_datos] = res_latest
            from src.logic.academic_processor import calcular_kpis_ejecutivos
            kpis_reales = calcular_kpis_ejecutivos(res_latest)

    k1, k2, k3 = st.columns(3, gap="large")

    # 1. Asistencia del campus
    asis_val = float(df_ast["asistencia"].iloc[0]) if not df_ast.empty else None

    # 2. Desempeño y Promedio de Materias
    if kpis_reales:
        bim = kpis_reales["bimestre"]
        pct_desempeno = kpis_reales["pct_desempeno"] * 100.0
        total_alumnos = f"{kpis_reales['total_alumnos']} alumnos"
        prom_math = kpis_reales["prom_math"] * 10.0
        prom_esp = kpis_reales["prom_español"] * 10.0
        prom_general = (prom_math + prom_esp) / 2.0
        val_des = f"{pct_desempeno:.1f}%"
        sub_des = f"Bimestre {bim} · {total_alumnos}"
        val_prom = f"{prom_general:.1f}/10"
        sub_prom = f"Math: {prom_math:.1f} · Esp: {prom_esp:.1f}"
    else:
        df_sede_acad = df_acad_hist[df_acad_hist['campus'] == sede_actual] if ('campus' in df_acad_hist.columns and not df_acad_hist.empty) else pd.DataFrame()
        if not df_sede_acad.empty and 'Bloque' in df_sede_acad.columns:
            b_actual = sorted(df_sede_acad['Bloque'].unique(), key=lambda b: int(str(b)[1:]) if str(b).startswith('B') and str(b)[1:].isdigit() else 99)[-1]
            b_row = df_sede_acad[df_sede_acad['Bloque'] == b_actual].iloc[0]
            prom_math = float(b_row.get('Matemáticas', 0.0)) * 10.0
            prom_esp = float(b_row.get('Español', 0.0)) * 10.0
            prom_la = float(b_row.get('Language Arts', 0.0)) * 10.0
            prom_general = (prom_math + prom_esp) / 2.0
            pct_desempeno = ((prom_math + prom_esp + prom_la) / 30.0) * 100.0
            val_des = f"{pct_desempeno:.1f}%"
            sub_des = f"Bimestre {b_actual} · Matrícula campus"
            val_prom = f"{prom_general:.1f}/10"
            sub_prom = f"Math: {prom_math:.1f} · Esp: {prom_esp:.1f}"
            bim = b_actual
        else:
            val_des = "Sin datos"
            sub_des = "Suba un archivo académico"
            val_prom = "Sin datos"
            sub_prom = "Suba un archivo académico"
            bim = "N/A"

    val_asis = f"{asis_val*100:.1f}%" if asis_val is not None else "Sin datos"
    sub_asis = "Asistencia consolidada del campus" if asis_val is not None else "Suba un reporte de asistencia"

    with k1:
        kpi_card(
            f"Asistencia ({sede_actual})",
            val_asis,
            sub_asis,
            estado="ok" if (asis_val is not None and asis_val >= 0.85) else "warning"
        )
    with k2:
        kpi_card(
            f"Alumnos en Desempeño ({bim})" if bim != "N/A" else "Alumnos en Desempeño",
            val_des,
            sub_des,
            estado="ok" if val_des != "Sin datos" else "warning"
        )
    with k3:
        kpi_card(
            f"Promedio Materias ({bim})" if bim != "N/A" else "Promedio Materias",
            val_prom,
            sub_prom,
            estado="ok" if val_prom != "Sin datos" else "warning"
        )

    render_asistencia_section(sede_actual, mostrar_uploader=True)
    render_cycle_comparison(df_ast, df_aca, df_ast_prev, df_aca_prev, sede_actual=sede_actual)
# ==============================

with tab2:
    render_academico_section(sede_actual)

with tab3:
    st.markdown("### Mapa de Calor - Indicador de Clima Escolar (ICE)")
    if not render_campus_dynamic_view("clima", sede_actual):
        st.altair_chart(chart_clima_heatmap(df_clima), use_container_width=True)
        st.markdown("### Distribución de Respuestas")
        st.altair_chart(chart_clima_barras(df_clima), use_container_width=True)
        st.info("**Lectura ejecutiva:** El clima escolar es mayoritariamente positivo. Se recomienda monitorear estrés acumulado.")

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
    st.markdown("### Acompañamiento Docente y Plataformas Digitales")
    render_adopcion_y_correlacion(sede_actual)
    st.markdown("---")
    render_ixl_section(sede_actual)


# Footer
render_footer()