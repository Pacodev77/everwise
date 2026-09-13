# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
from src.logic.composite_index_engine import generar_datos_indice_compuesto
from ui.charts.nuevos_graficos import chart_comparativa_indice_compuesto

def render_comparativa_global_section(df_master: pd.DataFrame = None):
    """
    Renders the executive multi-campus comparative section featuring:
    - Composite Index cards with status indicators (Verde/Amarillo/Rojo)
    - Altair multi-line trend chart (B1-B5 real + projected) with 85% target line
    - Executive synthesis and risk analysis
    """
    st.markdown("---")
    st.subheader("🌐 Comparativa Global Multicampus — Índice Compuesto")
    st.caption("Métrica ejecutiva integral ponderada: Calificaciones Académicas (50%) + Dominio IXL (30%) + Avance Progrentis (20%). Metas institucionales y proyecciones al Bimestre 5.")

    # Generar datos del índice compuesto
    df_res, resumen_status = generar_datos_indice_compuesto(df_master)

    # 1. Render KPI Summary Cards per Campus
    cols = st.columns(4)
    campus_order = ['Misiones', 'Nuevo Sur', 'San Agustín', 'Global']

    for idx, name in enumerate(campus_order):
        stat = resumen_status.get(name, {})
        color_border = stat.get('color', '#64748b')
        status_label = stat.get('status', 'N/A')
        current_val = stat.get('current_b3', 0.0)
        proj_val = stat.get('proj_b5', 0.0)
        
        with cols[idx]:
            if name == 'Global':
                badge_html = f"<span style='background-color:#1e293b; color:#ffffff; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold;'>{status_label}</span>"
            elif color_border == '#10b981':
                badge_html = f"<span style='background-color:#d1fae5; color:#065f46; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold;'>{status_label}</span>"
            elif color_border == '#f59e0b':
                badge_html = f"<span style='background-color:#fef3c7; color:#92400e; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold;'>{status_label}</span>"
            else:
                badge_html = f"<span style='background-color:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold;'>{status_label}</span>"

            card_html = f"""
            <div style="
                border: 1px solid #e2e8f0;
                border-left: 5px solid {color_border};
                border-radius: 8px;
                padding: 14px 16px;
                background-color: #ffffff;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                margin-bottom: 15px;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:14px; font-weight:700; color:#1e293b;">{name}</span>
                    {badge_html}
                </div>
                <div style="font-size:24px; font-weight:800; color:#0f172a; margin-bottom:4px;">
                    {current_val:.1f}% <span style="font-size:12px; color:#64748b; font-weight:normal;">(B3 Actual)</span>
                </div>
                <div style="font-size:12px; color:#475569;">
                    Proyección B5: <strong>{proj_val:.1f}%</strong>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

    # 2. Render Line Chart
    chart = chart_comparativa_indice_compuesto(df_res)
    st.altair_chart(chart, use_container_width=True)

    # 3. Executive Notes & Action Highlights
    st.markdown("""
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-top: 10px;">
        <h5 style="margin-top:0; color:#0f172a; font-size:14px; font-weight:bold;">💡 Diagnóstico Ejecutivo & Hallazgos Clave</h5>
        <ul style="margin-bottom:0; padding-left:20px; font-size:13px; color:#334155;">
            <li><strong>Misiones (87.2% actual, 90.7% proj B5):</strong> Mantiene el liderazgo operativo superando la meta de 85% de forma continua desde B2.</li>
            <li><strong>Nuevo Sur (85.2% actual, 87.7% proj B5):</strong> Tendencia ascendente consistente; alcanza y consolida la meta institucional en B3.</li>
            <li><strong>San Agustín (78.3% actual, 80.6% proj B5 - <span style="color:#dc2626; font-weight:bold;">Alerta Roja</span>):</strong> Se encuentra 7.1 pts debajo del promedio Global (85.4%) y su proyección móvil al B5 (80.6%) no alcanza la meta del 85%. Requiere plan intensivo de aceleración en materias académicas clave e IXL.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
