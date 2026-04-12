# sections/asistencia.py

import streamlit as st
from src.logic.narrative import narrativa_asistencia

def render_asistencia(df_asistencia, campus, valor_asistencia):
    st.divider()
    st.subheader("Resumen Ejecutivo · Asistencia")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Asistencia promedio", f"{valor_asistencia:.2%}")
        st.caption(narrativa_asistencia(valor_asistencia))

    with col2:
        st.dataframe(df_asistencia, use_container_width=True)
        