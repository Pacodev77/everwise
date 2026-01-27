import pandas as pd
import plotly.express as px
import streamlit as st

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

st.set_page_config(page_title="Dashboard de Asistencia Pro", layout="wide")
st.title("📊 Dashboard de Asistencia - Everwise Pro")


# =====================================================
# FUNCIONES DE DATOS
# =====================================================

def load_data(path: str) -> pd.DataFrame:
    """Carga el CSV y calcula la asistencia."""
    df = pd.read_csv(path)
    df['Asistencia'] = (df['presentes'] / df['inscritos']) * 100
    return df


def get_promedio_general(df: pd.DataFrame) -> float:
    """Calcula el promedio general de asistencia."""
    return df['Asistencia'].mean()


def get_stats_por_campus(df: pd.DataFrame, campus: str) -> dict:
    """Obtiene estadísticas de asistencia para un campus."""
    df_campus = df[df['campus'] == campus]
    return {
        "df": df_campus,
        "promedio": df_campus['Asistencia'].mean(),
        "max": df_campus['Asistencia'].max(),
        "min": df_campus['Asistencia'].min()
    }


def get_promedio_por_campus(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking de campus por asistencia."""
    return (
        df.groupby('campus')['Asistencia']
        .mean()
        .reset_index()
        .sort_values(by='Asistencia', ascending=False)
    )


# =====================================================
# FUNCIONES DE GRÁFICAS
# =====================================================

def bar_chart_campus(df: pd.DataFrame, promedio_general: float):
    fig = px.bar(
        df,
        x='campus',
        y='Asistencia',
        title="🏫 Promedio de asistencia por campus (Ranking)",
        labels={'Asistencia': 'Asistencia (%)', 'campus': 'Campus'},
        text='Asistencia',
        color='Asistencia',
        color_continuous_scale=['red', 'yellow', 'green'],
        hover_data={'Asistencia': ':.2f'}
    )

    fig.add_hline(
        y=promedio_general,
        line_dash="dash",
        line_color="blue",
        annotation_text="Promedio general",
        annotation_position="top left"
    )

    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(barcornerradius=10)

    return fig


def bar_chart_nivel(df: pd.DataFrame, campus: str, promedio_general: float):
    df_sorted = df.sort_values(by='Asistencia', ascending=False)

    fig = px.bar(
        df_sorted,
        x='nivel',
        y='Asistencia',
        title=f"👨‍🎓 Asistencia por nivel - {campus}",
        labels={'Asistencia': 'Asistencia (%)', 'nivel': 'Nivel'},
        text='Asistencia',
        color='Asistencia',
        color_continuous_scale=['red', 'yellow', 'green'],
        hover_data={
            'inscritos': True,
            'presentes': True,
            'Asistencia': ':.2f'
        }
    )

    fig.add_hline(
        y=promedio_general,
        line_dash="dash",
        line_color="blue",
        annotation_text="Promedio general",
        annotation_position="top left"
    )

    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(barcornerradius=10)

    return fig


# =====================================================
# APP PRINCIPAL (STREAMLIT)
# =====================================================

df = load_data("data/data.csv")
promedio_general = get_promedio_general(df)

campus_seleccionado = st.selectbox(
    "Selecciona un campus",
    df['campus'].unique()
)

stats = get_stats_por_campus(df, campus_seleccionado)

st.subheader(f"📌 Estadísticas de asistencia - {campus_seleccionado}")
st.write(f"- Promedio del campus: {stats['promedio']:.2f}%")
st.write(f"- Máximo: {stats['max']:.2f}%")
st.write(f"- Mínimo: {stats['min']:.2f}%")
st.write(f"- Promedio general: {promedio_general:.2f}%")

fig_campus = bar_chart_campus(
    get_promedio_por_campus(df),
    promedio_general
)
st.plotly_chart(fig_campus, use_container_width=True)

fig_nivel = bar_chart_nivel(
    stats['df'],
    campus_seleccionado,
    promedio_general
)
st.plotly_chart(fig_nivel, use_container_width=True)
