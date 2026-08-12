# src/logic/narrative.py

def narrativa_asistencia(valor_asistencia: float) -> str:
    if valor_asistencia >= 0.95:
        return "Asistencia sólida y estable. El campus opera dentro de estándares óptimos."
    elif valor_asistencia >= 0.85:
        return "Asistencia aceptable, pero con margen de mejora operativa."
    else:
        return "Asistencia crítica. Requiere intervención inmediata."

def narrativa_bloques(b1: float, b2: float, materia: str) -> str:
    delta = b2 - b1

    if delta > 0.03:
        return f"Mejora clara en {materia}. Las estrategias del Bloque 2 están dando resultado."
    elif delta > 0:
        return f"Ligera mejora en {materia}, aún sin impacto significativo."
    elif delta == 0:
        return f"Sin cambios relevantes en {materia}."
    else:
        return f"Retroceso en {materia}. Es necesario revisar la intervención pedagógica."


def narrativa_nivel(nivel: str, delta: float) -> str:
    if delta > 0.03:
        return f"{nivel} muestra una mejora significativa entre bloques."
    elif delta > 0:
        return f"{nivel} presenta avance leve."
    else:
        return f"{nivel} no muestra progreso; requiere atención específica."


def narrativa_tendencia(delta: float, materia: str) -> str:
    if delta > 0:
        return f"La tendencia proyecta crecimiento continuo en {materia} si se mantiene la estrategia actual."
    else:
        return f"La proyección en {materia} indica estancamiento o retroceso."
    