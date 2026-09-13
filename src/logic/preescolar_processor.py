# src/logic/preescolar_processor.py

# pyrefly: ignore [missing-import]
import pandas as pd
import numpy as np

STATUS_MAP = {
    "L": "Logrado",
    "LOGRADO": "Logrado",
    "CONSOLIDADO": "Logrado",
    "SATISFACTORIO": "Logrado",
    "EP": "En Proceso",
    "EN PROCESO": "En Proceso",
    "PROCESO": "En Proceso",
    "ED": "En Desarrollo",
    "EN DESARROLLO": "En Desarrollo",
    "DESARROLLO": "En Desarrollo",
    "INICIO": "En Desarrollo",
    "REQUIERE APOYO": "En Desarrollo"
}

def generar_datos_semilla_preescolar() -> pd.DataFrame:
    """Genera datos cualitativos canónicos ejecutivos para Preescolar en los 3 campus."""
    records = []
    campuses = ["Misiones", "Nuevo Sur", "San Agustín"]
    grados = ["K1", "K2", "K3"]
    areas = ["Lenguaje y Comunicación", "Pensamiento Matemático", "Desarrollo Socioemocional"]

    alumnos_nom = [
        ("PRE-101", "Lucía González Alanís", "K1"),
        ("PRE-102", "Diego Alejandro Treviño Garza", "K1"),
        ("PRE-103", "Frida Salinas Chapa", "K2"),
        ("PRE-104", "Rodrigo Rivas Brown", "K2"),
        ("PRE-105", "Elena Sofía de Ávila Álvarez", "K2"),
        ("PRE-106", "Santiago Pérez Gámez", "K3"),
        ("PRE-107", "Nuria Allande de la Llave", "K3"),
        ("PRE-108", "Heidy Aileen Argüello Hernández", "K3")
    ]

    obs_logrado = [
        "Demuestra excelente autonomía e intencionalidad en las actividades.",
        "Comunica ideas con claridad y sigue instrucciones complejas.",
        "Resuelve retos lógicos y patrones con alto entusiasmo.",
        "Muestra gran integración grupal y autorregulación en el aula."
    ]
    obs_proceso = [
        "Avanza favorablemente con guía y andamiaje docente.",
        "Participa activamente; requiere refuerzo al estructurar respuestas.",
        "Muestra interés y requiere apoyo en secuenciación lógica."
    ]
    obs_desarrollo = [
        "Iniciando exploración; se sugiere acompañamiento continuo.",
        "Desarrollando hábitos de interacción y enfoque en aula."
    ]

    for campus in campuses:
        for mat, nombre, grado in alumnos_nom:
            for area in areas:
                # Variaciones sutiles por campus y área
                rand_val = np.random.uniform(0, 1)
                if area == "Desarrollo Socioemocional":
                    p_log = 0.75
                    p_pro = 0.20
                else:
                    p_log = 0.65
                    p_pro = 0.25

                if campus == "Nuevo Sur":
                    p_log += 0.05

                if rand_val < p_log:
                    estatus = "Logrado"
                    obs = np.random.choice(obs_logrado)
                elif rand_val < (p_log + p_pro):
                    estatus = "En Proceso"
                    obs = np.random.choice(obs_proceso)
                else:
                    estatus = "En Desarrollo"
                    obs = np.random.choice(obs_desarrollo)

                records.append({
                    "campus": campus,
                    "MATRICULA": mat,
                    "ALUMNO": nombre,
                    "GRADO": grado,
                    "AREA_DESARROLLO": area,
                    "ESTATUS_CUALITATIVO": estatus,
                    "OBSERVACIONES": obs
                })

    return pd.DataFrame(records)

def procesar_log_preescolar(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Estandariza y limpia reportes cualitativos de Preescolar."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    col_map = {}
    for c in df.columns:
        cl = str(c).upper().strip()
        if "MATRICULA" in cl or "ID" in cl: col_map[c] = "MATRICULA"
        elif "ALUMNO" in cl or "NOMBRE" in cl: col_map[c] = "ALUMNO"
        elif "GRADO" in cl or "KINDER" in cl or "NIVEL" in cl: col_map[c] = "GRADO"
        elif "CAMPUS" in cl or "SEDE" in cl: col_map[c] = "campus"
        elif "AREA" in cl or "MATERIA" in cl or "DIMENSION" in cl: col_map[c] = "AREA_DESARROLLO"
        elif "ESTATUS" in cl or "EVALUACION" in cl or "NIVEL_LOGRO" in cl or "RESULTADO" in cl: col_map[c] = "ESTATUS_CUALITATIVO"
        elif "OBSERVACION" in cl or "COMENTARIO" in cl: col_map[c] = "OBSERVACIONES"

    df = df.rename(columns=col_map)
    req = ["ALUMNO", "GRADO", "AREA_DESARROLLO", "ESTATUS_CUALITATIVO"]
    for r in req:
        if r not in df.columns:
            df[r] = "Sin datos"

    if "MATRICULA" not in df.columns:
        df["MATRICULA"] = [f"PRE-{i+100}" for i in range(len(df))]
    if "OBSERVACIONES" not in df.columns:
        df["OBSERVACIONES"] = "Seguimiento en aula"

    # Mapeo estandarizado de estatus cualitativo (Opción A: Logrado, En Proceso, En Desarrollo)
    def _normalizar_estatus(val):
        v = str(val).upper().strip()
        for k, norm in STATUS_MAP.items():
            if k in v:
                return norm
        return "En Proceso"

    df["ESTATUS_CUALITATIVO"] = df["ESTATUS_CUALITATIVO"].apply(_normalizar_estatus)
    return df

def calcular_metricas_preescolar(df: pd.DataFrame) -> dict:
    """Calcula KPIs ejecutivos cualitativos para Preescolar."""
    if df is None or df.empty:
        return {
            "total_alumnos": 0,
            "total_evaluaciones": 0,
            "pct_logrado": 0.0,
            "pct_en_proceso": 0.0,
            "pct_en_desarrollo": 0.0,
            "area_destacada": "N/A",
            "area_oportunidad": "N/A"
        }

    total_alumnos = len(df["ALUMNO"].unique()) if "ALUMNO" in df.columns else len(df)
    total_eval = len(df)

    counts = df["ESTATUS_CUALITATIVO"].value_counts()
    log = counts.get("Logrado", 0)
    pro = counts.get("En Proceso", 0)
    des = counts.get("En Desarrollo", 0)

    pct_log = round((log / total_eval * 100), 1) if total_eval > 0 else 0.0
    pct_pro = round((pro / total_eval * 100), 1) if total_eval > 0 else 0.0
    pct_des = round((des / total_eval * 100), 1) if total_eval > 0 else 0.0

    # Área destacada (mayor % Logrado)
    area_log = df[df["ESTATUS_CUALITATIVO"] == "Logrado"].groupby("AREA_DESARROLLO").size()
    area_destacada = area_log.idxmax() if not area_log.empty else "General"

    # Área oportunidad (mayor % En Desarrollo / En Proceso)
    area_dev = df[df["ESTATUS_CUALITATIVO"] != "Logrado"].groupby("AREA_DESARROLLO").size()
    area_oportunidad = area_dev.idxmax() if not area_dev.empty else "General"

    return {
        "total_alumnos": total_alumnos,
        "total_evaluaciones": total_eval,
        "pct_logrado": pct_log,
        "pct_en_proceso": pct_pro,
        "pct_en_desarrollo": pct_des,
        "area_destacada": area_destacada,
        "area_oportunidad": area_oportunidad
    }
