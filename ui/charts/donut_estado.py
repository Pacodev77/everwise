# ui/charts/dona_estado.py

import pandas as pd
import altair as alt

def donut_estado(valor: float):
    """Genera un gráfico de dona con lógica de semáforo."""
    if valor >= 0.90:
        color, label = "#10b981", "Estable"
    elif valor >= 0.80:
        color, label = "#f59e0b", "Atención"
    else:
        color, label = "#ef4444", "Riesgo"

    df = pd.DataFrame({"v": [valor, 1 - valor], "k": ["p", "f"]})

    base = alt.Chart(df).mark_arc(
        innerRadius=30, outerRadius=44, cornerRadius=8
    ).encode(
        theta="v:Q",
        color=alt.Color("k:N", scale=alt.Scale(domain=["p", "f"], range=[color, "#e5e7eb"]), legend=None),
        tooltip=alt.value(None)
    )

    p_text = alt.Chart(pd.DataFrame({"v": [valor]})).mark_text(
        fontSize=16, fontWeight=800, dy=-4, color="#0f172a"
    ).encode(text=alt.Text("v:Q", format=".0%"))

    l_text = alt.Chart(pd.DataFrame({"l": [label]})).mark_text(
        fontSize=9, fontWeight=600, dy=12, color="#64748b"
    ).encode(text="l:N")

    return (base + p_text + l_text).properties(height=115).configure_view(strokeWidth=0)
