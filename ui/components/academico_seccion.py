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
)

def render_academico_section(sede_actual: str):
    clave_estado = f"academico_propio_{sede_actual}"

    st.markdown(f"#### Desempeño Académico — {sede_actual}")
    uploaded = st.file_uploader(
        f"Archivo Excel — {sede_actual}",
        type=["xlsx", "xls"],
        key=f"up_acad_{sede_actual.lower().replace(' ', '_')}"
    )

    if uploaded is not None:
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
        st.success(f"{resultado['total_alumnos']} alumnos procesados · Bimestre {resultado['bimestre']}")

    # ── Recopilar catálogo histórico de bimestres disponibles para este campus ──
    from src.logic.data_loader import get_academic_history_catalog, delete_academic_data
    catalog = get_academic_history_catalog()
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
        st.info("Sube el archivo de calificaciones para ver el desempeño académico.")
        return False

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
            return False

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

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Total alumnos", total)
    with k2:
        st.metric("En desempeño global", f"{pct_global}%",
                  delta=f"Bimestre {bimestre}")
    with k3:
        if not df_des.empty and "pct_desempeno" in df_des.columns and "Nivel" in df_des.columns:
            mejor_nivel = df_des.loc[df_des["pct_desempeno"].idxmax(), "Nivel"]
        else:
            mejor_nivel = "N/A"
        st.metric("Mejor nivel", mejor_nivel)

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
    chart_materias = alt.Chart(df_materias).mark_bar(
        cornerRadiusTopLeft=6, cornerRadiusTopRight=6
    ).encode(
        x=alt.X("Promedio:Q", title="Promedio (0-10)", scale=alt.Scale(domain=[0, 10])),
        y=alt.Y("Materia:N", sort="-x", title=None),
        color=alt.Color("Color:N", scale=None),
        tooltip=[
            alt.Tooltip("Materia:N"),
            alt.Tooltip("Promedio:Q", format=".2f")
        ]
    ).properties(height=180).configure_view(stroke="transparent")
    st.altair_chart(chart_materias, use_container_width=True)

    # ── Promedios detallados por materia y nivel ──────────────────────
    if df_prom is not None and not df_prom.empty and len(df_prom) > 1:
        from ui.charts.nuevos_graficos import chart_promedios_materia_nivel
        st.markdown("**Promedios por materia y nivel educativo**")
        st.altair_chart(chart_promedios_materia_nivel(df_prom), use_container_width=True)

    # ── Tabla detalle expandible ──────────────────────────────────────
    with st.expander("Ver tabla completa de alumnos"):
        cols_base = ["ALUMNO", "Grupo", "Nivel", "Language Arts", "Matemáticas", "Español"]
        cols = [c for c in cols_base if c in df_raw.columns]
        sort_col = "Matemáticas" if "Matemáticas" in df_raw.columns else ("Math" if "Math" in df_raw.columns else (cols[0] if cols else None))
        if sort_col and sort_col in df_raw.columns:
            st.dataframe(
                df_raw[cols].sort_values(sort_col, ascending=False),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.dataframe(
                df_raw[cols] if cols else df_raw,
                hide_index=True,
                use_container_width=True
            )

    return True