import pandas as pd
import numpy as np

def procesar_log_asistencia(df_crudo):
    """
    Inteligencia de Datos: Motor de Asistencia Top-Down
    Analiza logs biométricos masivos o registros caos, identificando automáticamente columnas.
    """
    # 1. LIMPIEZA INTELIGENTE Y MATCHING DE COLUMNAS (Sin Duplicados)
    col_mapping = {}
    found_keys = set()
    
    # Priorizar coincidencias exactas primero para evitar falsos positivos
    for exact_pass in [True, False]:
        for col in df_crudo.columns:
            if col in col_mapping: continue
            
            col_lower = str(col).lower().strip().replace('_', ' ')
            
            def is_match(keywords):
                if exact_pass:
                    return any(k == col_lower for k in keywords)
                return any(k in col_lower for k in keywords)

            if "Nivel" not in found_keys and is_match(['nivel', 'seccion', 'grado']):
                col_mapping[col] = "Nivel"
                found_keys.add("Nivel")
            elif "Perfil" not in found_keys and is_match(['perfil', 'rol', 'tipo de usuario']):
                col_mapping[col] = "Perfil"
                found_keys.add("Perfil")
            elif "Fecha" not in found_keys and is_match(['fecha', 'fecha de ingreso', 'dia']):
                col_mapping[col] = "Fecha"
                found_keys.add("Fecha")
            elif "Matricula" not in found_keys and is_match(['matrícula', 'matricula', 'id', 'correo', 'no. de control']):
                col_mapping[col] = "Matricula"
                found_keys.add("Matricula")
                
            
    df = df_crudo.rename(columns=col_mapping)
    
    # Failsafes (Aprendizaje / Omisión controlada si faltan datos base)
    if "Nivel" not in df.columns: df["Nivel"] = "General"
    if "Perfil" not in df.columns: df["Perfil"] = "Alumno"
    if "Fecha" not in df.columns: df["Fecha"] = pd.Timestamp.today().date()
    if "Matricula" not in df.columns: 
        # Si no hay identificador, usamos el índice asumiendo que cada fila es un registro único válido
        df["Matricula"] = df.index 
        
    # 2. TRANSFORMACIONES ROBUSTAS
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.date
    df = df.dropna(subset=['Fecha']) # Depurar corrupciones
    
    # 3. FILTRADO BIDIRECCIONAL (DOCENTES VS ALUMNADO)
    staff_keywords = 'maestr|docen|staff|admin|emplead|coordin|direc|teacher|employee'
    staff_mask = df['Perfil'].astype(str).str.lower().str.contains(staff_keywords, na=False)
    
    df_staff = df[staff_mask]
    df_alumnos = df[~staff_mask]
    
    # 4. MOTOR ALGORÍTMICO (Cálculo Inferencia Headcount vs Traffic)
    def inferir_y_calcular_kpi(df_subset, agrupar_por=None):
        if df_subset.empty: return pd.DataFrame() if agrupar_por else 0.0
        
        if agrupar_por:
            daily = df_subset.groupby(['Fecha', agrupar_por])['Matricula'].nunique().reset_index()
            # Asumimos que el récord de tránsito histórico de un nivel es igual al padrón físico esperado (100%)
            max_poblacion = daily.groupby(agrupar_por)['Matricula'].max().to_dict()
            
            daily['Tasa_Asistencia'] = daily.apply(
                lambda x: x['Matricula'] / max(max_poblacion.get(x[agrupar_por], 1), 1), axis=1
            )
            
            resumen = daily.groupby(agrupar_por)['Tasa_Asistencia'].mean().reset_index()
            resumen.rename(columns={'Tasa_Asistencia': 'Asistencia'}, inplace=True)
            return resumen
        else:
            daily = df_subset.groupby('Fecha')['Matricula'].nunique().reset_index()
            max_poblacion = daily['Matricula'].max()
            promedio_abs = daily['Matricula'].mean() / max(max_poblacion, 1)
            return promedio_abs

    resumen_alumnos = inferir_y_calcular_kpi(df_alumnos, 'Nivel')
    asistencia_staff = inferir_y_calcular_kpi(df_staff)
    
    try:
        asistencia_staff = float(asistencia_staff)
        if pd.isna(asistencia_staff): 
            asistencia_staff = 0.0
    except (ValueError, TypeError):
        asistencia_staff = 0.0 #Fallback empty
        
    # 5. CONSOLIDACIÓN DE NIVELES (Sanitización visual)
    if not isinstance(resumen_alumnos, pd.DataFrame) or resumen_alumnos.empty:
        # Fallback de plantilla vacía procesada
        pass 
    else:
        resumen_alumnos['Nivel_Sanitizado'] = 'Otros'
        resumen_alumnos.loc[resumen_alumnos['Nivel'].astype(str).str.lower().str.contains('pre|kin|mat|preschool', regex=True), 'Nivel_Sanitizado'] = 'Preescolar'
        resumen_alumnos.loc[resumen_alumnos['Nivel'].astype(str).str.lower().str.contains('pri|elementary', regex=True), 'Nivel_Sanitizado'] = 'Primaria'
        resumen_alumnos.loc[resumen_alumnos['Nivel'].astype(str).str.lower().str.contains('sec|media|middle', regex=True), 'Nivel_Sanitizado'] = 'Secundaria'
        
        resumen_alumnos = resumen_alumnos.groupby('Nivel_Sanitizado', as_index=False)['Asistencia'].mean()
        resumen_alumnos.rename(columns={'Nivel_Sanitizado': 'Nivel'}, inplace=True)
        
        # Calcular distribución global del pastel circular
        total_suma = resumen_alumnos['Asistencia'].sum()
        resumen_alumnos['Distribución'] = resumen_alumnos['Asistencia'] / total_suma if total_suma > 0 else 0
        
        # Validar missing base levels format
        for base_lvl in ['Preescolar', 'Primaria', 'Secundaria']:
            if base_lvl not in resumen_alumnos['Nivel'].values:
                resumen_alumnos = pd.concat([
                    resumen_alumnos, 
                    pd.DataFrame([{"Nivel": base_lvl, "Asistencia": 0.0, "Distribución": 0.0}])
                ], ignore_index=True)
                
    return resumen_alumnos, asistencia_staff
