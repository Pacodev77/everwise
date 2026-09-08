# src/logic/normalizar_asistencia.py

import os
import pandas as pd
import numpy as np
import re

def parse_date(val):
    """Parsea fechas considerando formatos mixtos, cadenas y números seriales de Excel."""
    if pd.isna(val):
        return None
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, (int, float)):
        try:
            # Excel serial date
            return pd.to_datetime(val, unit='D', origin='1899-12-30').date()
        except:
            return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['---', 'nan', 'null', 'none', '']:
        return None
    # Intentar con formatos comunes
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d']:
        try:
            return pd.to_datetime(val_str, format=fmt).date()
        except:
            pass
    try:
        # Fallback a la inferencia de pandas
        return pd.to_datetime(val_str, errors='coerce').date()
    except:
        return None

def parse_time(val):
    """Parsea horas considerando formatos de cadenas y números flotantes (fracción de día de Excel)."""
    if pd.isna(val):
        return None
    if isinstance(val, pd.Timestamp):
        return val.time()
    if isinstance(val, (int, float)):
        try:
            temp = pd.to_datetime(val, unit='D', origin='1899-12-30')
            return temp.time()
        except:
            return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['---', 'nan', 'null', 'none', '']:
        return None
    for fmt in ['%H:%M:%S', '%I:%M:%S %p', '%H:%M', '%I:%M %p']:
        try:
            return pd.to_datetime(val_str, format=fmt).time()
        except:
            pass
    try:
        return pd.to_datetime(val_str, errors='coerce').time()
    except:
        return None

def normalizar_nivel(val):
    """Mapea el nivel escolar a los valores canónicos (Preescolar, Primaria, Secundaria, Preparatoria, Staff) o SIN_MAPEAR."""
    if pd.isna(val):
        return 'SIN_MAPEAR'
    val_str = str(val).strip().upper()
    if not val_str or val_str in ['---', 'NONE', 'NAN', 'N/A', 'NULL', '']:
        return 'SIN_MAPEAR'

    # 1. Staff / Colaboradores / Maestros
    if any(k in val_str for k in ['STAFF', 'MAESTRO', 'DOCENTE', 'COLABORADOR', 'ADMINISTRAT', 'EMPLEADO', 'TEACHER', 'EMPLOYEE', 'ADMIN']):
        return 'Staff'

    # 2. Preescolar / Kinder / Preschool
    if any(k in val_str for k in ['PRESCHOOL', 'PREESCOLAR', 'KIND', 'KINDER', 'MATERN', 'MAT', 'PK', 'K1', 'K2', 'K3', 'PRE', 'PRES', 'NURSERY']):
        return 'Preescolar'

    # 3. Primaria / Elementary
    if any(k in val_str for k in ['ELEMENTARY', 'PRIMARIA', 'PRI', 'ELEM', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', '1ER', '2DO', '3ER', '4TO', '5TO', '6TO']):
        return 'Primaria'

    # 4. Secundaria / Middle School / High School
    if any(k in val_str for k in ['MIDDLE SCHOOL', 'SECUNDARIA', 'MIDDLE', 'SEC', 'MS', '7TH', '8TH', '9TH', '10TH', '11TH', '12TH', '1S', '2S', '3S', '7MO', '8VO', '9NO', 'HIGH SCHOOL', 'PREPARATORIA', 'PREPA', 'BACHILLERATO', 'HIGH', 'HS']):
        return 'Secundaria'

    # 5. Grados numéricos aislados (1-6 Primaria, 7+ Secundaria)
    match_num = re.search(r'\b([1-9]|1[0-2])\b', val_str)
    if match_num:
        num = int(match_num.group(1))
        if 1 <= num <= 6:
            return 'Primaria'
        elif 7 <= num <= 12:
            return 'Secundaria'

    return 'SIN_MAPEAR'

def normalizar_estatus(val):
    """Normaliza los estatus de asistencia a Presente, Retardo o Falta."""
    if pd.isna(val):
        return 'Presente'
    val_str = str(val).strip().lower()
    if 'falta' in val_str:
        return 'Falta'
    elif 'retardo' in val_str:
        return 'Retardo'
    elif any(x in val_str for x in ['puntual', 'a tiempo', 'presente']):
        return 'Presente'
    return 'Presente'

def normalizar_campus(val):
    """Normaliza los nombres de campus a los estándar de Everwise."""
    if pd.isna(val):
        return None
    val_str = str(val).strip().lower()
    if 'mision' in val_str:
        return 'Misiones'
    elif 'nuevo' in val_str or 'sur' in val_str:
        return 'Nuevo Sur'
    elif 'agustin' in val_str or 'agustín' in val_str:
        return 'San Agustín'
    return None

def detectar_firma_hoja(df_raw, sheetname=""):
    """Detecta automáticamente si la hoja corresponde a Firma A, B o C, o si no es reconocida."""
    # Buscar cabeceras en las primeras 15 filas
    for idx in range(min(15, len(df_raw))):
        row_vals = [str(val).lower().strip() for val in df_raw.iloc[idx] if pd.notna(val)]
        
        # Firma C (Estatus persona/día): Tiene 'asistencia', 'nombre', etc.
        matches_c = sum(1 for c in ['fecha', 'nombre', 'apellidos', 'empleado', 'colaborador', 'maestro', 'nivel', 'grado', 'matricula', 'matrícula', 'asistencia', 'estatus', 'notas'] if c in row_vals)
        if matches_c >= 3 and any(k in row_vals for k in ['asistencia', 'estatus']):
            if any(k in row_vals for k in ['nombre', 'empleado', 'colaborador', 'maestro', 'alumno']):
                return "Firma C", idx, [str(c).strip() for c in df_raw.iloc[idx]]
                
        # Firma A (Log crudo): Tiene campos de logs pero no de 'asistencia'
        matches_a = sum(1 for c in ['fecha', 'nombre', 'apellidos', 'empleado', 'maestro', 'colaborador', 'perfil', 'rol', 'horadeingreso', 'hora de ingreso', 'hora ingreso', 'hora entrada', 'hora salida', 'matricula', 'matrícula', 'id'] if c in row_vals)
        if matches_a >= 3:
            if any(k in row_vals for k in ['nombre', 'empleado', 'colaborador', 'maestro', 'alumno', 'id']):
                return "Firma A", idx, [str(c).strip() for c in df_raw.iloc[idx]]

    # Firma B (Resumen pre-agregado por fecha/nivel)
    for idx in range(min(15, len(df_raw))):
        row_vals = [str(val).lower().strip() for val in df_raw.iloc[idx] if pd.notna(val)]
        if 'fecha' in row_vals or 'date' in row_vals:
            has_person_fields = any(c in row_vals for c in ['nombre', 'apellidos', 'empleado', 'maestro'])
            if not has_person_fields:
                level_matches = sum(1 for c in ['elementary', 'middle school', 'middle', 'preschool', 'preeschool', 'colaboradores', 'maestros', 'staff', 'total'] if c in row_vals)
                if level_matches >= 2:
                    return "Firma B", idx, [str(c).strip() for c in df_raw.iloc[idx]]

    # Si la hoja tiene nombre explícito como 'maestros', 'docentes', 'staff', 'colaboradores'
    s_lower = str(sheetname).lower().strip()
    if any(k in s_lower for k in ['maestro', 'docente', 'staff', 'colaborador', 'empleado']):
        for idx in range(min(15, len(df_raw))):
            row_vals = [str(val).lower().strip() for val in df_raw.iloc[idx] if pd.notna(val)]
            if any(k in row_vals for k in ['fecha', 'date', 'dia', 'días']) or any(k in row_vals for k in ['nombre', 'empleado', 'id']):
                return "Firma A", idx, [str(c).strip() for c in df_raw.iloc[idx]]
                    
    return "Unknown", 0, []

def parsear_hoja(df_raw, signature, row_idx, headers, campus, filename, sheetname, reporte_val):
    """Parsea el contenido de una hoja según la firma detectada."""
    canon_rows = []
    summary_rows = []
    
    df_data = df_raw.iloc[row_idx+1:].copy()
    df_data.columns = headers
    
    is_staff_sheet = any(k in str(sheetname).lower() for k in ['maestro', 'docente', 'staff', 'colaborador', 'empleado'])
    
    if signature == "Firma A":
        for i, row in df_data.iterrows():
            try:
                date_val = parse_date(row.get('Fecha') or row.get('Date') or row.get('Dia'))
                if date_val is None:
                    reporte_val["filas_rechazadas"].append({
                        "archivo": filename, "hoja": sheetname, "fila": i + 1, "columna": "Fecha", "valor": str(row.get('Fecha')), "motivo": "Fecha no parseable"
                    })
                    continue
                
                perfil_val = str(row.get('Perfil') or row.get('Rol') or '').lower().strip()
                if is_staff_sheet or any(x in perfil_val for x in ['maestr', 'docen', 'staff', 'admin', 'emplead', 'coordin', 'direc', 'teacher', 'employee', 'colaborador']):
                    tipo_persona = 'colaborador'
                else:
                    tipo_persona = 'alumno'
                
                matricula_val = row.get('Matrícula') or row.get('Matricula') or row.get('ID') or row.get('Id')
                if pd.isna(matricula_val) or str(matricula_val).strip() in ['---', '', 'None', 'nan', '--- ']:
                    matricula_val = None
                else:
                    matricula_val = str(matricula_val).strip()
                
                nombre = str(row.get('Nombre') or row.get('Empleado') or row.get('Maestro') or '').strip().title()
                apellidos = str(row.get('Apellidos') or '').strip().title()
                
                orig_nivel = row.get('Nivel') or row.get('nivel')
                nivel_norm = normalizar_nivel(orig_nivel)
                
                # Intentar inferencia secundaria por Grado/Grupo o por Pestaña
                if nivel_norm == "SIN_MAPEAR":
                    grado_val = row.get('Grado y grupo') or row.get('Grado') or row.get('Grupo')
                    if pd.notna(grado_val):
                        nivel_norm = normalizar_nivel(grado_val)
                if nivel_norm == "SIN_MAPEAR" and is_staff_sheet:
                    nivel_norm = "Staff"
                elif nivel_norm == "SIN_MAPEAR":
                    nivel_norm = normalizar_nivel(sheetname)
                
                if orig_nivel and pd.notna(orig_nivel) and str(orig_nivel).strip() not in ['', '---']:
                    if nivel_norm == "SIN_MAPEAR":
                        reporte_val["valores_no_mapeados"].append({
                            "archivo": filename, "hoja": sheetname, "fila": i + 1, "columna": "Nivel", "valor": str(orig_nivel)
                        })
                
                grado_grupo = row.get('Grado y grupo') or row.get('Grado') or row.get('Grupo')
                if pd.isna(grado_grupo) or str(grado_grupo).strip() in ['---', '', 'None', 'nan']:
                    grado_grupo = None
                else:
                    grado_grupo = str(grado_grupo).strip()
                    
                hora_entrada = parse_time(row.get('horadeingreso') or row.get('Hora de ingreso') or row.get('Hora ingreso') or row.get('Hora entrada') or row.get('Entrada'))
                hora_salida = parse_time(row.get('Fecha y hora de salida') or row.get('Hora de salida') or row.get('Hora salida') or row.get('Salida'))
                
                row_str = " ".join([str(val).lower().strip() for val in row.values if pd.notna(val)])
                if 'retardo' in row_str:
                    estatus = 'Retardo'
                else:
                    estatus = 'Presente'
                    
                canon_rows.append({
                    "campus": campus,
                    "tipo_persona": tipo_persona,
                    "matricula": matricula_val,
                    "nombre": nombre,
                    "apellidos": apellidos,
                    "nivel_normalizado": nivel_norm,
                    "grado_grupo": grado_grupo,
                    "fecha": date_val,
                    "hora_entrada": hora_entrada,
                    "hora_salida": hora_salida,
                    "estatus": estatus,
                    "campus_ciclo": None,
                    "fuente_archivo": filename,
                    "fuente_hoja": sheetname
                })
            except Exception as e:
                reporte_val["filas_rechazadas"].append({
                    "archivo": filename, "hoja": sheetname, "fila": i + 1, "columna": "Todas", "valor": None, "motivo": f"Error: {e}"
                })
                
    elif signature == "Firma C":
        for i, row in df_data.iterrows():
            try:
                date_val = parse_date(row.get('Fecha') or row.get('Date'))
                if date_val is None:
                    reporte_val["filas_rechazadas"].append({
                        "archivo": filename, "hoja": sheetname, "fila": i + 1, "columna": "Fecha", "valor": str(row.get('Fecha')), "motivo": "Fecha no parseable"
                    })
                    continue
                
                nombre = str(row.get('Nombre') or row.get('Empleado') or row.get('Maestro') or '').strip().title()
                apellidos = str(row.get('Apellidos') or '').strip().title()
                
                mat_col = [c for c in headers if str(c).lower().strip() in ['matrícula', 'matricula', 'id']]
                matricula_val = row.get(mat_col[0]) if mat_col else None
                if pd.isna(matricula_val) or str(matricula_val).strip() in ['---', '', 'None', 'nan']:
                    matricula_val = None
                else:
                    matricula_val = str(matricula_val).strip()
                    
                orig_nivel = row.get('Nivel')
                nivel_norm = normalizar_nivel(orig_nivel)
                
                if nivel_norm == "SIN_MAPEAR":
                    grado_val = row.get('Grado y grupo') or row.get('Grado') or row.get('Grupo')
                    if pd.notna(grado_val):
                        nivel_norm = normalizar_nivel(grado_val)
                if nivel_norm == "SIN_MAPEAR" and is_staff_sheet:
                    nivel_norm = "Staff"
                elif nivel_norm == "SIN_MAPEAR":
                    nivel_norm = normalizar_nivel(sheetname)
                
                if orig_nivel and pd.notna(orig_nivel) and str(orig_nivel).strip() not in ['', '---']:
                    if nivel_norm == "SIN_MAPEAR":
                        reporte_val["valores_no_mapeados"].append({
                            "archivo": filename, "hoja": sheetname, "fila": i + 1, "columna": "Nivel", "valor": str(orig_nivel)
                        })
                    
                grado_grupo = row.get('Grado') or row.get('Grado y grupo')
                if pd.isna(grado_grupo) or str(grado_grupo).strip() in ['---', '', 'None', 'nan']:
                    grado_grupo = None
                else:
                    grado_grupo = str(grado_grupo).strip()
                    
                hora_entrada = parse_time(row.get('Hora de ingreso') or row.get('Hora ingreso') or row.get('Entrada'))
                hora_salida = parse_time(row.get('Hora de salida') or row.get('Hora salida') or row.get('Salida'))
                
                estatus = normalizar_estatus(row.get('Asistencia') or row.get('Estatus'))
                
                perfil_val = str(row.get('Perfil') or row.get('Rol') or '').lower().strip()
                if is_staff_sheet or any(x in perfil_val for x in ['maestr', 'docen', 'staff', 'admin', 'emplead', 'coordin', 'direc', 'teacher', 'employee', 'colaborador']):
                    tipo_persona = 'colaborador'
                elif nivel_norm in ['Preescolar', 'Primaria', 'Secundaria']:
                    tipo_persona = 'alumno'
                else:
                    if matricula_val is not None:
                        tipo_persona = 'alumno'
                    else:
                        tipo_persona = 'colaborador'
                    
                canon_rows.append({
                    "campus": campus,
                    "tipo_persona": tipo_persona,
                    "matricula": matricula_val,
                    "nombre": nombre,
                    "apellidos": apellidos,
                    "nivel_normalizado": nivel_norm,
                    "grado_grupo": grado_grupo,
                    "fecha": date_val,
                    "hora_entrada": hora_entrada,
                    "hora_salida": hora_salida,
                    "estatus": estatus,
                    "campus_ciclo": None,
                    "fuente_archivo": filename,
                    "fuente_hoja": sheetname
                })
            except Exception as e:
                reporte_val["filas_rechazadas"].append({
                    "archivo": filename, "hoja": sheetname, "fila": i + 1, "columna": "Todas", "valor": None, "motivo": f"Error: {e}"
                })
                
    elif signature == "Firma B":
        row_headcount = None
        for idx in range(row_idx):
            row_vals = [str(val).lower().strip() for val in df_raw.iloc[idx]]
            if any(k in row_vals for k in ['alumnos', 'colaborador', 'total por nivel']):
                row_headcount = df_raw.iloc[idx].values
                
        for i, row in df_data.iterrows():
            try:
                date_val = parse_date(row.get('Fecha'))
                if date_val is None:
                    continue
                
                is_staff = 'colaboradores' in sheetname.lower() or 'maestros' in sheetname.lower() or 'colaborador' in [str(c).lower() for c in headers]
                segmento = 'colaborador' if is_staff else 'alumno'
                
                for col in headers:
                    if col in ['Fecha', 'Total', 'Total de colaboradores', 'Total de alumnos Innovat', 'Porcentaje de asistencia por día'] or pd.isna(col):
                        continue
                        
                    nivel_norm = normalizar_nivel(col)
                    val_presentes = row.get(col)
                    if pd.isna(val_presentes) or str(val_presentes).strip() == '':
                        continue
                        
                    try:
                        presentes = float(str(val_presentes).replace(',', '.'))
                    except:
                        continue
                        
                    total_hc = None
                    if row_headcount is not None:
                        col_idx = list(headers).index(col)
                        if col_idx < len(row_headcount):
                            try:
                                total_hc = float(str(row_headcount[col_idx]).replace(',', '.'))
                            except:
                                pass
                                
                    if total_hc is None or total_hc <= 0:
                        total_hc = presentes
                        
                    tasa = presentes / total_hc if total_hc > 0 else 1.0
                    tasa = min(1.0, max(0.0, tasa))
                    
                    summary_rows.append({
                        "campus": campus,
                        "fecha": date_val,
                        "segmento": segmento,
                        "nivel": nivel_norm,
                        "presentes": int(presentes) if presentes.is_integer() else presentes,
                        "total": int(total_hc) if total_hc.is_integer() else total_hc,
                        "tasa_asistencia": round(tasa, 4),
                        "fuente_archivo": filename,
                        "fuente_hoja": sheetname
                    })
                    
                total_presentes = row.get('Total') or row.get('Total de colaboradores')
                total_hc_global = row.get('Total de alumnos Innovat')
                tasa_global = row.get('Porcentaje de asistencia por día') or row.get('TOTAL')
                
                try:
                    presentes = float(str(total_presentes).replace(',', '.')) if pd.notna(total_presentes) else None
                except:
                    presentes = None
                    
                try:
                    total_hc = float(str(total_hc_global).replace(',', '.')) if pd.notna(total_hc_global) else None
                except:
                    total_hc = None
                    
                try:
                    tasa = float(str(tasa_global).replace(',', '.').replace('%', '')) if pd.notna(tasa_global) else None
                    if tasa is not None and tasa > 1.0:
                        tasa = tasa / 100.0
                except:
                    tasa = None
                    
                if presentes is not None:
                    if total_hc is None:
                        total_hc = presentes
                    if tasa is None:
                        tasa = presentes / total_hc if total_hc > 0 else 1.0
                        
                    summary_rows.append({
                        "campus": campus,
                        "fecha": date_val,
                        "segmento": segmento,
                        "nivel": "Total",
                        "presentes": int(presentes) if presentes.is_integer() else presentes,
                        "total": int(total_hc) if total_hc.is_integer() else total_hc,
                        "tasa_asistencia": round(tasa, 4),
                        "fuente_archivo": filename,
                        "fuente_hoja": sheetname
                    })
            except Exception as e:
                pass
                
    return canon_rows, summary_rows

def procesar_archivo_asistencia(path_o_buffer, campus) -> (pd.DataFrame, dict):
    """
    Función principal autónoma para procesar y normalizar un archivo Excel de asistencia.
    Retorna un DataFrame canónico consolidado y un diccionario con el reporte detallado de validación.
    """
    filename = "Archivo_Subido"
    if isinstance(path_o_buffer, str):
        filename = os.path.basename(path_o_buffer)
    elif hasattr(path_o_buffer, "name"):
        filename = path_o_buffer.name
        
    reporte_validacion = {
        "status": "success",
        "fuente_archivo": filename,
        "campus": campus,
        "hojas_procesadas": [],
        "hojas_ignoradas": [],
        "filas_rechazadas": [],
        "valores_no_mapeados": [],
        "firmas_detectadas": {},
        "resumen_diario_nivel": pd.DataFrame()
    }
    
    todas_filas_canon = []
    todas_filas_resumen = []
    
    try:
        xl = pd.ExcelFile(path_o_buffer)
        for sheetname in xl.sheet_names:
            try:
                df_raw = pd.read_excel(xl, sheet_name=sheetname, header=None)
                signature, row_idx, headers = detectar_firma_hoja(df_raw, sheetname=sheetname)
                
                reporte_validacion["firmas_detectadas"][sheetname] = signature
                
                if signature == "Unknown":
                    reporte_validacion["hojas_ignoradas"].append({
                        "hoja": sheetname,
                        "motivo": "No coincide con Firma A, B o C (no cumple con las firmas de columnas esperadas)."
                    })
                    continue
                    
                canon, summary = parsear_hoja(df_raw, signature, row_idx, headers, campus, filename, sheetname, reporte_validacion)
                
                if signature in ["Firma A", "Firma C"]:
                    todas_filas_canon.extend(canon)
                    reporte_validacion["hojas_procesadas"].append({
                        "hoja": sheetname,
                        "firma": signature,
                        "filas_cargadas": len(canon)
                    })
                elif signature == "Firma B":
                    todas_filas_resumen.extend(summary)
                    reporte_validacion["hojas_procesadas"].append({
                        "hoja": sheetname,
                        "firma": signature,
                        "filas_cargadas": len(summary)
                    })
                    
            except Exception as e:
                reporte_validacion["hojas_ignoradas"].append({
                    "hoja": sheetname,
                    "motivo": f"Fallo catastrófico de lectura: {e}"
                })
                
    except Exception as e:
        reporte_validacion["status"] = "error"
        reporte_validacion["error_detalle"] = str(e)
        return pd.DataFrame(), reporte_validacion
        
    # Consolidar DataFrame Canónico
    if todas_filas_canon:
        df_canon = pd.DataFrame(todas_filas_canon)
        
        # Deduplicar
        # Separar alumnos y colaboradores para deduplicar con criterios específicos
        df_alumnos = df_canon[df_canon['tipo_persona'] == 'alumno'].copy()
        df_colabs = df_canon[df_canon['tipo_persona'] == 'colaborador'].copy()
        
        if not df_alumnos.empty:
            # Deduplicar alumnos: si tiene matrícula usar matrícula + fecha + estatus, si no usar nombre + apellidos + fecha + estatus
            mask_has_mat = df_alumnos['matricula'].notna()
            df_al_with_mat = df_alumnos[mask_has_mat].drop_duplicates(subset=['matricula', 'fecha', 'estatus'], keep='first')
            df_al_no_mat = df_alumnos[~mask_has_mat].drop_duplicates(subset=['nombre', 'apellidos', 'fecha', 'estatus'], keep='first')
            df_alumnos = pd.concat([df_al_with_mat, df_al_no_mat], ignore_index=True)
            
        if not df_colabs.empty:
            df_colabs = df_colabs.drop_duplicates(subset=['nombre', 'apellidos', 'fecha', 'estatus'], keep='first')
            
        df_canon = pd.concat([df_alumnos, df_colabs], ignore_index=True)
    else:
        df_canon = pd.DataFrame(columns=[
            'campus', 'tipo_persona', 'matricula', 'nombre', 'apellidos', 
            'nivel_normalizado', 'grado_grupo', 'fecha', 'hora_entrada', 
            'hora_salida', 'estatus', 'campus_ciclo', 'fuente_archivo', 'fuente_hoja'
        ])
        
    # Consolidar DataFrame Resumen (Firma B)
    if todas_filas_resumen:
        df_resumen = pd.DataFrame(todas_filas_resumen)
        # Deduplicar resúmenes agregados por campus, fecha, segmento y nivel
        df_resumen = df_resumen.drop_duplicates(subset=['campus', 'fecha', 'segmento', 'nivel'], keep='first')
        reporte_validacion["resumen_diario_nivel"] = df_resumen
        
    # Establecer estado warning si hay rechazos o campos sin mapear
    if reporte_validacion["filas_rechazadas"] or reporte_validacion["valores_no_mapeados"]:
        reporte_validacion["status"] = "warning"
        
    return df_canon, reporte_validacion

def convertir_canonico_a_agregado(df_canonico, df_resumen, campus):
    """
    Convierte el DataFrame canónico de grano de persona y el resumen diario
    a los formatos agregados heredados (df_niveles, staff_kpi, extra_info) 
    para mantener la compatibilidad con el resto del sistema de Everwise.
    """
    df_levels = pd.DataFrame()
    staff_asis = 0.90
    staff_desglose = {}
    dias_alumnos = None
    dias_staff = None
    
    # 1. Si tenemos datos de grano de persona (df_canonico)
    if df_canonico is not None and not df_canonico.empty:
        df_al = df_canonico[df_canonico['tipo_persona'] == 'alumno']
        df_staff = df_canonico[df_canonico['tipo_persona'] == 'colaborador']
        
        dias_alumnos = df_al['fecha'].nunique() if not df_al.empty else 0
        dias_staff = df_staff['fecha'].nunique() if not df_staff.empty else 0
        
        # Alumnos
        levels_list = []
        has_falta = (df_al['estatus'] == 'Falta').any()
        
        niveles_encontrados = list(df_al['nivel_normalizado'].unique())
        for x in ['Preescolar', 'Primaria', 'Secundaria']:
            if x not in niveles_encontrados:
                niveles_encontrados.append(x)
                
        total_pob = 0
        pob_por_nivel = {}
        for lvl in niveles_encontrados:
            df_lvl = df_al[df_al['nivel_normalizado'] == lvl]
            if df_lvl.empty:
                pob_por_nivel[lvl] = 0
                continue
            if has_falta:
                pob = df_lvl['matricula'].nunique()
            else:
                # daily proxy
                daily = df_lvl.groupby('fecha')['matricula'].nunique()
                pob = daily.max() if not daily.empty else 0
            pob_por_nivel[lvl] = pob
            total_pob += pob
            
        for lvl in niveles_encontrados:
            if lvl == 'SIN_MAPEAR' and pob_por_nivel.get(lvl, 0) == 0:
                continue
            df_lvl = df_al[df_al['nivel_normalizado'] == lvl]
            if df_lvl.empty:
                asis_rate = 0.0
            else:
                if has_falta:
                    total_rows = len(df_lvl)
                    present_rows = len(df_lvl[df_lvl['estatus'].isin(['Presente', 'Retardo'])])
                    asis_rate = present_rows / total_rows if total_rows > 0 else 0.0
                else:
                    daily = df_lvl.groupby('fecha')['matricula'].nunique()
                    max_pob = pob_por_nivel[lvl]
                    asis_rate = (daily.mean() / max_pob) if max_pob > 0 else 0.0
                    
            distrib = (pob_por_nivel[lvl] / total_pob) if total_pob > 0 else (1.0 / len(niveles_encontrados))
            levels_list.append({
                'Nivel': lvl,
                'Asistencia': round(asis_rate, 4),
                'Distribución': round(distrib, 4)
            })
        df_levels = pd.DataFrame(levels_list)
        
        # Staff
        if not df_staff.empty:
            has_falta_staff = (df_staff['estatus'] == 'Falta').any()
            if has_falta_staff:
                total_s = len(df_staff)
                present_s = len(df_staff[df_staff['estatus'].isin(['Presente', 'Retardo'])])
                staff_asis = present_s / total_s if total_s > 0 else 0.0
            else:
                daily_s = df_staff.groupby('fecha')['nombre'].count()
                max_s = daily_s.max() if not daily_s.empty else 0
                staff_asis = (daily_s.mean() / max_s) if max_s > 0 else 0.0
                
            for lvl in df_staff['nivel_normalizado'].unique():
                df_lvl_s = df_staff[df_staff['nivel_normalizado'] == lvl]
                if has_falta_staff:
                    total_l = len(df_lvl_s)
                    present_l = len(df_lvl_s[df_lvl_s['estatus'].isin(['Presente', 'Retardo'])])
                    rate_l = present_l / total_l if total_l > 0 else 0.0
                else:
                    daily_l = df_lvl_s.groupby('fecha')['nombre'].count()
                    max_l = daily_l.max() if not daily_l.empty else 0
                    rate_l = (daily_l.mean() / max_l) if max_l > 0 else 0.0
                lvl_key = "Staff General" if (pd.isna(lvl) or str(lvl).strip().upper() in ["SIN_MAPEAR", "NONE", "NAN", ""]) else str(lvl).strip()
                staff_desglose[lvl_key] = round(rate_l, 4)
                
    # 2. Si no tenemos df_canonico pero tenemos df_resumen (Firma B)
    elif df_resumen is not None and not df_resumen.empty:
        df_al = df_resumen[df_resumen['segmento'] == 'alumno']
        df_staff = df_resumen[df_resumen['segmento'] == 'colaborador']
        
        dias_alumnos = df_al['fecha'].nunique() if not df_al.empty else 0
        dias_staff = df_staff['fecha'].nunique() if not df_staff.empty else 0
        
        # Alumnos
        levels_list = []
        if not df_al.empty:
            grouped = df_al.groupby('nivel').agg(
                Asistencia=('tasa_asistencia', 'mean'),
                TotalHC=('total', 'mean')
            ).reset_index()
            
            df_levels_only = grouped[grouped['nivel'] != 'Total']
            total_hc = df_levels_only['TotalHC'].sum()
            
            for _, row in df_levels_only.iterrows():
                distrib = (row['TotalHC'] / total_hc) if total_hc > 0 else (1.0 / len(df_levels_only))
                levels_list.append({
                    'Nivel': row['nivel'],
                    'Asistencia': round(row['Asistencia'], 4),
                    'Distribución': round(distrib, 4)
                })
        df_levels = pd.DataFrame(levels_list)
        
        # Staff
        if not df_staff.empty:
            df_total_staff = df_staff[df_staff['nivel'] == 'Total']
            if not df_total_staff.empty:
                staff_asis = df_total_staff['tasa_asistencia'].mean()
            else:
                staff_asis = df_staff['tasa_asistencia'].mean()
                
            df_desglose_staff = df_staff[df_staff['nivel'] != 'Total']
            for lvl, grp in df_desglose_staff.groupby('nivel'):
                staff_desglose[lvl] = round(grp['tasa_asistencia'].mean(), 4)
                
    extra_info = {
        "es_matriz": False if df_canonico is not None and not df_canonico.empty else True,
        "staff_desglose": staff_desglose,
        "dias_alumnos": dias_alumnos,
        "dias_staff": dias_staff,
        "df_canonico": df_canonico,
        "df_resumen": df_resumen
    }
    
    return df_levels, staff_asis, extra_info

