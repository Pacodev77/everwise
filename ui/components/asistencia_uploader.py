# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import io
from src.logic.asistencia_engine import procesar_log_asistencia
from src.logic.data_loader import save_attendance_data, delete_attendance_data

def render_asistencia_uploader(sede_actual):
    """
    Herramienta para cargar reportes ejecutivos consolidados de asistencia
    o bitácoras biométricas.
    """
    with st.expander(f"Cargar Reporte o Log de Asistencia ({sede_actual})", expanded=False):
        st.markdown(
            f"**Motor Inteligente de Asistencia ({sede_actual})**: Sube el archivo Excel o CSV (Reporte mensual por campus o bitácora de checador). "
            f"El sistema detecta automáticamente la estructura, calcula asistencias por nivel y extrae métricas de colaboradores."
        )
        uploaded_file = st.file_uploader(
            f"Cargar archivo de asistencia", 
            type=["csv", "xlsx", "xls", "tsv", "txt"], 
            key=f"asist_{sede_actual.lower().replace(' ', '_')}"
        )
        
        if uploaded_file is not None:
            try:
                # Leer el archivo con manejo flexible de delimitadores
                df_raw = None
                file_input = None
                if uploaded_file.name.endswith(('.xlsx', '.xls')):
                    uploaded_file.seek(0)
                    file_input = uploaded_file
                    df_raw = pd.DataFrame()  # Dummy para pasar validación de lectura
                else:
                    # CSV / TSV / TXT
                    bytes_data = uploaded_file.getvalue()
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                        try:
                            # Probar detección automática de delimitador
                            df_raw = pd.read_csv(io.BytesIO(bytes_data), sep=None, engine='python', header=None, encoding=encoding)
                            break
                        except Exception:
                            try:
                                df_raw = pd.read_csv(io.BytesIO(bytes_data), sep=',', header=None, encoding=encoding)
                                break
                            except Exception:
                                pass
                    file_input = df_raw
                                
                if df_raw is None:
                    st.error("No se pudo leer el archivo. Verifica el formato e intenta nuevamente.")
                else:
                    # Procesar con el motor inteligente
                    df_niveles, staff_kpi, extra_info = procesar_log_asistencia(file_input, sede_actual)
                    
                    sedes_afectadas = []
                    if extra_info.get("es_matriz") and extra_info.get("campuses"):
                        # Se detectó una matriz multi-campus
                        campuses_encontrados = list(extra_info["campuses"].keys())
                        for c_name, c_data in extra_info["campuses"].items():
                            if c_name != "Global":
                                st.session_state[f"asistencia_data_{c_name}"] = {
                                    "niveles": c_data["niveles"],
                                    "staff": c_data["staff"],
                                    "staff_desglose": c_data.get("staff_desglose", {}),
                                    "dias_alumnos": c_data.get("dias_alumnos"),
                                    "dias_staff": c_data.get("dias_staff"),
                                    "kpi_general": c_data.get("kpi_general"),
                                    "alumnos_counts": c_data.get("alumnos_counts", {}),
                                    "asistencia_counts": c_data.get("asistencia_counts", {})
                                }
                                save_attendance_data(c_name, c_data["niveles"], c_data["staff"], df_canonico=c_data.get("df_canonico"), df_resumen=c_data.get("df_resumen"))
                                sedes_afectadas.append(c_name)
                        
                        if sedes_afectadas:
                            nombres_sedes = ", ".join(sedes_afectadas)
                            st.success(
                                f"Reporte consolidado procesado exitosamente. "
                                f"Se actualizaron los registros de asistencia para: **{nombres_sedes}**."
                            )
                        else:
                            st.success("Reporte de asistencia procesado exitosamente.")
                    elif not df_niveles.empty or (extra_info.get("df_resumen") is not None and not extra_info["df_resumen"].empty):
                        st.session_state[f"asistencia_data_{sede_actual}"] = {
                            "niveles": df_niveles,
                            "staff": staff_kpi,
                            "staff_desglose": extra_info.get("staff_desglose", {}),
                            "dias_alumnos": extra_info.get("dias_alumnos"),
                            "dias_staff": extra_info.get("dias_staff"),
                            "kpi_general": extra_info.get("kpi_general"),
                            "alumnos_counts": extra_info.get("alumnos_counts", {}),
                            "asistencia_counts": extra_info.get("asistencia_counts", {})
                        }
                        save_attendance_data(sede_actual, df_niveles, staff_kpi, df_canonico=extra_info.get("df_canonico"), df_resumen=extra_info.get("df_resumen"))
                        st.success(f"Asistencia de {sede_actual} procesada y guardada exitosamente.")
                    else:
                        st.warning("No se lograron extraer niveles o métricas lógicas de este archivo.")
                        
                    # Mostrar reporte de validación interactivo si está disponible
                    reporte = extra_info.get("reporte_validacion")
                    if reporte:
                        st.markdown("### Reporte de Normalización y Validación")
                        
                        # Hojas procesadas
                        st.write("**Hojas Procesadas:**")
                        for h in reporte["hojas_procesadas"]:
                            st.success(f"✔️ Hoja **{h['hoja']}** (Firma: {h['firma']}): {h['filas_cargadas']} filas procesadas.")
                            
                        # Hojas ignoradas
                        if reporte["hojas_ignoradas"]:
                            st.write("**Hojas Ignoradas (Pivot tables o desconocidas):**")
                            for h in reporte["hojas_ignoradas"]:
                                st.info(f"ℹ️ Hoja **{h['hoja']}** ignorada: {h['motivo']}")
                                
                        # Valores no mapeados
                        if reporte["valores_no_mapeados"]:
                            with st.expander("⚠️ Valores de nivel no mapeados (marcardos como SIN_MAPEAR)", expanded=False):
                                df_unmapped = pd.DataFrame(reporte["valores_no_mapeados"])
                                st.dataframe(df_unmapped, hide_index=True, use_container_width=True)
                                
                        # Filas rechazadas
                        if reporte["filas_rechazadas"]:
                            with st.expander("❌ Filas rechazadas por error de parseo (no cargadas)", expanded=False):
                                df_rejected = pd.DataFrame(reporte["filas_rechazadas"])
                                st.dataframe(df_rejected, hide_index=True, use_container_width=True)

            except Exception as e:
                st.error(f"Fallo en procesamiento de asistencia: {e}")

        # Opción de eliminación / reset
        if f"asistencia_data_{sede_actual}" in st.session_state:
            st.markdown("---")
            if st.button("Eliminar datos de asistencia cargados", key=f"del_asist_{sede_actual.lower().replace(' ', '_')}", use_container_width=True):
                del st.session_state[f"asistencia_data_{sede_actual}"]
                delete_attendance_data(sede_actual)
                st.rerun()
                
    if f"asistencia_data_{sede_actual}" in st.session_state:
        return st.session_state[f"asistencia_data_{sede_actual}"]
    return None

