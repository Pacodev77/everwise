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
        'Preescolar': '#10b981'    # Esmeralda
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

def chart_disciplina_casos(df_casos: pd.DataFrame):
    """Gráfico de barras ejecutivas para Radar de Casos Especiales."""
    value_vars = [c for c in ['Violencia Escolar', 'Faltas Graves', 'Apatía Severa'] if c in df_casos.columns]
    df_melt = df_casos.melt(id_vars=['campus'], value_vars=value_vars, var_name='Categoría', value_name='Casos')
    df_melt['Casos'] = df_melt['Casos'].astype(int)
    
    is_multi = len(df_melt['campus'].unique()) > 1
    
    if is_multi:
        base = alt.Chart(df_melt).encode(
            x=alt.X('campus:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight='bold')),
            xOffset=alt.XOffset('Categoría:N', sort=['Violencia Escolar', 'Faltas Graves', 'Apatía Severa']),
            y=alt.Y('Casos:Q', title='Número de Casos', axis=alt.Axis(grid=True, gridDash=[3, 3], gridColor='#e2e8f0')),
            color=alt.Color('Categoría:N', scale=alt.Scale(
                domain=['Violencia Escolar', 'Faltas Graves', 'Apatía Severa'],
                range=['#ef4444', '#f59e0b', '#6366f1']
            ), legend=alt.Legend(title=None, orient='top', labelFontSize=11)),
            tooltip=[alt.Tooltip('campus:N'), alt.Tooltip('Categoría:N'), alt.Tooltip('Casos:Q')]
        )
    else:
        base = alt.Chart(df_melt).encode(
            x=alt.X('Categoría:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight='bold'), sort=['Violencia Escolar', 'Faltas Graves', 'Apatía Severa']),
            y=alt.Y('Casos:Q', title='Número de Casos', axis=alt.Axis(grid=True, gridDash=[3, 3], gridColor='#e2e8f0')),
            color=alt.Color('Categoría:N', scale=alt.Scale(
                domain=['Violencia Escolar', 'Faltas Graves', 'Apatía Severa'],
                range=['#ef4444', '#f59e0b', '#6366f1']
            ), legend=None),
            tooltip=[alt.Tooltip('Categoría:N'), alt.Tooltip('Casos:Q')]
        )
        
    bars = base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=28 if not is_multi else 20)
    text = base.mark_text(baseline='bottom', dy=-4, fontWeight='bold', fontSize=12, color='#0f172a').encode(
        text=alt.Text('Casos:Q', format='d')
    )
    
    return (bars + text).properties(height=240).configure_view(stroke='transparent')

def chart_disciplina_cartas(df_cartas: pd.DataFrame):
    """Gráfico ejecutivo para Estatus de Cartas Compromiso (Firmadas vs Pendientes)."""
    value_vars = [c for c in ['Firmadas', 'Pendientes'] if c in df_cartas.columns]
    df_melt = df_cartas.melt(id_vars=['campus'], value_vars=value_vars, var_name='Estado', value_name='Cantidad')
    df_melt['Cantidad'] = df_melt['Cantidad'].astype(int)
    
    is_multi = len(df_melt['campus'].unique()) > 1
    
    if is_multi:
        base = alt.Chart(df_melt).encode(
            y=alt.Y('campus:N', title=None, axis=alt.Axis(labelFontSize=12, labelFontWeight='bold')),
            x=alt.X('Cantidad:Q', title='Total Cartas', axis=alt.Axis(grid=True, gridDash=[3, 3], gridColor='#e2e8f0')),
            color=alt.Color('Estado:N', scale=alt.Scale(
                domain=['Firmadas', 'Pendientes'],
                range=['#10b981', '#f43f5e']
            ), legend=alt.Legend(title=None, orient='top', labelFontSize=11)),
            tooltip=[alt.Tooltip('campus:N'), alt.Tooltip('Estado:N'), alt.Tooltip('Cantidad:Q')]
        )
        bars = base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, size=24)
        text = base.mark_text(align='left', dx=5, baseline='middle', fontWeight='bold', fontSize=11, color='#0f172a').encode(
            text=alt.Text('Cantidad:Q', format='d')
        )
        return (bars + text).properties(height=240).configure_view(stroke='transparent')
    else:
        base = alt.Chart(df_melt).encode(
            theta=alt.Theta('Cantidad:Q', stack=True),
            color=alt.Color('Estado:N', scale=alt.Scale(
                domain=['Firmadas', 'Pendientes'],
                range=['#10b981', '#f43f5e']
            ), legend=alt.Legend(title=None, orient='bottom', labelFontSize=11)),
            tooltip=[alt.Tooltip('Estado:N'), alt.Tooltip('Cantidad:Q')]
        )
        arc = base.mark_arc(innerRadius=45, outerRadius=75)
        text = base.mark_text(radius=60, fontWeight='bold', fontSize=13, color='white').encode(
            text=alt.Text('Cantidad:Q', format='d')
        )
        return (arc + text).properties(height=240).configure_view(stroke='transparent')

def chart_comparativa_indice_compuesto(df_res: pd.DataFrame):
    """Gráfico de líneas con proyecciones y meta 85% para el Índice Compuesto Institucional."""
    rule_df = pd.DataFrame({'meta': [85.0], 'label': ['Meta Institucional: 85%']})
    rule = alt.Chart(rule_df).mark_rule(color='#ef4444', strokeWidth=2, strokeDash=[4, 4]).encode(y='meta:Q')
    rule_text = alt.Chart(rule_df).mark_text(align='left', dx=10, dy=-6, color='#ef4444', fontWeight='bold', fontSize=12).encode(y='meta:Q', text='label:N')

    base = alt.Chart(df_res).encode(
        x=alt.X('bimestre:N', title=None, sort=['B1', 'B2', 'B3', 'B4', 'B5'], axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight='bold')),
        y=alt.Y('indice:Q', title='Índice Compuesto (%)', scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(format='.0f', grid=True, gridDash=[3, 3], gridColor='#e2e8f0')),
        color=alt.Color('campus:N', scale=alt.Scale(
            domain=['Misiones', 'Nuevo Sur', 'San Agustín', 'Global'],
            range=['#3b82f6', '#8b5cf6', '#10b981', '#0f172a']
        ), legend=alt.Legend(title=None, orient='top', labelFontSize=12)),
        strokeDash=alt.StrokeDash('tipo:N', scale=alt.Scale(
            domain=['Real', 'Proyección'],
            range=[[0, 0], [6, 4]]
        ), legend=alt.Legend(title=None, orient='top', labelFontSize=12)),
        tooltip=[
            alt.Tooltip('campus:N', title='Campus'),
            alt.Tooltip('bimestre_label:N', title='Bimestre'),
            alt.Tooltip('indice:Q', format='.1f', title='Índice (%)'),
            alt.Tooltip('tipo:N', title='Tipo')
        ]
    )

    lines = base.mark_line(strokeWidth=3)
    points = base.mark_circle(size=60)
    text = base.mark_text(baseline='bottom', dy=-8, fontWeight='bold', fontSize=11).encode(
        text=alt.Text('indice:Q', format='.1f')
    )

    return (lines + points + text + rule + rule_text).properties(height=340).configure_view(stroke='transparent')


