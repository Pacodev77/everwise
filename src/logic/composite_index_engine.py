# src/logic/composite_index_engine.py

# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

MATRICULA_CAMPUS = {
    "Misiones": 180,
    "Nuevo Sur": 150,
    "San Agustín": 170
}

BIMESTRES = ["B1", "B2", "B3", "B4", "B5"]
BIMESTRE_LABELS = {
    "B1": "B1 (Sep-Oct)",
    "B2": "B2 (Nov-Dic)",
    "B3": "B3 (Ene-Feb)",
    "B4": "B4 (Mar-Abr)",
    "B5": "B5 (May-Jun)"
}

def generar_datos_indice_compuesto(df_master: pd.DataFrame = None) -> tuple[pd.DataFrame, dict]:
    """
    Genera y calcula el Índice Compuesto Institucional para Misiones, Nuevo Sur, San Agustín y Global.
    Fórmula: (Calificaciones % * 0.50) + (IXL % * 0.30) + (Progrentis % * 0.20)
    Soporta bimestres reales (B1-B3) y proyecciones punteadas (B4-B5).
    """
    # Datos canónicos históricos por campus (B1, B2, B3)
    raw_data = {
        "Misiones": [
            {"bimestre": "B1", "acad": 85.0, "ixl": 72.0, "prog": 78.0},
            {"bimestre": "B2", "acad": 86.5, "ixl": 76.0, "prog": 81.0},
            {"bimestre": "B3", "acad": 87.8, "ixl": 79.0, "prog": 84.0},
        ],
        "Nuevo Sur": [
            {"bimestre": "B1", "acad": 88.0, "ixl": 80.0, "prog": 82.0},
            {"bimestre": "B2", "acad": 89.2, "ixl": 83.0, "prog": 85.0},
            {"bimestre": "B3", "acad": 90.5, "ixl": 86.0, "prog": 88.0},
        ],
        "San Agustín": [
            {"bimestre": "B1", "acad": 78.0, "ixl": 65.0, "prog": 70.0},
            {"bimestre": "B2", "acad": 79.5, "ixl": 68.0, "prog": 73.0},
            {"bimestre": "B3", "acad": 80.8, "ixl": 71.0, "prog": 75.0},
        ]
    }

    records = []

    # 1. Calcular historial real para los 3 campus
    campus_indices = {"Misiones": {}, "Nuevo Sur": {}, "San Agustín": {}}
    for campus, b_list in raw_data.items():
        for item in b_list:
            b = item["bimestre"]
            idx_val = (item["acad"] * 0.50) + (item["ixl"] * 0.30) + (item["prog"] * 0.20)
            campus_indices[campus][b] = round(idx_val, 2)
            records.append({
                "campus": campus,
                "bimestre": b,
                "bimestre_label": BIMESTRE_LABELS[b],
                "indice": round(idx_val, 2),
                "tipo": "Real"
            })

    # 2. Calcular Global ponderado por matrícula para B1, B2, B3
    global_indices = {}
    for b in ["B1", "B2", "B3"]:
        num = sum(campus_indices[c][b] * MATRICULA_CAMPUS[c] for c in MATRICULA_CAMPUS)
        den = sum(MATRICULA_CAMPUS.values())
        g_val = round(num / den, 2)
        global_indices[b] = g_val
        records.append({
            "campus": "Global",
            "bimestre": b,
            "bimestre_label": BIMESTRE_LABELS[b],
            "indice": g_val,
            "tipo": "Real"
        })

    # 3. Proyección para B4 y B5 usando tendencia / media móvil de B2->B3
    for campus in MATRICULA_CAMPUS:
        val_b2 = campus_indices[campus]["B2"]
        val_b3 = campus_indices[campus]["B3"]
        delta = val_b3 - val_b2

        val_b4 = round(val_b3 + delta, 2)
        val_b5 = round(val_b4 + delta, 2)

        campus_indices[campus]["B4"] = val_b4
        campus_indices[campus]["B5"] = val_b5

        # Para continuidad visual en el gráfico, B3 también forma el puente a la línea punteada
        for b, v in [("B4", val_b4), ("B5", val_b5)]:
            records.append({
                "campus": campus,
                "bimestre": b,
                "bimestre_label": BIMESTRE_LABELS[b],
                "indice": v,
                "tipo": "Proyección"
            })

    # Proyección Global para B4 y B5
    for b in ["B4", "B5"]:
        num = sum(campus_indices[c][b] * MATRICULA_CAMPUS[c] for c in MATRICULA_CAMPUS)
        den = sum(MATRICULA_CAMPUS.values())
        g_val = round(num / den, 2)
        global_indices[b] = g_val
        records.append({
            "campus": "Global",
            "bimestre": b,
            "bimestre_label": BIMESTRE_LABELS[b],
            "indice": g_val,
            "tipo": "Proyección"
        })

    df_res = pd.DataFrame(records)

    # 4. Evaluación de semáforo ejecutivo por campus
    # Criterio:
    # Verde: Índice B3 >= Global B3
    # Amarillo: Índice B3 entre 1 y 10 pts por debajo de Global B3
    # Rojo: Índice B3 > 10 pts por debajo de Global B3 O Proyección B5 < 85.0%
    global_b3 = global_indices["B3"]
    campus_status = {}

    for c in MATRICULA_CAMPUS:
        idx_actual = campus_indices[c]["B3"]
        idx_b5 = campus_indices[c]["B5"]
        diff = idx_actual - global_b3

        if idx_b5 < 85.0 or diff < -10.0:
            estado = "risk" # Rojo
            color_hex = "#ef4444"
            motivo = "Proyección B5 < 85%" if idx_b5 < 85.0 else "Más de 10 pts por debajo de Global"
        elif diff < -1.0:
            estado = "warning" # Amarillo
            color_hex = "#f59e0b"
            motivo = f"{abs(diff):.1f}% por debajo de Global"
        else:
            estado = "ok" # Verde
            color_hex = "#10b981"
            motivo = "Supera el promedio Global"

        campus_status[c] = {
            "indice_actual": idx_actual,
            "indice_b5": idx_b5,
            "global_b3": global_b3,
            "diff": diff,
            "estado": estado,
            "color_hex": color_hex,
            "motivo": motivo
        }

    campus_status["Global"] = {
        "indice_actual": global_indices["B3"],
        "indice_b5": global_indices["B5"],
        "global_b3": global_b3,
        "diff": 0.0,
        "estado": "info",
        "color_hex": "#0f172a",
        "motivo": "Promedio Global"
    }

    return df_res, campus_status
