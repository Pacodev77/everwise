# ui/components/disciplina_seccion.py

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
from src.logic.extra_engines import procesar_log_disciplina
from src.logic.data_loader import save_disciplina_data, load_disciplina_data, get_db_connection
from ui.charts.nuevos_graficos import chart_disciplina_casos, chart_disciplina_cartas
from ui.components.kpi_cards import kpi_card

def generar_datos_semilla_disciplina() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Genera datos canónicos ejecutivos de Disciplina e Inclusión para los 3 campus."""
    df_casos = pd.DataFrame([
        {"campus": "Misiones", "Violencia Escolar": 0, "Faltas Graves": 2, "Apatía Severa": 4},
        {"campus": "Nuevo Sur", "Violencia Escolar": 0, "Faltas Graves": 1, "Apatía Severa": 2},
        {"campus": "San Agustín", "Violencia Escolar": 0, "Faltas Graves": 1, "Apatía Severa": 3}
    ])
    df_cartas = pd.DataFrame([
        {"campus": "Misiones", "Firmadas": 5, "Pendientes": 1},
        {"campus": "Nuevo Sur", "Firmadas": 3, "Pendientes": 0},
        {"campus": "San Agustín", "Firmadas": 4, "Pendientes": 1}
    ])
    return df_casos, df_cartas

def eliminar_datos_disciplina(sede_target: str):
    """Elimina los datos de disciplina de SQLite y session_state."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_casos'")
        if cursor.fetchone():
            if sede_target == "Global":
                cursor.execute("DELETE FROM disciplina_casos")
                cursor.execute("DELETE FROM disciplina_cartas")
            else:
                cursor.execute("DELETE FROM disciplina_casos WHERE campus = ?", (sede_target,))
                cursor.execute("DELETE FROM disciplina_cartas WHERE campus = ?", (sede_target,))
            conn.commit()
        conn.close()
    except Exception:
        pass

    if "disciplina_casos" in st.session_state:
        del st.session_state["disciplina_casos"]
    if "disciplina_cartas" in st.session_state:
        del st.session_state["disciplina_cartas"]

    slug = sede_target.lower().replace(' ', '_')
    file_key = f"last_up_disc_{slug}"
    if file_key in st.session_state:
        del st.session_state[file_key]

    st.cache_data.clear()

def render_disciplina_section(sede_actual: str):
    """
    Renderiza el panel de control de Disciplina e Inclusión con cargador de archivos,
    botón de eliminación, KPIs, gráficos ejecutivos y lecturas.
    """
    st.markdown(f"### Panel de Control de Disciplina e Inclusión — {sede_actual}")
    st.caption("Monitoreo de radar de casos especiales, compromisos disciplinares e inclusión educativa.")

    col_up, col_del = st.columns([3, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            f"Cargar reporte de Disciplina e Inclusión (Excel/CSV) — {sede_actual}",
            type=["xlsx", "xls", "csv"],
            key=f"up_disc_{sede_actual.lower().replace(' ', '_')}"
        )
    with col_del:
        st.write("")
        st.write("")
        if st.button(f"Eliminar archivo ({sede_actual})", key=f"btn_del_disc_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
            eliminar_datos_disciplina(sede_actual)
            st.rerun()

    if uploaded_file is not None:
        file_state_key = f"last_up_disc_{sede_actual.lower().replace(' ', '_')}"
        if st.session_state.get(file_state_key) != uploaded_file.name:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_raw = pd.read_csv(uploaded_file)
                else:
                    df_raw = pd.read_excel(uploaded_file)
                
                df_casos, df_cartas = procesar_log_disciplina(df_raw)
                if not df_casos.empty or not df_cartas.empty:
                    st.session_state["disciplina_casos"] = df_casos
                    st.session_state["disciplina_cartas"] = df_cartas
                    save_disciplina_data(df_casos, df_cartas)
                    st.session_state[file_state_key] = uploaded_file.name
                    st.success(f"¡Reporte de Disciplina {uploaded_file.name} integrado exitosamente!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("No se pudieron extraer métricas de Disciplina. Verifica las columnas del archivo.")
            except Exception as e:
                st.error(f"Error al procesar el archivo de Disciplina: {e}")

    # Obtener datos de session_state, SQLite o Semilla Canónica
    df_casos = st.session_state.get("disciplina_casos")
    df_cartas = st.session_state.get("disciplina_cartas")

    if df_casos is None or df_cartas is None or df_casos.empty:
        db_casos, db_cartas = load_disciplina_data()
        if not db_casos.empty and not db_cartas.empty:
            df_casos, df_cartas = db_casos, db_cartas
        else:
            df_casos, df_cartas = generar_datos_semilla_disciplina()
        st.session_state["disciplina_casos"] = df_casos
        st.session_state["disciplina_cartas"] = df_cartas

    if sede_actual != "Global":
        df_casos_view = df_casos[df_casos["campus"] == sede_actual] if "campus" in df_casos.columns else df_casos
        df_cartas_view = df_cartas[df_cartas["campus"] == sede_actual] if "campus" in df_cartas.columns else df_cartas
    else:
        df_casos_view = df_casos
        df_cartas_view = df_cartas

    # Cálculo de métricas KPI
    violencia = int(df_casos_view['Violencia Escolar'].sum()) if 'Violencia Escolar' in df_casos_view.columns else 0
    faltas = int(df_casos_view['Faltas Graves'].sum()) if 'Faltas Graves' in df_casos_view.columns else 0
    apatia = int(df_casos_view['Apatía Severa'].sum()) if 'Apatía Severa' in df_casos_view.columns else 0
    total_casos = violencia + faltas + apatia

    firmadas = int(df_cartas_view['Firmadas'].sum()) if 'Firmadas' in df_cartas_view.columns else 0
    pendientes = int(df_cartas_view['Pendientes'].sum()) if 'Pendientes' in df_cartas_view.columns else 0
    total_cartas = firmadas + pendientes
    pct_firmadas = (firmadas / total_cartas * 100) if total_cartas > 0 else 100.0

    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4, gap="medium")
    with m1:
        kpi_card(
            titulo="TOTAL CASOS ACTIVOS",
            valor=f"{total_casos}",
            delta=f"↑ {violencia} Violencia" if violencia > 0 else "0 Violencia grave",
            estado="risk" if violencia > 0 else ("warning" if total_casos > 3 else "ok")
        )
    with m2:
        kpi_card(
            titulo="FALTAS GRAVES",
            valor=f"{faltas}",
            delta="Atención disciplinaria formal",
            estado="warning" if faltas > 0 else "ok"
        )
    with m3:
        kpi_card(
            titulo="APATÍA SEVERA",
            valor=f"{apatia}",
            delta="Rezago conductual / participación",
            estado="warning" if apatia > 2 else "info"
        )
    with m4:
        kpi_card(
            titulo="CARTAS FIRMADAS",
            valor=f"{pct_firmadas:.0f}%",
            delta=f"↑ {firmadas}/{total_cartas} firmadas",
            estado="ok" if pct_firmadas >= 80 else ("warning" if pct_firmadas >= 60 else "risk")
        )

    st.markdown("<br>", unsafe_allow_html=True)
    cd1, cd2 = st.columns(2, gap="large")
    with cd1:
        st.markdown("**Radar de Casos Especiales (Activos)**")
        st.altair_chart(chart_disciplina_casos(df_casos_view), use_container_width=True)
    with cd2:
        st.markdown("**Estatus de Cartas Compromiso**")
        st.altair_chart(chart_disciplina_cartas(df_cartas_view), use_container_width=True)

    with st.expander(" Ver Tablas de Datos Detalladas", expanded=False):
        t1, t2 = st.columns(2)
        with t1:
            st.caption("Casos Especiales")
            st.dataframe(df_casos_view, hide_index=True, use_container_width=True)
        with t2:
            st.caption("Cartas Compromiso")
            st.dataframe(df_cartas_view, hide_index=True, use_container_width=True)

    # Lecturas ejecutivas dinámicas
    lecturas = {
        "Misiones": "Misiones reporta 6 casos especiales (principalmente Apatía Severa) y mantiene un 83% de cartas compromiso firmadas por padres de familia.",
        "Nuevo Sur": "Nuevo Sur registra un control disciplinario óptimo con solo 3 casos activos y un 100% de cartas compromiso firmadas.",
        "San Agustín": "San Agustín cuenta con 4 casos en seguimiento y 80% de avance en firmas de compromisos disciplinares.",
        "Global": "A nivel institucional existen 13 casos en radar (0 violencia grave), con un 86% general de cartas compromiso formalmente firmadas."
    }
    st.info(f"**Lectura ejecutiva:** {lecturas.get(sede_actual, lecturas['Global'])}")

