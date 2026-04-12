# ui/charts/donuts.py

import altair as alt
import pandas as pd

def donut_estado(valor):
    if valor >= 0.9:
        color, label = "#10b981", "Estable"
    elif valor >= 0.8:
        color, label = "#f59e0b", "Atención"
    else:
        color, label = "#ef4444", "Riesgo"

    df = pd.DataFrame({"v": [valor, 1 - valor], "k": ["p", "f"]})

    base = alt.Chart(df).mark_arc(
        innerRadius=30,
        outerRadius=44,
        cornerRadius=8
    ).encode(
        theta="v:Q",
        color=alt.Color(
            "k:N",
            scale=alt.Scale(domain=["p", "f"], range=[color, "#e5e7eb"]),
            legend=None
        )
    )

    return base.properties(height=120).configure_view(strokeWidth=0)
