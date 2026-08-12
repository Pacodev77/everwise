# src/logic/academico_engine.py

import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

def procesar_log_academico(df_raw: pd.DataFrame):
    """
    Motor inteligente y aprueba de fallos para injerir y transformar sábanas de calificaciones.
    Independientemente del formato, intentará mapear: Campus, Bloque, Matemáticas, Español.
    """
    df = df_raw.copy()
    
    # 1. ESTANDARIZACIÓN DRÁSTICA DE COLUMNAS
    # Limpiamos nombres de columnas: quitamos acentos, espacios extra, pasamos a minúsculas
    original_cols = list(df.columns)
    df.columns = df.columns.astype(str).str.lower().str.strip().str.replace('á', 'a').str.replace('é', 'e').str.replace('í', 'i').str.replace('ó', 'o').str.replace('ú', 'u')
    
    # 2. IDENTIFICACIÓN HEURÍSTICA DE CAMPOS CLAVE
    col_map = {
        "campus": None,
        "bloque": None,
        "matematicas": None,
        "español": None
    }
    
    # Búsqueda por palabras clave aproximadas
    for col in df.columns:
        if any(x in col for x in ['campus', 'sede', 'escuela', 'colegio', 'plantel']):
            col_map['campus'] = col
        elif any(x in col for x in ['bloque', 'periodo', 'bimestre', 'trimestre', 'semestre', 'ciclo']):
            col_map['bloque'] = col
        elif any(x in col for x in ['mate', 'matematica', 'calculo', 'math']):
            col_map['matematicas'] = col
        elif any(x in col for x in ['español', 'lenguaje', 'lectura', 'spanish', 'literatura']):
            col_map['español'] = col
            
    # 3. FAILSAFES (INYECCIÓN DE VALORES POR DEFECTO PARA NO ROMPER EL SISTEMA)
    if not col_map['campus']: 
        df['campus_calc'] = "General"
    else:
        df['campus_calc'] = df[col_map['campus']].fillna("General").astype(str).str.title()
        
    if not col_map['bloque']:
        df['bloque_calc'] = "B1" # Asumimos B1 por defecto si no lo dice
    else:
        df['bloque_calc'] = df[col_map['bloque']].fillna("B1").astype(str).str.upper()

    # Matemáticas
    if col_map['matematicas']:
        df['math_calc'] = pd.to_numeric(df[col_map['matematicas']], errors='coerce')
    else:
        df['math_calc'] = 0.0 # Fallback radical
        
    # Español
    if col_map['español']:
        df['esp_calc'] = pd.to_numeric(df[col_map['español']], errors='coerce')
    else:
        df['esp_calc'] = 0.0 # Fallback radical

    # Si las calificaciones vienen en escala de 0 a 10 o 0 a 100, las normalizamos a % (0.0 - 1.0)
    for col in ['math_calc', 'esp_calc']:
        max_val = df[col].max()
        if max_val > 10.0:
            df[col] = df[col] / 100.0  # Era escala 100
        elif max_val > 1.0:
            df[col] = df[col] / 10.0   # Era escala 10
            
    # Llenar huecos numéricos limpios
    df['math_calc'] = df['math_calc'].fillna(0)
    df['esp_calc'] = df['esp_calc'].fillna(0)

    # 4. CONSOLIDACIÓN DE RESULTADOS AGREGADOS
    # Estructura 1: Histórico por Bloques (df_acad_hist)
    df_acad_hist = df.groupby(['campus_calc', 'bloque_calc'])[['math_calc', 'esp_calc']].mean().reset_index()
    df_acad_hist.rename(columns={
        'campus_calc': 'campus',
        'bloque_calc': 'Bloque',
        'math_calc': 'Matemáticas',
        'esp_calc': 'Español'
    }, inplace=True)
    
    # 5. SANIDAD OBLIGATORIA DEL CAMPUS
    # Mapear a los nombres correctos del sistema ("Misiones", "Nuevo Sur", "San Agustín")
    def limpiar_campus(nombre):
        n = nombre.lower()
        if 'misiones' in n: return 'Misiones'
        if 'sur' in n or 'nuevo' in n: return 'Nuevo Sur'
        if 'san ag' in n or 'agustin' in n: return 'San Agustín'
        return 'General'
        
    df_acad_hist['campus'] = df_acad_hist['campus'].apply(limpiar_campus)

    return df_acad_hist
