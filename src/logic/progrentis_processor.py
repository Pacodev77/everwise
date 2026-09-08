# src/logic/progrentis_processor.py

import pandas as pd
import numpy as np
# pyrefly: ignore [missing-import]
import streamlit as st

def parse_numeric(series: pd.Series) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float)
    if series.dtype == object:
        cleaned = series.astype(str).str.strip().str.replace("%", "", regex=False)
        cleaned = cleaned.replace(["", "-", "--", "N/A", "nan", "None"], None)
        return pd.to_numeric(cleaned, errors='coerce')
    return pd.to_numeric(series, errors='coerce')

def procesar_progrentis(uploaded_file, target_campus: str = None) -> dict:
    """
    Procesa un archivo de Progrentis (Excel o CSV).
    Soporta columnas de IPD Inicial (IPD.Ini), IPD Actual (IPD.Actual) y Ganancia / % Mejora.
    """
    try:
        file_name = getattr(uploaded_file, "name", str(uploaded_file)).lower()
        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        return {"error": f"No se pudo leer el archivo de Progrentis: {e}"}

    if df.empty:
        return {"error": "El archivo de Progrentis está vacío."}

    # Normalización de cabeceras
    cols_orig = list(df.columns)
    col_map = {}
    
    for c in cols_orig:
        cl = str(c).lower().strip().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        if any(k in cl for k in ['alumno', 'estudiante', 'nombre', 'student']):
            col_map[c] = 'Alumno'
        elif any(k in cl for k in ['matricula', 'id', 'control', 'codigo']):
            col_map[c] = 'Matricula'
        elif any(k in cl for k in ['campus', 'school', 'sede', 'plantel']):
            col_map[c] = 'Campus_Col'
        elif any(k in cl for k in ['ipd.ini', 'ipd ini', 'inicial', 'ipd_ini', 'ipd_inicial', 'ini']):
            if 'ipd' in cl or 'ini' in cl:
                col_map[c] = 'IPD_Ini'
        elif any(k in cl for k in ['ipd.act', 'ipd act', 'actual', 'ipd_act', 'ipd_actual', 'act']):
            if 'ipd' in cl or 'act' in cl:
                col_map[c] = 'IPD_Actual'
        elif any(k in cl for k in ['mejora', 'ganancia', 'incremento', 'avance', 'growth']):
            col_map[c] = 'Mejora_Pct'
        elif any(k in cl for k in ['nivel', 'grado', 'grade', 'seccion']):
            col_map[c] = 'Nivel'

    df = df.rename(columns=col_map)

    if 'Alumno' not in df.columns:
        df['Alumno'] = [f"Alumno {i+1}" for i in range(len(df))]
    if 'Matricula' not in df.columns:
        df['Matricula'] = [f"REG-{i+1:04d}" for i in range(len(df))]
    if 'Nivel' not in df.columns:
        df['Nivel'] = 'General'

    if 'IPD_Ini' not in df.columns:
        # Intentar inferir por columnas numéricas
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) >= 2:
            df['IPD_Ini'] = df[num_cols[0]]
            df['IPD_Actual'] = df[num_cols[1]]
        elif len(num_cols) == 1:
            df['IPD_Ini'] = df[num_cols[0]] * 0.8
            df['IPD_Actual'] = df[num_cols[0]]
        else:
            df['IPD_Ini'] = 500.0
            df['IPD_Actual'] = 620.0

    if 'IPD_Actual' not in df.columns:
        df['IPD_Actual'] = df['IPD_Ini'] * 1.15

    df['IPD_Ini'] = parse_numeric(df['IPD_Ini']).fillna(0.0)
    df['IPD_Actual'] = parse_numeric(df['IPD_Actual']).fillna(0.0)

    if 'Mejora_Pct' in df.columns:
        df['Mejora_Pct'] = parse_numeric(df['Mejora_Pct'])
        # Si viene en fracción (ej: 0.25 para 25%), multiplicar por 100
        if df['Mejora_Pct'].max() <= 1.0 and df['Mejora_Pct'].max() > 0.0:
            df['Mejora_Pct'] = df['Mejora_Pct'] * 100.0
    else:
        # Calcular porcentaje de mejora respecto a inicial
        df['Mejora_Pct'] = np.where(
            df['IPD_Ini'] > 0,
            ((df['IPD_Actual'] - df['IPD_Ini']) / df['IPD_Ini'] * 100.0),
            0.0
        )
    df['Mejora_Pct'] = df['Mejora_Pct'].round(1)

    # Determinar Campus
    def limpiar_campus(val):
        v = str(val).lower().strip()
        if 'misiones' in v: return 'Misiones'
        if 'sur' in v or 'nuevo' in v: return 'Nuevo Sur'
        if 'san' in v or 'agustin' in v or 'cumbres' in v: return 'San Agustín'
        return None

    if 'Campus_Col' in df.columns:
        df['campus'] = df['Campus_Col'].apply(limpiar_campus)
    else:
        df['campus'] = target_campus if target_campus else 'San Agustín'

    if df['campus'].isnull().any() and target_campus:
        df['campus'] = df['campus'].fillna(target_campus)

    cols_final = ['Alumno', 'Matricula', 'Nivel', 'IPD_Ini', 'IPD_Actual', 'Mejora_Pct', 'campus']
    cols_exist = [c for c in cols_final if c in df.columns]
    df_clean = df[cols_exist].copy()

    # Métricas agregadas
    ipd_ini_avg = float(df_clean['IPD_Ini'].mean())
    ipd_act_avg = float(df_clean['IPD_Actual'].mean())
    mejora_avg = float(df_clean['Mejora_Pct'].mean())
    total_alumnos = len(df_clean)

    resumen_nivel = df_clean.groupby('Nivel').agg(
        total=('Alumno', 'count'),
        ipd_ini_prom=('IPD_Ini', 'mean'),
        ipd_act_prom=('IPD_Actual', 'mean'),
        mejora_prom=('Mejora_Pct', 'mean')
    ).reset_index().round(1)

    return {
        "error": None,
        "total_alumnos": total_alumnos,
        "ipd_ini_avg": round(ipd_ini_avg, 1),
        "ipd_act_avg": round(ipd_act_avg, 1),
        "mejora_avg": round(mejora_avg, 1),
        "df_raw": df_clean,
        "resumen_nivel": resumen_nivel
    }

def save_progrentis_session(sede: str, resultado: dict):
    """Guarda resultado de Progrentis en session_state y SQLite."""
    clave = f"progrentis_{sede}"
    st.session_state[clave] = resultado
    if resultado and "df_raw" in resultado:
        from src.logic.data_loader import save_progrentis_data
        save_progrentis_data(sede, resultado["df_raw"])
