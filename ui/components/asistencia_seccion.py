import streamlit as st
import pandas as pd
import altair as alt
from ui.components.asistencia_uploader import render_asistencia_uploader

def render_asistencia_section(sede_actual, real_data=None, mostrar_uploader=False):
    """
    Renderiza un desglose detallado de asistencia para alumnos (por nivel) y Staff.
    Soporta ingestión de datos reales del Motor de Inteligencia (real_data).
    Renderiza un desglose detallado de asistencia para alumnos (por nivel) y Staff.
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
    
    # Datos de asistencia de alumnos
    if real_data is not None:
        # Inyectando Real Data proveniente de src/logic/asistencia_engine.py
        df_data = real_data["niveles"]
        staff_asis = real_data["staff"]
    else:
        # --- MOCK DATA FALLBACK ---
        if sede_actual == "Global":
            niveles = [
                {"Nivel": "Misiones", "Asistencia": 0.89, "Distribución": 0.333},
                {"Nivel": "Nuevo Sur", "Asistencia": 0.94, "Distribución": 0.333},
                {"Nivel": "San Agustín", "Asistencia": 0.91, "Distribución": 0.334}
            ]
            staff_asis = 0.92
        else:
            niveles = [
                {"Nivel": "Preescolar", "Asistencia": base_asis + 0.04, "Distribución": 0.414},
                {"Nivel": "Primaria", "Asistencia": base_asis - 0.02, "Distribución": 0.264},
                {"Nivel": "Secundaria", "Asistencia": base_asis - 0.08, "Distribución": 0.322}
            ]
            staff_asis = base_asis + 0.05 
            if staff_asis > 0.99: staff_asis = 0.99
        df_data = pd.DataFrame(niveles)
    
    # Lógica Dinámica de Semáforo basada en rendimiento
    def get_color(val):
        if val >= 0.90: return '#4ade80' # Verde (Bien)
        elif val >= 0.83: return '#fbbf24' # Amarillo (Regular / Medio)
        else: return '#f87171' # Rojo (Muy por debajo)
        
    df_data['Color'] = df_data['Asistencia'].apply(get_color)
    
    # Etiqueta combinada para mostrar el porcentaje debajo del nivel en el eje X
    df_data['Nivel_Etiqueta'] = df_data.apply(lambda r: f"{r['Nivel']}   {r['Asistencia']*100:.2f}%", axis=1)
    
    # Construcción de escala dinámica
    domain_niveles = df_data['Nivel'].tolist()
    range_colores = df_data['Color'].tolist()
    color_scale = alt.Scale(domain=domain_niveles, range=range_colores)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("**Asistencia por Segmento**")
        chart_niveles = alt.Chart(df_data).mark_bar(
            cornerRadiusTopLeft=6, 
            cornerRadiusTopRight=6,
            size=75  # Barras mucho más gruesas
        ).encode(
            x=alt.X('Nivel_Etiqueta:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12)),
            y=alt.Y('Asistencia:Q', title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format='%', grid=True)),
            color=alt.Color('Nivel:N', scale=color_scale, legend=alt.Legend(title="Segmentos", orient="top")),
            tooltip=[alt.Tooltip('Nivel:N'), alt.Tooltip('Asistencia:Q', format='.2%', title='Puntaje')]
        ).properties(height=260).configure_view(stroke='transparent')
        st.altair_chart(chart_niveles, use_container_width=True)
        
    with col2:
        st.markdown("**Distribución de Asistencia**")
        base_donut = alt.Chart(df_data).encode(
            theta=alt.Theta(field="Asistencia", type="quantitative", stack=True),
            color=alt.Color(field="Nivel", type="nominal", scale=color_scale, legend=alt.Legend(title="Segmentos", orient="right")),
            tooltip=[alt.Tooltip('Nivel:N'), alt.Tooltip('Asistencia:Q', title='Asistencia', format='.1%')]
        )
        # Reduciendo el grosor un 20-30% haciéndolo más estético
        donut = base_donut.mark_arc(innerRadius=65, outerRadius=95, stroke="#ffffff", strokeWidth=3.5).properties(height=260)
        
        # Números de porcentaje ultra-visibles, dentro del color
        text_pie = base_donut.mark_text(radius=80, size=15, color='#0f172a', fontWeight='bold').encode(
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
    
    st.info("**Monitor Operativo:** La asistencia de la plantilla laboral se audita de forma independiente para medir operabilidad.")
    
    k1, k2 = st.columns([1, 2])
    with k1:
        st.metric(
            label="Asistencia Staff Promedio", 
            value=f"{staff_asis*100:.1f}%", 
            delta="Parámetro Óptimo" if staff_asis >= 0.9 else "Atención Requerida", 
            delta_color="normal"
        )
    with k2:
        df_staff = pd.DataFrame([{"Rol": "Plantilla Laboral", "Valor": staff_asis}])
        chart_staff = alt.Chart(df_staff).mark_bar(
            cornerRadius=4, 
            color="#8b5cf6", # Morado distintivo para separar visualmente del semáforo de alumnos
            size=30
        ).encode(
            x=alt.X('Valor:Q', scale=alt.Scale(domain=[0, 1]), title=None, axis=alt.Axis(format='%')),
            y=alt.Y('Rol:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
            tooltip=[alt.Tooltip('Valor:Q', format='.1%', title='Operatividad')]
        ).properties(height=70).configure_view(stroke='transparent')
        st.altair_chart(chart_staff, use_container_width=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
