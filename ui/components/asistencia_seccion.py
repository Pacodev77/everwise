# ui/components/asistencia_seccion.py

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore [missing-import]
import altair as alt
from ui.components.asistencia_uploader import render_asistencia_uploader

def render_asistencia_section(sede_actual, real_data=None, mostrar_uploader=False):
    """
    Renderiza un desglose detallado de asistencia para alumnos (por nivel) y Staff.
    Soporta ingestión de datos reales del Motor de Inteligencia (real_data).
    Diseño adaptado para mantener estética ejecutiva.
    """
    st.markdown("---")
    
    if mostrar_uploader:
        data_from_uploader = render_asistencia_uploader(sede_actual)
        if data_from_uploader is not None:
            real_data = data_from_uploader
            
    st.markdown("### Asistencia y Participación")
    
    # --- MOCK DATA ---
    base_asis = 0.88
    if sede_actual == "Misiones": base_asis = 0.89
    elif sede_actual == "Nuevo Sur": base_asis = 0.91
    elif sede_actual == "San Agustín": base_asis = 0.93
    
    staff_desglose = None
    dias_alumnos = None
    dias_staff = None
    
    # Datos de asistencia de alumnos
    if real_data is not None and "niveles" in real_data and not real_data["niveles"].empty:
        # Inyectando Real Data proveniente de src/logic/asistencia_engine.py
        df_data = real_data["niveles"]
        staff_asis = real_data.get("staff", 0.0)
        staff_desglose = real_data.get("staff_desglose")
        dias_alumnos = real_data.get("dias_alumnos")
        dias_staff = real_data.get("dias_staff")
    else:
        st.info("Sin datos de asistencia registrados aún. Por favor suba un reporte de asistencia.")
        return
        
    # Badges informativos si hay datos de días registrados
    if dias_alumnos is not None or dias_staff is not None:
        info_tags = []
        if dias_alumnos is not None and dias_alumnos > 0:
            info_tags.append(f"**Días Alumnos:** {int(dias_alumnos)} días")
        if dias_staff is not None and dias_staff > 0:
            info_tags.append(f"**Días Colaboradores:** {int(dias_staff)} días")
        if info_tags:
            st.caption(" · ".join(info_tags))
    
    # Mapa de Colores Ejecutivos por Segmento (Campus y Niveles Educativos)
    COLOR_MAP_EJECUTIVO = {
        "Misiones": "#38bdf8",       # Azul Cielo / Cyan
        "Nuevo Sur": "#6366f1",      # Índigo / Violeta
        "San Agustín": "#10b981",    # Verde Esmeralda
        "Preescolar": "#10b981",     # Verde Esmeralda
        "Primaria": "#0284c7",       # Azul Corporativo
        "Secundaria": "#6366f1",     # Índigo
        "Staff General": "#8b5cf6",  # Púrpura Ejecutiva
        "Administrativo": "#14b8a6",  # Teal
    }
    
    FALLBACK_PALETTE = ["#38bdf8", "#6366f1", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]

    def assign_segment_color(idx, row):
        nivel_key = str(row['Nivel']).strip()
        if nivel_key in COLOR_MAP_EJECUTIVO:
            return COLOR_MAP_EJECUTIVO[nivel_key]
        return FALLBACK_PALETTE[idx % len(FALLBACK_PALETTE)]

    df_data['Color'] = [assign_segment_color(i, r) for i, r in df_data.iterrows()]
    df_data['Asistencia_Pct'] = df_data['Asistencia'].apply(lambda r: f"{r*100:.2f}%")
    
    # Construcción de escala dinámica
    domain_niveles = df_data['Nivel'].tolist()
    range_colores = df_data['Color'].tolist()
    color_scale = alt.Scale(domain=domain_niveles, range=range_colores)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("**Asistencia por Segmento**")
        bars = alt.Chart(df_data).mark_bar(
            cornerRadiusTopLeft=6, 
            cornerRadiusTopRight=6,
            size=65  # Barras estilizadas
        ).encode(
            x=alt.X('Nivel:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight='bold')),
            y=alt.Y('Asistencia:Q', title=None, scale=alt.Scale(domain=[0, 1.08]), axis=alt.Axis(format='%', grid=True)),
            color=alt.Color('Nivel:N', scale=color_scale, legend=alt.Legend(title="Segmentos", orient="top")),
            tooltip=[alt.Tooltip('Nivel:N', title='Segmento'), alt.Tooltip('Asistencia:Q', format='.2%', title='Asistencia')]
        )
        
        text_bar = alt.Chart(df_data).mark_text(
            align='center',
            baseline='bottom',
            dy=-6,
            fontSize=11,
            fontWeight='bold',
            color='#0f172a'
        ).encode(
            x=alt.X('Nivel:N'),
            y=alt.Y('Asistencia:Q'),
            text=alt.Text('Asistencia_Pct:N')
        )
        
        chart_niveles = (bars + text_bar).properties(height=260).configure_view(stroke='transparent')
        st.altair_chart(chart_niveles, use_container_width=True)
        
    with col2:
        st.markdown("**Distribución de Asistencia**")
        base_donut = alt.Chart(df_data).encode(
            theta=alt.Theta(field="Asistencia", type="quantitative", stack=True),
            color=alt.Color(field="Nivel", type="nominal", scale=color_scale, legend=alt.Legend(title="Segmentos", orient="right")),
            tooltip=[alt.Tooltip('Nivel:N', title='Segmento'), alt.Tooltip('Asistencia:Q', title='Asistencia', format='.2%')]
        )
        # Reduciendo el grosor un 20-30% haciéndolo más estético
        donut = base_donut.mark_arc(innerRadius=65, outerRadius=95, stroke="#ffffff", strokeWidth=3.5).properties(height=260)
        
        # Números de porcentaje ultra-visibles, dentro del color
        text_pie = base_donut.mark_text(radius=80, size=14, color='#ffffff', fontWeight='bold').encode(
            text=alt.Text(field='Asistencia', type='quantitative', format='.0%')
        )
        
        # Texto central "Asistencia" 
        text_center = alt.Chart(pd.DataFrame({'t': ['Asistencia']})).mark_text(
            size=18, fontWeight='normal', color='#475569'
        ).encode(text='t:N')
        
        st.altair_chart((donut + text_pie + text_center).configure_view(stroke='transparent'), use_container_width=True)
        
    st.markdown("---")
    
    # STAFF / DOCENTES (Separado y diferenciado para cumplir requisito)
    st.markdown("**Personal Docente y Staff**")
    st.info("**Monitor Operativo:** La asistencia de la plantilla laboral se audita por nivel y área funcional para garantizar la operatividad de los campus.")
    
    # Normalizar desglose de staff y mapear cualquier clave extraña
    cleaned_staff_desglose = {}
    if staff_desglose:
        for k, v in staff_desglose.items():
            k_str = str(k).strip()
            if k_str.upper() in ["SIN_MAPEAR", "NONE", "NAN", "", "UNKNOWN"]:
                k_str = "Staff General"
            cleaned_staff_desglose[k_str] = float(v)
            
    # Si no hay desglose por niveles o solo hay 1 item generico, crear áreas representativas si es necesario
    if not cleaned_staff_desglose:
        val_base = staff_asis if staff_asis > 0 else 0.95
        cleaned_staff_desglose = {
            "Staff General": val_base
        }
        
    df_staff_breakdown = pd.DataFrame([
        {"Área": k, "Asistencia": v} for k, v in cleaned_staff_desglose.items()
    ])
    
    # Mapa de colores ejecutivos por nivel / departamento
    COLOR_MAP_STAFF = {
        "Preescolar": "#10b981",       # Esmeralda
        "Primaria": "#0284c7",         # Azul Cielo
        "Secundaria": "#6366f1",       # Índigo
        "Staff General": "#8b5cf6",    # Púrpura Ejecutiva
        "Administrativo": "#14b8a6",    # Teal
        "Docentes": "#ec4899"          # Rosa / Magenta
    }
    
    def assign_color(row):
        area = row["Área"]
        if area in COLOR_MAP_STAFF:
            return COLOR_MAP_STAFF[area]
        val = row["Asistencia"]
        if val >= 0.90: return '#10b981'
        elif val >= 0.83: return '#f59e0b'
        else: return '#ef4444'

    df_staff_breakdown["Color"] = df_staff_breakdown.apply(assign_color, axis=1)
    df_staff_breakdown["Asistencia_Pct"] = df_staff_breakdown["Asistencia"].apply(lambda x: f"{x*100:.1f}%")
    
    k1, k2 = st.columns([1, 2.5], gap="large")
    with k1:
        st.metric(
            label="Asistencia Staff Promedio", 
            value=f"{staff_asis*100:.1f}%", 
            delta="Parámetro Óptimo (≥90%)" if staff_asis >= 0.9 else "Atención Requerida (<90%)", 
            delta_color="normal"
        )

    with k2:
        st.markdown("**Desglose de Operatividad del Personal**")
        
        domain_areas = df_staff_breakdown['Área'].tolist()
        range_colors = df_staff_breakdown['Color'].tolist()
        scale_staff = alt.Scale(domain=domain_areas, range=range_colors)
        
        # Gráfica de Barras Horizontales con Color por Nivel y Labels Integrados
        bars = alt.Chart(df_staff_breakdown).mark_bar(
            cornerRadiusTopRight=6, 
            cornerRadiusBottomRight=6,
            height=28
        ).encode(
            x=alt.X('Asistencia:Q', scale=alt.Scale(domain=[0, 1.08]), title=None, axis=alt.Axis(format='%', grid=True)),
            y=alt.Y('Área:N', title=None, sort=None, axis=alt.Axis(labelFontSize=12, labelFontWeight='bold')),
            color=alt.Color('Área:N', scale=scale_staff, legend=None),
            tooltip=[alt.Tooltip('Área:N', title='Nivel/Área'), alt.Tooltip('Asistencia:Q', format='.2%', title='Asistencia Operativa')]
        )
        
        # Texto del Porcentaje directo sobre cada barra
        text_labels = alt.Chart(df_staff_breakdown).mark_text(
            align='left',
            baseline='middle',
            dx=8,
            fontSize=12,
            fontWeight='bold',
            color='#0f172a'
        ).encode(
            x=alt.X('Asistencia:Q'),
            y=alt.Y('Área:N', sort=None),
            text=alt.Text('Asistencia_Pct:N')
        )
        
        # Línea de Referencia / Meta (90%)
        rule_meta = alt.Chart(pd.DataFrame({'meta': [0.90]})).mark_rule(
            strokeDash=[4, 4],
            color='#94a3b8',
            strokeWidth=2
        ).encode(x='meta:Q')
        
        chart_final_staff = (bars + text_labels + rule_meta).properties(
            height=max(160, len(df_staff_breakdown) * 48)
        ).configure_view(stroke='transparent')
        
        st.altair_chart(chart_final_staff, use_container_width=True)
        
    st.markdown("<br>", unsafe_allow_html=True)

