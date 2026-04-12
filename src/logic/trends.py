# src/logic/trends.py

import pandas as pd

def proyectar_tendencia(df_tendencia):
    """
    Calcula la tendencia lineal entre B1 y B2 y proyecta un tercer punto (Futuro).
    """
    # Cálculo de deltas (B2 - B1)
    lenguaje_delta = (
        df_tendencia["lenguaje"].iloc[1] - 
        df_tendencia["lenguaje"].iloc[0]
    )

    mate_delta = (
        df_tendencia["matematicas"].iloc[1] - 
        df_tendencia["matematicas"].iloc[0]
    )

    # Creación del DataFrame de proyección
    df_futuro = pd.concat([
        df_tendencia,
        pd.DataFrame([{
            "bloque": "Futuro",
            "lenguaje": df_tendencia["lenguaje"].iloc[1] + lenguaje_delta,
            "matematicas": df_tendencia["matematicas"].iloc[1] + mate_delta,
            "orden": 3
        }])
    ], ignore_index=True)

    return df_futuro