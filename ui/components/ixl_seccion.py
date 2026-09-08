# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
import altair as alt
import pandas as pd
from src.logic.ixl_processor import procesar_ixl, acumular_ixl, cruzar_con_academico

def render_ixl_section(sede_actual: str):
    clave = f"ixl_{sede_actual}"

    st.markdown("#### Diagnóstico IXL Math")
    uploaded = st.file_uploader(
        "Cargar reporte IXL (CSV)",
        type=["csv"],
        key=f"up_ixl_{sede_actual.lower().replace(' ', '_')}"
    )

    if uploaded is not None:
        resultado = procesar_ixl(uploaded)
        if resultado["error"]:
            st.error(resultado["error"])
            return
        acumular_ixl(sede_actual, resultado)
        st.success(f"{resultado['total_alumnos']} alumnos procesados")

    if clave not in st.session_state:
        st.info("Sube el reporte IXL para ver el diagnóstico de Math.")
        return

    res = st.session_state[clave]

    # ── Barra de reporte activo y botón de eliminación ──────────────
    col_info, col_del = st.columns([3, 1])
    with col_info:
        st.caption(f"Reporte IXL activo: **{sede_actual}** ({res['total_alumnos']} alumnos)")
    with col_del:
        if st.button(f"Eliminar archivo ({sede_actual})", key=f"del_ixl_sec_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
            from ui.components.uso_aplicaciones_seccion import eliminar_datos_ixl
            eliminar_datos_ixl(sede_actual)
            st.rerun()

    # ── KPIs rápidos ──────────────────────────────────────────────
    df_tier  = res["resumen_tier"]
    df_grado = res["resumen_grado"]

    on_above = df_tier[df_tier["Tier"].isin(["On grade","Above grade"])]["Alumnos"].sum()
    total    = res["total_alumnos"]
    pct_ok   = round(on_above / total * 100, 1)

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Total alumnos", total)
    with k2:
        st.metric("En nivel o superior", f"{pct_ok}%",
                  delta="On/Above grade")
    with k3:
        mejor_grado = df_grado.loc[df_grado["pct_on_above"].idxmax(), "Grade"]
        st.metric("Mejor grado", mejor_grado)

    # ── Distribución de tiers ──────────────────────────────────────
    st.markdown("**Distribución por nivel de desempeño**")
    chart_tier = alt.Chart(df_tier).mark_bar(
        cornerRadiusTopLeft=6, cornerRadiusTopRight=6
    ).encode(
        x=alt.X("Tier:N", title=None,
                sort=["Far below grade","Below grade","On grade","Above grade"]),
        y=alt.Y("Porcentaje:Q", title="%", scale=alt.Scale(domain=[0,100])),
        color=alt.Color("Color:N", scale=None),
        tooltip=[
            alt.Tooltip("Tier:N", title="Nivel"),
            alt.Tooltip("Alumnos:Q"),
            alt.Tooltip("Porcentaje:Q", format=".1f", title="%")
        ]
    ).properties(height=220).configure_view(stroke="transparent")
    st.altair_chart(chart_tier, use_container_width=True)

    # ── Percentil por grado ────────────────────────────────────────
    st.markdown("**% en nivel o superior por grado**")
    chart_grado = alt.Chart(df_grado).mark_bar(
        cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#3b82f6"
    ).encode(
        x=alt.X("Grade:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pct_on_above:Q", title="%", scale=alt.Scale(domain=[0,100])),
        tooltip=[
            alt.Tooltip("Grade:N", title="Grado"),
            alt.Tooltip("total:Q", title="Alumnos"),
            alt.Tooltip("pct_on_above:Q", format=".1f", title="% On/Above")
        ]
    ).properties(height=220).configure_view(stroke="transparent")
    st.altair_chart(chart_grado, use_container_width=True)

    # ── Áreas de Math ──────────────────────────────────────────────
    st.markdown("**Fortalezas y áreas de oportunidad en Math**")
    df_areas = res["resumen_areas"]
    chart_areas = alt.Chart(df_areas).mark_bar(
        cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#6366f1"
    ).encode(
        x=alt.X("Percentil:Q", title="Percentil promedio"),
        y=alt.Y("Área:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("Área:N"),
            alt.Tooltip("Percentil:Q", format=".1f")
        ]
    ).properties(height=240).configure_view(stroke="transparent")
    st.altair_chart(chart_areas, use_container_width=True)

    # ── Tabla detalle ──────────────────────────────────────────────
    with st.expander("Ver tabla completa de alumnos"):
        cols_mostrar = ["First name", "Last name", "Grade",
                        "Overall percentile", "Overall tier"]
        st.dataframe(
            res["df_raw"][cols_mostrar].sort_values(
                "Overall percentile", ascending=False
            ),
            hide_index=True,
            use_container_width=True
        )

def render_adopcion_y_correlacion(sede_actual: str):
    """Muestra Métricas de Adopción y Relación Práctica vs Resultados con datos reales."""
    clave_ixl = f"ixl_{sede_actual}"
    clave_aca = f"academico_propio_{sede_actual}"

    if clave_ixl not in st.session_state or clave_aca not in st.session_state:
        st.info("Sube tanto el archivo de calificaciones (tab Desempeño Académico) "
                 "como el reporte IXL para ver esta comparación.")
        return

    res_ixl = st.session_state[clave_ixl]
    res_aca = st.session_state[clave_aca]
    cruce = cruzar_con_academico(res_ixl, res_aca)

    if cruce is None or cruce["df_cruce"].empty:
        st.warning("No se pudo cruzar la información por grado. Verifica que ambos "
                   "archivos correspondan al mismo campus.")
        return

    st.markdown("### Uso de IXL y su Relación con Resultados Académicos")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("**Métricas de Adopción**")
        df_adopcion = pd.DataFrame([
            {"Estado": "Con práctica IXL", "Alumnos": cruce["total_ixl"]},
            {"Estado": "Sin registro", "Alumnos": max(cruce["total_matricula"] - cruce["total_ixl"], 0)}
        ])
        chart_adopcion = alt.Chart(df_adopcion).mark_bar(
            cornerRadiusTopLeft=6, cornerRadiusTopRight=6
        ).encode(
            x=alt.X("Estado:N", title=None),
            y=alt.Y("Alumnos:Q", title="Alumnos"),
            color=alt.Color("Estado:N",
                scale=alt.Scale(domain=["Con práctica IXL", "Sin registro"],
                                range=["#3b82f6", "#cbd5e1"]),
                legend=None),
            tooltip=["Estado:N", "Alumnos:Q"]
        ).properties(height=240).configure_view(stroke="transparent")
        st.altair_chart(chart_adopcion, use_container_width=True)
        st.caption(f"{cruce['pct_adopcion']}% de adopción "
                   f"({cruce['total_ixl']} de {cruce['total_matricula']} alumnos)")

    with col2:
        st.markdown("**Relación: Práctica IXL vs Resultado Académico**")
        df_c = cruce["df_cruce"]
        chart_corr = alt.Chart(df_c).mark_circle(size=120, color="#3b82f6").encode(
            x=alt.X("percentil_ixl:Q", title="Percentil promedio IXL"),
            y=alt.Y("promedio_calificacion_pct:Q", title="Promedio Math (%)"),
            tooltip=[
                alt.Tooltip("Grado:N"),
                alt.Tooltip("percentil_ixl:Q", format=".1f", title="Percentil IXL"),
                alt.Tooltip("promedio_calificacion_pct:Q", format=".1f", title="Promedio Math")
            ]
        )
        linea_tendencia = chart_corr.transform_regression(
            "percentil_ixl", "promedio_calificacion_pct"
        ).mark_line(color="#1d4ed8", strokeDash=[4, 4])

        st.altair_chart(
            (chart_corr + linea_tendencia).properties(height=240).configure_view(stroke="transparent"),
            use_container_width=True
        )
        st.caption("Cada punto representa un grado. La línea muestra la tendencia general.")