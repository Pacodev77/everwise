import pandas as pd
import streamlit as st
import numpy as np

@st.cache_data
def load_global_data():
    df_asistencia = pd.DataFrame({
        "campus": ["Misiones", "Nuevo Sur", "San Agustín"],
        "asistencia": [0.88, 0.94, 0.91]
    })
    df_academico = pd.DataFrame({
        "campus": ["Misiones", "Nuevo Sur", "San Agustín"],
        "dominio": [0.705, 0.69, 0.735]
    })
    
    # Mock data previo (2024-2025)
    df_asistencia_prev = pd.DataFrame({
        "campus": ["Misiones", "Nuevo Sur", "San Agustín"],
        "asistencia": [0.90, 0.92, 0.89]
    })
    df_academico_prev = pd.DataFrame({
        "campus": ["Misiones", "Nuevo Sur", "San Agustín"],
        "dominio": [0.65, 0.67, 0.71]
    })
    return df_asistencia, df_academico, df_asistencia_prev, df_academico_prev

@st.cache_data
def load_apps_data():
    df_apps_kpis = pd.DataFrame({
        'campus': ['Misiones', 'Misiones', 'Nuevo Sur', 'Nuevo Sur', 'San Agustín', 'San Agustín'],
        'Plataforma': ['IXL', 'Progrentis', 'IXL', 'Progrentis', 'IXL', 'Progrentis'],
        'Uso Efectivo (%)': [0.88, 0.75, 0.92, 0.80, 0.85, 0.70]
    })
    
    # Mock data para correlacion por campus
    np.random.seed(42)
    def gen_corr(c_name, offset):
        p_ixl = np.clip(np.random.normal(0.8+offset, 0.1, 5), 0.4, 1.0)
        r_ixl = np.clip(p_ixl * 0.9 + np.random.normal(0, 0.05, 5), 0.4, 1.0)
        p_pro = np.clip(np.random.normal(0.7+offset, 0.1, 5), 0.4, 1.0)
        r_pro = np.clip(p_pro * 0.85 + np.random.normal(0, 0.05, 5), 0.4, 1.0)
        return pd.DataFrame({
            "campus": [c_name]*10,
            "Grupo": [f"G-{i}" for i in range(1, 6)] * 2,
            "Plataforma": ["IXL"]*5 + ["Progrentis"]*5,
            "Práctica (%)": np.concatenate([p_ixl, p_pro]),
            "Resultado (%)": np.concatenate([r_ixl, r_pro])
        })
    df_c1 = gen_corr("Misiones", 0.0)
    df_c2 = gen_corr("Nuevo Sur", 0.05)
    df_c3 = gen_corr("San Agustín", -0.05)
    
    df_correlacion = pd.concat([df_c1, df_c2, df_c3], ignore_index=True)
    
    return df_apps_kpis, df_correlacion

@st.cache_data
def load_academico_bloques():
    """Genera dataset mock para comparativa B1 vs B2 vs B3"""
    return pd.DataFrame({
        "campus": ["Misiones"]*3 + ["Nuevo Sur"]*3 + ["San Agustín"]*3,
        "Bloque": ["B1", "B2", "B3"]*3,
        "Matemáticas": [0.68, 0.82, 0.85, 0.67, 0.69, 0.72, 0.72, 0.76, 0.80],
        "Español": [0.75, 0.88, 0.90, 0.81, 0.85, 0.88, 0.76, 0.80, 0.85]
    })

@st.cache_data
def load_clima_heatmap():
    """Genera datos matriciales para el Heatmap ICE (Clima Escolar)"""
    data = []
    campus_list = ["Misiones", "Nuevo Sur", "San Agustín"]
    categorias = ["Estrés Acumulado", "Motivación", "Sentido de Pertenencia", "Seguridad Física"]
    respuestas = ["Siempre", "A veces", "Nunca"]
    
    # Generar matriz falsa con distribución tendenciosa
    for c in campus_list:
        for cat in categorias:
            for resp in respuestas:
                base = np.random.uniform(0.1, 0.5)
                if resp == "Siempre" and cat != "Estrés Acumulado": base += 0.4
                if resp == "Nunca" and cat == "Estrés Acumulado": base += 0.3
                data.append({"campus": c, "Categoría": cat, "Respuesta": resp, "Proporción": base})
                
    df = pd.DataFrame(data)
    # Normalizar para que sumen 1 por categoría y campus
    df['Proporción'] = df.groupby(['campus', 'Categoría'])['Proporción'].transform(lambda x: x / x.sum())
    return df

@st.cache_data
def load_disciplina_data():
    """Genera datos de Casos Especiales y Cartas Compromiso"""
    df_casos = pd.DataFrame({
        "campus": ["Misiones", "Nuevo Sur", "San Agustín"],
        "Violencia Escolar": [2, 0, 1],
        "Faltas Graves": [5, 2, 4],
        "Apatía Severa": [12, 8, 15]
    })
    
    df_cartas = pd.DataFrame({
        "campus": ["Misiones", "Nuevo Sur", "San Agustín"],
        "Firmadas": [45, 60, 38],
        "Pendientes": [10, 5, 22]
    })
    return df_casos, df_cartas
