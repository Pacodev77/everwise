# pyrefly: ignore [missing-import]
import altair as alt
import pandas as pd

def chart_academico_bloques(df_acad: pd.DataFrame):
    """Gráfico de barras agrupadas comparativas por bloque."""
    value_vars = [col for col in ['Language Arts', 'Matemáticas', 'Español'] if col in df_acad.columns]
    df_melt = df_acad.melt(id_vars=['campus', 'Bloque'], value_vars=value_vars, 
                           var_name='Materia', value_name='Dominio')
    
    encoding_args = {
        'x': alt.X('Bloque:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=11)),
        'y': alt.Y('Dominio:Q', axis=alt.Axis(format="%"), title=None),
        'color': alt.Color('Bloque:N', scale=alt.Scale(
            domain=['B1', 'B2', 'B3', 'B4', 'B5'], 
            range=['#94a3b8', '#a78bfa', '#60a5fa', '#34d399', '#fb7185']
        ), legend=None),
        'row': alt.Row('Materia:N', header=alt.Header(title=None, labelOrient='top', labelFontSize=14, labelFontWeight='bold', labelPadding=10), sort=['Language Arts', 'Matemáticas', 'Español'])
    }
    if 'campus' in df_acad.columns and len(df_acad['campus'].unique()) > 1:
        encoding_args['column'] = alt.Column('campus:N', title=None, header=alt.Header(labelFontSize=14, labelFontWeight='bold'))
        
    chart = alt.Chart(df_melt).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(**encoding_args).properties(height=160).configure_view(stroke='transparent')
    
    return chart

def chart_clima_heatmap(df_clima: pd.DataFrame):
    """Heatmap de Clima Escolar ICE."""
    chart = alt.Chart(df_clima).mark_circle(stroke='white', strokeWidth=1).encode(
        x=alt.X('Respuesta:N', title='', sort=['Siempre', 'A veces', 'Nunca'], axis=alt.Axis(labelAngle=0, labelFontSize=12)),
        y=alt.Y('Categoría:N', title=None, axis=alt.Axis(labelFontSize=12)),
        size=alt.Size('Proporción:Q', scale=alt.Scale(range=[400, 3000]), legend=None),
        color=alt.Color('Proporción:Q', scale=alt.Scale(scheme='blues', domain=[0, 1]), legend=None),
        tooltip=[alt.Tooltip('Proporción:Q', format='.1%')]
    ).properties(width=150, height=320)
    
    text = chart.mark_text(baseline='middle', fontWeight='bold').encode(
        text=alt.Text('Proporción:Q', format='.0%'),
        color=alt.condition(
            alt.datum.Proporción > 0.4,
            alt.value('white'),
            alt.value('#1e293b')
        ),
        size=alt.value(12)
    )
    
    final_chart = chart + text
    if 'campus' in df_clima.columns and len(df_clima['campus'].unique()) > 1:
        return final_chart.facet(column=alt.Column('campus:N', title=None, header=alt.Header(labelFontSize=14, labelFontWeight='bold'))).configure_view(stroke='transparent')
    return final_chart.configure_view(stroke='transparent')

def chart_clima_barras(df_clima: pd.DataFrame):
    """Gráfico de barras horizontales apiladas para desglose de respuestas."""
    chart = alt.Chart(df_clima).mark_bar(cornerRadius=3).encode(
        y=alt.Y('Categoría:N', title=None),
        x=alt.X('Proporción:Q', title='Distribución', axis=alt.Axis(format='%')),
        color=alt.Color('Respuesta:N', 
                        scale=alt.Scale(domain=['Siempre', 'A veces', 'Nunca'], 
                                        range=['#3b82f6', '#94a3b8', '#e2e8f0'])),
        order=alt.Order('Respuesta_sort:Q'),
        tooltip=[alt.Tooltip('Categoría:N'), alt.Tooltip('Respuesta:N'), alt.Tooltip('Proporción:Q', format='.1%')]
    ).transform_calculate(
        Respuesta_sort="datum.Respuesta == 'Siempre' ? 1 : (datum.Respuesta == 'A veces' ? 2 : 3)"
    ).properties(height=180)
    
    if 'campus' in df_clima.columns and len(df_clima['campus'].unique()) > 1:
        return chart.facet(row=alt.Row('campus:N', title=None, header=alt.Header(labelFontSize=14, labelFontWeight='bold'))).configure_view(stroke='transparent')
    return chart.configure_view(stroke='transparent')

def chart_desempeno_nivel_barras(df_des: pd.DataFrame):
    """Gráfico ejecutivo horizontal de % en desempeño por nivel con espaciado y colores por nivel."""
    df_plot = df_des.copy()
    df_plot['pct_desempeno'] = df_plot['pct_desempeno'].astype(float)
    
    # Paleta distintiva y ejecutiva por Nivel
    color_map = {
        'Primaria': '#3b82f6',     # Azul Royal
        'Secundaria': '#8b5cf6',   # Púrpura / Índigo
        'Preescolar': '#10b981',   # Esmeralda
        'Preparatoria': '#f59e0b'  # Ámbar Cálido
    }
    df_plot['Color'] = df_plot['Nivel'].map(lambda n: color_map.get(str(n), '#64748b'))
    
    base = alt.Chart(df_plot).encode(
        y=alt.Y('Nivel:N', title=None, sort='-x', axis=alt.Axis(
            labelFontSize=13, 
            labelFontWeight='bold',
            labelPadding=10
        )),
        x=alt.X('pct_desempeno:Q', title='% Alumnos en Desempeño', scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(
            format='.0f',
            grid=True,
            gridDash=[3, 3],
            gridColor='#e2e8f0'
        )),
        tooltip=[
            alt.Tooltip('Nivel:N', title='Nivel'),
            alt.Tooltip('pct_desempeno:Q', format='.1f', title='% Desempeño'),
            alt.Tooltip('en_desempeno:Q', title='Alumnos en Desempeño'),
            alt.Tooltip('total:Q', title='Total Alumnos')
        ]
    )
    
    bars = base.mark_bar(
        cornerRadiusTopRight=6,
        cornerRadiusBottomRight=6,
        size=26
    ).encode(
        color=alt.Color('Color:N', scale=None)
    )
    
    text = base.mark_text(
        align='left',
        baseline='middle',
        dx=8,
        fontWeight='bold',
        fontSize=12,
        color='#0f172a'
    ).encode(
        text=alt.Text('pct_desempeno:Q', format='.1f')
    )
    
    calc_height = max(len(df_plot) * 60, 130)
    return (bars + text).properties(height=calc_height).configure_view(stroke='transparent')

def chart_promedios_materia_nivel(df_prom: pd.DataFrame):
    """Gráfico ejecutivo agrupado de promedios por materia y nivel con soporte insensible a mayúsculas/minúsculas."""
    df_norm = df_prom.copy()
    
    # Normalizar nombres de columnas tanto si vienen en minúsculas como mayúsculas
    col_map = {}
    for c in df_norm.columns:
        cl = str(c).lower().strip()
        if 'language' in cl or 'arts' in cl: col_map[c] = 'Language Arts'
        elif 'matem' in cl or 'math' in cl: col_map[c] = 'Matemáticas'
        elif 'espa' in cl or 'span' in cl: col_map[c] = 'Español'
    
    df_norm = df_norm.rename(columns=col_map)
    materias_cols = [c for c in ['Language Arts', 'Matemáticas', 'Español'] if c in df_norm.columns]
    
    df_melt = df_norm.melt(id_vars=['Nivel'], value_vars=materias_cols, var_name='Materia', value_name='Promedio')
    df_melt['Promedio'] = df_melt['Promedio'].astype(float)
    
    base = alt.Chart(df_melt).encode(
        x=alt.X('Nivel:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=13, labelFontWeight='bold', labelPadding=8)),
        xOffset=alt.XOffset('Materia:N', sort=['Language Arts', 'Matemáticas', 'Español']),
        y=alt.Y('Promedio:Q', title='Calificación Promedio (0-10)', scale=alt.Scale(domain=[0, 10]), axis=alt.Axis(
            grid=True,
            gridDash=[3, 3],
            gridColor='#e2e8f0'
        )),
        color=alt.Color('Materia:N', scale=alt.Scale(
            domain=['Language Arts', 'Matemáticas', 'Español'],
            range=['#6366f1', '#2563eb', '#10b981']
        ), legend=alt.Legend(title=None, orient='top', labelFontSize=12, symbolType='circle')),
        tooltip=[
            alt.Tooltip('Nivel:N', title='Nivel'),
            alt.Tooltip('Materia:N', title='Materia'),
            alt.Tooltip('Promedio:Q', format='.2f', title='Promedio')
        ]
    )
    
    bars = base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=28)
    text = base.mark_text(
        baseline='bottom',
        dy=-4,
        fontWeight='bold',
        fontSize=11,
        color='#0f172a'
    ).encode(
        text=alt.Text('Promedio:Q', format='.2f')
    )
    
    return (bars + text).properties(height=260).configure_view(stroke='transparent')
