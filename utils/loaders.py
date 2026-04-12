# utils/loaders.py
import pandas as pd

# ------------------------------------------------------
# Cargar asistencia estudiantes
# ------------------------------------------------------

def load_asistencia_estudiantes():
    """
    Devuelve la asistencia por campus, calculando la media de Preescolar, Primaria y Secundaria.
    """
    df_raw = pd.read_csv("data/Numeros_Everwise.csv", header=None)

    # Buscar fila que contiene "Preescolar" en la columna 0
    idx_inicio = df_raw[df_raw.iloc[:, 0] == "Preescolar"].index[0]

    # Tomar solo Preescolar, Primaria y Secundaria
    df_bloque = df_raw.iloc[idx_inicio : idx_inicio + 3, 0:4]

    # Renombrar columnas correctamente
    df_bloque.columns = ["nivel", "San Agustin", "Misiones", "Nuevo Sur"]

    # Limpiar % y pasar a float
    for campus in ["San Agustin", "Misiones", "Nuevo Sur"]:
        df_bloque[campus] = (
            df_bloque[campus]
            .astype(str)
            .str.replace("%", "", regex=False)
            .astype(float) / 100
        )

    # Calcular promedio por campus
    df_asistencia = pd.DataFrame({
        "campus": ["San Agustin", "Misiones", "Nuevo Sur"],
        "asistencia": [
            df_bloque["San Agustin"].mean(),
            df_bloque["Misiones"].mean(),
            df_bloque["Nuevo Sur"].mean()
        ]
    })

    return df_asistencia

# ------------------------------------------------------
# Cargar desempeño académico
# ------------------------------------------------------

def load_desempeno_b1():
    return pd.read_csv("data/B1_desempeño_everwise.csv", header=None)

def load_desempeno_b2():
    return pd.read_csv("data/B2_desempeño_everwise.csv", header=None)