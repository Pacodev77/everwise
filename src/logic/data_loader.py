# src/logic/data_loader.py

import os
import sqlite3
import pandas as pd
# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
import numpy as np
import re

DB_PATH = "data/everwise.db"

def get_db_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn

def init_audit_table():
    """Crea la tabla de bitácora de auditoría si no existe."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                action TEXT NOT NULL,
                details TEXT,
                campus TEXT,
                bimestre TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

# Inicializar tabla de auditoría al importar
init_audit_table()

def log_audit_event(username: str, action: str, details: str = "", campus: str = None, bimestre: str = None):
    """Registra una acción en la bitácora de auditoría corporativa del CRM."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (username, action, details, campus, bimestre) VALUES (?, ?, ?, ?, ?)",
            (username or "Sistema", action, details, campus, bimestre)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_recent_audit_logs(limit: int = 50) -> pd.DataFrame:
    """Recupera los eventos más recientes de la bitácora de auditoría."""
    try:
        conn = get_db_connection()
        df = pd.read_sql(
            "SELECT timestamp as Fecha, username as Usuario, action as Acción, details as Detalles, campus as Campus, bimestre as Periodo FROM audit_logs ORDER BY id DESC LIMIT ?", 
            conn, 
            params=(limit,)
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def init_session_state():
    """
    Inicializa el estado de la sesión leyendo los datos previamente cargados
    desde la base de datos SQLite, garantizando la persistencia al recargar la página.
    """
    if "session_initialized" in st.session_state:
        return
        
    st.session_state["session_initialized"] = True
    
    if not os.path.exists(DB_PATH):
        return
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Cargar Datos Académicos
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        if cursor.fetchone():
            df_acad = pd.read_sql("SELECT * FROM academic_data", conn)
            if not df_acad.empty:
                from src.logic.academic_processor import calcular_desempeno_por_nivel, calcular_promedios_por_nivel
                
                # Agrupar e inyectar cada combinación campus/bimestre
                for (campus, bimestre), group in df_acad.groupby(["campus", "bimestre"]):
                    res = {
                        "campus": campus,
                        "bimestre": bimestre,
                        "df_raw": group,
                        "desempeno": calcular_desempeno_por_nivel(group),
                        "promedios": calcular_promedios_por_nivel(group),
                        "total_alumnos": len(group),
                        "error": None
                    }
                    st.session_state[f"academico_{campus}_{bimestre}"] = res
                
                # Asignar la última versión como "academico_propio_{campus}"
                def _sort_bim(b):
                    s = str(b).upper().strip()
                    if s.startswith('B') and s[1:].isdigit():
                        return int(s[1:])
                    return 99

                for campus, campus_df in df_acad.groupby("campus"):
                    bimestres = campus_df["bimestre"].unique()
                    if len(bimestres) > 0:
                        sorted_bims = sorted(bimestres, key=_sort_bim)
                        latest_bim = sorted_bims[-1]
                        st.session_state[f"academico_propio_{campus}"] = st.session_state[f"academico_{campus}_{latest_bim}"]
                        
                        # Acumular el historial para deltas
                        for bim in sorted_bims:
                            clave_hist = f"historial_bimestres_{campus}"
                            if clave_hist not in st.session_state:
                                st.session_state[clave_hist] = {}
                            bim_df = campus_df[campus_df["bimestre"] == bim]
                            
                            # Evitar KeyErrors o nulos al calcular promedio dominio
                            cols_materias = ["Language Arts", "Matemáticas", "Español"]
                            for col in cols_materias:
                                if col not in bim_df.columns:
                                    bim_df[col] = 0.0
                                    
                            promedio_dominio = (
                                bim_df["Language Arts"].dropna().mean() +
                                bim_df["Matemáticas"].dropna().mean() +
                                bim_df["Español"].dropna().mean()
                            ) / 3.0 / 10.0
                            if pd.isna(promedio_dominio):
                                promedio_dominio = 0.0
                            st.session_state[clave_hist][bim] = round(promedio_dominio, 3)

        # 2. Cargar Asistencia
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
        if cursor.fetchone():
            df_ast = pd.read_sql("SELECT * FROM attendance_data", conn)
            if not df_ast.empty:
                for campus, group in df_ast.groupby("campus"):
                    staff_val = group["staff_asistencia"].iloc[0] if "staff_asistencia" in group.columns else 0.85
                    if pd.isna(staff_val): staff_val = 0.85
                    st.session_state[f"asistencia_data_{campus}"] = {
                        "niveles": group[["Nivel", "Asistencia", "Distribución"]].copy(),
                        "staff": float(staff_val)
                    }

        # 3. Cargar Clima Escolar
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clima_data'")
        if cursor.fetchone():
            df_clima = pd.read_sql("SELECT * FROM clima_data", conn)
            if not df_clima.empty:
                st.session_state["clima_data_global"] = df_clima

        # 4. Cargar Disciplina (Casos y Cartas)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_casos'")
        if cursor.fetchone():
            df_casos = pd.read_sql("SELECT * FROM disciplina_casos", conn)
            if not df_casos.empty:
                st.session_state["disciplina_casos_global"] = df_casos
                
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_cartas'")
        if cursor.fetchone():
            df_cartas = pd.read_sql("SELECT * FROM disciplina_cartas", conn)
            if not df_cartas.empty:
                st.session_state["disciplina_cartas_global"] = df_cartas

        # 5. Cargar Práctica Docente y Uso de Apps
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_apps_kpis'")
        if cursor.fetchone():
            df_apps = pd.read_sql("SELECT * FROM practica_apps_kpis", conn)
            if not df_apps.empty:
                st.session_state["practica_apps_global"] = df_apps
                
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_correlacion'")
        if cursor.fetchone():
            df_corr = pd.read_sql("SELECT * FROM practica_correlacion", conn)
            if not df_corr.empty:
                st.session_state["practica_corr_global"] = df_corr

        conn.close()
    except Exception as e:
        # Fallback silencioso para no romper la app si la base está bloqueada
        pass

# --- Funciones de Persistencia ---

def save_academic_data(campus, bimestre, df):
    """
    Guarda y consolida los datos académicos limpios en SQLite.
    Realiza un upsert incremental a nivel de (campus, bimestre, MATRICULA) para que si se
    suben archivos de diferentes niveles o secciones por separado, se unifiquen sin sobrescribirse.
    """
    if df is None or df.empty or campus == "Desconocido" or bimestre == "B?":
        return
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        existing_df = None
        if cursor.fetchone():
            try:
                existing_df = pd.read_sql(
                    "SELECT * FROM academic_data WHERE campus = ? AND bimestre = ?", 
                    conn, 
                    params=(campus, bimestre)
                )
            except Exception:
                existing_df = None
                
        df_new = df.copy()
        df_new["campus"] = campus
        df_new["bimestre"] = bimestre
        
        if existing_df is not None and not existing_df.empty:
            # Combinar manteniendo MATRICULA única: el nuevo registro actualiza al previo
            df_combined = pd.concat([existing_df, df_new], ignore_index=True)
            if "MATRICULA" in df_combined.columns:
                df_combined = df_combined.drop_duplicates(subset=["campus", "bimestre", "MATRICULA"], keep="last")
            else:
                df_combined = df_combined.drop_duplicates(subset=["campus", "bimestre", "ALUMNO"], keep="last")
            
            cursor.execute("DELETE FROM academic_data WHERE campus = ? AND bimestre = ?", (campus, bimestre))
            conn.commit()
            df_combined.to_sql("academic_data", conn, if_exists="append", index=False)
            total_guardados = len(df_combined)
        else:
            if "MATRICULA" in df_new.columns:
                df_new = df_new.drop_duplicates(subset=["campus", "bimestre", "MATRICULA"], keep="last")
            df_new.to_sql("academic_data", conn, if_exists="append", index=False)
            total_guardados = len(df_new)
            
        # Registrar evento de auditoría
        username = st.session_state.get("username", "Sistema") if "username" in st.session_state else "Sistema"
        log_audit_event(username, "CARGA_ACADEMICA", f"Guardados {total_guardados} alumnos", campus, bimestre)
        st.cache_data.clear()
    finally:
        conn.close()

def delete_academic_data(campus, bimestre=None):
    """Elimina los datos académicos del campus (o bimestre específico) en SQLite y limpia la caché."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        if cursor.fetchone():
            if bimestre:
                cursor.execute("DELETE FROM academic_data WHERE campus = ? AND bimestre = ?", (campus, bimestre))
            else:
                cursor.execute("DELETE FROM academic_data WHERE campus = ?", (campus,))
            conn.commit()
            
            username = st.session_state.get("username", "Sistema") if "username" in st.session_state else "Sistema"
            log_audit_event(username, "ELIMINACION_ACADEMICA", f"Periodo {bimestre if bimestre else 'Todo'}", campus, bimestre)
        st.cache_data.clear()
    finally:
        conn.close()

def get_academic_history_catalog():
    """Retorna un catálogo estructurado de todos los campus y bimestres almacenados en la base de datos."""
    if not os.path.exists(DB_PATH):
        return {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        if not cursor.fetchone():
            conn.close()
            return {}
        df_all = pd.read_sql("SELECT * FROM academic_data", conn)
        conn.close()
        
        if df_all.empty:
            return {}
            
        from src.logic.academic_processor import calcular_desempeno_por_nivel, calcular_promedios_por_nivel
        catalog = {}
        for (campus, bimestre), group in df_all.groupby(["campus", "bimestre"]):
            if campus not in catalog:
                catalog[campus] = {}
            catalog[campus][bimestre] = {
                "campus": campus,
                "bimestre": bimestre,
                "df_raw": group,
                "desempeno": calcular_desempeno_por_nivel(group),
                "promedios": calcular_promedios_por_nivel(group),
                "total_alumnos": len(group),
                "error": None
            }
        return catalog
    except Exception:
        return {}

def save_attendance_data(campus, df_niveles, staff_kpi):
    """Guarda y consolida los datos de asistencia en SQLite."""
    if df_niveles is None or df_niveles.empty or campus == "Desconocido":
        return
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        df_to_save = df_niveles.copy()
        df_to_save["campus"] = campus
        df_to_save["staff_asistencia"] = float(staff_kpi) if staff_kpi is not None else 0.85
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM attendance_data WHERE campus = ?", (campus,))
            conn.commit()
            
        df_to_save.to_sql("attendance_data", conn, if_exists="append", index=False)
        
        username = st.session_state.get("username", "Sistema") if "username" in st.session_state else "Sistema"
        log_audit_event(username, "CARGA_ASISTENCIA", f"Guardada asistencia staff: {staff_kpi:.1%}", campus)
        st.cache_data.clear()
    finally:
        conn.close()

def delete_attendance_data(campus):
    """Elimina los datos de asistencia del campus en SQLite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM attendance_data WHERE campus = ?", (campus,))
            conn.commit()
        st.cache_data.clear()
    finally:
        conn.close()

def save_clima_data(df_clima):
    """Guarda los datos de clima escolar en SQLite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clima_data'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM clima_data")
            conn.commit()
        df_clima.to_sql("clima_data", conn, if_exists="replace", index=False)
        st.cache_data.clear()
    finally:
        conn.close()

def save_disciplina_data(df_casos, df_cartas):
    """Guarda los datos de disciplina en SQLite."""
    conn = get_db_connection()
    try:
        # Casos
        conn.execute("DROP TABLE IF EXISTS disciplina_casos")
        df_casos.to_sql("disciplina_casos", conn, if_exists="replace", index=False)
        
        # Cartas
        conn.execute("DROP TABLE IF EXISTS disciplina_cartas")
        df_cartas.to_sql("disciplina_cartas", conn, if_exists="replace", index=False)
        st.cache_data.clear()
    finally:
        conn.close()

def save_practica_data(df_apps_kpis, df_correlacion):
    """Guarda los datos de práctica docente en SQLite."""
    conn = get_db_connection()
    try:
        # KPIs
        conn.execute("DROP TABLE IF EXISTS practica_apps_kpis")
        df_apps_kpis.to_sql("practica_apps_kpis", conn, if_exists="replace", index=False)
        
        # Correlación
        conn.execute("DROP TABLE IF EXISTS practica_correlacion")
        df_correlacion.to_sql("practica_correlacion", conn, if_exists="replace", index=False)
        st.cache_data.clear()
    finally:
        conn.close()

# --- Funciones de Carga Inteligente de Vistas ---

@st.cache_data
def load_global_data():
    """Carga los promedios globales de asistencia y dominio, priorizando la base de datos."""
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
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            # Carga asistencia
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
            if cursor.fetchone():
                df_att = pd.read_sql("SELECT campus, Asistencia FROM attendance_data", conn)
                if not df_att.empty:
                    df_att_grouped = df_att.groupby("campus")["Asistencia"].mean().reset_index()
                    for _, row in df_att_grouped.iterrows():
                        df_asistencia.loc[df_asistencia["campus"] == row["campus"], "asistencia"] = row["Asistencia"]
            
            # Carga académico
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
            if cursor.fetchone():
                df_acad_all = pd.read_sql("SELECT campus, bimestre, [Language Arts], [Matemáticas], [Español] FROM academic_data", conn)
                if not df_acad_all.empty:
                    for campus, campus_df in df_acad_all.groupby("campus"):
                        latest_bim = sorted(campus_df["bimestre"].unique())[-1]
                        latest_df = campus_df[campus_df["bimestre"] == latest_bim]
                        
                        cols_needed = ["Language Arts", "Matemáticas", "Español"]
                        for col in cols_needed:
                            if col not in latest_df.columns:
                                latest_df[col] = 0.0
                                
                        mean_grade = (
                            latest_df["Language Arts"].dropna().mean() +
                            latest_df["Matemáticas"].dropna().mean() +
                            latest_df["Español"].dropna().mean()
                        ) / 3.0
                        if pd.isna(mean_grade):
                            mean_grade = 0.0
                        df_academico.loc[df_academico["campus"] == campus, "dominio"] = mean_grade / 10.0
            conn.close()
        except Exception:
            pass
            
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
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_apps_kpis'")
            if cursor.fetchone():
                df_real_kpis = pd.read_sql("SELECT * FROM practica_apps_kpis", conn)
                if not df_real_kpis.empty:
                    df_apps_kpis = df_real_kpis
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_correlacion'")
            if cursor.fetchone():
                df_real_corr = pd.read_sql("SELECT * FROM practica_correlacion", conn)
                if not df_real_corr.empty:
                    df_correlacion = df_real_corr
            conn.close()
        except Exception:
            pass
            
    return df_apps_kpis, df_correlacion

@st.cache_data
def load_academico_bloques():
    """Genera comparativa B1-B5, incorporando los datos de la base de datos."""
    df_mock = pd.DataFrame({
        "campus": ["Misiones"]*5 + ["Nuevo Sur"]*5 + ["San Agustín"]*5,
        "Bloque": ["B1", "B2", "B3", "B4", "B5"]*3,
        "Matemáticas": [0.68, 0.82, 0.85, 0.88, 0.90, 0.67, 0.69, 0.72, 0.76, 0.80, 0.72, 0.76, 0.80, 0.83, 0.86],
        "Español": [0.75, 0.88, 0.90, 0.92, 0.94, 0.81, 0.85, 0.88, 0.90, 0.92, 0.76, 0.80, 0.85, 0.88, 0.90],
        "Language Arts": [0.70, 0.80, 0.85, 0.87, 0.89, 0.75, 0.78, 0.82, 0.85, 0.87, 0.70, 0.74, 0.78, 0.82, 0.85]
    })
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
            if cursor.fetchone():
                df_real = pd.read_sql("SELECT campus, bimestre as Bloque, [Language Arts], [Matemáticas], [Español] FROM academic_data", conn)
                if not df_real.empty:
                    df_real_grouped = df_real.groupby(["campus", "Bloque"]).mean().reset_index()
                    df_real_grouped["Matemáticas"] = df_real_grouped["Matemáticas"] / 10.0
                    df_real_grouped["Español"] = df_real_grouped["Español"] / 10.0
                    df_real_grouped["Language Arts"] = df_real_grouped["Language Arts"] / 10.0
                    
                    df_mock = df_mock.set_index(["campus", "Bloque"])
                    df_real_grouped = df_real_grouped.set_index(["campus", "Bloque"])
                    
                    df_combined = df_real_grouped.combine_first(df_mock).reset_index()
                    conn.close()
                    
                    # Ordenar bloques B1..B5
                    def _sort_key(r):
                        b = str(r['Bloque']).upper().strip()
                        num = int(b[1:]) if b.startswith('B') and b[1:].isdigit() else 99
                        return (r['campus'], num)
                        
                    df_combined['sort_order'] = df_combined['Bloque'].apply(
                        lambda b: int(str(b)[1:]) if str(b).startswith('B') and str(b)[1:].isdigit() else 99
                    )
                    df_combined = df_combined.sort_values(['campus', 'sort_order']).drop(columns=['sort_order'])
                    return df_combined
            conn.close()
        except Exception:
            pass
            
    return df_mock

@st.cache_data
def load_clima_heatmap():
    """Genera datos ICE de Clima Escolar, priorizando base de datos."""
    data = []
    campus_list = ["Misiones", "Nuevo Sur", "San Agustín"]
    categorias = ["Estrés Acumulado", "Motivación", "Sentido de Pertenencia", "Seguridad Física"]
    respuestas = ["Siempre", "A veces", "Nunca"]
    
    for c in campus_list:
        for cat in categorias:
            for resp in respuestas:
                base = np.random.uniform(0.1, 0.5)
                if resp == "Siempre" and cat != "Estrés Acumulado": base += 0.4
                if resp == "Nunca" and cat == "Estrés Acumulado": base += 0.3
                data.append({"campus": c, "Categoría": cat, "Respuesta": resp, "Proporción": base})
                
    df = pd.DataFrame(data)
    df['Proporción'] = df.groupby(['campus', 'Categoría'])['Proporción'].transform(lambda x: x / x.sum())
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clima_data'")
            if cursor.fetchone():
                df_real = pd.read_sql("SELECT * FROM clima_data", conn)
                if not df_real.empty:
                    df = df_real
            conn.close()
        except Exception:
            pass
            
    return df

@st.cache_data
def load_disciplina_data():
    """Genera datos de Disciplina, priorizando la base de datos."""
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
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_casos'")
            if cursor.fetchone():
                df_real_casos = pd.read_sql("SELECT * FROM disciplina_casos", conn)
                if not df_real_casos.empty:
                    df_casos = df_real_casos
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_cartas'")
            if cursor.fetchone():
                df_real_cartas = pd.read_sql("SELECT * FROM disciplina_cartas", conn)
                if not df_real_cartas.empty:
                    df_cartas = df_real_cartas
            conn.close()
        except Exception:
            pass
            
    return df_casos, df_cartas

def procesar_archivo_subido(uploaded_file):
    """
    Lee el archivo Excel subido y extrae automáticamente el bimestre 
    (B1 al B6) desde el nombre del archivo.
    """
    if uploaded_file is None:
        return None, None
        
    try:
        nombre_archivo = uploaded_file.name.upper()
        coincidencia = re.search(r'\bB[1-6]\b|[_.-]B[1-6]|[B][1-6]', nombre_archivo)
        
        if coincidencia:
            texto_match = coincidencia.group(0)
            solo_b = re.search(r'B[1-6]', texto_match)
            bimestre_detectado = solo_b.group(0) if solo_b else "Desconocido"
        else:
            bimestre_detectado = "Desconocido"
        
        df = pd.read_excel(uploaded_file)
        df['Bimestre_Origen'] = bimestre_detectado
        
        return df, bimestre_detectado
        
    except Exception as e:
        st.error(f"Error al procesar el archivo Excel: {e}")
        return None, None