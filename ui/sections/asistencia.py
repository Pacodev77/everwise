# ui/sections/asistencia.py

import streamlit as st
from logic.narrative import narrativa_asistencia

def render_asistencia(valor):
    st.subheader("Resumen Ejecutivo · Asistencia")
    st.metric("Asistencia promedio", f"{valor:.0%}")
    st.caption(narrativa_asistencia(valor))
