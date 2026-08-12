# app.py

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
from ui.components.kpi_cards import kpi_card
from ui.sections.sidebar import render_sidebar
from ui.sections.footer import render_footer
from ui.charts.bar_chart import chart_dominio_academico
from ui.charts.apps_charts import chart_comparativa_apps, chart_correlacion_practica
from ui.components.cycle_comparison import render_cycle_comparison
from src.logic.data_loader import (
    load_global_data, 
    load_apps_data, 
    load_academico_bloques, 
    load_clima_heatmap, 
    load_disciplina_data,
    get_recent_audit_logs,
    procesar_archivo_subido
)
from ui.charts.nuevos_graficos import chart_academico_bloques, chart_clima_heatmap, chart_clima_barras
from ui.components.data_uploader import render_global_uploader
from ui.components.asistencia_seccion import render_asistencia_section

# ======================================================
# 1. CONFIGURACIÓN Y ESTILOS
# ======================================================
st.set_page_config(
    page_title="Everwise | Dashboard Global",
    page_icon="assets/letra_blue.png",
    layout="wide"
)

try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

from src.logic.auth import require_login
require_login("General")

# ======================================================
# 2. LÓGICA DE DATOS
# ======================================================
from src.logic.data_loader import init_session_state
init_session_state()

df_asistencia, df_academico, df_asistencia_prev, df_academico_prev = load_global_data()
df_apps_kpis, df_correlacion = load_apps_data()
df_acad_hist = load_academico_bloques()
df_clima = load_clima_heatmap()

# Integrar datos reales de session_state si existen
df_clima_global_agg = st.session_state.get("clima_data_global", df_clima)
df_casos, df_cartas = load_disciplina_data()
df_casos = st.session_state.get("disciplina_casos", df_casos)
df_cartas = st.session_state.get("disciplina_cartas", df_cartas)

df_apps_kpis_global = st.session_state.get("practica_apps_kpis", df_apps_kpis)
df_correlacion = st.session_state.get("practica_correlacion", df_correlacion)

# ======================================================
# 3. SIDEBAR (NAVEGACIÓN Y CONFIGURACIÓN)
# ======================================================

ciclo_seleccionado = render_sidebar(sede_name=None)

# ======================================================
# 4. CONTENIDO PRINCIPAL
# ======================================================

# Header
st.markdown(f"""
    <div class="header-container">
        <div class="dashboard-title">Resumen Data 2025 · 2026 </div>
        <div class="dashboard-subtitle">Estado académico y operativo consolidado por campus</div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Resumen Ejecutivo", 
    "Desempeño Académico", 
    "Clima Escolar", 
    "Disciplina", 
    "Práctica Docente",
    "Auditoría y Bitácora CRM"
])

with tab1:
    # KPIs Ejecutivos
    st.markdown("### KPIs ejecutivos · Global")
    k1, k2, k3 = st.columns(3, gap="medium")
    
    # Dinámica de métricas académicas (Mates y Español) con control de errores
    try:
        if 'Bloque' in df_acad_hist.columns and not df_acad_hist.empty:
            bloques_ordenados = sorted(
                df_acad_hist['Bloque'].unique(),
                key=lambda b: int(str(b)[1:]) if str(b).startswith('B') and str(b)[1:].isdigit() else 99
            )
            b_actual = bloques_ordenados[-1] if bloques_ordenados else "B1"
            b_previo = bloques_ordenados[-2] if len(bloques_ordenados) > 1 else b_actual
            
            math_actual_series = df_acad_hist[df_acad_hist['Bloque'] == b_actual]['Matemáticas'].dropna()
            math_previo_series = df_acad_hist[df_acad_hist['Bloque'] == b_previo]['Matemáticas'].dropna()
            math_actual = math_actual_series.mean() if not math_actual_series.empty else 0.0
            math_previo = math_previo_series.mean() if not math_previo_series.empty else 0.0
            math_delta = (math_actual - math_previo) * 100
            
            esp_actual_series = df_acad_hist[df_acad_hist['Bloque'] == b_actual]['Español'].dropna()
            esp_previo_series = df_acad_hist[df_acad_hist['Bloque'] == b_previo]['Español'].dropna()
            esp_actual = esp_actual_series.mean() if not esp_actual_series.empty else 0.0
            esp_previo = esp_previo_series.mean() if not esp_previo_series.empty else 0.0
            esp_delta = (esp_actual - esp_previo) * 100
        else:
            b_actual, b_previo = "N/A", "N/A"
            math_actual, math_delta = 0.0, 0.0
            esp_actual, esp_delta = 0.0, 0.0
    except Exception as e:
        b_actual, b_previo = "N/A", "N/A"
        math_actual, math_delta = 0.0, 0.0
        esp_actual, esp_delta = 0.0, 0.0
        st.warning(f"Error calculando métricas académicas globales: {e}")
    
    with k1: kpi_card("Asistencia Promedio", "88%", "+2% vs mes anterior", estado="ok")
    with k2: kpi_card(f"Matemáticas ({b_actual})", f"{math_actual*100:.1f}%", f"{math_delta:+.1f}% vs {b_previo}", estado="ok" if math_delta >= 0 else "warning")
    with k3: kpi_card(f"Español ({b_actual})", f"{esp_actual*100:.1f}%", f"{esp_delta:+.1f}% vs {b_previo}", estado="ok" if esp_delta >= 0 else "warning")
    
    # AGREGACIÓN TOP-DOWN INVERSA (Consolidando los motores de inteligencia de Campus)
    campus_keys = ["Misiones", "Nuevo Sur", "San Agustín"]
    niveles_agg = []
    staff_agg = []
    campus_faltantes = []
    
    for c in campus_keys:
        state_key = f"asistencia_data_{c}"
        if state_key in st.session_state:
            try:
                data = st.session_state[state_key]
                if isinstance(data, dict) and "niveles" in data and not data["niveles"].empty:
                    campus_mean_series = data["niveles"]["Asistencia"].dropna()
                    campus_mean = campus_mean_series.mean() if not campus_mean_series.empty else 0.0
                    if pd.isna(campus_mean):
                        campus_mean = 0.0
                    niveles_agg.append({"Nivel": c, "Asistencia": campus_mean})
                    
                    staff_val = data.get("staff", 0.0)
                    staff_agg.append(staff_val if pd.notna(staff_val) else 0.0)
                else:
                    campus_faltantes.append(c)
            except Exception:
                campus_faltantes.append(c)
        else:
            campus_faltantes.append(c)
            
    if campus_faltantes:
        st.caption(f"Asistencia usando estimación previa para: {', '.join(campus_faltantes)}")
        
    real_global = None
    if niveles_agg:
        try:
            df_niveles_global = pd.DataFrame(niveles_agg)
            # Recalcular Pastel distribuido por Campus
            total_suma = df_niveles_global['Asistencia'].sum()
            df_niveles_global['Distribución'] = df_niveles_global['Asistencia'] / total_suma if total_suma > 0 else 0
            staff_global = sum(staff_agg) / len(staff_agg) if staff_agg else 0.0
            
            real_global = {"niveles": df_niveles_global, "staff": staff_global}
        except Exception as e:
            st.error(f"Error procesando agregación global de asistencia: {e}")
        
    render_asistencia_section("Global", real_global, mostrar_uploader=True)
    
    if real_global is not None:
        # Inyectando data real al motor comparativo
        df_asistencia = real_global["niveles"].rename(columns={"Nivel": "campus", "Asistencia": "asistencia"})
        df_asistencia['staff_asistencia'] = real_global["staff"]
        
    # Análisis Histórico
    render_cycle_comparison(df_asistencia, df_academico, df_asistencia_prev, df_academico_prev, "Global")

with tab2:
    st.markdown("### Seguimiento Académico y Trazabilidad")
    if not render_global_uploader("acad", "Desempeño Académico"):
        st.caption("Comparativa de avance por bloques académicos recientes.")
        st.altair_chart(chart_academico_bloques(df_acad_hist), use_container_width=True)
        st.info("**Aviso:** El seguimiento desde el Bloque 1 hasta el Bloque 5 evidencia la consolidación del dominio en asignaturas críticas.")

with tab3:
    st.markdown("### Mapa de Calor - Indicador de Clima Escolar (ICE)")
    if not render_global_uploader("clima", "Clima Escolar"):
        st.altair_chart(chart_clima_heatmap(df_clima_global_agg), use_container_width=True)
        st.markdown("### Distribución de Respuestas")
        st.altair_chart(chart_clima_barras(df_clima_global_agg), use_container_width=True)
        st.info("El mapa de calor representa áreas de riesgo si se detectan concentraciones altas en variables como 'Estrés Acumulado - Siempre'.")

with tab4:
    st.markdown("### Panel de Control de Disciplina e Inclusión")
    if not render_global_uploader("disc", "Disciplina e Inclusión"):
        cd1, cd2 = st.columns(2)
        with cd1:
            st.markdown("**Radar de Casos Especiales (Activos)**")
            st.dataframe(df_casos, hide_index=True, use_container_width=True)
        with cd2:
            st.markdown("**Alertas por Cartas Compromiso**")
            st.dataframe(df_cartas, hide_index=True, use_container_width=True)

with tab5:
    st.markdown("### Herramientas y Acompañamiento Docente")
    if not render_global_uploader("prac", "Práctica Docente"):
        st.markdown("### Uso de Aplicaciones: IXL vs Progrentis")
        colr1, colr2 = st.columns(2, gap="large")
        
        with colr1:
            st.markdown("**Métricas de Adopción**")
            st.altair_chart(chart_comparativa_apps(df_apps_kpis_global), use_container_width=True)
            st.caption("Cumplimiento porcentual general.")
        
        with colr2:
            st.markdown("**Relación Académica: Práctica vs Resultados (Dominio)**")
            st.altair_chart(chart_correlacion_practica(df_correlacion), use_container_width=True)

with tab6:
    st.markdown("### Bitácora de Auditoría y Trazabilidad CRM")
    st.caption("Registro inmutable de acciones, cargas de archivos y modificaciones realizadas por usuarios.")
    
    df_audit = get_recent_audit_logs(limit=100)
    
    if not df_audit.empty:
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1.5])
        with col_f1:
            usuarios_unicos = ["Todos"] + sorted(list(df_audit["Usuario"].dropna().unique()))
            u_sel = st.selectbox("Filtrar por Usuario", usuarios_unicos, key="audit_u_sel")
        with col_f2:
            acciones_unicas = ["Todas"] + sorted(list(df_audit["Acción"].dropna().unique()))
            a_sel = st.selectbox("Filtrar por Acción", acciones_unicas, key="audit_a_sel")
        with col_f3:
            st.write("")
            csv_data = df_audit.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Exportar Log CSV",
                data=csv_data,
                file_name="everwise_audit_log.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        df_audit_view = df_audit.copy()
        if u_sel != "Todos":
            df_audit_view = df_audit_view[df_audit_view["Usuario"] == u_sel]
        if a_sel != "Todas":
            df_audit_view = df_audit_view[df_audit_view["Acción"] == a_sel]
            
        st.dataframe(df_audit_view, hide_index=True, use_container_width=True)
    else:
        st.info("No hay eventos registrados en la bitácora aún.")

# Footer
render_footer(ciclo_seleccionado)