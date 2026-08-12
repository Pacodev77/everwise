# src/sections/academico_b1_b2.py

# pyrefly: ignore [missing-import]
import streamlit as st
from src.logic.narrative import narrativa_bloques

def render_academico_b1_b2(df_b1_campus, df_b2_campus):
    st.divider()
    st.subheader("Resumen Ejecutivo · Desempeño Académico")

    # Cálculos de promedios
    b1_leng = df_b1_campus["lenguaje"].mean()
    b2_leng = df_b2_campus["lenguaje"].mean()

    # Layout de métricas
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Lenguaje · B1", f"{b1_leng:.0%}")

    with col2:
        st.metric("Lenguaje · B2", f"{b2_leng:.0%}")

    # Narrativa automática
    st.caption(
        narrativa_bloques(
            b1_leng,
            b2_leng,
            "Lenguaje"
        )
    )