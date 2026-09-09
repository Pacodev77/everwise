# src/logic/ixl_processor.py

import pandas as pd
import numpy as np
# pyrefly: ignore [missing-import]
import streamlit as st

AREAS_MATH = [
    "Numbers and operations",
    "Algebra and algebraic thinking",
    "Fractions",
    "Geometry",
    "Measurement",
    "Data, statistics, and probability"
]

TIER_ORDEN = ["Far below grade", "Below grade", "On grade", "Above grade"]
TIER_COLOR = {
    "Far below grade" : "#ef4444",
    "Below grade"     : "#f59e0b",
    "On grade"        : "#22c55e",
    "Above grade"     : "#3b82f6",
}

def clean_numeric(series) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float)
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    if series.dtype == object:
        cleaned = series.astype(str).str.strip().str.replace("%", "", regex=False)
        cleaned = cleaned.replace(["", "-", "--", "N/A", "nan", "None"], None)
        return pd.to_numeric(cleaned, errors='coerce')
    return pd.to_numeric(series, errors='coerce')

def normalizar_nombre_school(val) -> str | None:
    if pd.isna(val):
        return None
    v = str(val).lower().strip()
    if any(k in v for k in ["san agustin", "agustin", "cumbres"]):
        return "San Agustín"
    elif "misiones" in v:
        return "Misiones"
    elif any(k in v for k in ["sur", "nuevo"]):
        return "Nuevo Sur"
    return None

def procesar_ixl(uploaded_file, target_campus: str = None) -> dict:
    """
    Procesa un archivo IXL (CSV o Excel), soportando archivos únicos multi-campus (School).
    Mapea 'San Agustin Cumbres' -> 'San Agustín', 'Misiones' -> 'Misiones', 'Nuevo Sur' -> 'Nuevo Sur'.
    Soporta alias flexibles de columnas ('Percentile', 'Overall percentile', 'Grade', 'Grado', 'Overall tier', 'Tier').
    """
    try:
        file_name = getattr(uploaded_file, "name", str(uploaded_file)).lower()
        if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            try:
                df = pd.read_csv(uploaded_file)
            except UnicodeDecodeError:
                if hasattr(uploaded_file, "seek"):
                    uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="latin1")
            except Exception:
                if hasattr(uploaded_file, "seek"):
                    uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
    except Exception as e:
        return {"error": f"No se pudo leer el archivo IXL: {e}"}

    if df is None or df.empty:
        return {"error": "El archivo IXL está vacío."}

    # Desduplicar nombres de columnas si existen repetidas desde el origen
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Normalización de cabeceras (mapping flexible de alias en inglés/español)
    col_map = {}
    school_col = None

    for col in df.columns:
        cl = str(col).strip().lower().replace("_", " ").replace("-", " ")
        cl = cl.encode("ascii", "ignore").decode("utf-8").strip()

        if cl in ["grade", "grado", "grade level", "gradelevel", "student grade"]:
            col_map[col] = "Grade"
        elif cl in ["percentile", "overall percentile", "percentil", "overall percentile score", "percentile score", "percentile %"]:
            col_map[col] = "Overall percentile"
        elif cl in ["overall tier", "tier", "overall tier level", "tier level", "performance tier", "tier status"]:
            col_map[col] = "Overall tier"
        elif cl in ["overall level", "level", "overall score"]:
            col_map[col] = "Overall level"
        elif cl in ["school", "escuela", "campus", "sede", "school name"]:
            col_map[col] = "School"
            school_col = "School"

    if col_map:
        df = df.rename(columns=col_map)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    if "School" in df.columns:
        school_col = "School"

    columnas_req = {"Grade", "Overall percentile"}
    cols_presentes = set(df.columns)
    faltantes = columnas_req - cols_presentes
    if faltantes:
        return {"error": f"Columnas faltantes en IXL: {', '.join(faltantes)}"}

    # Limpieza de valores numéricos de percentil
    s_pct = df["Overall percentile"]
    if isinstance(s_pct, pd.DataFrame):
        s_pct = s_pct.iloc[:, 0]
    df["Overall percentile"] = clean_numeric(s_pct)

    # Si 'Overall tier' no venía explícito pero tenemos percentil, podemos inferirlo
    s_tier = df["Overall tier"] if "Overall tier" in df.columns else None
    if isinstance(s_tier, pd.DataFrame):
        s_tier = s_tier.iloc[:, 0]

    if s_tier is None or s_tier.isnull().all():
        def infer_tier(p):
            if pd.isna(p): return "Sin datos"
            if p >= 60: return "Above grade"
            elif p >= 40: return "On grade"
            elif p >= 20: return "Below grade"
            else: return "Far below grade"
        df["Overall tier"] = df["Overall percentile"].apply(infer_tier)
    else:
        df["Overall tier"] = s_tier.astype(str).str.strip().replace(["--", "-", "", "N/A", "nan", "None"], np.nan).fillna("Sin datos")
    
    for area in AREAS_MATH:
        col_pct = f"{area} percentile"
        if col_pct in df.columns:
            s_area = df[col_pct]
            if isinstance(s_area, pd.DataFrame):
                s_area = s_area.iloc[:, 0]
            df[col_pct] = clean_numeric(s_area)

    # Manejo Multi-Campus si existe columna School
    campus_splits = {}
    if school_col:
        s_sch = df[school_col]
        if isinstance(s_sch, pd.DataFrame):
            s_sch = s_sch.iloc[:, 0]
        df["campus_normalizado"] = s_sch.apply(normalizar_nombre_school)
        if target_campus:
            df["campus_normalizado"] = df["campus_normalizado"].fillna(target_campus)
            
        campuses_encontrados = df["campus_normalizado"].dropna().unique()
        for c in campuses_encontrados:
            df_c = df[df["campus_normalizado"] == c].copy()
            res_c = {
                "error": None,
                "total_alumnos": len(df_c),
                "campus": c,
                "df_raw": df_c,
                "resumen_tier": calcular_resumen_tier(df_c),
                "resumen_grado": calcular_por_grado(df_c),
                "resumen_areas": calcular_areas(df_c),
            }
            campus_splits[c] = res_c
            acumular_ixl(c, res_c)
    else:
        c_name = target_campus if target_campus else "San Agustín"
        df["campus_normalizado"] = c_name
        res_c = {
            "error": None,
            "total_alumnos": len(df),
            "campus": c_name,
            "df_raw": df,
            "resumen_tier": calcular_resumen_tier(df),
            "resumen_grado": calcular_por_grado(df),
            "resumen_areas": calcular_areas(df),
        }
        campus_splits[c_name] = res_c
        acumular_ixl(c_name, res_c)

    return {
        "error"          : None,
        "total_alumnos"  : len(df),
        "df_raw"         : df,
        "campus_splits"  : campus_splits,
        "resumen_tier"   : calcular_resumen_tier(df),
        "resumen_grado"  : calcular_por_grado(df),
        "resumen_areas"  : calcular_areas(df),
    }

def calcular_resumen_tier(df: pd.DataFrame) -> pd.DataFrame:
    """% de alumnos por nivel de desempeño global."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Tier", "Alumnos", "Porcentaje", "Color"])
    df_calc = df.loc[:, ~df.columns.duplicated()].copy()
    total = len(df_calc)
    if total == 0 or "Overall tier" not in df_calc.columns:
        return pd.DataFrame(columns=["Tier", "Alumnos", "Porcentaje", "Color"])

    s_tier = df_calc["Overall tier"]
    if isinstance(s_tier, pd.DataFrame):
        s_tier = s_tier.iloc[:, 0]

    resumen = (
        s_tier
        .value_counts()
        .reset_index()
    )
    resumen.columns = ["Tier", "Alumnos"]
    resumen["Porcentaje"] = (resumen["Alumnos"] / total * 100).round(1)
    resumen["Color"] = resumen["Tier"].map(TIER_COLOR).fillna("#94a3b8")
    return resumen

def calcular_por_grado(df: pd.DataFrame) -> pd.DataFrame:
    """Percentil promedio y distribución de tiers por grado."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_calc = df.loc[:, ~df.columns.duplicated()].copy()
    if "Grade" not in df_calc.columns or "Overall percentile" not in df_calc.columns or "Overall tier" not in df_calc.columns:
        return pd.DataFrame()

    if isinstance(df_calc["Grade"], pd.DataFrame):
        df_calc["Grade"] = df_calc["Grade"].iloc[:, 0]
    if isinstance(df_calc["Overall percentile"], pd.DataFrame):
        df_calc["Overall percentile"] = df_calc["Overall percentile"].iloc[:, 0]
    if isinstance(df_calc["Overall tier"], pd.DataFrame):
        df_calc["Overall tier"] = df_calc["Overall tier"].iloc[:, 0]

    def format_grade(g):
        g_str = str(g).strip()
        if g_str.startswith("Grado "):
            return g_str
        try:
            val_f = float(g_str)
            if val_f.is_integer():
                return f"Grado {int(val_f)}"
            return f"Grado {val_f}"
        except Exception:
            return f"Grado {g_str}"

    df_calc["GradeLabel"] = df_calc["Grade"].apply(format_grade)

    resumen = df_calc.groupby("GradeLabel").agg(
        total=("GradeLabel", "count"),
        percentil_prom=("Overall percentile", "mean"),
        on_or_above=("Overall tier", lambda x: (
            x.isin(["On grade", "Above grade"]).sum()
        ))
    ).reset_index().rename(columns={"GradeLabel": "Grade"})

    resumen["pct_on_above"] = (
        resumen["on_or_above"] / resumen["total"] * 100
    ).round(1)
    resumen["percentil_prom"] = resumen["percentil_prom"].fillna(0.0).round(1)

    def grade_sort_key(g):
        s = str(g).replace("Grado ", "").strip()
        try:
            return float(s)
        except Exception:
            return 999

    resumen = resumen.sort_values(by="Grade", key=lambda col: col.apply(grade_sort_key))
    return resumen

def calcular_areas(df: pd.DataFrame) -> pd.DataFrame:
    """Percentil promedio por área de Math."""
    if df is None or df.empty:
        return pd.DataFrame()
    df_calc = df.loc[:, ~df.columns.duplicated()].copy()
    filas = []
    for area in AREAS_MATH:
        col_pct = f"{area} percentile"
        if col_pct in df_calc.columns:
            s_area = df_calc[col_pct]
            if isinstance(s_area, pd.DataFrame):
                s_area = s_area.iloc[:, 0]
            mean_val = pd.to_numeric(s_area, errors="coerce").mean()
            filas.append({
                "Área"     : area.replace(" and ", " & ").title(),
                "Percentil": round(mean_val, 1) if pd.notna(mean_val) else 0.0,
                "Color"    : "#3b82f6"
            })
    return pd.DataFrame(filas).sort_values("Percentil", ascending=False) if filas else pd.DataFrame()

def acumular_ixl(sede: str, resultado: dict):
    """Guarda el resultado en session_state y SQLite para el campus."""
    clave = f"ixl_{sede}"
    st.session_state[clave] = resultado
    if resultado and "df_raw" in resultado:
        from src.logic.data_loader import save_ixl_diagnostics_data
        save_ixl_diagnostics_data(sede, resultado["df_raw"])

def cruzar_con_academico(resultado_ixl: dict, resultado_academico: dict) -> dict | None:
    """
    Cruza datos de IXL con calificaciones reales agregados por grado.
    """
    if resultado_ixl is None or resultado_academico is None:
        return None

    df_ixl = resultado_ixl.get("df_raw")
    df_aca = resultado_academico.get("df_raw")
    if df_ixl is None or df_aca is None or df_ixl.empty or df_aca.empty:
        return None

    df_ixl = df_ixl.loc[:, ~df_ixl.columns.duplicated()].copy()
    df_aca = df_aca.loc[:, ~df_aca.columns.duplicated()].copy()

    total_matricula = resultado_academico.get("total_alumnos", len(df_aca))
    total_ixl        = resultado_ixl.get("total_alumnos", len(df_ixl))
    pct_adopcion      = round(min(total_ixl / max(total_matricula, 1), 1.0) * 100, 1)

    # 1. Extraer GradoNum entero del dataframe académico
    if "Grupo" in df_aca.columns:
        s_grupo = df_aca["Grupo"]
        if isinstance(s_grupo, pd.DataFrame): s_grupo = s_grupo.iloc[:, 0]
        df_aca["GradoNum"] = pd.to_numeric(s_grupo.astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    else:
        return None
    df_aca = df_aca.dropna(subset=["GradoNum"])
    if df_aca.empty:
        return None
    df_aca["GradoNum"] = df_aca["GradoNum"].astype(int)

    col_math = "Matemáticas" if "Matemáticas" in df_aca.columns else ("Math" if "Math" in df_aca.columns else None)
    if not col_math:
        return None

    prom_academico_grado = df_aca.groupby("GradoNum").agg(
        promedio_calificacion=(col_math, "mean")
    ).reset_index()

    # 2. Extraer GradoNum entero del dataframe IXL
    if "Grade" in df_ixl.columns:
        s_grade = df_ixl["Grade"]
        if isinstance(s_grade, pd.DataFrame): s_grade = s_grade.iloc[:, 0]
        df_ixl["GradoNum"] = pd.to_numeric(s_grade.astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    else:
        return None
    df_ixl = df_ixl.dropna(subset=["GradoNum"])
    if df_ixl.empty:
        return None
    df_ixl["GradoNum"] = df_ixl["GradoNum"].astype(int)

    prom_ixl_grado = df_ixl.groupby("GradoNum").agg(
        percentil_ixl=("Overall percentile", "mean")
    ).reset_index()

    # 3. Garantizar que ambos GradoNum sean tipo int idéntico
    prom_ixl_grado["GradoNum"] = prom_ixl_grado["GradoNum"].astype(int)
    prom_academico_grado["GradoNum"] = prom_academico_grado["GradoNum"].astype(int)

    df_cruce = pd.merge(prom_ixl_grado, prom_academico_grado, on="GradoNum", how="inner")
    if df_cruce.empty:
        return None

    df_cruce["Grado"] = df_cruce["GradoNum"].apply(lambda g: f"Grado {g}")
    df_cruce["promedio_calificacion_pct"] = df_cruce["promedio_calificacion"] / 10 * 100

    return {
        "pct_adopcion"  : pct_adopcion,
        "total_ixl"     : total_ixl,
        "total_matricula": total_matricula,
        "df_cruce"      : df_cruce,
    }