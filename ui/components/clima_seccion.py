# ui/components/clima_seccion.py

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
from src.logic.clima_engine import procesar_log_clima
from src.logic.data_loader import save_clima_data, load_clima_heatmap, get_db_connection
from ui.charts.nuevos_graficos import chart_clima_heatmap, chart_clima_barras

def generar_datos_semilla_clima() -> pd.DataFrame:
    """Genera datos canónicos ejecutivos de Clima Escolar para los 3 campus."""
    records = []
    campuses = ["Misiones", "Nuevo Sur", "San Agustín"]
    categorias = [
        ("Estrés Acumulado", 0.15, 0.45, 0.40),
        ("Motivación", 0.72, 0.22, 0.06),
        ("Sentido de Pertenencia", 0.80, 0.16, 0.04),
        ("Seguridad Física", 0.88, 0.10, 0.02)
    ]
    
    for campus in campuses:
        for cat, p_siempre, p_aveces, p_nunca in categorias:
            # Variaciones sutiles por campus
            if campus == "Nuevo Sur" and cat == "Motivación":
                p_siempre, p_aveces, p_nunca = 0.78, 0.18, 0.04
            elif campus == "San Agustín" and cat == "Estrés Acumulado":
                p_siempre, p_aveces, p_nunca = 0.12, 0.48, 0.40
                
            records.extend([
                {"campus": campus, "Categoría": cat, "Respuesta": "Siempre", "Proporción": p_siempre},
                {"campus": campus, "Categoría": cat, "Respuesta": "A veces", "Proporción": p_aveces},
                {"campus": campus, "Categoría": cat, "Respuesta": "Nunca", "Proporción": p_nunca}
            ])
            
    return pd.DataFrame(records)

def eliminar_datos_clima(sede_target: str):
    """Elimina los datos de clima escolar de SQLite y session_state."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clima_data'")
        if cursor.fetchone():
            if sede_target == "Global":
                cursor.execute("DELETE FROM clima_data")
            else:
                cursor.execute("DELETE FROM clima_data WHERE campus = ?", (sede_target,))
            conn.commit()
        conn.close()
    except Exception:
        pass

    if "clima_data_global" in st.session_state:
        del st.session_state["clima_data_global"]

    slug = sede_target.lower().replace(' ', '_')
    file_key = f"last_up_clima_{slug}"
    if file_key in st.session_state:
        del st.session_state[file_key]

    st.cache_data.clear()

def render_clima_section(sede_actual: str):
    """
    Renderiza la sección de Clima Escolar (ICE) con cargador de archivos, 
    botón de eliminación y visualizaciones.
    """
    st.markdown(f"### Mapa de Calor - Indicador de Clima Escolar (ICE) — {sede_actual}")
    st.caption("Evaluación del clima institucional, sentido de pertenencia y bienestar emocional.")

    col_up, col_del = st.columns([3, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            f"Cargar reporte de Clima Escolar (Excel/CSV) — {sede_actual}",
            type=["xlsx", "xls", "csv"],
            key=f"up_clima_{sede_actual.lower().replace(' ', '_')}"
        )
    with col_del:
        st.write("")
        st.write("")
        if st.button(f"Eliminar archivo ({sede_actual})", key=f"btn_del_clima_{sede_actual.lower().replace(' ', '_')}", use_container_width=True, type="secondary"):
            eliminar_datos_clima(sede_actual)
            st.rerun()

    if uploaded_file is not None:
        file_state_key = f"last_up_clima_{sede_actual.lower().replace(' ', '_')}"
        if st.session_state.get(file_state_key) != uploaded_file.name:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_raw = pd.read_csv(uploaded_file)
                else:
                    df_raw = pd.read_excel(uploaded_file)
                
                df_clima = procesar_log_clima(df_raw)
                if not df_clima.empty:
                    st.session_state["clima_data_global"] = df_clima
                    save_clima_data(df_clima)
                    st.session_state[file_state_key] = uploaded_file.name
                    st.success(f"¡Reporte de Clima Escolar {uploaded_file.name} integrado exitosamente!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("No se pudieron extraer métricas de Clima Escolar. Verifica las columnas del archivo.")
            except Exception as e:
                st.error(f"Error al procesar el archivo de Clima Escolar: {e}")

    # Obtener datos de session_state o SQLite para el ciclo activo
    ciclo_activo = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    df_clima_global = st.session_state.get("clima_data_global")
    if df_clima_global is None or df_clima_global.empty:
        df_clima_global = load_clima_heatmap(ciclo_activo)
        if (df_clima_global is None or df_clima_global.empty) and ciclo_activo == "2025 - 2026":
            df_clima_global = generar_datos_semilla_clima()
            st.session_state["clima_data_global"] = df_clima_global

    df_clima = pd.DataFrame()
    if df_clima_global is not None and not df_clima_global.empty:
        df_clima = df_clima_global if sede_actual == "Global" else df_clima_global[df_clima_global['campus'] == sede_actual]

    if not df_clima.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.altair_chart(chart_clima_heatmap(df_clima), use_container_width=True)
        st.markdown("### Distribución de Respuestas")
        st.altair_chart(chart_clima_barras(df_clima), use_container_width=True)
    else:
        st.info(f"No hay reportes de Clima Escolar registrados para el Ciclo Escolar {ciclo_activo} en {sede_actual}.")
