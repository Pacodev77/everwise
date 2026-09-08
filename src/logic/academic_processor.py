# src/logic/academic_processor.py

import re
import pandas as pd
# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
import numpy as np

COLUMNAS_REQUERIDAS = {"MATRICULA", "ALUMNO", "Grupo", "Language Arts", "Matemáticas", "Español", "Nivel"}

def validar_columnas(df: pd.DataFrame) -> tuple[bool, str]:
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        return False, f"Columnas faltantes: {', '.join(faltantes)}"
    return True, ""

def detectar_campus(nombre_archivo: str) -> str:
    nombre = nombre_archivo.lower()
    if "san" in nombre or "agustin" in nombre or "agustín" in nombre:
        return "San Agustín"
    if "misiones" in nombre:
        return "Misiones"
    if "sur" in nombre or "nuevo" in nombre:
        return "Nuevo Sur"
    return "Desconocido"

def detectar_bimestre(nombre_archivo: str) -> str:
    nombre = nombre_archivo.upper()

    # 1. Roman numerals with prefix (e.g. BIM_IV, BIMESTRE IV, B-IV, BIMIV)
    match_romano = re.search(r'(?:BIMESTRE|BLOQUE|BIM|B)[_\s-]*(V|IV|III|II|I)(?=[^A-Z0-9]|$)', nombre)
    if match_romano:
        romanos = {"I": "B1", "II": "B2", "III": "B3", "IV": "B4", "V": "B5"}
        return romanos.get(match_romano.group(1), "B?")

    # 2. Arabic numbers with prefix (e.g. BIMESTRE 4, BLOQUE 4, BIM_4, B-4, B4)
    match_arabigo = re.search(r'(?:BIMESTRE|BLOQUE|BIM|B)[_\s-]*([1-5])(?=[^0-9]|$)', nombre)
    if match_arabigo:
        return f"B{match_arabigo.group(1)}"

    # 3. Direct B1 to B5 tokens
    match_directo = re.search(r'\bB([1-5])\b', nombre)
    if match_directo:
        return f"B{match_directo.group(1)}"

    return "B?"

def _normalizar_texto_columna(col_name) -> str:
    c = str(col_name).strip().lower()
    c = (c.replace('á', 'a')
          .replace('é', 'e')
          .replace('í', 'i')
          .replace('ó', 'o')
          .replace('ú', 'u')
          .replace('ñ', 'n'))
    return c

def _mapear_columnas_hoja(df: pd.DataFrame) -> dict:
    columns = df.columns.tolist()
    cleaned = [_normalizar_texto_columna(c) for c in columns]
    col_map = {}
    
    # 1. MATRICULA
    for orig, c in zip(columns, cleaned):
        if orig in col_map: continue
        if any(k in c for k in ['matricula', 'student id', 'no. control', 'num control', 'control', 'id']) and len(c) < 25:
            col_map[orig] = 'MATRICULA'
            break
            
    # 2. ALUMNO
    for orig, c in zip(columns, cleaned):
        if orig in col_map: continue
        if any(k in c for k in ['alumno', 'nombre', 'student name', 'name', 'estudiante']) and len(c) < 25:
            col_map[orig] = 'ALUMNO'
            break

    # 3. Language Arts
    for orig, c in zip(columns, cleaned):
        if orig in col_map: continue
        if re.match(r'^(language\s*arts|english|ingles|reading|writing|lae\d*|lam\d*|la\d*|la)$', c) or ('language' in c and 'art' in c):
            col_map[orig] = 'Language Arts'
            break

    # 4. Matemáticas
    for orig, c in zip(columns, cleaned):
        if orig in col_map: continue
        if re.match(r'^(matematicas?|maths?|mathe\d*|mathm\d*|math\d*|mates?|calculo)$', c) or ('matemat' in c) or ('math' in c):
            col_map[orig] = 'Matemáticas'
            break

    # 5. Español
    for orig, c in zip(columns, cleaned):
        if orig in col_map: continue
        if re.match(r'^(espanol|spanish|espe\d*|espm\d*|esp\d*|esp|lengua|lectura|literatura)$', c) or ('espanol' in c) or ('spanish' in c):
            col_map[orig] = 'Español'
            break

    # 6. Grupo / Grado
    for orig, c in zip(columns, cleaned):
        if orig in col_map: continue
        if c in ['grupo', 'grade', 'grado', 'class', 'seccion', 'gp'] or c.startswith('grupo') or c.startswith('grado'):
            col_map[orig] = 'Grupo'
            break
            
    if 'Grupo' not in col_map.values():
        for orig in columns:
            if orig in col_map: continue
            sample = df[orig].dropna().astype(str).str.strip()
            if not sample.empty and sample.str.match(r'^\d+[A-Za-z]?$').mean() > 0.5:
                col_map[orig] = 'Grupo'
                break

    # 7. Nivel o Grado explícito si existe
    for orig, c in zip(columns, cleaned):
        if orig in col_map: continue
        if any(k in c for k in ['nivel', 'seccion', 'section', 'level', 'educativo']) and len(c) < 25:
            col_map[orig] = 'Nivel_Col'
            break
        elif any(k in c for k in ['grado', 'grade']) and len(c) < 20:
            col_map[orig] = 'Grado_Col'
            break

    return col_map

def _inferir_nivel_fila(row, sheet_name: str, file_name: str) -> str:
    # 1. Si la columna original Nivel_Col tiene un valor específico
    if "Nivel_Col" in row and pd.notna(row["Nivel_Col"]):
        n_str = str(row["Nivel_Col"]).strip().lower()
        if any(x in n_str for x in ["pre", "kin", "mat", "preschool", "kinder"]):
            return "Preescolar"
        elif any(x in n_str for x in ["pri", "elem", "primary", "primaria"]):
            return "Primaria"
        elif any(x in n_str for x in ["sec", "mid", "middle", "secundaria", "prep", "high", "bach"]):
            return "Secundaria"

    # 2. Si el nombre de la pestaña no es genérico ("Sheet1", "Hoja1", etc.)
    s_lower = str(sheet_name).lower().strip()
    generic_sheets = ["sheet", "hoja", "page", "tabla", "table", "datos", "data", "consolidado", "calificaciones", "export", "califs"]
    is_generic = any(s_lower.startswith(g) or s_lower == g for g in generic_sheets) or not s_lower
    if not is_generic:
        if any(x in s_lower for x in ["pre", "kin", "mat", "preschool", "kinder"]):
            return "Preescolar"
        elif any(x in s_lower for x in ["pri", "elem", "primary", "primaria"]):
            return "Primaria"
        elif any(x in s_lower for x in ["sec", "mid", "middle", "secundaria", "prep", "high", "bach"]):
            return "Secundaria"

    # 3. Inferir desde Grado_Col si existe
    if "Grado_Col" in row and pd.notna(row["Grado_Col"]):
        g_str = str(row["Grado_Col"]).lower().strip()
        if any(x in g_str for x in ["pre", "kin", "mat", "k1", "k2", "k3", "pk"]):
            return "Preescolar"
        num_m = re.search(r"\b([0-9]|1[0-2])\b", g_str)
        if num_m:
            g_num = int(num_m.group(1))
            if 1 <= g_num <= 6: return "Primaria"
            elif 7 <= g_num <= 12: return "Secundaria"

    # 4. Inferir desde Grupo (ej. 1A..6B -> Primaria, 7A..9C / 1S..3S -> Secundaria, K1..K3 -> Preescolar)
    if "Grupo" in row and pd.notna(row["Grupo"]):
        grp = str(row["Grupo"]).upper().strip()
        if any(x in grp for x in ["K1", "K2", "K3", "PK", "MAT", "PRE"]):
            return "Preescolar"
        if any(x in grp for x in ["1S", "2S", "3S", "SEC", "MID", "MS"]):
            return "Secundaria"
        if any(x in grp for x in ["PRI", "ELEM"]):
            return "Primaria"
        m = re.match(r"^([1-9]|1[0-2])([A-Z]|\b)", grp)
        if m:
            g_num = int(m.group(1))
            if 1 <= g_num <= 6: return "Primaria"
            elif 7 <= g_num <= 12: return "Secundaria"

    # 5. Inferir desde el nombre del archivo
    f_lower = str(file_name).lower()
    if any(x in f_lower for x in ["pre", "kin", "mat", "preschool"]):
        return "Preescolar"
    elif any(x in f_lower for x in ["pri", "elem", "primary", "primaria"]):
        return "Primaria"
    elif any(x in f_lower for x in ["sec", "mid", "middle", "secundaria"]):
        return "Secundaria"

    return "Primaria"

def limpiar_y_estandarizar_hoja(df: pd.DataFrame, sheet_name: str, campus: str, bimestre: str, file_name: str = "") -> pd.DataFrame:
    df = df.copy()
    
    # 1. Intentar mapeo de columnas con cabecera actual
    col_map = _mapear_columnas_hoja(df)
    
    # 2. Si no encuentra MATRICULA o ALUMNO, buscar cabecera en las primeras 5 filas
    if "MATRICULA" not in col_map.values() or "ALUMNO" not in col_map.values():
        for r_idx in range(min(5, len(df))):
            row_df = df.iloc[r_idx+1:].copy()
            row_df.columns = df.iloc[r_idx].tolist()
            map_try = _mapear_columnas_hoja(row_df)
            if "MATRICULA" in map_try.values() and "ALUMNO" in map_try.values():
                df = row_df
                col_map = map_try
                break

    if "MATRICULA" not in col_map.values() or "ALUMNO" not in col_map.values():
        return None

    df = df.rename(columns=col_map)

    # 3. Rellenar columnas faltantes no críticas
    if "Grupo" not in df.columns:
        df["Grupo"] = "G1"
    for m in ["Language Arts", "Matemáticas", "Español"]:
        if m not in df.columns:
            df[m] = 0.0

    # 4. Determinar el Nivel Educativo por fila para evitar hardcoding de "Sheet1"
    df["Nivel"] = df.apply(lambda r: _inferir_nivel_fila(r, sheet_name, file_name), axis=1)

    # 5. Limpieza de Filas (identificación, no vacíos, sin totales/firmas)
    df = df.dropna(subset=["MATRICULA", "ALUMNO"])
    df["MATRICULA"] = df["MATRICULA"].astype(str).str.strip()
    df["ALUMNO"] = df["ALUMNO"].astype(str).str.strip()
    df = df[(df["MATRICULA"] != "") & (df["ALUMNO"] != "")]

    excluir_keywords = ["total", "promedio", "average", "summary", "media", "resumen", "recap", "firma"]
    mask_excluir = (
        df["MATRICULA"].str.lower().str.contains("|".join(excluir_keywords), na=False) |
        df["ALUMNO"].str.lower().str.contains("|".join(excluir_keywords), na=False)
    )
    df = df[~mask_excluir]

    # 6. Conversión de Calificaciones a Flotantes y Normalización a escala [0.0, 10.0]
    for col in ["Language Arts", "Matemáticas", "Español"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Si toda la columna está en escala 0-1 (ej: 0.85 para 85%), multiplicar por 10
        max_val = df[col].max()
        if pd.notna(max_val) and max_val <= 1.0 and max_val > 0.0:
            df[col] = df[col] * 10.0
            
        # Dividir por 10 únicamente los valores individuales mayores a 10.0 (ej: 100 -> 10.0, 85 -> 8.5)
        df.loc[df[col] > 10.0, col] = df[col] / 10.0
        
        # Limitar rango al intervalo [0.0, 10.0]
        df[col] = df[col].clip(0.0, 10.0).fillna(0.0)

    cols_finales = ["MATRICULA", "ALUMNO", "Grupo", "Language Arts", "Matemáticas", "Español", "Nivel"]
    return df[cols_finales]

def calcular_desempeno_por_nivel(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["en_desempeno"] = (
        (df["Language Arts"] >= 8) &
        (df["Matemáticas"] >= 8) &
        (df["Español"] >= 8)
    )
    resumen = df.groupby("Nivel").agg(
        total=("MATRICULA", "count"),
        en_desempeno=("en_desempeno", "sum")
    ).reset_index()
    resumen["pct_desempeno"] = (resumen["en_desempeno"] / resumen["total"] * 100).round(1)
    return resumen

def calcular_promedios_por_nivel(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("Nivel").agg(
        language_arts=("Language Arts", "mean"),
        matemáticas=("Matemáticas", "mean"),
        español=("Español", "mean"),
        total_alumnos=("MATRICULA", "count")
    ).reset_index().round(2)

def procesar_archivo_academico(uploaded_file, target_campus: str = None) -> dict:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
    except Exception as e:
        return {"error": f"No se pudo leer el archivo Excel: {e}"}

    file_name = uploaded_file if isinstance(uploaded_file, str) else getattr(uploaded_file, "name", "Desconocido")
    campus   = detectar_campus(file_name)
    bimestre = detectar_bimestre(file_name)

    # Validar coincidencia de campus si se especifica la sede esperada
    if target_campus:
        if campus != "Desconocido" and campus != target_campus:
            return {
                "error": f"**Archivo no permitido:** El archivo '{file_name}' pertenece a **{campus}**, pero estás en la sede **{target_campus}**. Por favor sube el archivo en su campus correspondiente.",
                "campus": campus,
                "bimestre": bimestre,
                "df_raw": None,
                "desempeno": None,
                "promedios": None,
                "total_alumnos": 0
            }
        elif campus == "Desconocido":
            campus = target_campus

    all_dfs = []
    for sheet in sheet_names:
        sheet_lower = sheet.lower()
        # Omitir hojas informativas o de resúmenes
        if any(x in sheet_lower for x in ["resumen", "summary", "instrucciones", "info", "totales"]):
            continue

        try:
            df_sheet = pd.read_excel(xls, sheet_name=sheet)
        except Exception:
            continue

        if df_sheet.empty:
            continue

        df_clean = limpiar_y_estandarizar_hoja(df_sheet, sheet, campus, bimestre, file_name=file_name)
        if df_clean is not None and not df_clean.empty:
            all_dfs.append(df_clean)

    if not all_dfs:
        return {"error": "No se encontraron hojas válidas con calificaciones o alumnos."}

    df_combined = pd.concat(all_dfs, ignore_index=True)

    # Persistencia solo si el campus es válido y coincide
    if campus != "Desconocido":
        from src.logic.data_loader import save_academic_data
        save_academic_data(campus, bimestre, df_combined)

    return {
        "campus"        : campus,
        "bimestre"      : bimestre,
        "df_raw"        : df_combined,
        "desempeno"     : calcular_desempeno_por_nivel(df_combined),
        "promedios"     : calcular_promedios_por_nivel(df_combined),
        "total_alumnos" : len(df_combined),
        "error"         : None
    }


def calcular_dominio_academico(df: pd.DataFrame) -> float:
    """Calcula el Dominio Académico Promedio (GPA %) continuo en escala 0.0 a 1.0."""
    if df is None or df.empty:
        return 0.0
    prom_la = float(df["Language Arts"].mean()) if "Language Arts" in df.columns else 0.0
    prom_math = float(df["Matemáticas"].mean()) if "Matemáticas" in df.columns else 0.0
    prom_esp = float(df["Español"].mean()) if "Español" in df.columns else 0.0
    return float(round((prom_la + prom_math + prom_esp) / 3.0 / 10.0, 3))


def calcular_kpis_ejecutivos(resultado: dict) -> dict:
    """Extrae los KPIs principales para el Resumen Ejecutivo del campus."""
    df = resultado["df_raw"]

    prom_math = df["Matemáticas"].mean() / 10.0 if "Matemáticas" in df.columns else 0.0
    prom_esp  = df["Español"].mean() / 10.0 if "Español" in df.columns else 0.0
    prom_la   = df["Language Arts"].mean() / 10.0 if "Language Arts" in df.columns else 0.0

    df_copy = df.copy()
    df_copy["en_desempeno"] = (
        (df_copy["Language Arts"] >= 8) &
        (df_copy["Matemáticas"] >= 8) &
        (df_copy["Español"] >= 8)
    )
    pct_desempeno_global = df_copy["en_desempeno"].mean()

    return {
        "bimestre"           : resultado["bimestre"],
        "campus"             : resultado["campus"],
        "total_alumnos"      : resultado["total_alumnos"],
        "prom_math"          : round(prom_math, 3),
        "prom_español"       : round(prom_esp, 3),
        "prom_language_arts" : round(prom_la, 3),
        "pct_desempeno"      : round(pct_desempeno_global, 3),
        "dominio_academico"  : calcular_dominio_academico(df),
    }

def acumular_bimestre(sede: str, resultado: dict):
    """Guarda el promedio de desempeño del bimestre en session_state para la gráfica histórica."""
    clave = f"historial_bimestres_{sede}"
    if clave not in st.session_state:
        st.session_state[clave] = {}

    bimestre = resultado["bimestre"]
    df = resultado["df_raw"]

    st.session_state[clave][bimestre] = calcular_dominio_academico(df)

def calcular_distribucion_desempeno(df: pd.DataFrame) -> pd.DataFrame:
    """Distribución global: cuántos alumnos en cada categoría de desempeño."""
    df = df.copy()
    df["categoria"] = df.apply(_categorizar_alumno, axis=1)

    resumen = df["categoria"].value_counts().reset_index()
    resumen.columns = ["Categoría", "Alumnos"]
    total = len(df)
    resumen["Porcentaje"] = (resumen["Alumnos"] / total * 100).round(1)

    color_map = {
        "Sobresaliente"  : "#22c55e",
        "En desempeño"   : "#3b82f6",
        "En progreso"    : "#f59e0b",
        "Necesita apoyo" : "#ef4444",
    }
    resumen["Color"] = resumen["Categoría"].map(color_map)
    return resumen

def _categorizar_alumno(row) -> str:
    promedio = (row["Language Arts"] + row["Matemáticas"] + row["Español"]) / 3
    cumple_todas = (
        row["Language Arts"] >= 8 and
        row["Matemáticas"] >= 8 and
        row["Español"] >= 8
    )
    if cumple_todas and promedio >= 9.3:
        return "Sobresaliente"
    elif cumple_todas:
        return "En desempeño"
    elif promedio >= 7:
        return "En progreso"
    else:
        return "Necesita apoyo"

def calcular_color_nivel(pct: float) -> str:
    """Color dinámico según % de desempeño."""
    if pct >= 70:
        return "#22c55e"
    elif pct >= 50:
        return "#3b82f6"
    elif pct >= 30:
        return "#f59e0b"
    else:
        return "#ef4444"