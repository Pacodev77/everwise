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
                ciclo_escolar TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

def init_attendance_tables_conn(conn):
    """Crea las tablas de asistencia normalizada y resumen diario si no existen."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS normalized_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campus TEXT,
            tipo_persona TEXT,
            matricula TEXT,
            nombre TEXT,
            apellidos TEXT,
            nivel_normalizado TEXT,
            grado_grupo TEXT,
            fecha DATE,
            hora_entrada TEXT,
            hora_salida TEXT,
            estatus TEXT,
            campus_ciclo TEXT,
            fuente_archivo TEXT,
            fuente_hoja TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumen_diario_nivel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campus TEXT,
            fecha DATE,
            segmento TEXT,
            nivel TEXT,
            presentes INTEGER,
            total INTEGER,
            tasa_asistencia REAL,
            fuente_archivo TEXT,
            fuente_hoja TEXT
        )
    """)
    conn.commit()

def init_attendance_tables():
    conn = get_db_connection()
    try:
        init_attendance_tables_conn(conn)
    finally:
        conn.close()

# Inicializar tablas al importar
init_audit_table()
init_attendance_tables()

def reconstruct_attendance_state(campus, ciclo_escolar=None):
    """Reconstruye el estado completo de asistencia de un campus desde la base de datos."""
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Intentar cargar desde normalized_attendance (grano de persona)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='normalized_attendance'")
        if cursor.fetchone():
            df_canon = pd.read_sql(
                "SELECT * FROM normalized_attendance WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", 
                conn, 
                params=(campus, ciclo, ciclo)
            )
            if not df_canon.empty:
                # Parsear fechas
                df_canon['fecha'] = pd.to_datetime(df_canon['fecha']).dt.date
                
                df_al = df_canon[df_canon['tipo_persona'] == 'alumno']
                df_staff = df_canon[df_canon['tipo_persona'] == 'colaborador']
                
                dias_alumnos = df_al['fecha'].nunique() if not df_al.empty else 0
                dias_staff = df_staff['fecha'].nunique() if not df_staff.empty else 0
                
                levels_list = []
                has_falta = (df_al['estatus'] == 'Falta').any()
                
                niveles_encontrados = list(df_al['nivel_normalizado'].unique())
                # Asegurar niveles base
                for x in ['Preescolar', 'Primaria', 'Secundaria']:
                    if x not in niveles_encontrados:
                        niveles_encontrados.append(x)
                        
                total_pob = 0
                pob_por_nivel = {}
                for lvl in niveles_encontrados:
                    df_lvl = df_al[df_al['nivel_normalizado'] == lvl]
                    if df_lvl.empty:
                        pob_por_nivel[lvl] = 0
                        continue
                    if has_falta:
                        pob = df_lvl['matricula'].nunique()
                    else:
                        daily = df_lvl.groupby('fecha')['matricula'].nunique()
                        pob = daily.max() if not daily.empty else 0
                    pob_por_nivel[lvl] = pob
                    total_pob += pob
                    
                for lvl in niveles_encontrados:
                    if lvl == 'SIN_MAPEAR' and pob_por_nivel.get(lvl, 0) == 0:
                        continue
                    df_lvl = df_al[df_al['nivel_normalizado'] == lvl]
                    if df_lvl.empty:
                        asis_rate = 0.0
                    else:
                        if has_falta:
                            total_rows = len(df_lvl)
                            present_rows = len(df_lvl[df_lvl['estatus'].isin(['Presente', 'Retardo'])])
                            asis_rate = present_rows / total_rows if total_rows > 0 else 0.0
                        else:
                            daily = df_lvl.groupby('fecha')['matricula'].nunique()
                            max_pob = pob_por_nivel[lvl]
                            asis_rate = (daily.mean() / max_pob) if max_pob > 0 else 0.0
                            
                    distrib = (pob_por_nivel[lvl] / total_pob) if total_pob > 0 else (1.0 / len(niveles_encontrados))
                    levels_list.append({
                        'Nivel': lvl,
                        'Asistencia': round(asis_rate, 4),
                        'Distribución': round(distrib, 4)
                    })
                    
                df_levels = pd.DataFrame(levels_list)
                
                staff_asis = 0.90
                staff_desglose = {}
                if not df_staff.empty:
                    has_falta_staff = (df_staff['estatus'] == 'Falta').any()
                    if has_falta_staff:
                        total_s = len(df_staff)
                        present_s = len(df_staff[df_staff['estatus'].isin(['Presente', 'Retardo'])])
                        staff_asis = present_s / total_s if total_s > 0 else 0.0
                    else:
                        daily_s = df_staff.groupby('fecha')['nombre'].count()
                        max_s = daily_s.max() if not daily_s.empty else 0
                        staff_asis = (daily_s.mean() / max_s) if max_s > 0 else 0.0
                        
                    for lvl in df_staff['nivel_normalizado'].unique():
                        df_lvl_s = df_staff[df_staff['nivel_normalizado'] == lvl]
                        if has_falta_staff:
                            total_l = len(df_lvl_s)
                            present_l = len(df_lvl_s[df_lvl_s['estatus'].isin(['Presente', 'Retardo'])])
                            rate_l = present_l / total_l if total_l > 0 else 0.0
                        else:
                            daily_l = df_lvl_s.groupby('fecha')['nombre'].count()
                            max_l = daily_l.max() if not daily_l.empty else 0
                            rate_l = (daily_l.mean() / max_l) if max_l > 0 else 0.0
                        lvl_key = "Staff General" if (pd.isna(lvl) or str(lvl).strip().upper() in ["SIN_MAPEAR", "NONE", "NAN", ""]) else str(lvl).strip()
                        staff_desglose[lvl_key] = round(rate_l, 4)
                        
                return {
                    "niveles": df_levels,
                    "staff": float(staff_asis),
                    "staff_desglose": staff_desglose,
                    "dias_alumnos": dias_alumnos,
                    "dias_staff": dias_staff
                }
                
        # 2. Intentar cargar desde resumen_diario_nivel (Firma B)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resumen_diario_nivel'")
        if cursor.fetchone():
            df_res = pd.read_sql(
                "SELECT * FROM resumen_diario_nivel WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", 
                conn, 
                params=(campus, ciclo, ciclo)
            )
            if not df_res.empty:
                df_res['fecha'] = pd.to_datetime(df_res['fecha']).dt.date
                df_al = df_res[df_res['segmento'] == 'alumno']
                df_staff = df_res[df_res['segmento'] == 'colaborador']
                
                dias_alumnos = df_al['fecha'].nunique() if not df_al.empty else 0
                dias_staff = df_staff['fecha'].nunique() if not df_staff.empty else 0
                
                levels_list = []
                if not df_al.empty:
                    grouped = df_al.groupby('nivel').agg(
                        Asistencia=('tasa_asistencia', 'mean'),
                        TotalHC=('total', 'mean')
                    ).reset_index()
                    
                    df_levels_only = grouped[grouped['nivel'] != 'Total']
                    total_hc = df_levels_only['TotalHC'].sum()
                    
                    for _, row in df_levels_only.iterrows():
                        distrib = (row['TotalHC'] / total_hc) if total_hc > 0 else (1.0 / len(df_levels_only))
                        levels_list.append({
                            'Nivel': row['nivel'],
                            'Asistencia': round(row['Asistencia'], 4),
                            'Distribución': round(distrib, 4)
                        })
                else:
                    levels_list = [
                        {"Nivel": "Preescolar", "Asistencia": 0.0, "Distribución": 0.333},
                        {"Nivel": "Primaria", "Asistencia": 0.0, "Distribución": 0.333},
                        {"Nivel": "Secundaria", "Asistencia": 0.0, "Distribución": 0.334}
                    ]
                df_levels = pd.DataFrame(levels_list)
                
                staff_asis = 0.90
                staff_desglose = {}
                if not df_staff.empty:
                    df_total_staff = df_staff[df_staff['nivel'] == 'Total']
                    if not df_total_staff.empty:
                        staff_asis = df_total_staff['tasa_asistencia'].mean()
                    else:
                        staff_asis = df_staff['tasa_asistencia'].mean()
                        
                    df_desglose_staff = df_staff[df_staff['nivel'] != 'Total']
                    for lvl, grp in df_desglose_staff.groupby('nivel'):
                        staff_desglose[lvl] = round(grp['tasa_asistencia'].mean(), 4)
                        
                return {
                    "niveles": df_levels,
                    "staff": float(staff_asis),
                    "staff_desglose": staff_desglose,
                    "dias_alumnos": dias_alumnos,
                    "dias_staff": dias_staff
                }
                
        # 3. Fallback a la tabla heredada
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
        if cursor.fetchone():
            df_ast = pd.read_sql(
                "SELECT * FROM attendance_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", 
                conn, 
                params=(campus, ciclo, ciclo)
            )
            if not df_ast.empty:
                staff_val = df_ast["staff_asistencia"].iloc[0] if "staff_asistencia" in df_ast.columns else 0.85
                if pd.isna(staff_val): staff_val = 0.85
                cols_niv = [c for c in ["Nivel", "Asistencia", "Distribución"] if c in df_ast.columns]
                return {
                    "niveles": df_ast[cols_niv].copy(),
                    "staff": float(staff_val)
                }
        return None
    except Exception:
        return None
    finally:
        conn.close()


def log_audit_event(username: str, action: str, details: str = "", campus: str = None, bimestre: str = None, ciclo_escolar: str = None):
    """Registra una acción en la bitácora de auditoría corporativa del CRM."""
    try:
        ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (username, action, details, campus, bimestre, ciclo_escolar) VALUES (?, ?, ?, ?, ?, ?)",
            (username or "Sistema", action, details, campus, bimestre, ciclo)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_recent_audit_logs(limit: int = 50, ciclo_escolar: str = None) -> pd.DataFrame:
    """Recupera los eventos más recientes de la bitácora de auditoría filtrados por ciclo escolar."""
    try:
        ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
        ensure_schema_has_ciclo_escolar()
        conn = get_db_connection()
        df = pd.read_sql(
            "SELECT timestamp as Fecha, username as Usuario, action as Acción, details as Detalles, campus as Campus, bimestre as Periodo FROM audit_logs WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026') ORDER BY id DESC LIMIT ?", 
            conn, 
            params=(ciclo, ciclo, limit)
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def ensure_schema_has_ciclo_escolar():
    """Garantiza que todas las tablas de la BD SQLite tengan la columna ciclo_escolar."""
    if not os.path.exists(DB_PATH):
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        tables = [
            "academic_data", "attendance_data", "normalized_attendance", 
            "resumen_diario_nivel", "clima_data", "disciplina_casos", 
            "disciplina_cartas", "practica_apps_kpis", "practica_correlacion", 
            "practica_docente_data", "preescolar_qualitative_data",
            "ixl_diagnostics", "progrentis_data", "audit_logs"
        ]
        for t in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
            if cursor.fetchone():
                cursor.execute(f"PRAGMA table_info({t})")
                cols = [row[1] for row in cursor.fetchall()]
                if "ciclo_escolar" not in cols:
                    try:
                        cursor.execute(f"ALTER TABLE {t} ADD COLUMN ciclo_escolar TEXT DEFAULT '2025 - 2026'")
                        conn.commit()
                    except Exception:
                        pass
        conn.close()
    except Exception:
        pass

def init_session_state(ciclo_escolar: str = None):
    """
    Inicializa el estado de la sesión leyendo los datos previamente cargados
    desde la base de datos SQLite para el ciclo escolar activo.
    """
    if ciclo_escolar is None:
        ciclo_escolar = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
        
    st.session_state["ciclo_escolar_activo"] = ciclo_escolar

    current_init = st.session_state.get("session_initialized_cycle")
    if current_init == ciclo_escolar:
        return

    st.session_state["session_initialized_cycle"] = ciclo_escolar
    ensure_schema_has_ciclo_escolar()

    # Limpiar claves de módulos anteriores para dar paso a los datos del ciclo actual
    prefixes = (
        "ixl_", "progrentis_", "academico_", "asistencia_", 
        "clima_", "disciplina_", "practica_", "last_up_", "df_", "preescolar_"
    )
    keys_to_clean = [
        k for k in list(st.session_state.keys())
        if k.startswith(prefixes) and k != "cycle_vault"
    ]
    for k in keys_to_clean:
        del st.session_state[k]

    if not os.path.exists(DB_PATH):
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Cargar Datos Académicos por ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        if cursor.fetchone():
            df_acad = pd.read_sql(
                "SELECT * FROM academic_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", 
                conn, 
                params=(ciclo_escolar, ciclo_escolar)
            )
            if not df_acad.empty:
                from src.logic.academic_processor import calcular_desempeno_por_nivel, calcular_promedios_por_nivel
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

        # 2. Cargar Asistencia por ciclo
        campuses_stored = set()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='normalized_attendance'")
        if cursor.fetchone():
            cursor.execute("SELECT DISTINCT campus FROM normalized_attendance WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo_escolar, ciclo_escolar))
            campuses_stored.update([row[0] for row in cursor.fetchall() if row[0]])

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
        if cursor.fetchone():
            cursor.execute("SELECT DISTINCT campus FROM attendance_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo_escolar, ciclo_escolar))
            campuses_stored.update([row[0] for row in cursor.fetchall() if row[0]])

        for campus in campuses_stored:
            state_data = reconstruct_attendance_state(campus, ciclo_escolar)
            if state_data:
                st.session_state[f"asistencia_data_{campus}"] = state_data

        # 3. Cargar Clima Escolar por ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clima_data'")
        if cursor.fetchone():
            df_clima = pd.read_sql("SELECT * FROM clima_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
            if not df_clima.empty:
                st.session_state["clima_data_global"] = df_clima

        # 4. Cargar Disciplina por ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_casos'")
        if cursor.fetchone():
            df_casos = pd.read_sql("SELECT * FROM disciplina_casos WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
            if not df_casos.empty:
                st.session_state["disciplina_casos"] = df_casos

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_cartas'")
        if cursor.fetchone():
            df_cartas = pd.read_sql("SELECT * FROM disciplina_cartas WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
            if not df_cartas.empty:
                st.session_state["disciplina_cartas"] = df_cartas

        # 5. Cargar Práctica Docente y Uso de Apps por ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_apps_kpis'")
        if cursor.fetchone():
            df_apps = pd.read_sql("SELECT * FROM practica_apps_kpis WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
            if not df_apps.empty:
                st.session_state["practica_apps_kpis"] = df_apps

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_correlacion'")
        if cursor.fetchone():
            df_corr = pd.read_sql("SELECT * FROM practica_correlacion WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
            if not df_corr.empty:
                st.session_state["practica_correlacion"] = df_corr

        conn.close()
    except Exception:
        pass

# --- Funciones de Persistencia ---

def save_academic_data(campus, bimestre, df, ciclo_escolar=None):
    if df is None or df.empty or campus == "Desconocido" or bimestre == "B?":
        return
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        existing_df = None
        if cursor.fetchone():
            try:
                existing_df = pd.read_sql(
                    "SELECT * FROM academic_data WHERE campus = ? AND bimestre = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", 
                    conn, 
                    params=(campus, bimestre, ciclo, ciclo)
                )
            except Exception:
                existing_df = None

        df_new = df.copy()
        df_new["campus"] = campus
        df_new["bimestre"] = bimestre
        df_new["ciclo_escolar"] = ciclo

        if existing_df is not None and not existing_df.empty:
            df_combined = pd.concat([existing_df, df_new], ignore_index=True)
            if "MATRICULA" in df_combined.columns:
                df_combined = df_combined.drop_duplicates(subset=["campus", "bimestre", "ciclo_escolar", "MATRICULA"], keep="last")
            else:
                df_combined = df_combined.drop_duplicates(subset=["campus", "bimestre", "ciclo_escolar", "ALUMNO"], keep="last")

            cursor.execute("DELETE FROM academic_data WHERE campus = ? AND bimestre = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, bimestre, ciclo, ciclo))
            conn.commit()
            df_combined.to_sql("academic_data", conn, if_exists="append", index=False)
            total_guardados = len(df_combined)
        else:
            if "MATRICULA" in df_new.columns:
                df_new = df_new.drop_duplicates(subset=["campus", "bimestre", "ciclo_escolar", "MATRICULA"], keep="last")
            df_new.to_sql("academic_data", conn, if_exists="append", index=False)
            total_guardados = len(df_new)

        username = st.session_state.get("username", "Sistema") if "username" in st.session_state else "Sistema"
        log_audit_event(username, "CARGA_ACADEMICA", f"Guardados {total_guardados} alumnos ({ciclo})", campus, bimestre)
        st.cache_data.clear()
    finally:
        conn.close()

def delete_academic_data(campus, bimestre=None, ciclo_escolar=None):
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        if cursor.fetchone():
            if bimestre:
                cursor.execute("DELETE FROM academic_data WHERE campus = ? AND bimestre = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, bimestre, ciclo, ciclo))
            else:
                cursor.execute("DELETE FROM academic_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))
            conn.commit()

            username = st.session_state.get("username", "Sistema") if "username" in st.session_state else "Sistema"
            log_audit_event(username, "ELIMINACION_ACADEMICA", f"Periodo {bimestre if bimestre else 'Todo'} ({ciclo})", campus, bimestre)
        st.cache_data.clear()
    finally:
        conn.close()

def get_academic_history_catalog(ciclo_escolar: str = None):
    if ciclo_escolar is None:
        ciclo_escolar = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    if not os.path.exists(DB_PATH):
        return {}
    try:
        ensure_schema_has_ciclo_escolar()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
        if not cursor.fetchone():
            conn.close()
            return {}
        df_all = pd.read_sql("SELECT * FROM academic_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
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

def save_attendance_data(campus, df_niveles, staff_kpi, df_canonico=None, df_resumen=None, ciclo_escolar=None):
    if df_niveles is None or df_niveles.empty or campus == "Desconocido":
        return
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        init_attendance_tables_conn(conn)

        df_to_save = df_niveles.copy()
        df_to_save["campus"] = campus
        df_to_save["ciclo_escolar"] = ciclo
        df_to_save["staff_asistencia"] = float(staff_kpi) if staff_kpi is not None else 0.85

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM attendance_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))
            conn.commit()

        df_to_save.to_sql("attendance_data", conn, if_exists="append", index=False)

        if df_canonico is not None and not df_canonico.empty:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='normalized_attendance'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM normalized_attendance WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))
                conn.commit()
            df_canon_save = df_canonico.copy()
            df_canon_save['ciclo_escolar'] = ciclo
            df_canon_save['fecha'] = df_canon_save['fecha'].astype(str)
            df_canon_save['hora_entrada'] = df_canon_save['hora_entrada'].apply(lambda x: str(x) if x is not None else None)
            df_canon_save['hora_salida'] = df_canon_save['hora_salida'].apply(lambda x: str(x) if x is not None else None)
            df_canon_save.to_sql("normalized_attendance", conn, if_exists="append", index=False)

        if df_resumen is not None and not df_resumen.empty:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resumen_diario_nivel'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM resumen_diario_nivel WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))
                conn.commit()
            df_resumen_save = df_resumen.copy()
            df_resumen_save['ciclo_escolar'] = ciclo
            df_resumen_save['fecha'] = df_resumen_save['fecha'].astype(str)
            df_resumen_save.to_sql("resumen_diario_nivel", conn, if_exists="append", index=False)

        username = st.session_state.get("username", "Sistema") if "username" in st.session_state else "Sistema"
        log_audit_event(username, "CARGA_ASISTENCIA", f"Guardada asistencia staff: {staff_kpi:.1%} ({ciclo})", campus)
        st.cache_data.clear()
    finally:
        conn.close()

def delete_attendance_data(campus, ciclo_escolar=None):
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM attendance_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='normalized_attendance'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM normalized_attendance WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resumen_diario_nivel'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM resumen_diario_nivel WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))

        conn.commit()
        st.cache_data.clear()
    finally:
        conn.close()


def save_clima_data(df_clima, ciclo_escolar=None):
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        df_save = df_clima.copy()
        df_save["ciclo_escolar"] = ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clima_data'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM clima_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo, ciclo))
            conn.commit()
        df_save.to_sql("clima_data", conn, if_exists="append", index=False)
        st.cache_data.clear()
    finally:
        conn.close()

def save_disciplina_data(df_casos, df_cartas, ciclo_escolar=None):
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        df_casos_save = df_casos.copy()
        df_casos_save["ciclo_escolar"] = ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_casos'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM disciplina_casos WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo, ciclo))
        df_casos_save.to_sql("disciplina_casos", conn, if_exists="append", index=False)

        df_cartas_save = df_cartas.copy()
        df_cartas_save["ciclo_escolar"] = ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_cartas'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM disciplina_cartas WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo, ciclo))
        df_cartas_save.to_sql("disciplina_cartas", conn, if_exists="append", index=False)
        st.cache_data.clear()
    finally:
        conn.close()

def save_practica_data(df_apps_kpis, df_correlacion, ciclo_escolar=None):
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        df_apps_save = df_apps_kpis.copy()
        df_apps_save["ciclo_escolar"] = ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_apps_kpis'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM practica_apps_kpis WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo, ciclo))
        df_apps_save.to_sql("practica_apps_kpis", conn, if_exists="append", index=False)

        df_corr_save = df_correlacion.copy()
        df_corr_save["ciclo_escolar"] = ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_correlacion'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM practica_correlacion WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo, ciclo))
        df_corr_save.to_sql("practica_correlacion", conn, if_exists="append", index=False)
        st.cache_data.clear()
    finally:
        conn.close()

def save_practica_docente_data(campus: str, df: pd.DataFrame, ciclo_escolar=None):
    if df is None or df.empty:
        return
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        df_save = df.copy()
        df_save["ciclo_escolar"] = ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_docente_data'")
        if cursor.fetchone():
            if campus != "Global":
                cursor.execute("DELETE FROM practica_docente_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))
            else:
                cursor.execute("DELETE FROM practica_docente_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo, ciclo))
            conn.commit()
        df_save.to_sql("practica_docente_data", conn, if_exists="append", index=False)
        username = st.session_state.get("username", "Sistema") if "username" in st.session_state else "Sistema"
        log_audit_event(username, "CARGA_PRACTICA_DOCENTE", f"Guardados {len(df)} registros ({ciclo})", campus)
        st.cache_data.clear()
    finally:
        conn.close()

def save_preescolar_data(campus: str, df: pd.DataFrame, ciclo_escolar=None):
    if df is None or df.empty:
        return
    ciclo = ciclo_escolar or st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        df_save = df.copy()
        df_save["ciclo_escolar"] = ciclo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='preescolar_qualitative_data'")
        if cursor.fetchone():
            if campus != "Global":
                cursor.execute("DELETE FROM preescolar_qualitative_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", (campus, ciclo, ciclo))
            else:
                cursor.execute("DELETE FROM preescolar_qualitative_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", (ciclo, ciclo))
            conn.commit()
        df_save.to_sql("preescolar_qualitative_data", conn, if_exists="append", index=False)
        st.cache_data.clear()
    finally:
        conn.close()

def load_preescolar_data(campus: str = None, ciclo_escolar: str = None) -> pd.DataFrame:
    if ciclo_escolar is None:
        ciclo_escolar = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    ensure_schema_has_ciclo_escolar()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='preescolar_qualitative_data'")
        if not cursor.fetchone():
            return pd.DataFrame()
        if campus and campus != "Global":
            return pd.read_sql_query(
                "SELECT * FROM preescolar_qualitative_data WHERE campus = ? AND (ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026'))", 
                conn, params=(campus, ciclo_escolar, ciclo_escolar)
            )
        return pd.read_sql_query(
            "SELECT * FROM preescolar_qualitative_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", 
            conn, params=(ciclo_escolar, ciclo_escolar)
        )
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

# --- Funciones de Carga Inteligente de Vistas ---

@st.cache_data
def load_global_data(ciclo_escolar: str = "2025 - 2026"):
    """Carga los promedios globales de asistencia y dominio desde la base de datos para el ciclo escolar especificado."""
    df_asistencia = pd.DataFrame(columns=["campus", "asistencia"])
    df_academico = pd.DataFrame(columns=["campus", "dominio"])
    df_asistencia_prev = pd.DataFrame(columns=["campus", "asistencia"])
    df_academico_prev = pd.DataFrame(columns=["campus", "dominio"])

    if os.path.exists(DB_PATH):
        try:
            ensure_schema_has_ciclo_escolar()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            rows_ast = []
            for c in ["Misiones", "Nuevo Sur", "San Agustín"]:
                st_data = reconstruct_attendance_state(c, ciclo_escolar)
                if st_data and "niveles" in st_data and isinstance(st_data["niveles"], pd.DataFrame) and not st_data["niveles"].empty:
                    mean_a = st_data["niveles"]["Asistencia"].mean()
                    if pd.notna(mean_a) and mean_a > 0:
                        rows_ast.append({"campus": c, "asistencia": float(mean_a)})
            if rows_ast:
                df_asistencia = pd.DataFrame(rows_ast)
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_data'")
                if cursor.fetchone():
                    df_att = pd.read_sql("SELECT campus, Asistencia FROM attendance_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                    if not df_att.empty:
                        df_att_grouped = df_att.groupby("campus")["Asistencia"].mean().reset_index()
                        df_asistencia = df_att_grouped.rename(columns={"Asistencia": "asistencia"})

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
            if cursor.fetchone():
                df_acad_all = pd.read_sql("SELECT campus, bimestre, [Language Arts], [Matemáticas], [Español] FROM academic_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                if not df_acad_all.empty:
                    rows = []
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
                        rows.append({"campus": campus, "dominio": mean_grade / 10.0})
                    df_academico = pd.DataFrame(rows)
            conn.close()
        except Exception:
            pass

    return df_asistencia, df_academico, df_asistencia_prev, df_academico_prev

def obtener_datos_por_ciclo(ciclo: str, df_ast_25_26, df_aca_25_26, df_ast_24_25, df_aca_24_25):
    """Carga y retorna dinámicamente los dataframes de asistencia y académico según el ciclo escolar activo."""
    if not ciclo:
        ciclo = "2025 - 2026"
    df_ast, df_aca, df_ast_prev, df_aca_prev = load_global_data(ciclo)
    return df_ast, df_aca, df_ast_prev, df_aca_prev

@st.cache_data
def load_apps_data(ciclo_escolar: str = "2025 - 2026"):
    df_apps_kpis = pd.DataFrame(columns=['campus', 'Plataforma', 'Uso Efectivo (%)'])
    df_correlacion = pd.DataFrame(columns=["campus", "Grupo", "Plataforma", "Práctica (%)", "Resultado (%)"])

    if os.path.exists(DB_PATH):
        try:
            ensure_schema_has_ciclo_escolar()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_apps_kpis'")
            if cursor.fetchone():
                df_real_kpis = pd.read_sql("SELECT * FROM practica_apps_kpis WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                if not df_real_kpis.empty:
                    df_apps_kpis = df_real_kpis
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practica_correlacion'")
            if cursor.fetchone():
                df_real_corr = pd.read_sql("SELECT * FROM practica_correlacion WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                if not df_real_corr.empty:
                    df_correlacion = df_real_corr
            conn.close()
        except Exception:
            pass

    return df_apps_kpis, df_correlacion

@st.cache_data
def load_academico_bloques(ciclo_escolar: str = "2025 - 2026"):
    empty_df = pd.DataFrame(columns=["campus", "Bloque", "Matemáticas", "Español", "Language Arts"])

    if os.path.exists(DB_PATH):
        try:
            ensure_schema_has_ciclo_escolar()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_data'")
            if cursor.fetchone():
                df_real = pd.read_sql("SELECT campus, bimestre as Bloque, [Language Arts], [Matemáticas], [Español] FROM academic_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                if not df_real.empty:
                    df_real_grouped = df_real.groupby(["campus", "Bloque"]).mean().reset_index()
                    df_real_grouped["Matemáticas"] = df_real_grouped["Matemáticas"] / 10.0
                    df_real_grouped["Español"] = df_real_grouped["Español"] / 10.0
                    df_real_grouped["Language Arts"] = df_real_grouped["Language Arts"] / 10.0

                    df_real_grouped['sort_order'] = df_real_grouped['Bloque'].apply(
                        lambda b: int(str(b)[1:]) if str(b).startswith('B') and str(b)[1:].isdigit() else 99
                    )
                    df_combined = df_real_grouped.sort_values(['campus', 'sort_order']).drop(columns=['sort_order'])
                    conn.close()
                    return df_combined
            conn.close()
        except Exception:
            pass

    return empty_df

@st.cache_data
def load_clima_heatmap(ciclo_escolar: str = "2025 - 2026"):
    df = pd.DataFrame(columns=["campus", "Categoría", "Respuesta", "Proporción"])

    if os.path.exists(DB_PATH):
        try:
            ensure_schema_has_ciclo_escolar()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clima_data'")
            if cursor.fetchone():
                df_real = pd.read_sql("SELECT * FROM clima_data WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                if not df_real.empty:
                    df = df_real
            conn.close()
        except Exception:
            pass

    return df

@st.cache_data
def load_disciplina_data(ciclo_escolar: str = "2025 - 2026"):
    df_casos = pd.DataFrame(columns=["campus", "Violencia Escolar", "Faltas Graves", "Apatía Severa"])
    df_cartas = pd.DataFrame(columns=["campus", "Firmadas", "Pendientes"])

    if os.path.exists(DB_PATH):
        try:
            ensure_schema_has_ciclo_escolar()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_casos'")
            if cursor.fetchone():
                df_real_casos = pd.read_sql("SELECT * FROM disciplina_casos WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                if not df_real_casos.empty:
                    df_casos = df_real_casos
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disciplina_cartas'")
            if cursor.fetchone():
                df_real_cartas = pd.read_sql("SELECT * FROM disciplina_cartas WHERE ciclo_escolar = ? OR (ciclo_escolar IS NULL AND ? = '2025 - 2026')", conn, params=(ciclo_escolar, ciclo_escolar))
                if not df_real_cartas.empty:
                    df_cartas = df_real_cartas
            conn.close()
        except Exception:
            pass

    return df_casos, df_cartas

def save_ixl_diagnostics_data(campus: str, df: pd.DataFrame):
    """Guarda y consolida el diagnóstico IXL por campus y ciclo escolar en SQLite."""
    if df is None or df.empty or not campus:
        return
    ciclo = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ixl_diagnostics'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE ixl_diagnostics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campus TEXT,
                    ciclo_escolar TEXT,
                    Grade TEXT,
                    Overall_percentile REAL,
                    Overall_tier TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        else:
            try:
                cursor.execute("ALTER TABLE ixl_diagnostics ADD COLUMN ciclo_escolar TEXT")
                conn.commit()
            except Exception:
                pass
            
        cursor.execute("DELETE FROM ixl_diagnostics WHERE campus = ? AND (ciclo_escolar = ? OR ciclo_escolar IS NULL)", (campus, ciclo))
        conn.commit()
        
        df_save = df.copy()
        df_save["campus"] = campus
        df_save["ciclo_escolar"] = ciclo
        if "Overall percentile" in df_save.columns:
            df_save["Overall_percentile"] = df_save["Overall percentile"]
        elif "Percentile" in df_save.columns:
            df_save["Overall_percentile"] = df_save["Percentile"]
            
        if "Overall tier" in df_save.columns:
            df_save["Overall_tier"] = df_save["Overall tier"]
            
        cols_to_keep = [c for c in ["campus", "ciclo_escolar", "Grade", "Overall_percentile", "Overall_tier"] if c in df_save.columns]
        df_save[cols_to_keep].to_sql("ixl_diagnostics", conn, if_exists="append", index=False)
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def save_progrentis_data(campus: str, df: pd.DataFrame):
    """Guarda datos de uso de Progrentis por campus y ciclo escolar en SQLite."""
    if df is None or df.empty or not campus:
        return
    ciclo = st.session_state.get("ciclo_escolar_activo", "2025 - 2026")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='progrentis_data'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE progrentis_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campus TEXT,
                    ciclo_escolar TEXT,
                    Alumno TEXT,
                    Matricula TEXT,
                    Nivel TEXT,
                    IPD_Ini REAL,
                    IPD_Actual REAL,
                    Mejora_Pct REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        else:
            try:
                cursor.execute("ALTER TABLE progrentis_data ADD COLUMN ciclo_escolar TEXT")
                conn.commit()
            except Exception:
                pass
            
        cursor.execute("DELETE FROM progrentis_data WHERE campus = ? AND (ciclo_escolar = ? OR ciclo_escolar IS NULL)", (campus, ciclo))
        conn.commit()
        
        df_save = df.copy()
        df_save["campus"] = campus
        df_save["ciclo_escolar"] = ciclo
        cols_to_keep = [c for c in ["campus", "ciclo_escolar", "Alumno", "Matricula", "Nivel", "IPD_Ini", "IPD_Actual", "Mejora_Pct"] if c in df_save.columns]
        df_save[cols_to_keep].to_sql("progrentis_data", conn, if_exists="append", index=False)
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def reset_all_system_data():
    """
    Elimina completamente todos los datos almacenados en SQLite y en st.session_state.
    Restablece la aplicación a su estado inicial en blanco.
    """
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            tables = [
                "academic_data", "attendance_data", "normalized_attendance", 
                "resumen_diario_nivel", "clima_data", "disciplina_casos", 
                "disciplina_cartas", "practica_apps_kpis", "practica_correlacion", 
                "audit_logs", "ixl_diagnostics", "progrentis_data", "practica_docente_data"
            ]
            for t in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {t}")
            conn.commit()
            conn.close()
        except Exception:
            pass
            
    init_audit_table()
    init_attendance_tables()

    keys_to_keep = {"authenticated", "username", "user_name", "user_role", "user_email"}
    keys_to_delete = [k for k in st.session_state if k not in keys_to_keep]
    for k in keys_to_delete:
        del st.session_state[k]
        
    st.cache_data.clear()

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