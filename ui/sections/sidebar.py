# ui/sections/sidebar.py
# pyrefly: ignore [missing-import]
import streamlit as st

def render_sidebar(sede_name=None):
    with st.sidebar:
        # Logo de la institución
        st.image("assets/EVERWISE_LOGO.png", use_container_width=True)

        st.markdown("<style> [data-testid='stSidebarNav'] {display: none;} </style>", unsafe_allow_html=True)
        
        # ── Perfil de Usuario Activo (CRM Profile Card) ──
        user_name = st.session_state.get("user_name", "Usuario")
        user_role = st.session_state.get("user_role", "General")
        user_email = st.session_state.get("user_email", "")

        role_badge_color = "#3b82f6" if user_role == "General" else "#10b981"
        st.markdown(f"""
            <div style='background: rgba(241, 245, 249, 0.85); border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.75rem 0.9rem; margin-bottom: 1.25rem;'>
                <div style='font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: #64748b; letter-spacing: 0.5px;'>Sesión Activa</div>
                <div style='font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-top: 2px;'>{user_name}</div>
                <div style='display: flex; align-items: center; gap: 6px; margin-top: 4px;'>
                    <span style='background: {role_badge_color}; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 600;'>{user_role}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("### Navegación")

        if user_role == "General":
            if st.button("Inicio Global", use_container_width=True, type="primary" if sede_name is None else "secondary"): 
                st.switch_page("app.py")
            if st.button("Misiones", use_container_width=True, type="primary" if sede_name == "Misiones" else "secondary"): 
                st.switch_page("pages/1_Misiones.py")
            if st.button("Nuevo Sur", use_container_width=True, type="primary" if sede_name == "Nuevo Sur" else "secondary"): 
                st.switch_page("pages/2_Nuevo_Sur.py")
            if st.button("San Agustín", use_container_width=True, type="primary" if sede_name == "San Agustín" else "secondary"): 
                st.switch_page("pages/3_San_Agustin.py")
        elif user_role == "Misiones":
            if st.button("Mi Campus · Misiones", use_container_width=True, type="primary"): 
                st.switch_page("pages/1_Misiones.py")
        elif user_role == "Nuevo Sur":
            if st.button("Mi Campus · Nuevo Sur", use_container_width=True, type="primary"): 
                st.switch_page("pages/2_Nuevo_Sur.py")
        elif user_role == "San Agustín":
            if st.button("Mi Campus · San Agustín", use_container_width=True, type="primary"): 
                st.switch_page("pages/3_San_Agustin.py")

        st.write("---")

        ciclo_seleccionado = st.selectbox(
            "Ciclo Escolar Activo",
            options=["2025 - 2026", "2024 - 2025", "2023 - 2024"],
            index=0
        )
        st.caption("SaaS Core Everwise · v1.0  Enterprise")

        st.write("---")
        if st.button("Cerrar Sesión", use_container_width=True):
            from src.logic.auth import logout
            logout()

        return ciclo_seleccionado