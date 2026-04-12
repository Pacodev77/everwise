# pipelines/build_mart_global.py

import pandas as pd

def build_everwise_core(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    df["asistencia"] = df["asistencia"].clip(0, 1)
    df["dominio_academico"] = df["dominio_academico"].clip(0, 1)

    df["riesgo_academico"] = 1 - df["dominio_academico"]

    return df
