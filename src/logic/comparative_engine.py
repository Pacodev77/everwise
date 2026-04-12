import pandas as pd

def generar_recomendaciones_ciclo(df_actual: pd.DataFrame, df_previo: pd.DataFrame) -> dict:
    """
    Analiza la brecha entre el ciclo actual y el anterior (ej. 2025 vs 2024),
    devolviendo un diccionario con listas de qué mantener, mejorar y modificar.
    Para este análisis tomamos las métricas de asistencia y dominio.
    """
    promedio_ast_actual = df_actual['asistencia'].mean()
    promedio_dom_actual = df_actual['dominio'].mean()
    
    promedio_ast_previo = df_previo['asistencia'].mean()
    promedio_dom_previo = df_previo['dominio'].mean()

    delta_ast = promedio_ast_actual - promedio_ast_previo
    delta_dom = promedio_dom_actual - promedio_dom_previo

    recomendaciones = {
        "mantener": [],
        "mejorar": [],
        "modificar": []
    }

    # Identificar si estamos en un campus específico o en la red global
    if 'campus' in df_actual.columns and len(df_actual['campus'].unique()) == 1:
        sede = df_actual['campus'].iloc[0]
        contexto_nombre = f"en el campus {sede}"
    else:
        contexto_nombre = "a nivel red global"

    # Extraer evaluación de Staff si fue inyectada
    staff_ast = df_actual['staff_asistencia'].mean() if 'staff_asistencia' in df_actual.columns else None

    # Transformadores semánticos para el usuario
    ast_status = "está aumentando" if delta_ast > 0 else "está disminuyendo" if delta_ast < 0 else "se mantiene estable"
    ast_calidad = "buena" if promedio_ast_actual >= 0.90 else "deficiente (requiere atención urgente)"

    # Evaluar Asistencia Operativa (Alumnos)
    if delta_ast >= 0 and promedio_ast_actual >= 0.90:
        recomendaciones["mantener"].append(
            f"La asistencia de alumnos es {ast_calidad} ({promedio_ast_actual*100:.1f}%) y {ast_status} {contexto_nombre}. Mantener estrategias de seguimiento."
        )
    elif delta_ast > 0 and promedio_ast_actual < 0.90:
        recomendaciones["mejorar"].append(
            f"La asistencia de alumnos {ast_status} (+{delta_ast*100:.1f}%) {contexto_nombre}. Sin embargo, sigue siendo deficiente. Debes mejorar campañas."
        )
    else:
        recomendaciones["modificar"].append(
            f"La asistencia de alumnos es {ast_calidad} y {ast_status} ({delta_ast*100:.1f}%) {contexto_nombre}. Hay que mejorar urgentemente el clima con los alumnos."
        )

    # Evaluar Asistencia Operativa (Staff) 
    if staff_ast is not None:
        if staff_ast < 0.90:
             recomendaciones["modificar"].append(f"La asistencia del Staff es baja ({staff_ast*100:.1f}%). Es crítico mejorar y auditar operativamente al equipo de trabajo.")
        else:
             recomendaciones["mantener"].append(f"La asistencia del Staff operativo se encuentra bien balanceada y estable ({staff_ast*100:.1f}%).")

    # Evaluar Nivel Académico
    if delta_dom >= 0.05:
        recomendaciones["mantener"].append(
            f"Ecosistema de aprendizaje en B2 {contexto_nombre}. El crecimiento es notable (+5%). Conservar estrategias y plana titular local."
        )
    elif delta_dom >= 0 and delta_dom < 0.05:
        recomendaciones["mejorar"].append(
            f"Crecimiento académico estancado (+{delta_dom*100:.1f}%) {contexto_nombre}. Focalizar en observación docente y acompañamiento específico a este grupo."
        )
    else:
        recomendaciones["modificar"].append(
            f"Pérdida de rendimiento académico ({delta_dom*100:.1f}%) {contexto_nombre}. Se recomienda auditoría interna a las metodologías del campus."
        )

    return recomendaciones
