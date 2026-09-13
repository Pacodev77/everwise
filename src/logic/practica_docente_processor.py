# src/logic/practica_docente_processor.py

import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
import io

RUBRICAS_METADATA = {
    "R1_planificacion": {
        "codigo": "R1",
        "nombre": "Planificación e Intencionalidad Pedagógica",
        "desc": "Alineación curricular, claridad en objetivos de aprendizaje y secuencia didáctica.",
        "meta": 4.5
    },
    "R2_clima": {
        "codigo": "R2",
        "nombre": "Gestión del Aula y Clima de Aprendizaje",
        "desc": "Manejo proactivo de grupo, ambiente de respeto, participación activa y seguridad emocional.",
        "meta": 4.6
    },
    "R3_estrategias": {
        "codigo": "R3",
        "nombre": "Estrategias Didácticas y Metodologías Activas",
        "desc": "Aprendizaje basado en indagación, pensamiento crítico, trabajo colaborativo y resolución de problemas.",
        "meta": 4.4
    },
    "R4_evaluacion": {
        "codigo": "R4",
        "nombre": "Evaluación Formativa y Retroalimentación",
        "desc": "Monitoreo del aprendizaje en tiempo real, instrumentos de evaluación continua y retroalimentación oportuna.",
        "meta": 4.5
    },
    "R5_digital": {
        "codigo": "R5",
        "nombre": "Integración Digital y Tecnológica",
        "desc": "Uso efectivo y pedagógico de plataformas educativas (IXL, Progrentis, LMS) en el aula.",
        "meta": 4.3
    },
    "R6_diferenciacion": {
        "codigo": "R6",
        "nombre": "Inclusión, Atención a la Diversidad y Diferenciación",
        "desc": "Adecuaciones curriculares, atención a ritmos de aprendizaje y estrategias para necesidades especiales.",
        "meta": 4.2
    }
}

NIVELES_DESEMPENO_CONFIG = {
    "Destacado": {"min": 4.6, "max": 5.0, "color": "#10b981", "badge": "success"},
    "Avanzado": {"min": 4.0, "max": 4.59, "color": "#3b82f6", "badge": "primary"},
    "Competente": {"min": 3.4, "max": 3.99, "color": "#f59e0b", "badge": "warning"},
    "En Desarrollo": {"min": 1.0, "max": 3.39, "color": "#ef4444", "badge": "danger"}
}

def determinar_nivel_desempeno(score: float) -> str:
    """Clasifica el puntaje global (1.0 a 5.0) en una categoría ejecutiva de desempeño."""
    if pd.isna(score):
        return "Sin Datos"
    if score >= 4.6:
        return "Destacado"
    elif score >= 4.0:
        return "Avanzado"
    elif score >= 3.4:
        return "Competente"
    else:
        return "En Desarrollo"

def generar_datos_semilla_practica(campus: str = "Misiones") -> pd.DataFrame:
    """
    Genera un conjunto de datos canónico y realista de evaluación docente 
    para asegurar que el panel cuente con información ejecutiva out-of-the-box.
    """
    docentes_base = {
        "Misiones": [
            ("Lic. María Fernández", "Primaria", "Matemáticas"),
            ("Prof. Carlos Mendoza", "Secundaria", "Español"),
            ("Mtra. Ana Laura Gómez", "Preescolar", "Español"),
            ("Prof. Roberto Silva", "Secundaria", "Language Arts"),
            ("Lic. Sofía Villarreal", "Primaria", "Español"),
            ("Mtra. Elena Torres", "Preescolar", "Language Arts"),
            ("Prof. Javier Hernández", "Secundaria", "Matemáticas"),
            ("Lic. Gabriela Treviño", "Primaria", "Language Arts")
        ],
        "Nuevo Sur": [
            ("Mtra. Patricia Garza", "Primaria", "Español"),
            ("Prof. Alejandro Ríos", "Secundaria", "Matemáticas"),
            ("Lic. Claudia Martínez", "Preescolar", "Matemáticas"),
            ("Prof. Fernando Cantú", "Secundaria", "Language Arts"),
            ("Mtra. Verónica Salinas", "Primaria", "Matemáticas"),
            ("Lic. Rodrigo Almaguer", "Secundaria", "Español"),
            ("Mtra. Daniela Montemayor", "Primaria", "Language Arts")
        ],
        "San Agustín": [
            ("Prof. David Cavazos", "Secundaria", "Matemáticas"),
            ("Mtra. Lucía Benavides", "Primaria", "Español"),
            ("Lic. Andrés Morales", "Secundaria", "Language Arts"),
            ("Mtra. Carmen Elizondo", "Preescolar", "Español"),
            ("Prof. Ricardo Zepeda", "Primaria", "Matemáticas"),
            ("Lic. Karen Serna", "Secundaria", "Español"),
            ("Mtra. Isabel Sepúlveda", "Primaria", "Language Arts")
        ]
    }

    docentes_lista = docentes_base.get(campus, docentes_base["Misiones"])
    
    # Generación determinista pero variada por campus
    np.random.seed(hash(campus) % 10000)
    
    observadores = ["Coordinación Pedagógica", "Dirección Académica", "Mentoria Docente"]
    
    recomendaciones_catalogo = [
        "Consolidar la retroalimentación formativa inmediata en actividades individuales.",
        "Reforzar el uso de rúbricas digitalizadas en IXL para seguimiento en tiempo real.",
        "Promover mayor diferenciación para alumnos con ritmo de aprendizaje acelerado.",
        "Excelente clima de aula y dominio metodológico; compartir buenas prácticas.",
        "Integrar metodologías basadas en problemas en la apertura de la sesión."
    ]

    records = []
    for idx, (docente, nivel, materia) in enumerate(docentes_lista):
        if campus == "Misiones":
            r1 = round(np.random.uniform(4.2, 4.9), 2)
            r2 = round(np.random.uniform(4.4, 5.0), 2)
            r3 = round(np.random.uniform(4.0, 4.8), 2)
            r4 = round(np.random.uniform(3.9, 4.7), 2)
            r5 = round(np.random.uniform(4.1, 4.9), 2)
            r6 = round(np.random.uniform(3.6, 4.5), 2)
        elif campus == "Nuevo Sur":
            r1 = round(np.random.uniform(4.3, 5.0), 2)
            r2 = round(np.random.uniform(4.5, 5.0), 2)
            r3 = round(np.random.uniform(4.1, 4.9), 2)
            r4 = round(np.random.uniform(4.0, 4.8), 2)
            r5 = round(np.random.uniform(4.2, 4.9), 2)
            r6 = round(np.random.uniform(3.8, 4.6), 2)
        else: # San Agustín
            r1 = round(np.random.uniform(4.4, 5.0), 2)
            r2 = round(np.random.uniform(4.3, 4.9), 2)
            r3 = round(np.random.uniform(4.2, 4.9), 2)
            r4 = round(np.random.uniform(4.1, 4.8), 2)
            r5 = round(np.random.uniform(4.3, 5.0), 2)
            r6 = round(np.random.uniform(3.9, 4.7), 2)

        score_global = round((r1 + r2 + r3 + r4 + r5 + r6) / 6.0, 2)
        nivel_des = determinar_nivel_desempeno(score_global)
        
        fecha_obs = f"2026-02-{(idx * 3 % 20) + 5:02d}"
        obs = observadores[idx % len(observadores)]
        recom = recomendaciones_catalogo[idx % len(recomendaciones_catalogo)]

        records.append({
            "campus": campus,
            "docente": docente,
            "nivel": nivel,
            "materia": materia,
            "R1_planificacion": r1,
            "R2_clima": r2,
            "R3_estrategias": r3,
            "R4_evaluacion": r4,
            "R5_digital": r5,
            "R6_diferenciacion": r6,
            "score_global": score_global,
            "nivel_desempeno": nivel_des,
            "fecha_observacion": fecha_obs,
            "observador": obs,
            "recomendacion": recom
        })

    return pd.DataFrame(records)

def procesar_archivo_practica(uploaded_file, target_campus: str = "General") -> dict:
    """
    Procesa un archivo Excel o CSV subido para actualizar dinámicamente las rúbricas docentes.
    """
    if uploaded_file is None:
        return {"error": "No se recibió ningún archivo."}
        
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty:
            return {"error": "El archivo cargado se encuentra vacío."}

        # Mapeo flexible de columnas
        col_map = {}
        for col in df.columns:
            cl = str(col).lower().strip()
            if "docente" in cl or "profesor" in cl or "maestro" in cl:
                col_map[col] = "docente"
            elif "campus" in cl or "sede" in cl:
                col_map[col] = "campus"
            elif "nivel" in cl or "grado" in cl:
                col_map[col] = "nivel"
            elif "materia" in cl or "asignatura" in cl:
                col_map[col] = "materia"
            elif "planific" in cl or "r1" in cl:
                col_map[col] = "R1_planificacion"
            elif "clima" in cl or "aula" in cl or "r2" in cl:
                col_map[col] = "R2_clima"
            elif "estrategia" in cl or "activa" in cl or "r3" in cl:
                col_map[col] = "R3_estrategias"
            elif "evaluac" in cl or "formativa" in cl or "r4" in cl:
                col_map[col] = "R4_evaluacion"
            elif "digital" in cl or "tecnolog" in cl or "r5" in cl:
                col_map[col] = "R5_digital"
            elif "diferenc" in cl or "inclusi" in cl or "r6" in cl:
                col_map[col] = "R6_diferenciacion"

        df = df.rename(columns=col_map)

        if "docente" not in df.columns:
            return {"error": "No se encontró la columna de 'Docente' o 'Profesor' en el archivo."}

        # Asignar campus objetivo si no viene en el archivo
        if "campus" not in df.columns:
            df["campus"] = target_campus if target_campus != "Global" else "Misiones"
        else:
            df["campus"] = df["campus"].fillna(target_campus if target_campus != "Global" else "Misiones")

        if "nivel" not in df.columns:
            df["nivel"] = "Primaria"
        if "materia" not in df.columns:
            df["materia"] = "General"

        # Asegurar columnas de rúbricas en escala 1.0 - 5.0
        rubricas_keys = list(RUBRICAS_METADATA.keys())
        for r_key in rubricas_keys:
            if r_key not in df.columns:
                df[r_key] = 4.0
            else:
                # Normalizar si viene en escala 0-100 o 0-10
                df[r_key] = pd.to_numeric(df[r_key], errors="coerce").fillna(4.0)
                mean_val = df[r_key].mean()
                if mean_val > 10:
                    df[r_key] = (df[r_key] / 20.0).clip(1.0, 5.0)
                elif mean_val > 5:
                    df[r_key] = (df[r_key] / 2.0).clip(1.0, 5.0)
                else:
                    df[r_key] = df[r_key].clip(1.0, 5.0)

        # Recalcular score global
        df["score_global"] = df[rubricas_keys].mean(axis=1).round(2)
        df["nivel_desempeno"] = df["score_global"].apply(determinar_nivel_desempeno)
        
        if "fecha_observacion" not in df.columns:
            df["fecha_observacion"] = "2026-02-15"
        if "observador" not in df.columns:
            df["observador"] = "Coordinación Pedagógica"
        if "recomendacion" not in df.columns:
            df["recomendacion"] = "Mantener fortalezas metodológicas e impulsar diferenciación."

        return {
            "error": None,
            "df_raw": df,
            "total_evaluados": len(df)
        }

    except Exception as e:
        return {"error": f"Error al procesar el archivo de Práctica Docente: {e}"}

def calcular_metricas_ejecutivas_practica(df_docentes: pd.DataFrame) -> dict:
    """
    Calcula los agregados, KPIs y métricas clave para el reporte ejecutivo de Práctica Docente.
    """
    if df_docentes is None or df_docentes.empty:
        return {}

    rubricas_keys = list(RUBRICAS_METADATA.keys())
    for r in rubricas_keys:
        if r not in df_docentes.columns:
            df_docentes[r] = 4.0

    if "score_global" not in df_docentes.columns:
        df_docentes["score_global"] = df_docentes[rubricas_keys].mean(axis=1)

    igpd_prom = round(float(df_docentes["score_global"].mean()), 2)
    total_evaluados = len(df_docentes)

    # Nivel de desempeño
    counts_tier = df_docentes["nivel_desempeno"].value_counts().to_dict()
    destacados_avanzados = counts_tier.get("Destacado", 0) + counts_tier.get("Avanzado", 0)
    pct_dest_avanzado = round((destacados_avanzados / total_evaluados) * 100.0, 1) if total_evaluados > 0 else 0.0

    # Promedios por rúbrica
    promedios_rubricas = []
    for r_key, meta in RUBRICAS_METADATA.items():
        val_prom = round(float(df_docentes[r_key].mean()), 2) if r_key in df_docentes.columns else 4.0
        promedios_rubricas.append({
            "key": r_key,
            "codigo": meta["codigo"],
            "nombre": meta["nombre"],
            "promedio": val_prom,
            "meta": meta["meta"],
            "cumplimiento_pct": round((val_prom / meta["meta"]) * 100.0, 1)
        })

    df_rubricas_summary = pd.DataFrame(promedios_rubricas).sort_values("promedio", ascending=True)
    
    # Identificar dimensión prioritaria de mejora (la de menor puntaje)
    dim_prioritaria = df_rubricas_summary.iloc[0]["nombre"] if not df_rubricas_summary.empty else "N/A"
    score_prioritaria = df_rubricas_summary.iloc[0]["promedio"] if not df_rubricas_summary.empty else 0.0

    # Agregado por Nivel Escolar
    df_nivel = df_docentes.groupby("nivel").agg(
        docentes=("docente", "count"),
        igpd_promedios=("score_global", "mean")
    ).reset_index()
    df_nivel["igpd_promedios"] = df_nivel["igpd_promedios"].round(2)

    return {
        "igpd_promedio": igpd_prom,
        "igpd_pct": round((igpd_prom / 5.0) * 100.0, 1),
        "total_evaluados": total_evaluados,
        "pct_destacado_avanzado": pct_dest_avanzado,
        "dimension_prioritaria": dim_prioritaria,
        "score_prioritaria": score_prioritaria,
        "rubricas_summary": df_rubricas_summary,
        "desglose_nivel": df_nivel,
        "distribucion_tiers": counts_tier
    }
