# src/logic/charts.py

# pyrefly: ignore [missing-import]
import altair as alt

def bar_lenguaje_chart(df_barras):
    """
    Gráfico de barras ejecutivas para Lenguaje (B1 vs B2)
    """
    return (
        alt.Chart(df_barras)
        .mark_bar(
            cornerRadiusTopLeft=10,
            cornerRadiusTopRight=10
        )
        .encode(
            x=alt.X("bloque:N", title=None),
            y=alt.Y(
                "lenguaje:Q",
                title="Lenguaje",
                axis=alt.Axis(format="%")
            ),
            tooltip=[
                alt.Tooltip("bloque:N", title="Bloque"),
                alt.Tooltip("lenguaje:Q", title="Lenguaje", format=".0%")
            ]
        )
        .properties(height=260)
    )

def sparkline_lenguaje(df_futuro, columna="lenguaje"):
    """
    Sparkline minimalista para tendencia ejecutiva
    """
    return (
        alt.Chart(df_futuro)
        .mark_line(
            strokeWidth=3,
            interpolate="monotone"
        )
        .encode(
            x=alt.X("bloque:N", title=None, axis=None),
            y=alt.Y(columna + ":Q", title=None, axis=None)
        )
        .properties(height=70)
    )


# Funcion desde gemini ai (Es nueva)
def trend_chart_ejecutivo(df_futuro, columna="lenguaje"):
    """
    Gráfico de tendencia con líneas suaves (curvas) y estética limpia.
    """
    chart = (
        alt.Chart(df_futuro)
        .mark_line(
            interpolate='monotone', # Esto suaviza la línea (curvas en lugar de ángulos rectos)
            strokeWidth=4,
            color='#2563EB',
            point=alt.OverlayMarkDef(size=60, color='#2563EB', filled=True) # Puntos suaves
        )
        .encode(
            x=alt.X("bloque:N", title=None, axis=alt.Axis(labelAngle=0, labelFlush=True)),
            y=alt.Y(f"{columna}:Q", title=None, axis=alt.Axis(format='%', gridOpacity=0.4)),
            tooltip=["bloque", alt.Tooltip(f"{columna}:Q", format=".1%")]
        )
        .properties(height=300)
        .configure_view(strokeOpacity=0) # Quita el borde cuadrado del gráfico
        .configure_axis(gridDash=[4,4], gridColor="#E2E8F0") # Grid punteado suave
    )
    return chart