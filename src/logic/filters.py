# src/logic/filters.py

def filtrar_por_campus(df, campus):
    return df[df["campus"] == campus]

# src/logic/kpis.py

# Kpis asistencia (Estudiantes)
def asistencia_promedio_por_campus(df):
    return (
        df
        .groupby("campus")["asistencia"]
        .mean()
        .reset_index()
    )

# Kpis por Campus
def kpi_promedio_academico(df):
    return (
        df
        .groupby(["campus", "bloque"])
        .agg({
            "lenguaje": "mean",
            "matematicas": "mean"
        })
        .reset_index()
    )

# Indicadores de mejora
def kpi_mejora_b1_b2(df):
    """
    Calcula la mejora (delta) entre B1 y B2
    por campus y nivel.
    """
    pivot = (
        df
        .groupby(["campus", "nivel", "bloque"])
        .agg({
            "lenguaje": "mean",
            "matematicas": "mean"
        })
        .reset_index()
        .pivot(
            index=["campus", "nivel"],
            columns="bloque",
            values=["lenguaje", "matematicas"]
        )
    )

    # Aplanar columnas
    pivot.columns = [
        f"{col[0]}_{col[1]}" for col in pivot.columns
    ]
    pivot = pivot.reset_index()

    # Calcular mejoras
    pivot["mejora_lenguaje"] = pivot["lenguaje_B2"] - pivot["lenguaje_B1"]
    pivot["mejora_matematicas"] = pivot["matematicas_B2"] - pivot["matematicas_B1"]

    return pivot
