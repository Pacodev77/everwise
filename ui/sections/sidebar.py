# ui/sections/sidebar.py
# pyrefly: ignore [missing-import]
import streamlit as st
import datetime

def obtener_ciclos_escolares_dinamicos():
    """Genera dinámicamente el ciclo escolar actual y ciclos anteriores/futuros sin harcodeo."""
    now = datetime.datetime.now()
    year_start = now.year if now.month >= 8 else now.year - 1
    
    # Generar lista de ciclos ordenados descendentemente (futuros primero, luego actual, luego pasados)
    ciclos = [f"{y} - {y+1}" for y in range(year_start + 2, year_start - 3, -1)]
    ciclo_actual = f"{year_start} - {year_start + 1}"
    idx_default = ciclos.index(ciclo_actual) if ciclo_actual in ciclos else 0
    return ciclos, idx_default

def gestionar_cambio_de_ciclo(nuevo_ciclo: str):
    """
    Aísla y gestiona el estado del sistema según el ciclo escolar activo.
    Guarda el estado del ciclo saliente y restaura el estado del ciclo entrante.
    """
    if "cycle_vault" not in st.session_state:
        st.session_state["cycle_vault"] = {}

    ciclo_activo = st.session_state.get("ciclo_escolar_activo")

    if ciclo_activo is None:
        st.session_state["ciclo_escolar_activo"] = nuevo_ciclo
        return

    if ciclo_activo != nuevo_ciclo:
        prefixes = (
            "ixl_", "progrentis_", "academico_", "asistencia_", 
            "clima_", "disciplina_", "practica_", "last_up_", "df_"
        )
        keys_modulo = [
            k for k in list(st.session_state.keys())
            if k.startswith(prefixes) and k != "cycle_vault"
        ]
        
        # Guardar en el vault el estado del ciclo que sale
        if ciclo_activo not in st.session_state["cycle_vault"]:
            st.session_state["cycle_vault"][ciclo_activo] = {}
            
        for k in keys_modulo:
            st.session_state["cycle_vault"][ciclo_activo][k] = st.session_state[k]
            del st.session_state[k]

        # Actualizar ciclo activo
        st.session_state["ciclo_escolar_activo"] = nuevo_ciclo

        # Restaurar estado del ciclo que entra si existe
        if nuevo_ciclo in st.session_state["cycle_vault"]:
            vault_nuevo = st.session_state["cycle_vault"][nuevo_ciclo]
            for k, val in vault_nuevo.items():
                st.session_state[k] = val

        st.cache_data.clear()
        st.rerun()

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

        ciclos_opciones, idx_default = obtener_ciclos_escolares_dinamicos()
        ciclo_seleccionado = st.selectbox(
            "Ciclo Escolar Activo",
            options=ciclos_opciones,
            index=idx_default
        )

        gestionar_cambio_de_ciclo(ciclo_seleccionado)

        st.write("---")
        # ── Reset / Reinicio General del Sistema ──
        if st.button("Reiniciar Sistema", use_container_width=True):
            st.session_state["mostrar_confirmacion_reset"] = True

        if st.session_state.get("mostrar_confirmacion_reset", False):
            st.error("**ADVERTENCIA DE REINICIO**\n\nSe eliminarán permanentemente todos los archivos cargados, historiales y la base de datos de todos los campus.")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                if st.button("Sí, borrar todo", type="primary", use_container_width=True, key="btn_confirm_reset_sb"):
                    from src.logic.data_loader import reset_all_system_data
                    reset_all_system_data()
                    st.session_state["mostrar_confirmacion_reset"] = False
                    st.rerun()
            with col_res2:
                if st.button("Cancelar", use_container_width=True, key="btn_cancel_reset_sb"):
                    st.session_state["mostrar_confirmacion_reset"] = False
                    st.rerun()

        st.write("---")
        if st.button("Cerrar Sesión", use_container_width=True):
            from src.logic.auth import logout
            logout()

        # ── Footer / Branding Ejecutivo ──
        st.markdown("""
            <div style='margin-top: 1.5rem; padding-top: 0.75rem; border-top: 1px solid #cbd5e1; font-size: 0.78rem; color: #64748b; text-align: center; line-height: 1.4;'>
                <div style='font-weight: 700; color: #94a3b8; font-size: 0.85rem; letter-spacing: 0.3px;'>Everwise® v2.1</div>
                <div style='margin-top: 2px; font-weight: 500;'>Crafted by <span style='font-weight: 700; color: #94a3b8;'>Paco Ruiz</span></div>
                <div style='font-size: 0.72rem; color: #94a3b8; margin-top: 4px;'>© 2025–2026.</div>
            </div>
        """, unsafe_allow_html=True)

        return ciclo_seleccionado