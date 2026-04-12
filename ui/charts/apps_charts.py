import altair as alt
import pandas as pd

def chart_comparativa_apps(df_apps_kpis):
    """
    Gráfica de barras comparando IXL vs Progrentis en: Uso Efectivo.
    """
    id_vars = ['Plataforma']
    if 'campus' in df_apps_kpis.columns:
        id_vars.append('campus')
        
    df_melt = pd.melt(df_apps_kpis, id_vars=id_vars, value_vars=['Uso Efectivo (%)'],
                      var_name='Métrica', value_name='Valor')

    column_field = 'campus:N' if 'campus' in df_apps_kpis.columns and len(df_apps_kpis['campus'].unique()) > 1 else 'Métrica:N'

    base = alt.Chart(df_melt).mark_bar(cornerRadiusEnd=5).encode(
        x=alt.X('Plataforma:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
        y=alt.Y('Valor:Q', axis=alt.Axis(format="%"), title=None),
        color=alt.Color('Plataforma:N', scale=alt.Scale(domain=['IXL', 'Progrentis'], range=['#3b82f6', '#10b981'])),
        column=alt.Column(column_field, header=alt.Header(title=None, labelOrient='bottom', labelFontSize=14, labelFontWeight='bold'))
    ).properties(width=80, height=250)

    return base.configure_view(stroke='transparent')


def chart_correlacion_practica(df_correlacion):
    """
    Gráfico de dispersión (Scatter plot) que valida "resultado ↑ / práctica ↑".
    """
    scatter = alt.Chart(df_correlacion).mark_circle(size=80, opacity=0.7).encode(
        x=alt.X("Práctica (%):Q", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
        y=alt.Y("Resultado (%):Q", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
        color=alt.Color("Plataforma:N", scale=alt.Scale(domain=['IXL', 'Progrentis'], range=['#3b82f6', '#10b981'])),
        tooltip=["Plataforma", "Grupo", "Práctica (%)", "Resultado (%)"]
    ).properties(height=280)

    # Línea de tendencia por plataforma
    trend = scatter.transform_regression(
        "Práctica (%)", "Resultado (%)", groupby=["Plataforma"]
    ).mark_line(strokeDash=[5,5], size=2)

    final = scatter + trend
    if 'campus' in df_correlacion.columns and len(df_correlacion['campus'].unique()) > 1:
        return final.facet(column=alt.Column('campus:N', title=None, header=alt.Header(labelFontSize=14, labelFontWeight='bold'))).configure_view(stroke='transparent')
    
    return final.configure_view(stroke='transparent')
