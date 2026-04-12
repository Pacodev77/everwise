import streamlit as st
import pandas as pd
from src.logic.asistencia_engine import procesar_log_asistencia
import sys
import subprocess

def render_asistencia_uploader(sede_actual):
    """
    Herramienta exclusiva de Campus bottom-up para entrenar el motor de asistencia
    con bitácoras de tránsitos crudos / biometría.
    """
    with st.expander(f"Cargar Log Biométrico / Asistencia en {sede_actual}", expanded=False):
        st.markdown(f"**Motor Inteligente de Datos ({sede_actual})**: Despliega un archivo CSV o Excel del reloj checador / scanner. El motor buscará limpiarlo, relacionarlo y medir asistencias automáticamente.")
        uploaded_file = st.file_uploader(f"Cargar Bitácora", type=["csv", "xlsx", "xls"], key=f"asist_{sede_actual}")
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_raw = pd.read_csv(uploaded_file, header=0) # raw log files usually have header at 0
                else:
                    try:
                        df_raw = pd.read_excel(uploaded_file, header=0)
                    except ImportError:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--user"])
                        st.error("Reiniciando motor de excel. Presiona Ctrl+C y vuelve a correr Streamlit.")
                        st.stop()
                        
                # Mandar a Inteligencia Algorítmica
                df_niveles, staff_kpi = procesar_log_asistencia(df_raw)
                
                if not df_niveles.empty:
                    st.success(f"Motor completado. Se procesaron {len(df_raw)} registros de tráficos exitosamente.")
                    st.session_state[f"asistencia_data_{sede_actual}"] = {
                        "niveles": df_niveles,
                        "staff": staff_kpi
                    }
                else:
                    st.warning("No se lograron extraer alumnos o métricas lógicas de este archivo.")

            except Exception as e:
                st.error(f"Fallo crítico en reconocimiento inteligente: {e}")
                
    # Retorna los datos si los encontró (para consumo inmediato)
    if f"asistencia_data_{sede_actual}" in st.session_state:
        return st.session_state[f"asistencia_data_{sede_actual}"]
    return None
