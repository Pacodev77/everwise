# ui/charts/bar_chart.py

import altair as alt

def chart_dominio_academico(df_academico):
    bar_chart = alt.Chart(df_academico).mark_bar(cornerRadiusEnd=10).encode(
        x=alt.X("campus:N", title=None, axis=alt.Axis(labelAngle=0), scale=alt.Scale(paddingInner=0.5)),
        y=alt.Y("dominio:Q", axis=alt.Axis(format="%"), title="Nivel de logro"),
        color=alt.Color("dominio:Q", scale=alt.Scale(domain=[0.70, 0.85, 1.0], range=["#ef4444", "#f59e0b", "#10b981"]), legend=None)
    ).properties(height=300)
    return bar_chart
