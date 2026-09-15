# ui/components/academico_seccion.py

# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
import altair as alt
import pandas as pd
from src.logic.academic_processor import (
    procesar_archivo_academico,
    acumular_bimestre,
    calcular_distribucion_desempeno,
    calcular_color_nivel,
    _categorizar_alumno,
)
from ui.components.kpi_cards import kpi_card

def render_academico_section(sede_actual: str):
    tab_ps, tab_pre = st.tabs(["Primaria y Secundaria (GPA %)", "Preescolar (Cualitativo)"])

    with tab_ps:
        clave_estado = f"academico_propio_{sede_actual}"

        st.markdown(f"#### Desempeño Académico — {sede_actual}")
        col_up, col_del = st.columns([3, 1])
        with col_up:
            uploaded = st.file_uploader(
                f"Archivo Excel — {sede_actual}",
                type=["xlsx", "xls"],
                key=f"up_acad_{sede_actual.lower().replace(' ', '_')}"
            )
        with col_del:
            st.write("")
            st.write("")
            if st.button(f"Eliminar archivo ({sede_actual})", key=f"btn_del_acad_top_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
                from src.logic.data_loader import delete_academic_data
                file_state_key = f"last_up_acad_{sede_actual.lower().replace(' ', '_')}"
                if file_state_key in st.session_state:
                    del st.session_state[file_state_key]
                if clave_estado in st.session_state:
                    del st.session_state[clave_estado]
                delete_academic_data(sede_actual)
                st.cache_data.clear()
                st.rerun()

        if uploaded is not None:
            file_state_key = f"last_up_acad_{sede_actual.lower().replace(' ', '_')}"
            if st.session_state.get(file_state_key) != uploaded.name:
                resultado = procesar_archivo_academico(uploaded, target_campus=sede_actual)
                if resultado.get("error"):
                    st.error(resultado["error"])
                    return False

                if resultado.get("campus") != "Desconocido" and resultado.get("campus") != sede_actual:
                    st.error(f"Acceso Bloqueado: El archivo corresponde a **{resultado.get('campus')}** y no a **{sede_actual}**. Sube el archivo en su sede correspondiente.")
                    return False

                clave_bim = f"academico_{sede_actual}_{resultado['bimestre']}"
                st.session_state[clave_bim] = resultado
                st.session_state[clave_estado] = resultado
                acumular_bimestre(sede_actual, resultado)
                st.session_state[file_state_key] = uploaded.name
                st.cache_data.clear()
                st.rerun()

            st.success(f"Archivo activo: {uploaded.name} · Bimestre {st.session_state[clave_estado]['bimestre']}")

        # ── Recopilar catálogo histórico de bimestres disponibles para este campus ──
        from src.logic.data_loader import get_academic_history_catalog, delete_academic_data
        ciclo_activo = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
        catalog = get_academic_history_catalog(ciclo_activo)
        bimestres_map = {}

        # 1. Desde SQLite
        if sede_actual in catalog:
            for b_name, b_data in catalog[sede_actual].items():
                bimestres_map[b_name] = b_data

        # 2. Desde session_state
        prefijo = f"academico_{sede_actual}_"
        for k, val in st.session_state.items():
            if k.startswith(prefijo) and isinstance(val, dict):
                b_name = val.get("bimestre")
                if b_name and b_name != "B?":
                    bimestres_map[b_name] = val

        if not bimestres_map and clave_estado not in st.session_state:
            st.info(f"Sube el archivo de calificaciones para el Ciclo Escolar {ciclo_activo} en {sede_actual} para ver el desempeño académico.")
        else:
            # Ordenar los bimestres numéricamente (B1, B2, B3, B4, B5...)
            def _sort_bim_key(b):
                s = str(b).upper().strip()
                if s.startswith('B') and s[1:].isdigit():
                    return int(s[1:])
                return 99

            opciones_bimestres = sorted(list(bimestres_map.keys()), key=_sort_bim_key)

            # Identificar el bimestre activo por defecto
            if clave_estado in st.session_state and st.session_state[clave_estado].get("bimestre") in opciones_bimestres:
                bim_activo_defecto = st.session_state[clave_estado]["bimestre"]
            elif opciones_bimestres:
                bim_activo_defecto = opciones_bimestres[-1]
            else:
                bim_activo_defecto = None

            # ── Barra de Navegación Histórica Permanente y Controles ──────────
            st.markdown("---")
            c_sel, c_info, c_del = st.columns([2, 2.5, 1.5])

            with c_sel:
                if opciones_bimestres:
                    idx_defecto = opciones_bimestres.index(bim_activo_defecto) if bim_activo_defecto in opciones_bimestres else 0
                    bimestre_seleccionado = st.selectbox(
                        "Periodo / Bimestre Histórico:",
                        options=opciones_bimestres,
                        index=idx_defecto,
                        key=f"sel_bim_{sede_actual.lower().replace(' ', '_')}"
                    )
                    res = bimestres_map[bimestre_seleccionado]
                    st.session_state[clave_estado] = res
                elif clave_estado in st.session_state:
                    res = st.session_state[clave_estado]
                    bimestre_seleccionado = res.get("bimestre", "B?")
                else:
                    res = None

            if res is not None:
                with c_info:
                    st.write("") # spacer
                    st.caption(f"Visualizando: **{sede_actual} · Bimestre {res['bimestre']}** ({res.get('total_alumnos', 0)} alumnos)")

                with c_del:
                    st.write("") # spacer
                    if st.button("Eliminar periodo", key=f"del_acad_{sede_actual.lower().replace(' ', '_')}", use_container_width=True):
                        bim_a_borrar = res.get("bimestre")
                        delete_academic_data(sede_actual, bim_a_borrar)
                        
                        # Limpiar clave de sesión
                        clave_del = f"academico_{sede_actual}_{bim_a_borrar}"
                        if clave_del in st.session_state:
                            del st.session_state[clave_del]
                        if clave_estado in st.session_state and st.session_state[clave_estado].get("bimestre") == bim_a_borrar:
                            del st.session_state[clave_estado]
                            
                        clave_hist = f"historial_bimestres_{sede_actual}"
                        if clave_hist in st.session_state and isinstance(st.session_state[clave_hist], dict):
                            st.session_state[clave_hist].pop(bim_a_borrar, None)
                            
                        st.cache_data.clear()
                        st.rerun()

                # ── Selector manual de emergencia solo si el bimestre no se detectó ─────
                if res.get("bimestre") == "B?":
                    bimestre_input = st.selectbox(
                        "No se detectó el bimestre en el nombre del archivo. ¿A cuál corresponde?",
                        options=["B1", "B2", "B3", "B4", "B5"],
                        key=f"bim_manual_{sede_actual}"
                    )
                    st.session_state[clave_estado]["bimestre"] = bimestre_input
                    acumular_bimestre(sede_actual, st.session_state[clave_estado])

                df_des   = res["desempeno"]
                df_prom  = res["promedios"]
                bimestre = res["bimestre"]

                # ── KPIs rápidos ─────────────────────────────────────────────────
                total = res["total_alumnos"]
                suma_desempeno = df_des["en_desempeno"].sum() if "en_desempeno" in df_des.columns else 0
                suma_total = df_des["total"].sum() if "total" in df_des.columns else 0
                
                pct_global = round((suma_desempeno / suma_total * 100), 1) if suma_total > 0 else 0.0
                df_des = df_des.copy()
                if "pct_desempeno" in df_des.columns:
                    df_des["Color"] = df_des["pct_desempeno"].apply(calcular_color_nivel)

                k1, k2, k3 = st.columns(3, gap="medium")
                with k1:
                    kpi_card(
                        titulo="TOTAL ALUMNOS",
                        valor=f"{total}",
                        delta=f"Matrícula evaluada en Bimestre {bimestre}",
                        estado="info"
                    )
                with k2:
                    estado_tasa = "ok" if pct_global >= 80.0 else ("warning" if pct_global >= 60.0 else "risk")
                    kpi_card(
                        titulo="TASA DE ALUMNOS EN NIVEL ÓPTIMO",
                        valor=f"{pct_global:.1f}%",
                        delta=f"↑ Bimestre {bimestre} (≥8.0 en todas)",
                        estado=estado_tasa
                    )
                with k3:
                    if not df_des.empty and "pct_desempeno" in df_des.columns and "Nivel" in df_des.columns:
                        mejor_nivel = df_des.loc[df_des["pct_desempeno"].idxmax(), "Nivel"]
                    else:
                        mejor_nivel = "N/A"
                    kpi_card(
                        titulo="MEJOR NIVEL",
                        valor=f"{mejor_nivel}",
                        delta=f"Líder en desempeño académico",
                        estado="ok" if mejor_nivel != "N/A" else "warning"
                    )

                # ── Distribución de categorías ────────────────────────────────────
                st.markdown("**Distribución por nivel de desempeño**")
                df_dist = calcular_distribucion_desempeno(res["df_raw"])
                chart_dist = alt.Chart(df_dist).mark_bar(
                    cornerRadiusTopLeft=6, cornerRadiusTopRight=6
                ).encode(
                    x=alt.X("Categoría:N", title=None,
                            sort=["Necesita apoyo", "En progreso", "En desempeño", "Sobresaliente"]),
                    y=alt.Y("Porcentaje:Q", title="%", scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color("Color:N", scale=None),
                    tooltip=[
                        alt.Tooltip("Categoría:N"),
                        alt.Tooltip("Alumnos:Q"),
                        alt.Tooltip("Porcentaje:Q", format=".1f", title="%")
                    ]
                ).properties(height=220).configure_view(stroke="transparent")
                st.altair_chart(chart_dist, use_container_width=True)

                # ── % desempeño por nivel educativo ──────────────────────────────
                st.markdown("**% en desempeño por nivel**")
                chart_nivel = alt.Chart(df_des).mark_bar(
                    cornerRadiusTopLeft=6, cornerRadiusTopRight=6
                ).encode(
                    x=alt.X("Nivel:N", title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("pct_desempeno:Q", title="%", scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color("Color:N", scale=None),
                    tooltip=[
                        alt.Tooltip("Nivel:N"),
                        alt.Tooltip("total:Q", title="Alumnos"),
                        alt.Tooltip("pct_desempeno:Q", format=".1f", title="% Desempeño")
                    ]
                ).properties(height=220).configure_view(stroke="transparent")
                st.altair_chart(chart_nivel, use_container_width=True)

                # ── Promedios por materia ─────────────────────────────────────────
                st.markdown("**Promedio por materia**")
                df_raw = res["df_raw"]
                prom_la = float(df_raw["Language Arts"].mean()) if "Language Arts" in df_raw.columns else 0.0
                prom_mat = float(df_raw["Matemáticas"].mean()) if "Matemáticas" in df_raw.columns else (float(df_raw["Math"].mean()) if "Math" in df_raw.columns else 0.0)
                prom_esp = float(df_raw["Español"].mean()) if "Español" in df_raw.columns else 0.0

                df_materias = pd.DataFrame({
                    "Materia": ["Language Arts", "Matemáticas", "Español"],
                    "Promedio": [prom_la, prom_mat, prom_esp]
                })
                df_materias["Color"] = df_materias["Promedio"].apply(
                    lambda v: calcular_color_nivel(v * 10)
                )

                base_materias = alt.Chart(df_materias).encode(
                    x=alt.X("Promedio:Q", title="Promedio (0-10)", scale=alt.Scale(domain=[0, 10])),
                    y=alt.Y("Materia:N", sort="-x", title=None),
                    color=alt.Color("Color:N", scale=None),
                    tooltip=[
                        alt.Tooltip("Materia:N", title="Materia"),
                        alt.Tooltip("Promedio:Q", title="Promedio General", format=".2f")
                    ]
                )
                bars_materias = base_materias.mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
                text_materias = base_materias.mark_text(align="left", dx=8, baseline="middle", fontWeight="bold", fontSize=12, color="#0f172a").encode(
                    text=alt.Text("Promedio:Q", format=".2f")
                )
                chart_materias = (bars_materias + text_materias).properties(height=180).configure_view(stroke="transparent")
                st.altair_chart(chart_materias, use_container_width=True)

                # ── Promedios detallados por materia y nivel ──────────────────────
                if df_prom is not None and not df_prom.empty and len(df_prom) > 1:
                    from ui.charts.nuevos_graficos import chart_promedios_materia_nivel
                    st.markdown("**Promedios por materia y nivel educativo**")
                    st.altair_chart(chart_promedios_materia_nivel(df_prom), use_container_width=True)

                # ── Alumnos por debajo del nivel esperado (< 8.0) ─────────────────
                cols_mat = [c for c in ["Language Arts", "Matemáticas", "Español"] if c in df_raw.columns]

                if cols_mat:
                    mask_bajo = (df_raw[cols_mat] < 8.0).any(axis=1)
                    df_bajo = df_raw[mask_bajo].copy()
                else:
                    df_bajo = pd.DataFrame()

                with st.expander("Alumnos por debajo del nivel esperado (< 8.0)", expanded=False):
                    st.caption("Identificación de alumnos con riesgo o rezago académico en el periodo.")
                    if not df_bajo.empty:
                        def _obtener_materias_riesgo(row):
                            riesgos = []
                            for col in cols_mat:
                                val = row[col]
                                if pd.notna(val) and float(val) < 8.0:
                                    riesgos.append(f"{col} ({val:.1f})")
                            return ", ".join(riesgos) if riesgos else "Ninguna"

                        df_bajo["Materias < 8.0"] = df_bajo.apply(_obtener_materias_riesgo, axis=1)
                        cols_mostrar = [c for c in ["ALUMNO", "Grupo", "Nivel"] if c in df_bajo.columns] + cols_mat + ["Materias < 8.0"]
                        st.dataframe(df_bajo[cols_mostrar], hide_index=True, use_container_width=True)
                    else:
                        st.info("**Sin Alumnos Registrados por Debajo de 8.0:** En el archivo cargado para este periodo, **el 100% de la matrícula evaluada alcanza o supera la meta de 8.0** en todas las asignaturas.")

                # ── Tabla detalle expandible con filtros interactivos ───────────────
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("Ver tabla completa de alumnos con filtros de atención prioritaria", expanded=False):
                    df_tabla = df_raw.copy()
                    
                    # Calcular Promedio y Categoría para cada alumno
                    cols_mat = [c for c in ["Language Arts", "Matemáticas", "Español"] if c in df_tabla.columns]
                    if cols_mat:
                        df_tabla["Promedio"] = df_tabla[cols_mat].mean(axis=1).round(2)
                        df_tabla["Categoría"] = df_tabla.apply(_categorizar_alumno, axis=1)
                    else:
                        df_tabla["Promedio"] = 0.0
                        df_tabla["Categoría"] = "N/A"

                    # Barra de Filtros
                    col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.2, 1.8, 1.5])

                    with col_f1:
                        cat_opciones = ["Todos", "Necesita apoyo", "En progreso", "En desempeño", "Sobresaliente"]
                        filtro_cat = st.selectbox(
                            "Categoría de Desempeño:",
                            options=cat_opciones,
                            key=f"filter_cat_{sede_actual.lower().replace(' ', '_')}"
                        )

                    with col_f2:
                        niveles_disp = ["Todos"] + sorted(list(df_tabla["Nivel"].dropna().unique())) if "Nivel" in df_tabla.columns else ["Todos"]
                        filtro_nivel = st.selectbox(
                            "Nivel Educativo:",
                            options=niveles_disp,
                            key=f"filter_nivel_{sede_actual.lower().replace(' ', '_')}"
                        )

                    with col_f3:
                        filtro_orden = st.selectbox(
                            "Ordenar por Promedio:",
                            options=["Ascendente (Necesitan apoyo primero)", "Descendente (Mayor promedio primero)"],
                            key=f"filter_orden_{sede_actual.lower().replace(' ', '_')}"
                        )

                    with col_f4:
                        filtro_busqueda = st.text_input(
                            "Buscar Alumno / Grupo:",
                            value="",
                            placeholder="Escribe un nombre...",
                            key=f"filter_search_{sede_actual.lower().replace(' ', '_')}"
                        )

                    # Aplicar filtrado dinámico
                    df_filtrado = df_tabla.copy()

                    if filtro_cat != "Todos":
                        df_filtrado = df_filtrado[df_filtrado["Categoría"] == filtro_cat]

                    if filtro_nivel != "Todos" and "Nivel" in df_filtrado.columns:
                        df_filtrado = df_filtrado[df_filtrado["Nivel"] == filtro_nivel]

                    if filtro_busqueda.strip():
                        query = filtro_busqueda.strip().lower()
                        mask_alumno = df_filtrado["ALUMNO"].astype(str).str.lower().str.contains(query, na=False) if "ALUMNO" in df_filtrado.columns else False
                        mask_grupo = df_filtrado["Grupo"].astype(str).str.lower().str.contains(query, na=False) if "Grupo" in df_filtrado.columns else False
                        df_filtrado = df_filtrado[mask_alumno | mask_grupo]

                    # Ordenar resultados
                    asc = filtro_orden.startswith("Ascendente")
                    if "Promedio" in df_filtrado.columns:
                        df_filtrado = df_filtrado.sort_values("Promedio", ascending=asc)

                    # Selección final de columnas
                    cols_finales = ["ALUMNO", "Grupo", "Nivel", "Language Arts", "Matemáticas", "Español", "Promedio", "Categoría"]
                    cols_existen = [c for c in cols_finales if c in df_filtrado.columns]

                    st.caption(f"Mostrando **{len(df_filtrado)} de {len(df_tabla)}** alumnos.")
                    st.dataframe(
                        df_filtrado[cols_existen],
                        hide_index=True,
                        use_container_width=True
                    )

    with tab_pre:
        from ui.components.preescolar_seccion import render_preescolar_section
        render_preescolar_section(sede_actual)

    return True