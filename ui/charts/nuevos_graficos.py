import altair as alt
import pandas as pd

def chart_academico_bloques(df_acad: pd.DataFrame):
    """Gráfico de barras agrupadas comparativas por bloque."""
    df_melt = df_acad.melt(id_vars=['campus', 'Bloque'], value_vars=['Matemáticas', 'Español'], 
                           var_name='Materia', value_name='Dominio')
    
    encoding_args = {
        'x': alt.X('Bloque:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=11)),
        'y': alt.Y('Dominio:Q', axis=alt.Axis(format="%"), title=None),
        'color': alt.Color('Bloque:N', scale=alt.Scale(domain=['B1', 'B2', 'B3'], range=['#94a3b8', '#8b5cf6', '#3b82f6']), legend=None),
        'row': alt.Row('Materia:N', header=alt.Header(title=None, labelOrient='top', labelFontSize=14, labelFontWeight='bold', labelPadding=10), sort=['Español', 'Matemáticas'])
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
