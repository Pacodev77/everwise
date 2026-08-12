# src/logic/comparative_engine.py

import pandas as pd

def generar_recomendaciones_ciclo(df_actual: pd.DataFrame, df_previo: pd.DataFrame) -> dict:
    """
    Analiza la brecha entre el ciclo actual y el anterior (ej. 2025 vs 2024),
    devolviendo un diccionario con listas de qué mantener, mejorar y modificar.
    Si se detecta una API key de Gemini, intenta generar las recomendaciones con IA.
    De lo contrario, utiliza un motor dinámico local detallado basado en datos reales.
    """
    promedio_ast_actual = df_actual['asistencia'].mean() if not df_actual.empty and 'asistencia' in df_actual.columns else 0.0
    promedio_dom_actual = df_actual['dominio'].mean() if not df_actual.empty and 'dominio' in df_actual.columns else 0.0
    
    promedio_ast_previo = df_previo['asistencia'].mean() if not df_previo.empty and 'asistencia' in df_previo.columns else 0.0
    promedio_dom_previo = df_previo['dominio'].mean() if not df_previo.empty and 'dominio' in df_previo.columns else 0.0

    delta_ast = promedio_ast_actual - promedio_ast_previo
    delta_dom = promedio_dom_actual - promedio_dom_previo

    # Identificar si estamos en un campus específico o en la red global
    if not df_actual.empty and 'campus' in df_actual.columns and len(df_actual['campus'].unique()) == 1:
        sede = df_actual['campus'].iloc[0]
        contexto_nombre = f"campus {sede}"
    else:
        contexto_nombre = "red global"

    # Extraer evaluación de Staff si fue inyectada
    staff_ast = df_actual['staff_asistencia'].mean() if not df_actual.empty and 'staff_asistencia' in df_actual.columns else None

    # Intentar generar con Gemini si hay API Key disponible
    import os
    import streamlit as st
    api_key = os.environ.get("GEMINI_API_KEY") or st.session_state.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")

    if api_key:
        try:
            # pyrefly: ignore [missing-import]
            import google.generativeai as genai
            import json
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Eres un experto coordinador escolar y analista de datos educativos.
            Analiza los siguientes datos del dashboard escolar para {contexto_nombre}:
            
            Métricas del Ciclo Seleccionado:
            - Asistencia de Alumnos: {promedio_ast_actual*100:.1f}% (Ciclo Anterior: {promedio_ast_previo*100:.1f}%) -> Delta: {delta_ast*100:+.1f}%
            - Dominio Académico: {promedio_dom_actual*100:.1f}% (Ciclo Anterior: {promedio_dom_previo*100:.1f}%) -> Delta: {delta_dom*100:+.1f}%
            - Asistencia del Staff Operativo: {f'{staff_ast*100:.1f}%' if staff_ast is not None else 'No disponible'}
            
            Genera un plan de acción retrospectivo con recomendaciones específicas basadas en estos números.
            Divide tu análisis en 3 categorías:
            1. "mantener": Puntos fuertes, logros y estrategias estables que se deben continuar.
            2. "mejorar": Áreas de oportunidad donde se observa crecimiento lento o necesidad de optimización.
            3. "modificar": Acciones correctivas urgentes ante retrocesos, caídas de rendimiento o problemas operativos críticos.
            
            Reglas críticas:
            - Menciona explícitamente los porcentajes y deltas en el texto de las recomendaciones.
            - Sé muy profesional, ejecutivo y conciso (máximo 2 a 3 puntos cortos por categoría).
            - Responde únicamente en formato JSON con la siguiente estructura de listas de strings, sin bloques de código markdown:
            {{
                "mantener": ["recomendación 1 con números", "recomendación 2"],
                "mejorar": ["recomendación 1 con deltas"],
                "modificar": ["recomendación 1 con porcentajes"]
            }}
            """
            
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Limpiar posibles bloques de markdown
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            return {
                "mantener": data.get("mantener", []),
                "mejorar": data.get("mejorar", []),
                "modificar": data.get("modificar", [])
            }
        except Exception as e:
            # Si falla, continúa con el motor local
            pass

    # MOTOR LOCAL DINÁMICO (Fallback de alta calidad basado en datos reales)
    recomendaciones = {
        "mantener": [],
        "mejorar": [],
        "modificar": []
    }

    # 1. Asistencia de alumnos
    if delta_ast >= 0.02:
        recomendaciones["mantener"].append(
            f"El aumento en la asistencia de alumnos (+{delta_ast*100:.1f}%) en {contexto_nombre} (llegando a {promedio_ast_actual*100:.1f}%) es excelente. Mantener los incentivos y el monitoreo diario."
        )
    elif delta_ast >= 0:
        recomendaciones["mantener"].append(
            f"La asistencia de alumnos en {contexto_nombre} se mantiene estable en {promedio_ast_actual*100:.1f}% (+{delta_ast*100:.1f}% vs ciclo anterior). Conservar los canales actuales."
        )
    elif delta_ast > -0.03:
        recomendaciones["mejorar"].append(
            f"La asistencia de alumnos bajó un {abs(delta_ast)*100:.1f}% en {contexto_nombre} (registrando {promedio_ast_actual*100:.1f}%). Es necesario mejorar el contacto preventivo con familias."
        )
    else:
        recomendaciones["modificar"].append(
            f"Se detecta una caída severa de {delta_ast*100:.1f}% en la asistencia estudiantil en {contexto_nombre} ({promedio_ast_actual*100:.1f}%). Modificar el plan de retención y revisar casos especiales de deserción."
        )

    # 2. Asistencia de Staff
    if staff_ast is not None:
        if staff_ast >= 0.95:
            recomendaciones["mantener"].append(
                f"La asistencia del Staff operativo se encuentra en niveles óptimos ({staff_ast*100:.1f}%), asegurando la continuidad del servicio educativo."
            )
        elif staff_ast >= 0.90:
            recomendaciones["mejorar"].append(
                f"La asistencia del Staff registra {staff_ast*100:.1f}%. Se sugiere mejorar el clima laboral y optimizar la planeación de guardias pedagógicas."
            )
        else:
            recomendaciones["modificar"].append(
                f"Bajo nivel de asistencia de Staff ({staff_ast*100:.1f}%). Modificar y auditar de inmediato los registros de incidencias para evitar ausentismo recurrente."
            )

    # 3. Dominio Académico
    if delta_dom >= 0.04:
        recomendaciones["mantener"].append(
            f"El dominio académico promedio en {contexto_nombre} creció un notable +{delta_dom*100:.1f}%, situándose en {promedio_dom_actual*100:.1f}%. Replicar las mejores prácticas docentes."
        )
    elif delta_dom >= 0:
        recomendaciones["mejorar"].append(
            f"El dominio académico muestra un avance moderado de +{delta_dom*100:.1f}% en {contexto_nombre} ({promedio_dom_actual*100:.1f}%). Reforzar las tutorías personalizadas."
        )
    elif delta_dom > -0.03:
        recomendaciones["mejorar"].append(
            f"Se observa un leve retroceso académico de {delta_dom*100:.1f}% en {contexto_nombre} ({promedio_dom_actual*100:.1f}%). Incrementar las sesiones de nivelación."
        )
    else:
        recomendaciones["modificar"].append(
            f"Caída crítica de {delta_dom*100:.1f}% en el dominio académico general en {contexto_nombre} (registrando {promedio_dom_actual*100:.1f}%). Modificar urgentemente los esquemas de acompañamiento docente."
        )

    return recomendaciones
