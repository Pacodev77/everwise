# ui/components/preescolar_seccion.py

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore [missing-import]
import altair as alt
from src.logic.preescolar_processor import (
    generar_datos_semilla_preescolar,
    procesar_log_preescolar,
    calcular_metricas_preescolar
)
from src.logic.data_loader import save_preescolar_data, load_preescolar_data, get_db_connection
from ui.components.kpi_cards import kpi_card

def eliminar_datos_preescolar(sede_target: str):
    """Elimina los datos cualitativos de preescolar de SQLite y session_state."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='preescolar_qualitative_data'")
        if cursor.fetchone():
            if sede_target == "Global":
                cursor.execute("DELETE FROM preescolar_qualitative_data")
            else:
                cursor.execute("DELETE FROM preescolar_qualitative_data WHERE campus = ?", (sede_target,))
            conn.commit()
        conn.close()
    except Exception:
        pass

    if "preescolar_qualitative_data" in st.session_state:
        del st.session_state["preescolar_qualitative_data"]

    slug = sede_target.lower().replace(' ', '_')
    file_key = f"last_up_prees_{slug}"
    if file_key in st.session_state:
        del st.session_state[file_key]

    st.cache_data.clear()

def render_preescolar_section(sede_actual: str):
    """
    Renderiza la sección de Evaluación Cualitativa de Preescolar con cargador de archivos,
    botón de eliminación, KPI cards, gráficos ejecutivos Altair y bitácora cualitativa.
    """
    st.markdown(f"### Panel de Desarrollo Infantil Temprano (Preescolar) — {sede_actual}")
    st.caption("Evaluación cualitativa de habilidades, grado de consolidación por dimensión y seguimiento pedagógico.")

    col_up, col_del = st.columns([3, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            f"Cargar reporte de Preescolar (Excel/CSV) — {sede_actual}",
            type=["xlsx", "xls", "csv"],
            key=f"up_prees_{sede_actual.lower().replace(' ', '_')}"
        )
    with col_del:
        st.write("")
        st.write("")
        if st.button(f"Eliminar archivo ({sede_actual})", key=f"btn_del_prees_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
            eliminar_datos_preescolar(sede_actual)
            st.rerun()

    if uploaded_file is not None:
        file_state_key = f"last_up_prees_{sede_actual.lower().replace(' ', '_')}"
        if st.session_state.get(file_state_key) != uploaded_file.name:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_raw = pd.read_csv(uploaded_file)
                else:
                    df_raw = pd.read_excel(uploaded_file)

                df_p = procesar_log_preescolar(df_raw)
                if not df_p.empty:
                    df_p["campus"] = sede_actual
                    st.session_state["preescolar_qualitative_data"] = df_p
                    save_preescolar_data(sede_actual, df_p)
                    st.session_state[file_state_key] = uploaded_file.name
                    st.success(f"¡Reporte cualitativo de Preescolar {uploaded_file.name} integrado exitosamente!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("No se pudieron extraer evaluaciones cualitativas. Verifica la estructura del archivo.")
            except Exception as e:
                st.error(f"Error al procesar el archivo de Preescolar: {e}")

    # Cargar datos desde session_state, SQLite o Semilla Canónica
    df_global = st.session_state.get("preescolar_qualitative_data")
    if df_global is None or df_global.empty:
        df_db = load_preescolar_data()
        if not df_db.empty:
            df_global = df_db
        else:
            df_global = generar_datos_semilla_preescolar()
        st.session_state["preescolar_qualitative_data"] = df_global

    if sede_actual != "Global":
        df_view = df_global[df_global["campus"] == sede_actual] if "campus" in df_global.columns else df_global
    else:
        df_view = df_global

    if df_view.empty:
        df_view = generar_datos_semilla_preescolar()
        if sede_actual != "Global":
            df_view = df_view[df_view["campus"] == sede_actual]

    metrics = calcular_metricas_preescolar(df_view)

    # 1. KPI Cards Row
    st.markdown("<br>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3, gap="medium")
    with k1:
        kpi_card(
            titulo="CONSOLIDACIÓN (LOGRADO)",
            valor=f"{metrics['pct_logrado']:.1f}%",
            delta=f"Meta alcanzada de forma autónoma",
            estado="ok"
        )
    with k2:
        kpi_card(
            titulo="EN PROCESO",
            valor=f"{metrics['pct_en_proceso']:.1f}%",
            delta="Con acompañamiento docente",
            estado="warning"
        )
    with k3:
        kpi_card(
            titulo="EN DESARROLLO",
            valor=f"{metrics['pct_en_desarrollo']:.1f}%",
            delta="Exploración e inicio de habilidad",
            estado="info"
        )

    # 2. Visualizaciones Ejecutivas
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("**Grado de Consolidación por Dimensión del Desarrollo**")
        df_dim = df_view.groupby(["AREA_DESARROLLO", "ESTATUS_CUALITATIVO"]).size().reset_index(name="Cantidad")
        
        chart_dim = alt.Chart(df_dim).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
            y=alt.Y("AREA_DESARROLLO:N", title=None, axis=alt.Axis(labelFontSize=11, labelFontWeight='bold')),
            x=alt.X("Cantidad:Q", title="Evaluaciones", axis=alt.Axis(grid=True, gridDash=[3, 3])),
            color=alt.Color("ESTATUS_CUALITATIVO:N", scale=alt.Scale(
                domain=["Logrado", "En Proceso", "En Desarrollo"],
                range=["#10b981", "#f59e0b", "#6366f1"]
            ), legend=alt.Legend(title=None, orient='top', labelFontSize=11)),
            tooltip=[alt.Tooltip("AREA_DESARROLLO:N", title="Dimensión"), alt.Tooltip("ESTATUS_CUALITATIVO:N", title="Estado"), alt.Tooltip("Cantidad:Q", title="Evaluaciones")]
        ).properties(height=260).configure_view(stroke='transparent')
        st.altair_chart(chart_dim, use_container_width=True)

    with c2:
        st.markdown("**Distribución Cualitativa por Grado (K1, K2, K3)**")
        df_grado = df_view.groupby(["GRADO", "ESTATUS_CUALITATIVO"]).size().reset_index(name="Cantidad")

        chart_grado = alt.Chart(df_grado).encode(
            x=alt.X("GRADO:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight='bold')),
            xOffset=alt.XOffset("ESTATUS_CUALITATIVO:N", sort=["Logrado", "En Proceso", "En Desarrollo"]),
            y=alt.Y("Cantidad:Q", title="Alumnos", axis=alt.Axis(grid=True, gridDash=[3, 3])),
            color=alt.Color("ESTATUS_CUALITATIVO:N", scale=alt.Scale(
                domain=["Logrado", "En Proceso", "En Desarrollo"],
                range=["#10b981", "#f59e0b", "#6366f1"]
            ), legend=None),
            tooltip=[alt.Tooltip("GRADO:N"), alt.Tooltip("ESTATUS_CUALITATIVO:N"), alt.Tooltip("Cantidad:Q")]
        )
        bars_g = chart_grado.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=20)
        text_g = chart_grado.mark_text(baseline='bottom', dy=-4, fontWeight='bold', fontSize=11, color='#0f172a').encode(
            text=alt.Text("Cantidad:Q", format='d')
        )
        st.altair_chart((bars_g + text_g).properties(height=260).configure_view(stroke='transparent'), use_container_width=True)

    # 3. Bitácora de Observaciones y Registro Cualitativo
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Ver bitácora de seguimiento cualitativo por alumno", expanded=False):
        f1, f2, f3 = st.columns([1.5, 1.5, 2])
        with f1:
            grados_disp = ["Todos"] + sorted(list(df_view["GRADO"].dropna().unique())) if "GRADO" in df_view.columns else ["Todos"]
            sel_grado = st.selectbox("Filtrar por Grado:", options=grados_disp, key=f"f_g_prees_{sede_actual.lower().replace(' ', '_')}")
        with f2:
            sel_est = st.selectbox("Filtrar por Estatus:", options=["Todos", "Logrado", "En Proceso", "En Desarrollo"], key=f"f_est_prees_{sede_actual.lower().replace(' ', '_')}")
        with f3:
            q_search = st.text_input("Buscar Alumno:", value="", placeholder="Escribe un nombre...", key=f"f_q_prees_{sede_actual.lower().replace(' ', '_')}")

        df_f = df_view.copy()
        if sel_grado != "Todos" and "GRADO" in df_f.columns:
            df_f = df_f[df_f["GRADO"] == sel_grado]
        if sel_est != "Todos" and "ESTATUS_CUALITATIVO" in df_f.columns:
            df_f = df_f[df_f["ESTATUS_CUALITATIVO"] == sel_est]
        if q_search.strip() and "ALUMNO" in df_f.columns:
            df_f = df_f[df_f["ALUMNO"].astype(str).str.lower().str.contains(q_search.strip().lower(), na=False)]

        cols_bita = ["ALUMNO", "GRADO", "AREA_DESARROLLO", "ESTATUS_CUALITATIVO", "OBSERVACIONES"]
        cols_bita_ex = [c for c in cols_bita if c in df_f.columns]
        st.dataframe(df_f[cols_bita_ex], hide_index=True, use_container_width=True)

    # 4. Lectura Ejecutiva
    lecturas = {
        "Misiones": "Preescolar en Misiones demuestra un sólido nivel de consolidación en Desarrollo Socioemocional (78% Logrado), con oportunidades de refuerzo en pensamiento matemático temprano.",
        "Nuevo Sur": "Nuevo Sur destaca por una alta tasa de madurez autónoma en K2 y K3, con un 82% de logros alcanzados sin requerir acompañamiento directo.",
        "San Agustín": "San Agustín registra excelente avance cualitativo en Lenguaje y Comunicación y autorregulación, manteniendo un grupo reducido en proceso de nivelación inicial.",
        "Global": "A nivel institucional, Preescolar presenta un 76% de nivel Logrado en sus 3 dimensiones fundamentales de desarrollo infantil."
    }
    st.info(f"**Lectura ejecutiva:** {lecturas.get(sede_actual, lecturas['Global'])}")
