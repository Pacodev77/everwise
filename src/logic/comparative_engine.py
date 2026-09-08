# src/logic/comparative_engine.py

import pandas as pd

def generar_recomendaciones_ciclo(df_actual: pd.DataFrame, df_previo: pd.DataFrame, sede_actual: str = None) -> dict:
    """
    Genera un plan de acción retrospectivo inteligente basado en los datos reales cargados.
    Analiza desempeño académico por materias, niveles educativos, bimestres históricos
    y asistencia.
    """
    import os
    import json
    import streamlit as st
    import pandas as pd

    recomendaciones = {
        "mantener": [],
        "mejorar": [],
        "modificar": []
    }

    # 1. Intentar obtener datos académicos detallados de la sede o global
    res_acad = None
    if sede_actual and f"academico_propio_{sede_actual}" in st.session_state:
        res_acad = st.session_state[f"academico_propio_{sede_actual}"]
    elif not sede_actual or sede_actual == "Global":
        for c in ["San Agustín", "Misiones", "Nuevo Sur"]:
            if f"academico_propio_{c}" in st.session_state:
                res_acad = st.session_state[f"academico_propio_{c}"]
                break

    # Si no hay res_acad en session_state, intentar desde el catálogo de SQLite
    if not res_acad and sede_actual and sede_actual != "Global":
        from src.logic.data_loader import get_academic_history_catalog
        catalog = get_academic_history_catalog()
        if sede_actual in catalog and catalog[sede_actual]:
            def _sort_b(b):
                s = str(b).upper().strip()
                return int(s[1:]) if s.startswith('B') and s[1:].isdigit() else 99
            latest_b = sorted(catalog[sede_actual].keys(), key=_sort_b)[-1]
            res_acad = catalog[sede_actual][latest_b]

    contexto_str = f"campus {sede_actual}" if (sede_actual and sede_actual != "Global") else "red global"

    # Extraer métricas de asistencia si están disponibles
    prom_ast = None
    if not df_actual.empty and 'asistencia' in df_actual.columns and df_actual['asistencia'].notna().any():
        prom_ast = df_actual['asistencia'].dropna().mean()
    elif sede_actual and f"asistencia_data_{sede_actual}" in st.session_state:
        ast_data = st.session_state[f"asistencia_data_{sede_actual}"]
        if isinstance(ast_data, dict) and "niveles" in ast_data and not ast_data["niveles"].empty:
            prom_ast = ast_data["niveles"]["Asistencia"].mean()

    # Intentar generar con Gemini AI si la API Key está configurada
    api_key = os.environ.get("GEMINI_API_KEY") or st.session_state.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
    if api_key and res_acad and "df_raw" in res_acad and res_acad["df_raw"] is not None and not res_acad["df_raw"].empty:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            df_raw = res_acad["df_raw"]
            prom_m = df_raw["Matemáticas"].mean()
            prom_e = df_raw["Español"].mean()
            prom_la = df_raw["Language Arts"].mean()

            prompt = f"""
            Eres un consultor ejecutivo escolar de Everwise. Analiza los siguientes datos reales del {contexto_str} (Bimestre {res_acad.get('bimestre', 'B1')}, {res_acad.get('total_alumnos', 0)} alumnos):
            - Promedio Matemáticas: {prom_m:.1f}/10
            - Promedio Español: {prom_e:.1f}/10
            - Promedio Language Arts: {prom_la:.1f}/10
            - Asistencia Alumnos: {f'{prom_ast*100:.1f}%' if prom_ast else 'Sin datos de asistencia'}

            Genera un plan de acción retrospectivo con recomendaciones ejecutivas concretas basándote en estos números exactos.
            Responde exclusivamente en formato JSON con la siguiente estructura de listas de strings, sin código markdown:
            {{
                "mantener": ["Logro o fortaleza principal con números exactos"],
                "mejorar": ["Área de oportunidad con materias o promedios"],
                "modificar": ["Acción correctiva para la materia o nivel de menor rendimiento"]
            }}
            """
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:]
            if text.endswith("```"): text = text[:-3]
            data = json.loads(text.strip())
            return {
                "mantener": data.get("mantener", []),
                "mejorar": data.get("mejorar", []),
                "modificar": data.get("modificar", [])
            }
        except Exception:
            pass

    # ── MOTOR LOCAL DINÁMICO (Basado en los datos reales del archivo subido) ──
    if res_acad and "df_raw" in res_acad and res_acad["df_raw"] is not None and not res_acad["df_raw"].empty:
        df_raw = res_acad["df_raw"]
        bimestre = res_acad.get("bimestre", "actual")
        total_alumnos = res_acad.get("total_alumnos", len(df_raw))

        # Promedios por materia
        prom_m = float(df_raw["Matemáticas"].mean()) if "Matemáticas" in df_raw.columns else 0.0
        prom_e = float(df_raw["Español"].mean()) if "Español" in df_raw.columns else 0.0
        prom_la = float(df_raw["Language Arts"].mean()) if "Language Arts" in df_raw.columns else 0.0

        materias = [
            ("Matemáticas", prom_m),
            ("Español", prom_e),
            ("Language Arts", prom_la)
        ]
        materias_ordenadas = sorted(materias, key=lambda x: x[1], reverse=True)
        mejor_materia, mejor_prom = materias_ordenadas[0]
        peor_materia, peor_prom = materias_ordenadas[-1]

        # % Alumnos en desempeño
        df_eval = df_raw.copy()
        df_eval["en_desempeno"] = (
            (df_eval["Language Arts"] >= 8) &
            (df_eval["Matemáticas"] >= 8) &
            (df_eval["Español"] >= 8)
        )
        pct_desempeno = float(df_eval["en_desempeno"].mean()) * 100.0

        # Análisis por nivel educativo
        if "desempeno" in res_acad and isinstance(res_acad["desempeno"], pd.DataFrame) and not res_acad["desempeno"].empty:
            df_des_niv = res_acad["desempeno"]
            mejor_niv_row = df_des_niv.loc[df_des_niv["pct_desempeno"].idxmax()]
            peor_niv_row = df_des_niv.loc[df_des_niv["pct_desempeno"].idxmin()]
            mejor_nivel_nombre = str(mejor_niv_row["Nivel"])
            mejor_nivel_pct = float(mejor_niv_row["pct_desempeno"])
            peor_nivel_nombre = str(peor_niv_row["Nivel"])
            peor_nivel_pct = float(peor_niv_row["pct_desempeno"])
        else:
            mejor_nivel_nombre, mejor_nivel_pct = "Primaria", pct_desempeno
            peor_nivel_nombre, peor_nivel_pct = "Secundaria", pct_desempeno

        # 1. QUÉ MANTENER
        if pct_desempeno >= 65.0:
            recomendaciones["mantener"].append(
                f"Sostener la sólida tasa de desempeño global ({pct_desempeno:.1f}% en Bimestre {bimestre} sobre {total_alumnos} alumnos) en {contexto_str}."
            )
        recomendaciones["mantener"].append(
            f"Mantener la estrategia pedagógica de {mejor_materia}, la cual registra el mayor promedio académico del campus con {mejor_prom:.1f}/10."
        )

        # 2. QUÉ MEJORAR
        if peor_materia != mejor_materia:
            recomendaciones["mejorar"].append(
                f"Reforzar la asignatura de {peor_materia} (promedio actual de {peor_prom:.1f}/10) mediante talleres prácticos y ejercicios de nivelación."
            )
        else:
            recomendaciones["mejorar"].append(
                "Incrementar las sesiones de acompañamiento grupal para elevar los promedios generales por encima de 8.5/10."
            )

        if prom_ast is not None:
            if prom_ast >= 0.90:
                recomendaciones["mantener"].append(
                    f"Consolidar la alta asistencia escolar ({prom_ast*100:.1f}%), reforzando la comunicación periódica con padres de familia."
                )
            else:
                recomendaciones["mejorar"].append(
                    f"Optimizar el seguimiento a inasistencias (asistencia actual: {prom_ast*100:.1f}%) con avisos automáticos al detectar ausencias."
                )
        else:
            recomendaciones["mejorar"].append(
                "Cargar el reporte de asistencia escolar para integrar indicadores de puntualidad y ausentismo en este plan ejecutivo."
            )

        # 3. QUÉ MODIFICAR
        if peor_nivel_nombre != mejor_nivel_nombre and peor_nivel_pct < mejor_nivel_pct:
            recomendaciones["modificar"].append(
                f"Revisar y modificar el plan de intervención en {peor_nivel_nombre}, al registrar solo un {peor_nivel_pct:.1f}% de alumnos en desempeño (vs {mejor_nivel_pct:.1f}% en {mejor_nivel_nombre})."
            )
        elif peor_prom < 8.0:
            recomendaciones["modificar"].append(
                f"Modificar el esquema de evaluación y tutorías en {peor_materia} al situarse por debajo del umbral óptimo de 8.0/10."
            )
        else:
            recomendaciones["modificar"].append(
                "Ajustar la frecuencia de repasos antes de las evaluaciones bimestrales para disminuir la variabilidad entre grupos."
            )

    else:
        # Si aún no se ha subido archivo académico ni de asistencia
        recomendaciones["mantener"].append("Cargue archivos de calificaciones por bimestre para generar un análisis comparativo.")
        recomendaciones["mejorar"].append("El motor analizará automáticamente promedios por materia, deltas entre bimestres y tasas por nivel.")
        recomendaciones["modificar"].append("Suba la información de su campus para habilitar las recomendaciones estratégicas personalizadas.")

    return recomendaciones
