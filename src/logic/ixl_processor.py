# src/logic/ixl_processor.py

import pandas as pd
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

def clean_numeric(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        cleaned = series.astype(str).str.strip().str.replace("%", "", regex=False)
        cleaned = cleaned.replace(["", "-", "--", "N/A", "nan", "None"], None)
        return pd.to_numeric(cleaned, errors='coerce')
    return pd.to_numeric(series, errors='coerce')

def procesar_ixl(uploaded_file) -> dict:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        return {"error": f"No se pudo leer el archivo: {e}"}

    columnas_req = {"Grade", "Overall percentile", "Overall tier"}
    faltantes = columnas_req - set(df.columns)
    if faltantes:
        return {"error": f"Columnas faltantes: {', '.join(faltantes)}"}

    df["Overall tier"] = df["Overall tier"].fillna("Sin datos")
    df["Overall percentile"] = clean_numeric(df["Overall percentile"])
    
    for area in AREAS_MATH:
        col_pct = f"{area} percentile"
        if col_pct in df.columns:
            df[col_pct] = clean_numeric(df[col_pct])

    return {
        "error"          : None,
        "total_alumnos"  : len(df),
        "df_raw"         : df,
        "resumen_tier"   : calcular_resumen_tier(df),
        "resumen_grado"  : calcular_por_grado(df),
        "resumen_areas"  : calcular_areas(df),
    }

def calcular_resumen_tier(df: pd.DataFrame) -> pd.DataFrame:
    """% de alumnos por nivel de desempeño global."""
    total = len(df)
    resumen = (
        df["Overall tier"]
        .value_counts()
        .reset_index()
    )
    resumen.columns = ["Tier", "Alumnos"]
    resumen["Porcentaje"] = (resumen["Alumnos"] / total * 100).round(1)
    resumen["Color"] = resumen["Tier"].map(TIER_COLOR).fillna("#94a3b8")
    return resumen

def calcular_por_grado(df: pd.DataFrame) -> pd.DataFrame:
    """Percentil promedio y distribución de tiers por grado."""
    resumen = df.groupby("Grade").agg(
        total=("Grade", "count"),
        percentil_prom=("Overall percentile", "mean"),
        on_or_above=("Overall tier", lambda x: (
            x.isin(["On grade", "Above grade"]).sum()
        ))
    ).reset_index()
    resumen["pct_on_above"] = (
        resumen["on_or_above"] / resumen["total"] * 100
    ).round(1)
    resumen["percentil_prom"] = resumen["percentil_prom"].round(1)
    resumen["Grade"] = resumen["Grade"].apply(lambda g: f"Grado {g}")
    return resumen

def calcular_areas(df: pd.DataFrame) -> pd.DataFrame:
    """Percentil promedio por área de Math."""
    filas = []
    for area in AREAS_MATH:
        col_pct = f"{area} percentile"
        if col_pct in df.columns:
            filas.append({
                "Área"     : area.replace(" and ", " & ").title(),
                "Percentil": round(df[col_pct].mean(), 1),
                "Color"    : "#3b82f6"
            })
    return pd.DataFrame(filas).sort_values("Percentil", ascending=False)

def acumular_ixl(sede: str, resultado: dict):
    """Guarda el resultado en session_state para el campus."""
    clave = f"ixl_{sede}"
    st.session_state[clave] = resultado

def cruzar_con_academico(resultado_ixl: dict, resultado_academico: dict) -> dict | None:
    """
    Cruza datos de IXL con calificaciones reales, agregados por grado/nivel.
    No depende de nombres de alumnos — usa promedios por grado.
    """
    if resultado_ixl is None or resultado_academico is None:
        return None

    df_ixl = resultado_ixl["df_raw"]
    df_aca = resultado_academico["df_raw"]

    # Adopción: % de alumnos con registro en IXL vs matrícula total
    total_matricula = resultado_academico["total_alumnos"]
    total_ixl        = resultado_ixl["total_alumnos"]
    pct_adopcion      = round(min(total_ixl / total_matricula, 1.0) * 100, 1)

    # Promedio académico por Grupo (ej: "1A" → grado 1)
    df_aca = df_aca.copy()
    df_aca["GradoNum"] = df_aca["Grupo"].astype(str).str.extract(r"(\d+)").astype(float)
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

    # Promedio IXL por Grade
    prom_ixl_grado = df_ixl.groupby("Grade").agg(
        percentil_ixl=("Overall percentile", "mean")
    ).reset_index().rename(columns={"Grade": "GradoNum"})

    # Cruce por grado
    df_cruce = pd.merge(prom_ixl_grado, prom_academico_grado, on="GradoNum", how="inner")
    df_cruce["Grado"] = df_cruce["GradoNum"].apply(lambda g: f"Grado {g}")
    df_cruce["promedio_calificacion_pct"] = df_cruce["promedio_calificacion"] / 10 * 100

    return {
        "pct_adopcion"  : pct_adopcion,
        "total_ixl"     : total_ixl,
        "total_matricula": total_matricula,
        "df_cruce"      : df_cruce,
    }