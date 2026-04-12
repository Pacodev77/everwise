import pandas as pd
import numpy as np

def procesar_log_clima(df_raw: pd.DataFrame):
    """
    Motor inteligente para ingerir formularios de Clima Escolar (ICE).
    Busca preguntas relacionadas con el estado anímico, cruza respuestas (Siempre, A veces, Nunca)
    y estandariza los resultados para la matriz Punchcard.
    """
    df = df_raw.copy()
    
    # 1. ESTANDARIZACIÓN DE COLUMNAS
    df.columns = df.columns.astype(str).str.lower().str.strip().str.replace('á', 'a').str.replace('é', 'e').str.replace('í', 'i').str.replace('ó', 'o').str.replace('ú', 'u')
    
    # 2. MATCH HEURÍSTICO DE METADATOS Y CATEGORÍAS
    campus_col = None
    
    # Buscar columna Campus
    for col in df.columns:
        if any(x in col for x in ['campus', 'sede', 'escuela', 'plantel']):
            campus_col = col
            break
            
    if not campus_col:
        df['campus'] = "General"
    else:
        df['campus'] = df[campus_col].fillna("General").astype(str).str.title()
        
    # Limpieza de Campus
    def limpiar_campus(nombre):
        n = nombre.lower()
        if 'misiones' in n: return 'Misiones'
        if 'sur' in n or 'nuevo' in n: return 'Nuevo Sur'
        if 'san ag' in n or 'agustin' in n: return 'San Agustín'
        return 'General'
        
    df['campus'] = df['campus'].apply(limpiar_campus)

    # Buscar Columnas Evaluativas por Categoría ICE
    # Categorías Oficiales: Estrés Acumulado, Motivación, Sentido de Pertenencia, Seguridad Física
    cat_columns = {
        "Estrés Acumulado": [],
        "Motivación": [],
        "Sentido de Pertenencia": [],
        "Seguridad Física": []
    }
    
    for col in df.columns:
        if any(w in col for w in ['estres', 'ansiedad', 'cansancio', 'carga']):
            cat_columns["Estrés Acumulado"].append(col)
        elif any(w in col for w in ['motiva', 'animo', 'entusiasmo', 'inspira', 'ganas']):
            cat_columns["Motivación"].append(col)
        elif any(w in col for w in ['pertene', 'identidad', 'incluido', 'parte de', 'comunidad']):
            cat_columns["Sentido de Pertenencia"].append(col)
        elif any(w in col for w in ['segur', 'bullying', 'acoso', 'peligro', 'fisic']):
            cat_columns["Seguridad Física"].append(col)
            
    # Función para estandarizar las respuestas a [Siempre, A veces, Nunca]
    def clasificar_frecuencia(val):
        v = str(val).lower().strip()
        if any(x in v for x in ['siempre', 'todo el', 'mucho', 'total', 'frecuente', 'diario', '5', '4']):
            return "Siempre"
        if any(x in v for x in ['veces', 'regular', 'ocasional', 'medio', '3']):
            return "A veces"
        if any(x in v for x in ['nunca', 'jamas', 'nada', 'poco', 'raro', '2', '1']):
            return "Nunca"
        return "A veces" # Fallback neutral

    # Procesar data frame para pivotar
    resultados = []
    
    for _, row in df.iterrows():
        c_name = row['campus']
        
        for cat_real, matched_cols in cat_columns.items():
            for m_col in matched_cols:
                resp_text = clasificar_frecuencia(row[m_col])
                resultados.append({
                    "campus": c_name,
                    "Categoría": cat_real,
                    "Respuesta": resp_text,
                    "Count": 1
                })
                
    # Si el DataFrame no encontró NINGUNA coincidencia heurística, inyectamos Falsa
    if len(resultados) == 0:
        return pd.DataFrame() # Fallback vacio
        
    df_res = pd.DataFrame(resultados)
    
    # 4. Agrupación y Cálculo de Proporciones (Punchcard Matrix Format)
    # Contamos cuántas respuestas cayeron en cada bloque
    df_agg = df_res.groupby(['campus', 'Categoría', 'Respuesta']).count().reset_index()
    
    # Calculamos proporcion dividiendo por el total de respuestas en esa categoría para su campus
    df_agg['Proporción'] = df_agg.groupby(['campus', 'Categoría'])['Count'].transform(lambda x: x / x.sum())
    
    # Completar faltantes para que la matriz gráfica no se rompa si no hay votos de 'Nunca' o 'Siempre'
    # Esta es una medida de protección para Altair
    todas_respuestas = pd.DataFrame({'Respuesta': ['Siempre', 'A veces', 'Nunca']})
    # Requiere cross join, hacemos un pequeño hack usando MultiIndex
    matrix_perfecta = (
        df_agg[['campus', 'Categoría']].drop_duplicates()
        .merge(todas_respuestas, how='cross')
    )
    
    df_final = pd.merge(matrix_perfecta, df_agg, on=['campus', 'Categoría', 'Respuesta'], how='left').fillna(0)
    
    return df_final
