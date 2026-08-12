# ui/components/data_uploader.py

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
from src.logic.academic_processor import procesar_archivo_academico, acumular_bimestre
from src.logic.data_loader import (
    save_academic_data,
    delete_academic_data,
    get_academic_history_catalog,
)


# ── UPLOADER GLOBAL (app.py) ──────────────────────────────────────────
def render_global_uploader(key, context_name):
    st.info(
        f"**Repositorio Central ({context_name}):** Carga uno o varios archivos simultáneamente. "
        f"El motor identificará automáticamente el campus y bimestre, consolidará el histórico y lo guardará en la base de datos persistente."
    )

    uploaded_files = st.file_uploader(
        f"Cargar archivos para {context_name}",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        key=f"up_global_{key}"
    )

    processed_any = False
    if uploaded_files:
        resumen_procesados = []
        for uploaded_file in uploaded_files:
            try:
                # Leer el archivo según su extensión
                if uploaded_file.name.endswith('.csv'):
                    df_raw = pd.read_csv(uploaded_file)
                else:
                    df_raw = pd.read_excel(uploaded_file)

                if key == "acad":
                    resultado = procesar_archivo_academico(uploaded_file)
                    if resultado.get("error"):
                        st.error(f"Error en {uploaded_file.name}: {resultado['error']}")
                        continue
                    campus   = resultado["campus"]
                    bimestre = resultado["bimestre"]
                    clave    = f"academico_{campus}_{bimestre}"
                    st.session_state[clave] = resultado
                    acumular_bimestre(campus, resultado)
                    st.session_state[f"academico_propio_{campus}"] = resultado
                    
                    resumen_procesados.append({
                        "Archivo": uploaded_file.name,
                        "Campus": campus,
                        "Bimestre": bimestre,
                        "Alumnos": resultado["total_alumnos"]
                    })
                    processed_any = True

                elif key == "clima":
                    from src.logic.clima_engine import procesar_log_clima
                    from src.logic.data_loader import save_clima_data
                    df_clima = procesar_log_clima(df_raw)
                    if df_clima.empty:
                        st.error(f"No se pudieron extraer métricas de Clima Escolar de {uploaded_file.name}. Verifica las columnas.")
                        continue
                    st.session_state["clima_data_global"] = df_clima
                    save_clima_data(df_clima)
                    st.success(f"Archivo de Clima Escolar {uploaded_file.name} integrado exitosamente.")
                    _mostrar_clima(df_clima)
                    processed_any = True

                elif key == "disc":
                    from src.logic.extra_engines import procesar_log_disciplina
                    from src.logic.data_loader import save_disciplina_data
                    df_casos, df_cartas = procesar_log_disciplina(df_raw)
                    if df_casos.empty and df_cartas.empty:
                        st.error(f"No se pudieron extraer métricas de Disciplina de {uploaded_file.name}. Verifica las columnas.")
                        continue
                    st.session_state["disciplina_casos"] = df_casos
                    st.session_state["disciplina_cartas"] = df_cartas
                    save_disciplina_data(df_casos, df_cartas)
                    st.success(f"Archivo de Disciplina e Inclusión {uploaded_file.name} integrado exitosamente.")
                    _mostrar_disciplina(df_casos, df_cartas)
                    processed_any = True

                elif key == "prac":
                    from src.logic.extra_engines import procesar_log_practica
                    from src.logic.data_loader import save_practica_data
                    df_apps_kpis, df_correlacion = procesar_log_practica(df_raw)
                    if df_apps_kpis.empty and df_correlacion.empty:
                        st.error(f"No se pudieron extraer métricas de Práctica Docente de {uploaded_file.name}. Verifica las columnas.")
                        continue
                    st.session_state["practica_apps_kpis"] = df_apps_kpis
                    st.session_state["practica_correlacion"] = df_correlacion
                    save_practica_data(df_apps_kpis, df_correlacion)
                    st.success(f"Archivo de Práctica Docente y Uso de Apps {uploaded_file.name} integrado exitosamente.")
                    _mostrar_practica(df_apps_kpis, df_correlacion)
                    processed_any = True

            except Exception as e:
                st.error(f"Error crítico en procesamiento de {uploaded_file.name}: {e}")
        
        if key == "acad" and resumen_procesados:
            st.success(f"Lote completado: se procesaron e integraron **{len(resumen_procesados)} archivos** en la base de datos.")
            st.dataframe(pd.DataFrame(resumen_procesados), hide_index=True, use_container_width=True)

    # Mostrar datos persistentes o previos
    if key == "clima":
        if "clima_data_global" in st.session_state:
            _mostrar_clima(st.session_state["clima_data_global"])
            return True
    elif key == "disc":
        if "disciplina_casos" in st.session_state and "disciplina_cartas" in st.session_state:
            _mostrar_disciplina(st.session_state["disciplina_casos"], st.session_state["disciplina_cartas"])
            return True
    elif key == "prac":
        if "practica_apps_kpis" in st.session_state and "practica_correlacion" in st.session_state:
            _mostrar_practica(st.session_state["practica_apps_kpis"], st.session_state["practica_correlacion"])
            return True
    elif key == "acad":
        return _mostrar_explorador_academico_global()

    return processed_any


# ── UPLOADER POR CAMPUS (pages/1_Misiones.py, etc.) ──────────────────
def render_campus_uploader(campus_name: str):
    clave_estado = f"academico_propio_{campus_name}"

    st.markdown(f"#### Cargar datos de {campus_name}")
    uploaded_files = st.file_uploader(
        f"Archivos Excel — {campus_name}",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key=f"up_{campus_name.lower().replace(' ', '_')}"
    )

    processed_any = False
    if uploaded_files:
        for uploaded_file in uploaded_files:
            resultado = procesar_archivo_academico(uploaded_file, target_campus=campus_name)

            if resultado.get("error"):
                st.error(f"Error en {uploaded_file.name}: {resultado['error']}")
                continue

            if resultado["campus"] != campus_name and resultado["campus"] != "Desconocido":
                st.warning(f"El archivo {uploaded_file.name} parece ser de **{resultado['campus']}**, "
                           f"no de {campus_name}. ¿Deseas cargarlo de todas formas?")
                if not st.button(f"Sí, cargar {uploaded_file.name} de todas formas", key=f"forzar_{campus_name}_{uploaded_file.name}"):
                    continue

            st.session_state[f"academico_{campus_name}_{resultado['bimestre']}"] = resultado
            st.session_state[clave_estado] = resultado
            acumular_bimestre(campus_name, resultado)
            st.success(f"{uploaded_file.name} cargado · {resultado['total_alumnos']} alumnos · "
                       f"Bimestre {resultado['bimestre']}")
            processed_any = True

    # Mostrar todos los bimestres activos cargados para este campus
    claves_activas = [k for k in st.session_state if k.startswith(f"academico_{campus_name}_")]
    if claves_activas:
        for clave in sorted(claves_activas):
            _mostrar_desempeno(st.session_state[clave])
        return True

    return processed_any


# ── VISTA CAMPUS DESDE GLOBAL ──────────────────────────────────────────
def render_campus_dynamic_view(key: str, campus_name: str):
    if key == "clima":
        if "clima_data_global" in st.session_state:
            df_clima = st.session_state["clima_data_global"]
            df_clima_filtered = df_clima[df_clima['campus'] == campus_name]
            if not df_clima_filtered.empty:
                _mostrar_clima(df_clima_filtered)
                return True
        return False
    elif key == "disc":
        if "disciplina_casos" in st.session_state and "disciplina_cartas" in st.session_state:
            df_casos = st.session_state["disciplina_casos"]
            df_cartas = st.session_state["disciplina_cartas"]
            df_casos_filtered = df_casos[df_casos['campus'] == campus_name]
            df_cartas_filtered = df_cartas[df_cartas['campus'] == campus_name]
            if not df_casos_filtered.empty or not df_cartas_filtered.empty:
                _mostrar_disciplina(df_casos_filtered, df_cartas_filtered)
                return True
        return False
    elif key == "prac":
        if "practica_apps_kpis" in st.session_state and "practica_correlacion" in st.session_state:
            df_apps_kpis = st.session_state["practica_apps_kpis"]
            df_correlacion = st.session_state["practica_correlacion"]
            df_apps_kpis_filtered = df_apps_kpis[df_apps_kpis['campus'] == campus_name]
            df_correlacion_filtered = df_correlacion[df_correlacion['campus'] == campus_name]
            if not df_apps_kpis_filtered.empty or not df_correlacion_filtered.empty:
                _mostrar_practica(df_apps_kpis_filtered, df_correlacion_filtered)
                return True
        return False
    else:  # Default/Fallback: "acad"
        clave_propia  = f"academico_propio_{campus_name}"
        clave_global  = f"academico_{campus_name}_"

        if clave_propia in st.session_state:
            _mostrar_desempeno(st.session_state[clave_propia])
            return True

        claves = [k for k in st.session_state if k.startswith(clave_global)]
        if claves:
            for clave in sorted(claves):
                _mostrar_desempeno(st.session_state[clave])
            return True

        return False


# ── EXPLORADOR HISTÓRICO CONSOLIDADO ──────────────────────────────────
def _mostrar_explorador_academico_global() -> bool:
    catalog = get_academic_history_catalog()
    
    # Combinar con claves de session_state si existen
    for k, val in st.session_state.items():
        if k.startswith("academico_") and not k.startswith("academico_propio_") and isinstance(val, dict):
            c = val.get("campus")
            b = val.get("bimestre")
            if c and b:
                if c not in catalog:
                    catalog[c] = {}
                if b not in catalog[c]:
                    catalog[c][b] = val

    if not catalog:
        return False

    st.markdown("---")
    st.markdown("### Histórico Académico Consolidado en Base de Datos")
    
    campuses_disponibles = sorted(list(catalog.keys()))
    col_c, col_b, col_del = st.columns([2, 2, 1.5])
    
    with col_c:
        campus_sel = st.selectbox("Seleccionar Campus:", options=campuses_disponibles, key="sel_acad_global_campus")
    
    bimestres_disponibles = sorted(list(catalog[campus_sel].keys()))
    with col_b:
        bim_sel = st.selectbox("Seleccionar Bimestre:", options=bimestres_disponibles, key="sel_acad_global_bim")
        
    with col_del:
        st.write("") # spacer
        st.write("")
        if st.button("Eliminar Bimestre", key=f"del_global_acad_{campus_sel}_{bim_sel}", use_container_width=True):
            delete_academic_data(campus_sel, bim_sel)
            clave = f"academico_{campus_sel}_{bim_sel}"
            if clave in st.session_state:
                del st.session_state[clave]
            st.cache_data.clear()
            st.rerun()

    datos_sel = catalog[campus_sel][bim_sel]
    _mostrar_desempeno(datos_sel)
    return True


# ── HELPERS PRIVADOS DE RENDERIZACIÓN ─────────────────────────────────
def _mostrar_desempeno(resultado: dict):
    from ui.charts.nuevos_graficos import chart_desempeno_nivel_barras, chart_promedios_materia_nivel
    df_des  = resultado["desempeno"]
    df_prom = resultado["promedios"]
    campus   = resultado["campus"]
    bimestre = resultado["bimestre"]

    st.markdown(f"#### Desempeño Académico — **{campus}** · **{bimestre}** ({resultado.get('total_alumnos', 0)} alumnos)")

    # KPIs por nivel
    if df_des is not None and not df_des.empty:
        cols = st.columns(len(df_des))
        for i, row in df_des.iterrows():
            with cols[i]:
                st.metric(
                    label=str(row["Nivel"]),
                    value=f"{row['pct_desempeno']}%",
                    help=f"{int(row['en_desempeno'])} de {int(row['total'])} alumnos en desempeño"
                )

        # Detalle por nivel con gráfico y tabla
        st.markdown("**Detalle por nivel**")
        st.altair_chart(chart_desempeno_nivel_barras(df_des), use_container_width=True)
        st.dataframe(
            df_des.rename(columns={
                "total"         : "Total alumnos",
                "en_desempeno"  : "En desempeño",
                "pct_desempeno" : "% Desempeño"
            }),
            hide_index=True,
            use_container_width=True
        )

    # Promedios por materia y nivel con gráfico y tabla
    if df_prom is not None and not df_prom.empty:
        st.markdown("**Promedios por materia y nivel**")
        st.altair_chart(chart_promedios_materia_nivel(df_prom), use_container_width=True)
        st.dataframe(
            df_prom.rename(columns={
                "language_arts" : "Language Arts",
                "matemáticas"   : "Matemáticas",
                "español"       : "Español",
                "total_alumnos" : "Total"
            }),
            hide_index=True,
            use_container_width=True
        )


def _mostrar_clima(df_clima):
    from ui.charts.nuevos_graficos import chart_clima_heatmap, chart_clima_barras
    st.markdown("### Clima Escolar Consolidado")
    st.altair_chart(chart_clima_heatmap(df_clima), use_container_width=True)
    st.markdown("### Distribución de Respuestas")
    st.altair_chart(chart_clima_barras(df_clima), use_container_width=True)


def _mostrar_disciplina(df_casos, df_cartas):
    st.markdown("### Disciplina e Inclusión Consolidada")
    cd1, cd2 = st.columns(2)
    with cd1:
        st.markdown("**Radar de Casos Especiales (Activos)**")
        st.dataframe(df_casos, hide_index=True, use_container_width=True)
    with cd2:
        st.markdown("**Alertas por Cartas Compromiso**")
        st.dataframe(df_cartas, hide_index=True, use_container_width=True)


def _mostrar_practica(df_apps_kpis, df_correlacion):
    from ui.charts.apps_charts import chart_comparativa_apps, chart_correlacion_practica
    st.markdown("### Práctica Docente y Uso de Aplicaciones")
    colr1, colr2 = st.columns(2, gap="large")
    with colr1:
        st.markdown("**Métricas de Adopción**")
        st.altair_chart(chart_comparativa_apps(df_apps_kpis), use_container_width=True)
    with colr2:
        st.markdown("**Relación Académica: Práctica vs Resultados (Dominio)**")
        st.altair_chart(chart_correlacion_practica(df_correlacion), use_container_width=True)
