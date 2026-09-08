# tests/test_normalizacion.py

import os
import pandas as pd
from src.logic.normalizar_asistencia import procesar_archivo_asistencia

# Fixtures mapping to real downloaded files
FIXTURES = {
    "Nuevo_Sur_Detalle": "/Users/pacodev/Downloads/Detalle de asistencias Nuevo Sur 08 Oct - 05 Nov 2025.xlsx",
    "San_Agustin_Asistencia": "/Users/pacodev/Downloads/Asistencia San Agustin 12 enero - 20 feb.xlsx",
    "Misiones_Asistencia": "/Users/pacodev/Downloads/Asistencia Misiones 12 ene- 20 feb.xlsx",
    "Misiones_Detalle": "/Users/pacodev/Downloads/Detalle Misiones 6 Nov 19 dic.xlsx",
    "Nuevo_Sur_Retardos": "/Users/pacodev/Downloads/Retardos Nuevo Sur 12 enero 20 feb.xlsx"
}

def verify_file_exists(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fixture file not found: {path}")

def test_nuevo_sur_detalle_firma_b():
    path = FIXTURES["Nuevo_Sur_Detalle"]
    verify_file_exists(path)
    
    df_canon, reporte = procesar_archivo_asistencia(path, "Nuevo Sur")
    
    # Debe ser Firma B (resúmenes pre-agregados), por lo que df_canonico debe estar vacío
    assert df_canon.empty
    assert reporte["status"] == "success"
    
    # Debe haber procesado dos hojas
    assert len(reporte["hojas_procesadas"]) == 2
    for h in reporte["hojas_procesadas"]:
        assert h["firma"] == "Firma B"
        
    df_res = reporte["resumen_diario_nivel"]
    assert not df_res.empty
    # Verificar columnas del resumen diario
    for col in ['campus', 'fecha', 'segmento', 'nivel', 'presentes', 'total', 'tasa_asistencia']:
        assert col in df_res.columns
    assert (df_res['campus'] == "Nuevo Sur").all()

def test_san_agustin_asistencia_firma_a():
    path = FIXTURES["San_Agustin_Asistencia"]
    verify_file_exists(path)
    
    df_canon, reporte = procesar_archivo_asistencia(path, "San Agustín")
    
    # Debe ser Firma A (logs de checada)
    assert not df_canon.empty
    assert reporte["status"] in ["success", "warning"]
    
    # Verificar columnas canónicas
    expected_cols = [
        'campus', 'tipo_persona', 'matricula', 'nombre', 'apellidos', 
        'nivel_normalizado', 'grado_grupo', 'fecha', 'hora_entrada', 
        'hora_salida', 'estatus', 'campus_ciclo', 'fuente_archivo', 'fuente_hoja'
    ]
    for col in expected_cols:
        assert col in df_canon.columns
        
    # Verificar que el campus sea el correcto
    assert (df_canon['campus'] == "San Agustín").all()
    
    # Debe haber procesado Alumnos y Colaboradores como Firma A
    firmas = reporte["firmas_detectadas"]
    assert firmas["Alumnos"] == "Firma A"
    assert firmas["Colaboradores"] == "Firma A"
    # Otras hojas deben ser ignoradas o marcadas como Unknown
    assert firmas["Retardos"] == "Unknown"
    assert firmas["Pivot Table 1"] == "Unknown"

def test_misiones_asistencia_firma_a():
    path = FIXTURES["Misiones_Asistencia"]
    verify_file_exists(path)
    
    df_canon, reporte = procesar_archivo_asistencia(path, "Misiones")
    
    assert not df_canon.empty
    assert (df_canon['campus'] == "Misiones").all()
    
    firmas = reporte["firmas_detectadas"]
    assert firmas["Sheet0"] == "Firma A"
    assert firmas["Colaboradores"] == "Firma A"
    assert firmas["Detail3-Preescolar-18022026"] == "Firma A"
    
    # Comprobar niveles normalizados
    alumnos = df_canon[df_canon['tipo_persona'] == 'alumno']
    if not alumnos.empty:
        # Los niveles normales deben ser Preescolar, Primaria, Secundaria
        niveles_validos = ['Preescolar', 'Primaria', 'Secundaria', 'SIN_MAPEAR']
        for lvl in alumnos['nivel_normalizado'].unique():
            assert lvl in niveles_validos

def test_misiones_detalle_firma_a():
    path = FIXTURES["Misiones_Detalle"]
    verify_file_exists(path)
    
    df_canon, reporte = procesar_archivo_asistencia(path, "Misiones")
    
    assert not df_canon.empty
    assert (df_canon['campus'] == "Misiones").all()
    
    firmas = reporte["firmas_detectadas"]
    assert firmas["Sheet0"] == "Firma A"
    assert firmas["Copy of Sheet0"] == "Firma A"

def test_nuevo_sur_retardos_firma_c():
    path = FIXTURES["Nuevo_Sur_Retardos"]
    verify_file_exists(path)
    
    df_canon, reporte = procesar_archivo_asistencia(path, "Nuevo Sur")
    
    # Debe ser Firma C (estatus por persona/día)
    assert not df_canon.empty
    assert (df_canon['campus'] == "Nuevo Sur").all()
    
    firmas = reporte["firmas_detectadas"]
    assert firmas["Sheet0"] == "Firma C"
    
    # Debe contener estatus como Falta y Presente y Retardo
    estatus_unicos = df_canon['estatus'].unique()
    for est in estatus_unicos:
        assert est in ['Presente', 'Retardo', 'Falta']
    assert 'Falta' in estatus_unicos
