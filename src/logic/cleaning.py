# src/logic/cleaning.py

import pandas as pd

def limpiar_desempeno_b1(df_raw):
    registros = []
    nivel_actual = None

    for _, row in df_raw.iterrows():
        nivel_raw = str(row[1]).strip().upper()
        if nivel_raw in ["PREESCOLAR", "PRIMARIA", "SECUNDARIA", "PRESCHOOL", "ELEMENTARY", "MIDDLE SCHOOL"]:
            if nivel_raw in ["PRESCHOOL", "PREESCOLAR"]: nivel_actual = "Preescolar"
            elif nivel_raw in ["ELEMENTARY", "PRIMARIA"]: nivel_actual = "Primaria"
            elif nivel_raw in ["MIDDLE SCHOOL", "SECUNDARIA"]: nivel_actual = "Secundaria"
            continue

        campus_raw = str(row[0]).strip()

        if campus_raw in ["Misiones", "Nuevo Sur", "San Agustin"] and nivel_actual:
            try:
                lenguaje = float(row[2].replace("%", "")) / 100
                matematicas = float(row[3].replace("%", "")) / 100
            except:
                continue

            registros.append({
                "campus": campus_raw,
                "nivel": nivel_actual,
                "lenguaje": lenguaje,
                "matematicas": matematicas,
                "bloque": "B1"
            })

    df = pd.DataFrame(registros)
    df = df.drop_duplicates(subset=["campus", "nivel"])

    return df


def limpiar_desempeno_b2(df_raw):
    registros = []
    nivel_actual = None

    for _, row in df_raw.iterrows():
        nivel_raw = str(row[1]).strip().upper()
        if nivel_raw in ["PREESCOLAR", "PRIMARIA", "SECUNDARIA", "PRESCHOOL", "ELEMENTARY", "MIDDLE SCHOOL"]:
            if nivel_raw in ["PRESCHOOL", "PREESCOLAR"]: nivel_actual = "Preescolar"
            elif nivel_raw in ["ELEMENTARY", "PRIMARIA"]: nivel_actual = "Primaria"
            elif nivel_raw in ["MIDDLE SCHOOL", "SECUNDARIA"]: nivel_actual = "Secundaria"
            continue

        campus_raw = str(row[0]).strip()

        if campus_raw in ["Misiones", "Nuevo Sur", "San Agustin"] and nivel_actual:
            try:
                lenguaje = float(row[2].replace("%", "")) / 100
                matematicas = float(row[3].replace("%", "")) / 100
            except:
                continue

            registros.append({
                "campus": campus_raw,
                "nivel": nivel_actual,
                "lenguaje": lenguaje,
                "matematicas": matematicas,
                "bloque": "B2"
            })

    df = pd.DataFrame(registros)
    df = df.drop_duplicates(subset=["campus", "nivel"])

    return df


def unir_bloques(df_b1, df_b2):
    return pd.concat([df_b1, df_b2], ignore_index=True)
