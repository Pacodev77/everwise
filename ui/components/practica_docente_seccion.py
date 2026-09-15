# ui/components/practica_docente_seccion.py

# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
import altair as alt
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

from ui.components.kpi_cards import kpi_card
from src.logic.practica_docente_processor import (
    RUBRICAS_METADATA,
    NIVELES_DESEMPENO_CONFIG,
    generar_datos_semilla_practica,
    procesar_archivo_practica,
    calcular_metricas_ejecutivas_practica
)

def eliminar_datos_practica_docente(sede_target: str):
    """Elimina los datos de evaluación docente de SQLite y session_state para el campus indicado."""
    if not sede_target:
        return

    from src.logic.data_loader import get_db_connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_docente_data'")
        if cursor.fetchone():
            if sede_target == "Global":
                cursor.execute("DELETE FROM practica_docente_data")
            else:
                cursor.execute("DELETE FROM practica_docente_data WHERE campus = ?", (sede_target,))
            conn.commit()
        conn.close()
    except Exception:
        pass

    slug = sede_target.lower().replace(' ', '_')
    keys_del = [f"practica_docente_{sede_target}", f"last_up_practica_{slug}"]
    for k in keys_del:
        if k in st.session_state:
            del st.session_state[k]

    if "cycle_vault" in st.session_state:
        for cycle in st.session_state["cycle_vault"]:
            for k in keys_del:
                if k in st.session_state["cycle_vault"][cycle]:
                    del st.session_state["cycle_vault"][cycle][k]

    st.cache_data.clear()

def render_practica_docente_section(sede_actual: str):
    """
    Renderiza el tablero ejecutivo de Práctica Docente y Rúbricas Pedagógicas.
    """
    st.markdown(f"### Práctica Docente — {sede_actual}")
    st.caption("Evaluación ejecutiva de competencias pedagógicas, rúbricas de desempeño docente y acompañamiento en aula.")

    ciclo_activo = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    clave_state = f"practica_docente_{sede_actual}"

    # Carga desde SQLite / Session State / Semilla Canónica para el ciclo activo
    if clave_state not in st.session_state:
        dfs_to_concat = []
        from src.logic.data_loader import get_db_connection
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_docente_data'")
            if cursor.fetchone():
                if sede_actual == "Global":
                    query = "SELECT * FROM practica_docente_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')"
                    params = (ciclo_activo, ciclo_activo)
                else:
                    query = "SELECT * FROM practica_docente_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))"
                    params = (sede_actual, ciclo_activo, ciclo_activo)
                df_db = pd.read_sql(query, conn, params=params)
                if not df_db.empty:
                    dfs_to_concat.append(df_db)
            conn.close()
        except Exception:
            pass

        if not dfs_to_concat and ciclo_activo == "2025 - 2026":
            campuses_to_gen = ["Misiones", "Nuevo Sur", "San Agustín"] if sede_actual == "Global" else [sede_actual]
            for c in campuses_to_gen:
                dfs_to_concat.append(generar_datos_semilla_practica(c))

        if dfs_to_concat:
            df_combined = pd.concat(dfs_to_concat, ignore_index=True)
            if "docente" in df_combined.columns and "campus" in df_combined.columns:
                df_combined = df_combined.drop_duplicates(subset=["campus", "docente"], keep="last")
            st.session_state[clave_state] = df_combined

    df_docentes = st.session_state.get(clave_state, pd.DataFrame()).copy()
    if not df_docentes.empty and "materia" in df_docentes.columns:
        df_docentes["materia"] = df_docentes["materia"].replace({"General": "Español"})
        st.session_state[clave_state] = df_docentes

    metrics = calcular_metricas_ejecutivas_practica(df_docentes)

    if df_docentes.empty or not metrics:
        st.info(f"No se encontraron evaluaciones de práctica docente registradas para el Ciclo Escolar {ciclo_activo} en {sede_actual}.")
        return

    tab_eval, tab_bitacora, tab_gestion = st.tabs([
        "Tablero Ejecutivo de Rúbricas",
        "Bitácora de Observaciones de Aula",
        "Carga y Gestión de Datos"
    ])

    # ==========================================
    # TAB 1: TABLERO EJECUTIVO DE RÚBRICAS
    # ==========================================
    with tab_eval:
        igpd_val = metrics["igpd_promedio"]
        total_eval = metrics["total_evaluados"]
        pct_dest = metrics["pct_destacado_avanzado"]
        dim_pri = metrics["dimension_prioritaria"]
        score_pri = metrics["score_prioritaria"]

        # 1. KPI Cards Row
        k1, k2, k3, k4 = st.columns(4, gap="medium")
        with k1:
            kpi_card(
                titulo="ÍNDICE GLOBAL PRÁCTICA (IGPD)",
                valor=f"{igpd_val:.2f} / 5.0",
                delta=f"Equivalente al {metrics['igpd_pct']:.1f}% · Nivel " + ("Óptimo" if igpd_val >= 4.2 else "Aceptable"),
                estado="ok" if igpd_val >= 4.2 else "warning"
            )
        with k2:
            kpi_card(
                titulo="DOCENTES EVALUADOS",
                valor=f"{total_eval}",
                delta="Cobertura del 100% de la plantilla",
                estado="info"
            )
        with k3:
            kpi_card(
                titulo="DESEMPENO DESTACADO / AVANZADO",
                valor=f"{pct_dest:.1f}%",
                delta=f"Criterio: IGPD ≥ 4.0 / 5.0",
                estado="ok" if pct_dest >= 70.0 else "warning"
            )
        with k4:
            kpi_card(
                titulo="DIMENSIÓN PRIORITARIA",
                valor=f"{score_pri:.2f}",
                delta=f"Oportunidad: {dim_pri[:25]}...",
                estado="warning" if score_pri < 4.2 else "ok"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns([1.6, 1], gap="large")

        with col_g1:
            st.markdown("#### Promedio Evaluado por Dimensión de Rúbrica Pedagógica")
            st.caption("Puntaje medio obtenido en escala de 1.0 a 5.0 vs Meta Institucional (4.5).")

            df_rub_sum = metrics["rubricas_summary"].copy()
            df_rub_sum["color_hex"] = df_rub_sum["promedio"].apply(
                lambda p: "#10b981" if p >= 4.4 else ("#3b82f6" if p >= 4.0 else "#f59e0b")
            )
            
            chart_rub = alt.Chart(df_rub_sum).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, height=24).encode(
                x=alt.X("promedio:Q", title="Puntaje Promedio (1.0 - 5.0)", scale=alt.Scale(domain=[0, 5.0]), axis=alt.Axis(grid=True, gridDash=[3,3])),
                y=alt.Y("nombre:N", title=None, sort="-x", axis=alt.Axis(labelFontSize=11, labelFontWeight="bold")),
                color=alt.Color("color_hex:N", scale=None),
                tooltip=[
                    alt.Tooltip("codigo:N", title="Código"),
                    alt.Tooltip("nombre:N", title="Rúbrica"),
                    alt.Tooltip("promedio:Q", format=".2f", title="Promedio Evaluado"),
                    alt.Tooltip("meta:Q", format=".2f", title="Meta Institucional"),
                    alt.Tooltip("cumplimiento_pct:Q", format=".1f", title="% Cumplimiento Meta")
                ]
            ).properties(height=240)

            rule_meta = alt.Chart(pd.DataFrame([{"meta": 4.5}])).mark_rule(color="#ef4444", strokeDash=[4, 4], strokeWidth=2).encode(x="meta:Q")
            st.altair_chart((chart_rub + rule_meta).configure_view(stroke="transparent"), use_container_width=True)

        with col_g2:
            st.markdown("#### Distribución de Niveles de Desempeño")
            st.caption("Porcentaje de docentes según categoría de logro.")

            dist_tiers = metrics["distribucion_tiers"]
            df_dist = pd.DataFrame([
                {"Nivel": k, "Cantidad": dist_tiers.get(k, 0), "Color": NIVELES_DESEMPENO_CONFIG[k]["color"]}
                for k in ["Destacado", "Avanzado", "Competente", "En Desarrollo"]
            ])
            df_dist["Porcentaje"] = (df_dist["Cantidad"] / total_eval) * 100.0 if total_eval > 0 else 0.0

            chart_donut = alt.Chart(df_dist).mark_arc(innerRadius=42, outerRadius=72).encode(
                theta=alt.Theta("Cantidad:Q"),
                color=alt.Color("Nivel:N", scale=alt.Scale(
                    domain=["Destacado", "Avanzado", "Competente", "En Desarrollo"],
                    range=["#10b981", "#3b82f6", "#f59e0b", "#ef4444"]
                ), legend=alt.Legend(orient="bottom", title=None, labelFontSize=11)),
                tooltip=[alt.Tooltip("Nivel:N"), alt.Tooltip("Cantidad:Q"), alt.Tooltip("Porcentaje:Q", format=".1f", title="% Plantilla")]
            ).properties(height=240).configure_view(stroke="transparent")

            st.altair_chart(chart_donut, use_container_width=True)

        # 2. Desglose por Nivel Escolar o Campus
        st.markdown("---")
        col_sub1, col_sub2 = st.columns(2, gap="large")

        with col_sub1:
            st.markdown("#### Desempeño Docente por Nivel Escolar")
            df_niv = metrics["desglose_nivel"].copy()
            if not df_niv.empty:
                chart_niv = alt.Chart(df_niv).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=35).encode(
                    x=alt.X("nivel:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight="bold")),
                    y=alt.Y("igpd_promedios:Q", title="IGPD Promedio", scale=alt.Scale(domain=[0, 5.0])),
                    color=alt.value("#6366f1"),
                    tooltip=[alt.Tooltip("nivel:N", title="Nivel"), alt.Tooltip("docentes:Q", title="Docentes"), alt.Tooltip("igpd_promedios:Q", format=".2f", title="IGPD Promedio")]
                ).properties(height=220).configure_view(stroke="transparent")
                st.altair_chart(chart_niv, use_container_width=True)

        with col_sub2:
            if sede_actual == "Global" and "campus" in df_docentes.columns:
                st.markdown("#### Comparativa de IGPD por Campus Corporativo")
                df_camp_agg = df_docentes.groupby("campus").agg(
                    docentes=("docente", "count"),
                    igpd=("score_global", "mean")
                ).reset_index().round(2)

                chart_camp = alt.Chart(df_camp_agg).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=35).encode(
                    x=alt.X("campus:N", title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight="bold")),
                    y=alt.Y("igpd:Q", title="IGPD Promedio", scale=alt.Scale(domain=[0, 5.0])),
                    color=alt.value("#10b981"),
                    tooltip=[alt.Tooltip("campus:N", title="Campus"), alt.Tooltip("docentes:Q", title="Docentes Evaluados"), alt.Tooltip("igpd:Q", format=".2f", title="IGPD")]
                ).properties(height=220).configure_view(stroke="transparent")
                st.altair_chart(chart_camp, use_container_width=True)
            else:
                st.markdown("#### Distribución de Materias Evaluadas")
                df_mat_clean = df_docentes[df_docentes["materia"] != "General"].copy()
                df_mat = df_mat_clean.groupby("materia").agg(
                    docentes=("docente", "count"),
                    igpd=("score_global", "mean")
                ).reset_index().round(2)

                chart_mat = alt.Chart(df_mat).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=35).encode(
                    x=alt.X("materia:N", title=None, sort=["Español", "Language Arts", "Matemáticas"], axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight="bold")),
                    y=alt.Y("igpd:Q", title="IGPD Promedio", scale=alt.Scale(domain=[0, 5.0])),
                    color=alt.value("#3b82f6"),
                    tooltip=[alt.Tooltip("materia:N", title="Materia"), alt.Tooltip("docentes:Q", title="Docentes"), alt.Tooltip("igpd:Q", format=".2f", title="IGPD")]
                ).properties(height=220).configure_view(stroke="transparent")
                st.altair_chart(chart_mat, use_container_width=True)

    # ==========================================
    # TAB 2: BITÁCORA DE OBSERVACIONES DE AULA
    # ==========================================
    with tab_bitacora:
        st.markdown("#### Bitácora Digital de Acompañamiento y Observación Docente")
        st.caption("Registro ejecutivo de evaluaciones, observadores académicos y recomendaciones pedagógicas en aula.")

        f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 1.5])
        with f_col1:
            niveles_opt = ["Todos"] + sorted(list(df_docentes["nivel"].dropna().unique()))
            sel_nivel = st.selectbox("Filtrar por Nivel", niveles_opt, key=f"f_niv_{sede_actual.lower().replace(' ', '_')}")
        with f_col2:
            tiers_opt = ["Todos", "Destacado", "Avanzado", "Competente", "En Desarrollo"]
            sel_tier = st.selectbox("Filtrar por Desempeño", tiers_opt, key=f"f_tier_{sede_actual.lower().replace(' ', '_')}")
        with f_col3:
            st.write("")
            csv_data = df_docentes.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Exportar Bitácora CSV",
                data=csv_data,
                file_name=f"everwise_practica_docente_{sede_actual.lower().replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        df_view = df_docentes.copy()
        if sel_nivel != "Todos":
            df_view = df_view[df_view["nivel"] == sel_nivel]
        if sel_tier != "Todos":
            df_view = df_view[df_view["nivel_desempeno"] == sel_tier]

        # Renombrar columnas para visualización clara
        rename_dict = {
            "campus": "Campus",
            "docente": "Docente Evaluado",
            "nivel": "Nivel",
            "materia": "Materia",
            "score_global": "IGPD (1-5)",
            "nivel_desempeno": "Categoría",
            "R1_planificacion": "R1 Planif.",
            "R2_clima": "R2 Clima",
            "R3_estrategias": "R3 Estrateg.",
            "R4_evaluacion": "R4 Eval.",
            "R5_digital": "R5 Digital",
            "R6_diferenciacion": "R6 Inclusión",
            "fecha_observacion": "Fecha Obs.",
            "observador": "Observador Académico",
            "recomendacion": "Recomendación Pedagógica"
        }

        cols_display = [c for c in [
            "campus", "docente", "nivel", "materia", "score_global", "nivel_desempeno",
            "R1_planificacion", "R2_clima", "R3_estrategias", "R4_evaluacion", "R5_digital", "R6_diferenciacion",
            "fecha_observacion", "observador", "recomendacion"
        ] if c in df_view.columns]

        df_table = df_view[cols_display].rename(columns=rename_dict)
        st.dataframe(df_table, hide_index=True, use_container_width=True)

    # ==========================================
    # TAB 3: CARGA Y GESTIÓN DE DATOS
    # ==========================================
    with tab_gestion:
        st.markdown("#### Carga de Evaluaciones y Gestión de Datos de Práctica Docente")
        st.caption("Sube un archivo de observaciones docentes (Excel o CSV) para integrar nuevos registros de rúbricas al sistema.")

        col_up, col_del = st.columns([3, 1])
        with col_up:
            uploaded_file = st.file_uploader(
                f"Cargar reporte de Práctica Docente (Excel/CSV) — {sede_actual}",
                type=["xlsx", "xls", "csv"],
                key=f"up_practica_{sede_actual.lower().replace(' ', '_')}"
            )
        with col_del:
            st.write("")
            st.write("")
            if st.button(f"Eliminar archivo ({sede_actual})", key=f"btn_del_practica_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
                eliminar_datos_practica_docente(sede_actual)
                st.rerun()

        if uploaded_file is not None:
            file_state_key = f"last_up_practica_{sede_actual.lower().replace(' ', '_')}"
            if st.session_state.get(file_state_key) != uploaded_file.name:
                res_proc = procesar_archivo_practica(uploaded_file, target_campus=sede_actual)
                if res_proc.get("error"):
                    st.error(res_proc["error"])
                else:
                    df_new = res_proc["df_raw"]
                    from src.logic.data_loader import save_practica_docente_data
                    save_practica_docente_data(sede_actual, df_new)
                    st.session_state[clave_state] = df_new
                    st.session_state[file_state_key] = uploaded_file.name
                    st.success(f"¡Evaluaciones docentes cargadas exitosamente! ({len(df_new)} docentes procesados)")
                    st.cache_data.clear()
                    st.rerun()

        st.markdown("""
            <div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; margin-top: 1.5rem; font-size: 0.85rem; color: #475569;'>
                <strong>Estructura esperada del archivo Excel/CSV:</strong><br>
                • <code>Docente</code> (obligatorio): Nombre del profesor.<br>
                • <code>Campus</code>: Misiones, Nuevo Sur o San Agustín.<br>
                • <code>Nivel</code> / <code>Materia</code>: Preescolar, Primaria, Secundaria / Matemáticas, Español, etc.<br>
                • Columnas de Rúbricas (escala 1.0 a 5.0): <code>R1_planificacion</code>, <code>R2_clima</code>, <code>R3_estrategias</code>, <code>R4_evaluacion</code>, <code>R5_digital</code>, <code>R6_diferenciacion</code>.
            </div>
        """, unsafe_allow_html=True)
