# src/logic/extra_engines.py

import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

def procesar_log_disciplina(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Procesa un archivo de disciplina con columnas:
    campus/sede, violencia, faltas, apatia, firmadas, pendientes.
    """
    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.lower().str.strip().str.replace('á', 'a').str.replace('é', 'e').str.replace('í', 'i').str.replace('ó', 'o').str.replace('ú', 'u')
    
    def limpiar_campus(nombre):
        n = str(nombre).lower().strip()
        if 'misiones' in n: return 'Misiones'
        if 'sur' in n or 'nuevo' in n: return 'Nuevo Sur'
        if 'san ag' in n or 'agustin' in n: return 'San Agustín'
        return 'General'

    campus_col = None
    for col in df.columns:
        if any(x in col for x in ['campus', 'sede', 'escuela', 'plantel']):
            campus_col = col
            break
            
    if campus_col:
        df['campus'] = df[campus_col].apply(limpiar_campus)
    else:
        df['campus'] = 'General'
        
    # Buscar columnas numéricas correspondientes
    col_casos = {}
    col_cartas = {}
    
    for col in df.columns:
        if 'violencia' in col:
            col_casos['Violencia Escolar'] = col
        elif 'falta' in col or 'grave' in col:
            col_casos['Faltas Graves'] = col
        elif 'apatia' in col or 'severa' in col:
            col_casos['Apatía Severa'] = col
        elif 'firmada' in col or 'firmas' in col or 'carta' in col:
            if 'pend' in col:
                col_cartas['Pendientes'] = col
            else:
                col_cartas['Firmadas'] = col
        elif 'pend' in col:
            col_cartas['Pendientes'] = col
            
    campus_list = ['Misiones', 'Nuevo Sur', 'San Agustín']
    
    # Construir df_casos
    casos_data = []
    for campus in campus_list:
        sub = df[df['campus'] == campus]
        violencia = pd.to_numeric(sub[col_casos['Violencia Escolar']], errors='coerce').sum() if 'Violencia Escolar' in col_casos else 0
        faltas = pd.to_numeric(sub[col_casos['Faltas Graves']], errors='coerce').sum() if 'Faltas Graves' in col_casos else 0
        apatia = pd.to_numeric(sub[col_casos['Apatía Severa']], errors='coerce').sum() if 'Apatía Severa' in col_casos else 0
        casos_data.append({
            "campus": campus,
            "Violencia Escolar": int(np.nan_to_num(violencia)) if pd.notna(violencia) else 0,
            "Faltas Graves": int(np.nan_to_num(faltas)) if pd.notna(faltas) else 0,
            "Apatía Severa": int(np.nan_to_num(apatia)) if pd.notna(apatia) else 0
        })
    df_casos = pd.DataFrame(casos_data)
    
    # Construir df_cartas
    cartas_data = []
    for campus in campus_list:
        sub = df[df['campus'] == campus]
        firmadas = pd.to_numeric(sub[col_cartas['Firmadas']], errors='coerce').sum() if 'Firmadas' in col_cartas else 0
        pendientes = pd.to_numeric(sub[col_cartas['Pendientes']], errors='coerce').sum() if 'Pendientes' in col_cartas else 0
        cartas_data.append({
            "campus": campus,
            "Firmadas": int(np.nan_to_num(firmadas)) if pd.notna(firmadas) else 0,
            "Pendientes": int(np.nan_to_num(pendientes)) if pd.notna(pendientes) else 0
        })
    df_cartas = pd.DataFrame(cartas_data)
    
    return df_casos, df_cartas

def procesar_log_practica(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Procesa un archivo de práctica docente y uso de apps.
    Mapea adopción por plataforma y relación práctica vs resultados.
    """
    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.lower().str.strip().str.replace('á', 'a').str.replace('é', 'e').str.replace('í', 'i').str.replace('ó', 'o').str.replace('ú', 'u')
    
    def limpiar_campus(nombre):
        n = str(nombre).lower().strip()
        if 'misiones' in n: return 'Misiones'
        if 'sur' in n or 'nuevo' in n: return 'Nuevo Sur'
        if 'san ag' in n or 'agustin' in n: return 'San Agustín'
        return 'General'

    campus_col = None
    for col in df.columns:
        if any(x in col for x in ['campus', 'sede', 'escuela', 'plantel']):
            campus_col = col
            break
            
    if campus_col:
        df['campus'] = df[campus_col].apply(limpiar_campus)
    else:
        df['campus'] = 'General'
        
    plat_col = None
    uso_col = None
    prac_col = None
    res_col = None
    group_col = None
    
    for col in df.columns:
        if 'plat' in col or 'app' in col:
            plat_col = col
        elif 'uso' in col or 'efec' in col or 'adop' in col:
            uso_col = col
        elif 'prac' in col:
            prac_col = col
        elif 'res' in col or 'dom' in col:
            res_col = col
        elif 'grup' in col or 'grad' in col:
            group_col = col
            
    if plat_col:
        df['Plataforma'] = df[plat_col].apply(lambda x: 'Progrentis' if 'prog' in str(x).lower() else 'IXL')
    else:
        df['Plataforma'] = 'IXL'
        
    if group_col:
        df['Grupo'] = df[group_col].astype(str)
    else:
        df['Grupo'] = 'G-General'
        
    def parse_numeric_percent(series):
        if series is None:
            return pd.Series(0.0, index=df.index)
        s = series.astype(str).str.replace('%', '', regex=False).str.strip()
        s = pd.to_numeric(s, errors='coerce').fillna(0.0)
        if s.max() > 1.0:
            s = s / 100.0
        return s
        
    df['Uso Efectivo (%)'] = parse_numeric_percent(df[uso_col]) if uso_col else 0.80
    df['Práctica (%)'] = parse_numeric_percent(df[prac_col]) if prac_col else 0.75
    df['Resultado (%)'] = parse_numeric_percent(df[res_col]) if res_col else 0.70
    
    df_apps_kpis = df.groupby(['campus', 'Plataforma'])['Uso Efectivo (%)'].mean().reset_index()
    df_correlacion = df[['campus', 'Grupo', 'Plataforma', 'Práctica (%)', 'Resultado (%)']].copy()
    
    return df_apps_kpis, df_correlacion
