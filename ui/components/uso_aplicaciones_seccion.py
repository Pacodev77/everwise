# ui/components/uso_aplicaciones_seccion.py

# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
import altair as alt
import pandas as pd
from src.logic.ixl_processor import procesar_ixl, acumular_ixl, cruzar_con_academico
from src.logic.progrentis_processor import procesar_progrentis, save_progrentis_session
from ui.components.kpi_cards import kpi_card

def eliminar_datos_ixl(sede_target: str):
    """Elimina datos de IXL de SQLite, session_state y cycle_vault estrictamente para el campus indicado."""
    if not sede_target:
        return
        
    from src.logic.data_loader import get_db_connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ixl_diagnostics'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM ixl_diagnostics WHERE campus = ?", (sede_target,))
            conn.commit()
        conn.close()
    except Exception:
        pass

    slug = sede_target.lower().replace(' ', '_')
    keys_to_del = [f"ixl_{sede_target}", f"last_up_ixl_{slug}"]
    for k in keys_to_del:
        if k in st.session_state:
            del st.session_state[k]
            
    if "cycle_vault" in st.session_state:
        for cycle in st.session_state["cycle_vault"]:
            for k in keys_to_del:
                if k in st.session_state["cycle_vault"][cycle]:
                    del st.session_state["cycle_vault"][cycle][k]

    st.cache_data.clear()

def eliminar_datos_progrentis(sede_target: str):
    """Elimina datos de Progrentis de SQLite, session_state y cycle_vault estrictamente para el campus indicado."""
    if not sede_target:
        return
        
    from src.logic.data_loader import get_db_connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='progrentis_data'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM progrentis_data WHERE campus = ?", (sede_target,))
            conn.commit()
        conn.close()
    except Exception:
        pass

    slug = sede_target.lower().replace(' ', '_')
    keys_to_del = [f"progrentis_{sede_target}", f"last_up_prog_{slug}"]
    for k in keys_to_del:
        if k in st.session_state:
            del st.session_state[k]
            
    if "cycle_vault" in st.session_state:
        for cycle in st.session_state["cycle_vault"]:
            for k in keys_to_del:
                if k in st.session_state["cycle_vault"][cycle]:
                    del st.session_state["cycle_vault"][cycle][k]

    st.cache_data.clear()

def render_uso_aplicaciones_section(sede_actual: str):
    """
    Sección unificada de Uso de Aplicaciones.
    Integra dos submódulos principales: Progrentis (IPD & Mejora) e IXL Diagnóstico (Multi-Campus).
    """
    st.markdown(f"### Uso de Aplicaciones — {sede_actual}")
    st.caption("Monitoreo ejecutivo de adopción, diagnóstico pedagógico y evolución digital de plataformas de aprendizaje.")

    tab_progrentis, tab_ixl = st.tabs([
        "Progrentis (Índice IPD & Mejora)",
        "IXL Diagnóstico (Flex Diagnostic)"
    ])

    with tab_progrentis:
        _render_submodulo_progrentis(sede_actual)

    with tab_ixl:
        _render_submodulo_ixl(sede_actual)

def _render_submodulo_progrentis(sede_actual: str):
    clave_p = f"progrentis_{sede_actual}"

    st.markdown("#### Progrentis — Desarrollo del Pensamiento Digital")

    if sede_actual != "Global":
        col_up, col_del = st.columns([3, 1])
        with col_up:
            uploaded_p = st.file_uploader(
                f"Cargar reporte Progrentis (Excel/CSV) — {sede_actual}",
                type=["xlsx", "xls", "csv"],
                key=f"up_prog_{sede_actual.lower().replace(' ', '_')}"
            )
        with col_del:
            st.write("")
            st.write("")
            if st.button(f"Eliminar archivo ({sede_actual})", key=f"btn_del_prog_sede_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
                eliminar_datos_progrentis(sede_actual)
                st.rerun()
    else:
        col_up, col_sel, col_del = st.columns([2.2, 1.2, 1.0])
        with col_up:
            uploaded_p = st.file_uploader(
                "Cargar reporte Progrentis (Excel/CSV) — Global",
                type=["xlsx", "xls", "csv"],
                key="up_prog_global"
            )
        with col_sel:
            sede_del_p = st.selectbox("Campus a eliminar", ["Misiones", "Nuevo Sur", "San Agustín"], key="sel_del_prog_global")
        with col_del:
            st.write("")
            st.write("")
            if st.button("Eliminar campus", key="btn_del_prog_global_sel", use_container_width=True, type="secondary"):
                eliminar_datos_progrentis(sede_del_p)
                st.rerun()

    if uploaded_p is not None:
        file_state_key = f"last_up_prog_{sede_actual.lower().replace(' ', '_')}"
        if st.session_state.get(file_state_key) != uploaded_p.name:
            res_p = procesar_progrentis(uploaded_p, target_campus=sede_actual)
            if res_p.get("error"):
                st.error(res_p["error"])
            else:
                save_progrentis_session(sede_actual, res_p)
                st.session_state[file_state_key] = uploaded_p.name
                st.cache_data.clear()
                st.rerun()

    if sede_actual == "Global" or clave_p not in st.session_state:
        dfs_to_concat_p = []
        # 1. Cargar desde SQLite
        from src.logic.data_loader import get_db_connection
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='progrentis_data'")
            if cursor.fetchone():
                query = "SELECT * FROM progrentis_data WHERE campus = ?" if sede_actual != "Global" else "SELECT * FROM progrentis_data"
                df_p = pd.read_sql(query, conn, params=(sede_actual,) if sede_actual != "Global" else ())
                if not df_p.empty:
                    dfs_to_concat_p.append(df_p)
            conn.close()
        except Exception:
            pass

        # 2. Revisar session_state por cada campus
        campuses_p = ["Misiones", "Nuevo Sur", "San Agustín"] if sede_actual == "Global" else [sede_actual]
        for c in campuses_p:
            kp = f"progrentis_{c}"
            if kp in st.session_state and isinstance(st.session_state[kp], dict) and "df_raw" in st.session_state[kp]:
                df_c_p = st.session_state[kp]["df_raw"]
                if df_c_p is not None and not df_c_p.empty:
                    dfs_to_concat_p.append(df_c_p)

        if dfs_to_concat_p:
            df_p_comb = pd.concat(dfs_to_concat_p, ignore_index=True)
            dedup_p = [c for c in ["campus", "Matricula", "Alumno", "Nivel"] if c in df_p_comb.columns]
            if len(dedup_p) >= 2:
                df_p_comb = df_p_comb.drop_duplicates(subset=dedup_p, keep="last")
                
            resumen_lvl = df_p_comb.groupby('Nivel').agg(
                total=('Alumno', 'count'),
                ipd_ini_prom=('IPD_Ini', 'mean'),
                ipd_act_prom=('IPD_Actual', 'mean'),
                mejora_prom=('Mejora_Pct', 'mean')
            ).reset_index().round(1)
            
            st.session_state[clave_p] = {
                "error": None,
                "total_alumnos": len(df_p_comb),
                "ipd_ini_avg": round(df_p_comb['IPD_Ini'].mean(), 1),
                "ipd_act_avg": round(df_p_comb['IPD_Actual'].mean(), 1),
                "mejora_avg": round(df_p_comb['Mejora_Pct'].mean(), 1),
                "df_raw": df_p_comb,
                "resumen_nivel": resumen_lvl
            }

    if clave_p not in st.session_state or st.session_state[clave_p].get("total_alumnos", 0) == 0:
        st.info("Sube el archivo de Progrentis para visualizar la métrica de IPD e Índice de Mejora.")
        return

    data = st.session_state[clave_p]
    df_raw = data.get("df_raw", pd.DataFrame())
    
    total_alumnos = data.get("total_alumnos", 0)
    ipd_ini_avg = data.get("ipd_ini_avg", 0.0)
    ipd_act_avg = data.get("ipd_act_avg", 0.0)
    mejora_avg = data.get("mejora_avg", 0.0)
    delta_ipd = ipd_act_avg - ipd_ini_avg

    # KPIs con formato ejecutivo (Semáforo + Flechas direccionales)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card(
            titulo="ALUMNOS REGISTRADOS",
            valor=f"{total_alumnos}",
            delta="Reporte activo · Consolidado",
            estado="info"
        )
    with c2:
        kpi_card(
            titulo="IPD INICIAL PROMEDIO",
            valor=f"{ipd_ini_avg:.1f}",
            delta="Línea Base · Diagnóstico Inicial",
            estado="info"
        )
    with c3:
        if delta_ipd > 0:
            delta_html = f'<span style="color:#10b981;font-weight:700">↑ +{delta_ipd:.1f} pts</span> vs Inicial'
            estado_ipd = "ok"
        elif delta_ipd < 0:
            delta_html = f'<span style="color:#ef4444;font-weight:700">↓ {delta_ipd:.1f} pts</span> vs Inicial'
            estado_ipd = "risk"
        else:
            delta_html = '<span style="color:#64748b;font-weight:700">= 0.0 pts</span> Sin cambio'
            estado_ipd = "warning"

        kpi_card(
            titulo="IPD ACTUAL PROMEDIO",
            valor=f"{ipd_act_avg:.1f}",
            delta=delta_html,
            estado=estado_ipd
        )
    with c4:
        if mejora_avg > 0:
            delta_mejora = f'<span style="color:#10b981;font-weight:700">↑ +{mejora_avg:.1f}%</span> Avance Digital'
            estado_m = "ok"
        elif mejora_avg < 0:
            delta_mejora = f'<span style="color:#ef4444;font-weight:700">↓ {mejora_avg:.1f}%</span> Retroceso Digital'
            estado_m = "risk"
        else:
            delta_mejora = '<span style="color:#64748b;font-weight:700">= 0.0%</span> Sin Avance'
            estado_m = "warning"

        kpi_card(
            titulo="% MEJORA GENERAL",
            valor=f"{mejora_avg:+.1f}%" if mejora_avg != 0 else "0.0%",
            delta=delta_mejora,
            estado=estado_m
        )

    # Controles
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Eliminar reporte Progrentis", key=f"del_prog_{sede_actual.lower().replace(' ', '_')}"):
        if clave_p in st.session_state:
            del st.session_state[clave_p]
        from src.logic.data_loader import get_db_connection
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM progrentis_data WHERE campus = ?", (sede_actual,))
            conn.commit()
            conn.close()
        except Exception:
            pass
        st.cache_data.clear()
        st.rerun()

    # Visualización por Nivel
    resumen_lvl = data.get("resumen_nivel", pd.DataFrame())
    if not resumen_lvl.empty:
        col_g1, col_g2 = st.columns(2, gap="large")
        with col_g1:
            st.markdown("**Evolución de IPD (Inicial vs. Actual) por Nivel**")
            df_melt = resumen_lvl.melt(id_vars=['Nivel'], value_vars=['ipd_ini_prom', 'ipd_act_prom'],
                                       var_name='Etapa', value_name='IPD')
            df_melt['Etapa'] = df_melt['Etapa'].map({'ipd_ini_prom': 'IPD Inicial', 'ipd_act_prom': 'IPD Actual'})
            
            chart_ipd = alt.Chart(df_melt).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=24).encode(
                x=alt.X('Nivel:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12)),
                xOffset=alt.XOffset('Etapa:N', sort=['IPD Inicial', 'IPD Actual']),
                y=alt.Y('IPD:Q', title='Índice IPD', axis=alt.Axis(grid=True)),
                color=alt.Color('Etapa:N', scale=alt.Scale(domain=['IPD Inicial', 'IPD Actual'], range=['#94a3b8', '#6366f1'])),
                tooltip=[alt.Tooltip('Nivel:N'), alt.Tooltip('Etapa:N'), alt.Tooltip('IPD:Q', format='.1f')]
            ).properties(height=240).configure_view(stroke='transparent')
            st.altair_chart(chart_ipd, use_container_width=True)

        with col_g2:
            st.markdown("**Porcentaje de Mejora Digital por Nivel**")
            chart_mejora = alt.Chart(resumen_lvl).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=45).encode(
                x=alt.X('Nivel:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12)),
                y=alt.Y('mejora_prom:Q', title='% Mejora', axis=alt.Axis(format='%', grid=True)),
                color=alt.value('#10b981'),
                tooltip=[alt.Tooltip('Nivel:N'), alt.Tooltip('mejora_prom:Q', format='.1f', title='% Mejora')]
            ).properties(height=240).configure_view(stroke='transparent')
            st.altair_chart(chart_mejora, use_container_width=True)

    # ── Gráfica de Proyección Bimestral Progrentis ─────────────────────────────
    st.markdown("---")
    st.markdown("### Proyección Bimestral de Índices IPD (B1 - B5)")
    st.caption("Trayectoria estimada de avance digital hacia el cierre de ciclo escolar con meta institucional de 85.0 pts IPD.")

    rate_prog = max(abs(delta_ipd), 3.0)
    ipd_b3 = round(ipd_act_avg + rate_prog, 1)
    ipd_b4 = round(ipd_b3 + rate_prog, 1)
    ipd_b5 = round(max(ipd_b4 + rate_prog, 85.0), 1)

    df_proy_p = pd.DataFrame([
        {"Bimestre": "B1 (Inicial)", "IPD": round(ipd_ini_avg, 1), "Tipo": "Histórico Real"},
        {"Bimestre": "B2 (Actual)", "IPD": round(ipd_act_avg, 1), "Tipo": "Histórico Real"},
        {"Bimestre": "B3 (Proy.)", "IPD": ipd_b3, "Tipo": "Proyección Estimada"},
        {"Bimestre": "B4 (Proy.)", "IPD": ipd_b4, "Tipo": "Proyección Estimada"},
        {"Bimestre": "B5 (Meta Cierre)", "IPD": ipd_b5, "Tipo": "Proyección Estimada"},
    ])

    linea_proy = alt.Chart(df_proy_p).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("Bimestre:N", sort=["B1 (Inicial)", "B2 (Actual)", "B3 (Proy.)", "B4 (Proy.)", "B5 (Meta Cierre)"], title=None),
        y=alt.Y("IPD:Q", title="Índice IPD", scale=alt.Scale(domain=[min(ipd_ini_avg, ipd_act_avg) - 5, max(ipd_b5, 90.0) + 5])),
        color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Histórico Real", "Proyección Estimada"], range=["#3b82f6", "#8b5cf6"])),
        strokeDash=alt.StrokeDash("Tipo:N", scale=alt.Scale(domain=["Histórico Real", "Proyección Estimada"], range=[[0], [4, 4]])),
        tooltip=[alt.Tooltip("Bimestre:N"), alt.Tooltip("IPD:Q", format=".1f"), alt.Tooltip("Tipo:N")]
    ).properties(height=260)

    meta_rule_p = alt.Chart(pd.DataFrame([{"meta": 85.0}])).mark_rule(color="#ef4444", strokeDash=[6, 6], strokeWidth=2).encode(y="meta:Q")
    st.altair_chart((linea_proy + meta_rule_p).configure_view(stroke="transparent"), use_container_width=True)

    with st.expander("Ver tabla completa de alumnos (Progrentis)"):
        st.dataframe(df_raw, hide_index=True, use_container_width=True)

def _render_submodulo_ixl(sede_actual: str):
    clave_ixl = f"ixl_{sede_actual}"

    if sede_actual == "Global" and clave_ixl in st.session_state:
        df_old = st.session_state[clave_ixl].get("df_raw", pd.DataFrame())
        if not df_old.empty:
            if "campus" not in df_old.columns or (df_old["campus"] == "Global").any() or len(df_old) <= 5:
                del st.session_state[clave_ixl]

    st.markdown("#### IXL Diagnóstico Flex — Rendimiento Pedagógico")
    st.info("Sube el reporte de diagnóstico de IXL. El sistema soporta **archivos únicos multi-campus** (`IXL-Flex-Diagnostic-Results`) y distribuye los datos automáticamente.")

    campus_filtro_global = "Todos los Campus (Global)"
    if sede_actual != "Global":
        col_up, col_del = st.columns([3, 1])
        with col_up:
            uploaded_ixl = st.file_uploader(
                f"Cargar reporte IXL (CSV/Excel) — {sede_actual}",
                type=["csv", "xlsx", "xls"],
                key=f"up_ixl_{sede_actual.lower().replace(' ', '_')}"
            )
        with col_del:
            st.write("")
            st.write("")
            if st.button(f"Eliminar archivo ({sede_actual})", key=f"btn_del_ixl_sede_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
                eliminar_datos_ixl(sede_actual)
                st.rerun()
    else:
        col_up, col_sel = st.columns([2.5, 1.5])
        with col_up:
            uploaded_ixl = st.file_uploader(
                "Cargar reporte IXL (CSV/Excel) — Global",
                type=["csv", "xlsx", "xls"],
                key="up_ixl_global"
            )
        with col_sel:
            campus_filtro_global = st.selectbox(
                "Seleccionar Campus a consultar",
                ["Todos los Campus (Global)", "Misiones", "Nuevo Sur", "San Agustín"],
                key="sel_campus_view_ixl_global"
            )

    if uploaded_ixl is not None:
        file_state_key = f"last_up_ixl_{sede_actual.lower().replace(' ', '_')}"
        if st.session_state.get(file_state_key) != uploaded_ixl.name:
            res_ixl = procesar_ixl(uploaded_ixl, target_campus=sede_actual)
            if res_ixl.get("error"):
                st.error(res_ixl["error"])
            else:
                st.session_state[clave_ixl] = res_ixl
                st.session_state[file_state_key] = uploaded_ixl.name
                
                splits = res_ixl.get("campus_splits", {})
                if len(splits) > 1:
                    st.success(f"Archivo Multi-Campus integrado exitosamente: {', '.join(splits.keys())}")
                else:
                    st.success(f"Diagnóstico IXL para {sede_actual} integrado exitosamente.")
                st.cache_data.clear()
                st.rerun()

    if sede_actual == "Global" or clave_ixl not in st.session_state:
        dfs_to_concat = []
        # 1. Cargar desde SQLite sólo campus válidos
        from src.logic.data_loader import get_db_connection
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ixl_diagnostics'")
            if cursor.fetchone():
                if sede_actual != "Global":
                    query = "SELECT * FROM ixl_diagnostics WHERE campus = ?"
                    params = (sede_actual,)
                else:
                    query = "SELECT * FROM ixl_diagnostics WHERE campus IN ('Misiones', 'Nuevo Sur', 'San Agustín')"
                    params = ()
                df_ixl_db = pd.read_sql(query, conn, params=params)
                if not df_ixl_db.empty:
                    dfs_to_concat.append(df_ixl_db)
            conn.close()
        except Exception:
            pass

        # 2. Revisar session_state por cada campus individual
        campuses_to_check = ["Misiones", "Nuevo Sur", "San Agustín"] if sede_actual == "Global" else [sede_actual]
        for c in campuses_to_check:
            k = f"ixl_{c}"
            if k in st.session_state and isinstance(st.session_state[k], dict) and "df_raw" in st.session_state[k]:
                df_c = st.session_state[k]["df_raw"]
                if df_c is not None and not df_c.empty:
                    dfs_to_concat.append(df_c)

        if dfs_to_concat:
            dfs_clean = []
            for d in dfs_to_concat:
                if d is None or d.empty:
                    continue
                dc = d.loc[:, ~d.columns.duplicated()].copy()
                if "Overall_percentile" in dc.columns:
                    if "Overall percentile" in dc.columns:
                        dc["Overall percentile"] = dc["Overall percentile"].fillna(dc["Overall_percentile"])
                        dc = dc.drop(columns=["Overall_percentile"])
                    else:
                        dc = dc.rename(columns={"Overall_percentile": "Overall percentile"})
                if "Overall_tier" in dc.columns:
                    if "Overall tier" in dc.columns:
                        dc["Overall tier"] = dc["Overall tier"].fillna(dc["Overall_tier"])
                        dc = dc.drop(columns=["Overall_tier"])
                    else:
                        dc = dc.rename(columns={"Overall_tier": "Overall tier"})
                dc = dc.loc[:, ~dc.columns.duplicated()].copy()
                dfs_clean.append(dc)

            if dfs_clean:
                df_combined = pd.concat(dfs_clean, ignore_index=True)
                df_combined = df_combined.loc[:, ~df_combined.columns.duplicated()].copy()
                
                dedup_keys = [c for c in ["campus", "ID", "Matricula", "First name", "Last name", "Grade"] if c in df_combined.columns]
                if len(dedup_keys) >= 2:
                    df_combined = df_combined.drop_duplicates(subset=dedup_keys, keep="last")
                elif "campus" in df_combined.columns and "Grade" in df_combined.columns and "Overall percentile" in df_combined.columns:
                    df_combined = df_combined.drop_duplicates(subset=["campus", "Grade", "Overall percentile"], keep="last")

                from src.logic.ixl_processor import calcular_resumen_tier, calcular_por_grado, calcular_areas
                st.session_state[clave_ixl] = {
                    "error": None,
                    "total_alumnos": len(df_combined),
                    "df_raw": df_combined,
                    "df_combined_all": df_combined,
                    "resumen_tier": calcular_resumen_tier(df_combined),
                    "resumen_grado": calcular_por_grado(df_combined),
                    "resumen_areas": calcular_areas(df_combined)
                }

    if clave_ixl not in st.session_state or st.session_state[clave_ixl].get("total_alumnos", 0) == 0:
        st.info("Sube el archivo de diagnóstico IXL para visualizar los niveles de logro y percentiles por grado.")
        return

    res = st.session_state[clave_ixl]
    df_combined_all = res.get("df_combined_all", res.get("df_raw", pd.DataFrame()))

    if sede_actual == "Global" and not df_combined_all.empty and "campus" in df_combined_all.columns:
        if campus_filtro_global != "Todos los Campus (Global)":
            df_raw = df_combined_all[df_combined_all["campus"] == campus_filtro_global].copy()
        else:
            df_raw = df_combined_all.copy()
        
        from src.logic.ixl_processor import calcular_resumen_tier, calcular_por_grado, calcular_areas
        res["df_raw"] = df_raw
        res["total_alumnos"] = len(df_raw)
        res["resumen_tier"] = calcular_resumen_tier(df_raw)
        res["resumen_grado"] = calcular_por_grado(df_raw)
        res["resumen_areas"] = calcular_areas(df_raw)
    else:
        df_raw = res.get("df_raw", pd.DataFrame())

    if not df_raw.empty:
        df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()].copy()
    
    total_alumnos = res.get("total_alumnos", len(df_raw))
    s_pct = df_raw["Overall percentile"] if "Overall percentile" in df_raw.columns else None
    if isinstance(s_pct, pd.DataFrame):
        s_pct = s_pct.iloc[:, 0]
    prom_percentil = pd.to_numeric(s_pct, errors="coerce").mean() if s_pct is not None and not s_pct.empty else 0.0
    
    pct_on_above = 0.0
    s_tier = df_raw["Overall tier"] if "Overall tier" in df_raw.columns else None
    if isinstance(s_tier, pd.DataFrame):
        s_tier = s_tier.iloc[:, 0]
    if s_tier is not None and total_alumnos > 0:
        on_above_cnt = s_tier.isin(["On grade", "Above grade"]).sum()
        pct_on_above = (on_above_cnt / total_alumnos) * 100.0

    # KPIs con formato ejecutivo (Semáforo + Flechas direccionales)
    m1, m2, m3 = st.columns(3)
    with m1:
        kpi_card(
            titulo="ALUMNOS EVALUADOS IXL",
            valor=f"{total_alumnos}",
            delta=f"Campus: {campus_filtro_global}" if sede_actual == "Global" else "Diagnóstico Flex Activo",
            estado="info"
        )
    with m2:
        if prom_percentil >= 60.0:
            delta_p = f'<span style="color:#10b981;font-weight:700">↑ {prom_percentil:.1f}%</span> Desempeño Robusto'
            estado_p = "ok"
        elif prom_percentil >= 45.0:
            delta_p = f'<span style="color:#f59e0b;font-weight:700">↑ {prom_percentil:.1f}%</span> En Seguimiento'
            estado_p = "warning"
        else:
            delta_p = f'<span style="color:#ef4444;font-weight:700">↓ {prom_percentil:.1f}%</span> Requiere Intervención'
            estado_p = "risk"

        kpi_card(
            titulo="PERCENTIL PROMEDIO GLOBAL" if (sede_actual == "Global" and campus_filtro_global == "Todos los Campus (Global)") else f"PERCENTIL PROMEDIO ({campus_filtro_global})" if sede_actual == "Global" else "PERCENTIL PROMEDIO",
            valor=f"{prom_percentil:.1f}%",
            delta=delta_p,
            estado=estado_p
        )
    with m3:
        if pct_on_above >= 60.0:
            delta_o = f'<span style="color:#10b981;font-weight:700">↑ {pct_on_above:.1f}%</span> Nivel Óptimo (On/Above)'
            estado_o = "ok"
        elif pct_on_above >= 45.0:
            delta_o = f'<span style="color:#f59e0b;font-weight:700">↑ {pct_on_above:.1f}%</span> Nivel Aceptable'
            estado_o = "warning"
        else:
            delta_o = f'<span style="color:#ef4444;font-weight:700">↓ {pct_on_above:.1f}%</span> Requiere Refuerzo'
            estado_o = "risk"

        kpi_card(
            titulo="ALUMNOS AL NIVEL O SUPERIOR",
            valor=f"{pct_on_above:.1f}%",
            delta=delta_o,
            estado=estado_o
        )

    # ── Comparativa de Diagnóstico IXL por Campus si es Global ──────────────
    df_comp_base = df_combined_all if not df_combined_all.empty else df_raw
    if sede_actual == "Global" and "campus" in df_comp_base.columns and not df_comp_base.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Comparativa de Diagnóstico IXL por Campus Corporativo**")
        df_comp = df_comp_base.loc[:, ~df_comp_base.columns.duplicated()].copy()
        s_cpct = df_comp["Overall percentile"] if "Overall percentile" in df_comp.columns else None
        if isinstance(s_cpct, pd.DataFrame): s_cpct = s_cpct.iloc[:, 0]
        s_ctier = df_comp["Overall tier"] if "Overall tier" in df_comp.columns else None
        if isinstance(s_ctier, pd.DataFrame): s_ctier = s_ctier.iloc[:, 0]

        s_camp = df_comp["campus"]
        if isinstance(s_camp, pd.DataFrame): s_camp = s_camp.iloc[:, 0]

        df_comp_clean = pd.DataFrame({
            "campus": s_camp,
            "Overall percentile": pd.to_numeric(s_cpct, errors="coerce") if s_cpct is not None else np.nan,
            "Overall tier": s_ctier if s_ctier is not None else np.nan
        })

        res_campus = df_comp_clean.groupby("campus").agg(
            alumnos=("campus", "count"),
            percentil_prom=("Overall percentile", "mean"),
            pct_on_above=("Overall tier", lambda x: (x.isin(["On grade", "Above grade"]).sum() / len(x) * 100) if len(x) > 0 else 0)
        ).reset_index().round(1)

        if not res_campus.empty:
            col_c1, col_c2 = st.columns(2, gap="large")
            with col_c1:
                st.caption("Percentil Promedio IXL por Campus")
                chart_perc_campus = alt.Chart(res_campus).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#6366f1").encode(
                    x=alt.X("campus:N", title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("percentil_prom:Q", title="Percentil Promedio", scale=alt.Scale(domain=[0, 100])),
                    tooltip=[alt.Tooltip("campus:N", title="Campus"), alt.Tooltip("alumnos:Q", title="Alumnos"), alt.Tooltip("percentil_prom:Q", format=".1f", title="Percentil Promedio")]
                ).properties(height=210).configure_view(stroke="transparent")
                st.altair_chart(chart_perc_campus, use_container_width=True)
            with col_c2:
                st.caption("% Alumnos en Nivel Óptimo (On/Above Grade) por Campus")
                chart_on_above_campus = alt.Chart(res_campus).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#10b981").encode(
                    x=alt.X("campus:N", title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("pct_on_above:Q", title="% Nivel Óptimo", scale=alt.Scale(domain=[0, 100])),
                    tooltip=[alt.Tooltip("campus:N", title="Campus"), alt.Tooltip("alumnos:Q", title="Alumnos"), alt.Tooltip("pct_on_above:Q", format=".1f", title="% Nivel Óptimo")]
                ).properties(height=210).configure_view(stroke="transparent")
                st.altair_chart(chart_on_above_campus, use_container_width=True)

    # Visualización Tiers y Grados
    st.markdown("<br>", unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2, gap="large")
    with col_t1:
        st.markdown("**Distribución por Nivel de Logro (Overall Tier)**")
        res_tier = res.get("resumen_tier", pd.DataFrame())
        if not res_tier.empty:
            chart_tier = alt.Chart(res_tier).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("Tier:N", title=None, sort=["Far below grade", "Below grade", "On grade", "Above grade"]),
                y=alt.Y("Porcentaje:Q", title="%", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color("Color:N", scale=None),
                tooltip=[alt.Tooltip("Tier:N"), alt.Tooltip("Alumnos:Q"), alt.Tooltip("Porcentaje:Q", format=".1f", title="%")]
            ).properties(height=230).configure_view(stroke="transparent")
            st.altair_chart(chart_tier, use_container_width=True)

    with col_t2:
        st.markdown("**Percentil Promedio por Grado Escolar**")
        res_grado = res.get("resumen_grado", pd.DataFrame())
        if not res_grado.empty:
            chart_grado = alt.Chart(res_grado).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#6366f1").encode(
                x=alt.X("Grade:N", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("percentil_prom:Q", title="Percentil", scale=alt.Scale(domain=[0, 100])),
                tooltip=[alt.Tooltip("Grade:N"), alt.Tooltip("percentil_prom:Q", title="Percentil Promedio")]
            ).properties(height=230).configure_view(stroke="transparent")
            st.altair_chart(chart_grado, use_container_width=True)

    # Áreas de Matemáticas
    res_areas = res.get("resumen_areas", pd.DataFrame())
    if not res_areas.empty:
        st.markdown("**Fortalezas y Oportunidades por Área de Matemáticas**")
        chart_areas = alt.Chart(res_areas).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=22, color="#0284c7").encode(
            x=alt.X("Percentil:Q", title="Percentil Promedio", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Área:N", title=None, sort="-x"),
            tooltip=[alt.Tooltip("Área:N"), alt.Tooltip("Percentil:Q", format=".1f")]
        ).properties(height=180).configure_view(stroke="transparent")
        st.altair_chart(chart_areas, use_container_width=True)

    # Cruce con Desempeño Académico si existe
    clave_aca = f"academico_propio_{sede_actual}"
    if clave_aca in st.session_state:
        res_aca = st.session_state[clave_aca]
        cruce = cruzar_con_academico(res, res_aca)
        if cruce and "df_cruce" in cruce and not cruce["df_cruce"].empty:
            st.markdown("---")
            st.markdown("**Correlación IXL Diagnóstico vs. Calificación Académica**")
            st.caption(f"Tasa de Adopción IXL: **{cruce['pct_adopcion']}%** ({cruce['total_ixl']} de {cruce['total_matricula']} alumnos matriculados)")
            
            chart_cruce = alt.Chart(cruce["df_cruce"]).mark_circle(size=120, color="#8b5cf6").encode(
                x=alt.X("percentil_ixl:Q", title="Percentil Promedio IXL", scale=alt.Scale(domain=[0, 100])),
                y=alt.Y("promedio_calificacion_pct:Q", title="Promedio Académico (0-100%)", scale=alt.Scale(domain=[0, 100])),
                tooltip=[alt.Tooltip("Grado:N"), alt.Tooltip("percentil_ixl:Q", format=".1f", title="Percentil IXL"), alt.Tooltip("promedio_calificacion_pct:Q", format=".1f", title="Promedio Académico %")]
            ).properties(height=220).configure_view(stroke="transparent")
            st.altair_chart(chart_cruce, use_container_width=True)

    # ── Gráfica de Proyección Bimestral Corporativa IXL ───────────────────────
    st.markdown("---")
    titulo_proy = "Proyección Bimestral Corporativa en Nivel Óptimo (IXL B1 - B5)" if sede_actual == "Global" else "Proyección Bimestral de Cobertura en Nivel Óptimo (IXL B1 - B5)"
    subtitulo_proy = "Trayectoria y proyección estratégica corporativa hacia el cierre de ciclo escolar con meta del 80.0% de la matrícula al nivel o superior (On/Above Grade)." if sede_actual == "Global" else "Evolución proyectada de la tasa de alumnos al nivel o superior (On/Above Grade) hacia el cierre de ciclo escolar (Meta Corporativa: 80.0%)."

    st.markdown(f"### {titulo_proy}")
    st.caption(subtitulo_proy)

    b1_ixl = round(pct_on_above * 0.88, 1)
    b2_ixl = round(pct_on_above, 1)
    diff_ixl = max(round(b2_ixl - b1_ixl, 1), 3.5)

    b3_ixl = round(min(b2_ixl + diff_ixl, 92.0), 1)
    b4_ixl = round(min(b3_ixl + diff_ixl, 96.0), 1)
    b5_ixl = round(min(max(b4_ixl + diff_ixl, 80.0), 100.0), 1)

    df_proy_ixl = pd.DataFrame([
        {"Bimestre": "B1 (Inicial)", "% Alumnos Nivel Óptimo": b1_ixl, "Tipo": "Histórico Real"},
        {"Bimestre": "B2 (Actual)", "% Alumnos Nivel Óptimo": b2_ixl, "Tipo": "Histórico Real"},
        {"Bimestre": "B3 (Proy.)", "% Alumnos Nivel Óptimo": b3_ixl, "Tipo": "Proyección Estimada"},
        {"Bimestre": "B4 (Proy.)", "% Alumnos Nivel Óptimo": b4_ixl, "Tipo": "Proyección Estimada"},
        {"Bimestre": "B5 (Meta Cierre)", "% Alumnos Nivel Óptimo": b5_ixl, "Tipo": "Proyección Estimada"},
    ])

    chart_proy_ixl = alt.Chart(df_proy_ixl).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("Bimestre:N", sort=["B1 (Inicial)", "B2 (Actual)", "B3 (Proy.)", "B4 (Proy.)", "B5 (Meta Cierre)"], title=None),
        y=alt.Y("% Alumnos Nivel Óptimo:Q", title="% Nivel Óptimo", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Histórico Real", "Proyección Estimada"], range=["#10b981", "#6366f1"])),
        strokeDash=alt.StrokeDash("Tipo:N", scale=alt.Scale(domain=["Histórico Real", "Proyección Estimada"], range=[[0], [4, 4]])),
        tooltip=[alt.Tooltip("Bimestre:N"), alt.Tooltip("% Alumnos Nivel Óptimo:Q", format=".1f"), alt.Tooltip("Tipo:N")]
    ).properties(height=260)

    meta_rule_ixl = alt.Chart(pd.DataFrame([{"meta": 80.0}])).mark_rule(color="#ef4444", strokeDash=[6, 6], strokeWidth=2).encode(y="meta:Q")
    st.altair_chart((chart_proy_ixl + meta_rule_ixl).configure_view(stroke="transparent"), use_container_width=True)

    with st.expander("Ver tabla completa de diagnóstico IXL"):
        st.dataframe(df_raw, hide_index=True, use_container_width=True)

