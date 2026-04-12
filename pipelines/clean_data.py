# pipelines/clean_data.py

import pandas as pd

def normalizar_porcentajes(df, columnas):
    df = df.copy()
    for col in columnas:
        df[col] = df[col].clip(0, 1)
    return df
