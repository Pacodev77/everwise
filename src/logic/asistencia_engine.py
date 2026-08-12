# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
import re

def parse_num(val):
    """Parsea números considerando formato hispano (coma como decimal) y porcentajes."""
    if pd.isna(val):
        return None
    val_str = str(val).strip().replace('%', '')
    if not val_str:
        return None
    val_str = val_str.replace(',', '.')
    try:
        n = float(val_str)
        if '%' in str(val):
            return n / 100.0
        return n
    except (ValueError, TypeError):
        return None

def parse_pct(val):
    """Parsea porcentajes asegurando rango entre 0.0 y 1.0."""
    num = parse_num(val)
    if num is None:
        return None
    if num > 1.0:
        return num / 100.0
    return num

def sanitizar_nivel(col_name):
    """Sanitiza nombres de nivel/sección/área a las categorías estándar."""
    col_str = str(col_name).lower().strip()
    if any(k in col_str for k in ['pre', 'kin', 'mat', 'preschool', 'preescolar']):
        return 'Preescolar'
    elif any(k in col_str for k in ['pri', 'elem', 'elementary', 'primaria']):
        return 'Primaria'
    elif any(k in col_str for k in ['sec', 'mid', 'middle', 'secundaria']):
        return 'Secundaria'
    elif any(k in col_str for k in ['dep', 'sport', 'deporte']):
        return 'Deportes'
    elif any(k in col_str for k in ['tot', 'prom', 'dias', 'días', 'día', 'dìa', 'dia']):
        return 'Total'
    return col_str.title()

def identificar_campus(texto):
    """Identifica la sede a partir de un texto."""
    t = str(texto).lower().strip()
    if 'mision' in t:
        return 'Misiones'
    elif 'nuevo' in t or 'sur' in t:
        return 'Nuevo Sur'
    elif 'agustin' in t or 'agustín' in t or 'san agustin' in t or 'san agustín' in t:
        return 'San Agustín'
    elif 'everwise' in t or 'global' in t or 'general' in t or 'red' in t:
        return 'Global'
    return None

def _es_formato_matriz(df_crudo):
    """Determina si el DataFrame corresponde a la matriz ejecutiva de asistencia."""
    sample_text = " ".join([str(c) for c in df_crudo.columns]) + " " + " ".join([str(x) for x in df_crudo.head(15).values.flatten()])
    sample_text = sample_text.lower()
    
    keywords_matriz = ['elementary', 'middle school', 'preschool', 'colaboradores', '% asistencia', 'total de días', 'total de dias', 'total de dìas']
    match_count = sum(1 for k in keywords_matriz if k in sample_text)
    
    campus_keywords = ['misiones', 'nuevo sur', 'san agust', 'everwise']
    campus_match_count = sum(1 for c in campus_keywords if c in sample_text)
    
    return match_count >= 2 or (campus_match_count >= 2 and ('asistencia' in sample_text or 'alumnos' in sample_text))

def _procesar_matriz_asistencia(df_crudo, sede_actual=None):
    """
    Parsea reportes ejecutivos consolidados con bloques por sede (Misiones, Nuevo Sur, San Agustín, Everwise).
    """
    cols_as_row = [str(c) for c in df_crudo.columns]
    has_header_in_cols = any(identificar_campus(c) for c in cols_as_row) or any(sanitizar_nivel(c) in ['Preescolar', 'Primaria', 'Secundaria'] for c in cols_as_row)
    
    if has_header_in_cols:
        df_work = pd.concat([pd.DataFrame([cols_as_row]), df_crudo.reset_index(drop=True)], ignore_index=True)
    else:
        df_work = df_crudo.copy()
        
    campus_blocks = []
    current_campus = None
    current_rows = []

    for idx, row in df_work.iterrows():
        first_cell = row.iloc[0]
        campus_match = identificar_campus(first_cell)
        
        if campus_match:
            if current_campus:
                campus_blocks.append((current_campus, current_rows))
            current_campus = campus_match
            current_rows = [(idx, row)]
        elif current_campus:
            current_rows.append((idx, row))

    if current_campus:
        campus_blocks.append((current_campus, current_rows))

    if not campus_blocks:
        campus_blocks.append((sede_actual or 'General', [(0, df_work.iloc[0])] + list(df_work.iloc[1:].iterrows())))

    campus_results = {}
    
    for cname, rows in campus_blocks:
        header_row = rows[0][1]
        col_headers = [header_row.iloc[i] for i in range(len(header_row))]
        
        col_to_level = {}
        total_col_idx = None
        for i in range(1, len(col_headers)):
            header_val = col_headers[i]
            if pd.isna(header_val) or str(header_val).strip() == '':
                continue
            s_level = sanitizar_nivel(header_val)
            if s_level == 'Total':
                total_col_idx = i
            else:
                col_to_level[i] = s_level

        alumnos_counts = {}
        asistencia_counts = {}
        pct_asistencia = {}
        staff_pcts = {}
        total_alumnos_kpi = None
        total_staff_kpi = None
        dias_alumnos = None
        dias_staff = None

        for r_idx, r in rows[1:]:
            first_val = str(r.iloc[0]).lower().strip()
            
            if any(k in first_val for k in ['% asist', 'tasa asist', '% alu']) or first_val.startswith('%'):
                for c_idx, lvl in col_to_level.items():
                    if c_idx < len(r):
                        val = parse_pct(r.iloc[c_idx])
                        if val is not None:
                            pct_asistencia[lvl] = val
                if total_col_idx is not None and total_col_idx < len(r):
                    val = parse_pct(r.iloc[total_col_idx])
                    if val is not None:
                        total_alumnos_kpi = val
                else:
                    valid_row_vals = [parse_pct(x) for x in r.iloc[1:].values if pd.notna(x) and str(x).strip() != '']
                    if valid_row_vals:
                        total_alumnos_kpi = valid_row_vals[-1]

            elif any(k in first_val for k in ['colaborador', 'staff', 'docent', 'emplead', 'personal', 'maestr']):
                for c_idx, lvl in col_to_level.items():
                    if c_idx < len(r):
                        val = parse_pct(r.iloc[c_idx])
                        if val is not None:
                            staff_pcts[lvl] = val
                if total_col_idx is not None and total_col_idx < len(r):
                    val = parse_pct(r.iloc[total_col_idx])
                    if val is not None:
                        total_staff_kpi = val
                else:
                    valid_row_vals = [parse_pct(x) for x in r.iloc[1:].values if pd.notna(x) and str(x).strip() != '']
                    if valid_row_vals:
                        total_staff_kpi = valid_row_vals[-1]

            elif any(k in first_val for k in ['alumn', 'estudiant', 'matricul', 'headcount', 'padron']):
                for c_idx, lvl in col_to_level.items():
                    if c_idx < len(r):
                        val = parse_num(r.iloc[c_idx])
                        if val is not None:
                            alumnos_counts[lvl] = val
                if total_col_idx is not None and total_col_idx < len(r):
                    val = parse_num(r.iloc[total_col_idx])
                    if val is not None:
                        dias_alumnos = int(val) if val.is_integer() else val

            elif any(k in first_val for k in ['asistencia', 'asistencias']) and not first_val.startswith('%'):
                for c_idx, lvl in col_to_level.items():
                    if c_idx < len(r):
                        val = parse_num(r.iloc[c_idx])
                        if val is not None:
                            asistencia_counts[lvl] = val

            elif first_val == 'nan' or first_val == '':
                if total_col_idx is not None and total_col_idx < len(r):
                    val = parse_num(r.iloc[total_col_idx])
                    if val is not None and val > 0:
                        dias_staff = int(val) if val.is_integer() else val

        base_levels = ['Preescolar', 'Primaria', 'Secundaria']
        all_levels_found = list(dict.fromkeys(base_levels + [lvl for lvl in col_to_level.values() if lvl not in ['Deportes', 'Total']]))
        
        total_headcount = sum(alumnos_counts.get(lvl, 0.0) for lvl in all_levels_found)
        
        levels_list = []
        for lvl in all_levels_found:
            asis_rate = pct_asistencia.get(lvl)
            if asis_rate is None and lvl in alumnos_counts and lvl in asistencia_counts:
                denom = alumnos_counts[lvl]
                asis_rate = round(asistencia_counts[lvl] / denom, 4) if denom > 0 else 0.0
            if asis_rate is None:
                asis_rate = 0.0
                
            distrib = (alumnos_counts.get(lvl, 0.0) / total_headcount) if total_headcount > 0 else (1.0 / len(all_levels_found))
            
            levels_list.append({
                'Nivel': lvl,
                'Asistencia': round(asis_rate, 4),
                'Distribución': round(distrib, 4)
            })

        df_levels = pd.DataFrame(levels_list)

        if total_alumnos_kpi is None:
            total_alumnos_kpi = df_levels['Asistencia'].mean() if not df_levels.empty else 0.0

        if total_staff_kpi is None:
            total_staff_kpi = sum(staff_pcts.values()) / len(staff_pcts) if staff_pcts else 0.90

        campus_results[cname] = {
            'niveles': df_levels,
            'staff': float(total_staff_kpi),
            'staff_desglose': staff_pcts,
            'kpi_general': float(total_alumnos_kpi),
            'dias_alumnos': dias_alumnos,
            'dias_staff': dias_staff,
            'alumnos_counts': alumnos_counts,
            'asistencia_counts': asistencia_counts
        }

    chosen_cname = sede_actual if sede_actual in campus_results else list(campus_results.keys())[0]
    selected_data = campus_results[chosen_cname]
    
    extra_info = {
        'es_matriz': True,
        'campuses': campus_results,
        'staff_desglose': selected_data.get('staff_desglose', {}),
        'dias_alumnos': selected_data.get('dias_alumnos'),
        'dias_staff': selected_data.get('dias_staff'),
        'alumnos_counts': selected_data.get('alumnos_counts', {}),
        'asistencia_counts': selected_data.get('asistencia_counts', {})
    }

    return selected_data['niveles'], selected_data['staff'], extra_info

def _procesar_log_biometrico(df_crudo):
    col_mapping = {}
    found_keys = set()
    
    for exact_pass in [True, False]:
        for col in df_crudo.columns:
            if col in col_mapping:
                continue
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
    
    if "Nivel" not in df.columns: df["Nivel"] = "General"
    if "Perfil" not in df.columns: df["Perfil"] = "Alumno"
    if "Fecha" not in df.columns: df["Fecha"] = pd.Timestamp.today().date()
    if "Matricula" not in df.columns: df["Matricula"] = df.index 
        
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.date
    df = df.dropna(subset=['Fecha'])
    
    staff_keywords = 'maestr|docen|staff|admin|emplead|coordin|direc|teacher|employee'
    staff_mask = df['Perfil'].astype(str).str.lower().str.contains(staff_keywords, na=False)
    
    df_staff = df[staff_mask]
    df_alumnos = df[~staff_mask]
    
    def inferir_y_calcular_kpi(df_subset, agrupar_por=None):
        if df_subset.empty: return pd.DataFrame() if agrupar_por else 0.0
        
        if agrupar_por:
            daily = df_subset.groupby(['Fecha', agrupar_por])['Matricula'].nunique().reset_index()
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
            return daily['Matricula'].mean() / max(max_poblacion, 1)

    resumen_alumnos = inferir_y_calcular_kpi(df_alumnos, 'Nivel')
    asistencia_staff = inferir_y_calcular_kpi(df_staff)
    
    try:
        asistencia_staff = float(asistencia_staff)
        if pd.isna(asistencia_staff): 
            asistencia_staff = 0.0
    except (ValueError, TypeError):
        asistencia_staff = 0.0
        
    if isinstance(resumen_alumnos, pd.DataFrame) and not resumen_alumnos.empty:
        resumen_alumnos['Nivel_Sanitizado'] = 'Otros'
        resumen_alumnos.loc[resumen_alumnos['Nivel'].astype(str).str.lower().str.contains('pre|kin|mat|preschool', regex=True), 'Nivel_Sanitizado'] = 'Preescolar'
        resumen_alumnos.loc[resumen_alumnos['Nivel'].astype(str).str.lower().str.contains('pri|elementary', regex=True), 'Nivel_Sanitizado'] = 'Primaria'
        resumen_alumnos.loc[resumen_alumnos['Nivel'].astype(str).str.lower().str.contains('sec|media|middle', regex=True), 'Nivel_Sanitizado'] = 'Secundaria'
        
        resumen_alumnos = resumen_alumnos.groupby('Nivel_Sanitizado', as_index=False)['Asistencia'].mean()
        resumen_alumnos.rename(columns={'Nivel_Sanitizado': 'Nivel'}, inplace=True)
        
        total_suma = resumen_alumnos['Asistencia'].sum()
        resumen_alumnos['Distribución'] = resumen_alumnos['Asistencia'] / total_suma if total_suma > 0 else 0
        
        for base_lvl in ['Preescolar', 'Primaria', 'Secundaria']:
            if base_lvl not in resumen_alumnos['Nivel'].values:
                resumen_alumnos = pd.concat([
                    resumen_alumnos, 
                    pd.DataFrame([{"Nivel": base_lvl, "Asistencia": 0.0, "Distribución": 0.0}])
                ], ignore_index=True)
    else:
        resumen_alumnos = pd.DataFrame([
            {"Nivel": "Preescolar", "Asistencia": 0.0, "Distribución": 0.333},
            {"Nivel": "Primaria", "Asistencia": 0.0, "Distribución": 0.333},
            {"Nivel": "Secundaria", "Asistencia": 0.0, "Distribución": 0.334}
        ])
                
    extra_info = {'es_matriz': False, 'campuses': {}}
    return resumen_alumnos, asistencia_staff, extra_info

def procesar_log_asistencia(df_crudo, sede_actual=None):
    """
    Punto de entrada inteligente: Detecta automáticamente si el archivo es
    una Matriz Ejecutiva Consolidada de Campus o una Bitácora Biométrica Transaccional.
    """
    if _es_formato_matriz(df_crudo):
        return _procesar_matriz_asistencia(df_crudo, sede_actual)
    else:
        return _procesar_log_biometrico(df_crudo)
