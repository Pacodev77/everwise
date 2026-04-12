# ui/sections/sidebar.py
import streamlit as st
import datetime

def render_sidebar(sede_name=None):
    with st.sidebar:
        st.image("assets/EVERWISE_LOGO.png", use_container_width=True)
        
        st.markdown("<style> [data-testid='stSidebarNav'] {display: none;} </style>", unsafe_allow_html=True)
        st.markdown("### Navegación")
        
        role = st.session_state.get('user_role', '')
        
        # Ocultar botones a los que no tienen acceso
        if role == "General":
            if st.button("Inicio Global", use_container_width=True): st.switch_page("app.py")
            if st.button("Misiones", use_container_width=True): st.switch_page("pages/1_Misiones.py")
            if st.button("Nuevo Sur", use_container_width=True): st.switch_page("pages/2_Nuevo_Sur.py")
            if st.button("San Agustín", use_container_width=True): st.switch_page("pages/3_San_Agustin.py")
        elif role == "Misiones":
            if st.button("Mi Campus · Misiones", use_container_width=True): st.switch_page("pages/1_Misiones.py")
        elif role == "Nuevo Sur":
            if st.button("Mi Campus · Nuevo Sur", use_container_width=True): st.switch_page("pages/2_Nuevo_Sur.py")
        elif role == "San Agustín":
            if st.button("Mi Campus · San Agustín", use_container_width=True): st.switch_page("pages/3_San_Agustin.py")

        st.write("---")
        
        ciclo_seleccionado = st.selectbox(
            "## Ciclo Escolar",
            options=["2025 - 2026", "2024 - 2025", "2023 - 2024"],
            index=0
        )
        st.caption("Data 2025 · 2026")
        st.caption("Versión · EV-1.0")
        
        st.write("---")
        if st.button("Cerrar Sesión", use_container_width=True):
            from src.logic.auth import logout
            logout()
            
        return ciclo_seleccionado
