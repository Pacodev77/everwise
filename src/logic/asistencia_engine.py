# src/logic/asistencia_engine.py

import pandas as pd
from src.logic.normalizar_asistencia import (
    procesar_archivo_asistencia,
    convertir_canonico_a_agregado
)

def procesar_log_asistencia(df_or_buffer, campus=None):
    """
    Wrapper compatible para procesar archivos de asistencia utilizando el nuevo motor normalizador.
    Soporta tanto buffers de archivos como DataFrames de pandas.
    """
    import io
    # Si recibimos un DataFrame (antiguo formato de Streamlit), lo escribimos en memoria
    # como Excel para que el motor de hojas múltiples funcione correctamente.
    if isinstance(df_or_buffer, pd.DataFrame):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_or_buffer.to_excel(writer, index=False, header=False)
        buffer.seek(0)
        file_input = buffer
    else:
        file_input = df_or_buffer
        
    df_canon, reporte = procesar_archivo_asistencia(file_input, campus or "Desconocido")
    
    df_res = reporte.get("resumen_diario_nivel", pd.DataFrame())
    
    df_niveles, staff_kpi, extra_info = convertir_canonico_a_agregado(df_canon, df_res, campus or "Desconocido")
    
    # Inyectar el reporte de validación en extra_info para que el uploader pueda mostrarlo
    extra_info["reporte_validacion"] = reporte
    
    return df_niveles, staff_kpi, extra_info
