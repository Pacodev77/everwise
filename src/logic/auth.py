import streamlit as st

USERS = {
    "director": {"password": "123", "role": "General", "name": "Director General"},
    "misiones": {"password": "123", "role": "Misiones", "name": "Coordinador Misiones"},
    "nuevosur": {"password": "123", "role": "Nuevo Sur", "name": "Coordinador Nuevo Sur"},
    "sanagustin": {"password": "123", "role": "San Agustín", "name": "Coordinador San Agustín"}
}

def render_login_page():
    st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Everwise</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            st.markdown("**Ingreso Operativo**")
            username = st.text_input("Usuario (ej. director, misiones, nuevosur)")
            password = st.text_input("Contraseña (123)", type="password")
            submitted = st.form_submit_button("Validar Identidad", use_container_width=True)
            
            if submitted:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_role = USERS[username]["role"]
                    st.session_state.user_name = USERS[username]["name"]
                    
                    role = st.session_state.user_role
                    # Auto-ruteo basado en permisos
                    if role == "Misiones":
                        st.switch_page("pages/1_Misiones.py")
                    elif role == "Nuevo Sur":
                        st.switch_page("pages/2_Nuevo_Sur.py")
                    elif role == "San Agustín":
                        st.switch_page("pages/3_San_Agustin.py")
                    else:
                        st.switch_page("app.py")
                else:
                    st.error("Credenciales incorrectas o acceso denegado.")
                    
        st.info("**Roles de prueba:**\n- Usuario: `director` (Nivel Master)\n- Usuario: `misiones` (Aisla la sede)\n- Pass universal: `123`")

def require_login(campus_context="General"):
    """
    Valida credenciales. Bloquea la navegación cruzada aislando por Roles (RBAC).
    """
    # 1. Si no hay login
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        render_login_page()
        st.stop()
        
    # 2. Si ya hay login, validar el nivel de acceso (RBAC real)
    user_role = st.session_state.get('user_role', 'Invitado')
    
    if user_role != "General":
        if campus_context == "General":
            st.warning(f"**Acceso Restringido:** Tu rol de '{user_role}' no tiene los privilegios ejecutivos para ver la Visión Global (Consolidada).")
            # Redirección forzada de vuelta a su dominio permitido
            btn = st.button(f"Regresar a mi Dashboard de {user_role}", type='primary')
            if btn:
                if user_role == "Misiones": st.switch_page("pages/1_Misiones.py")
                elif user_role == "Nuevo Sur": st.switch_page("pages/2_Nuevo_Sur.py")
                elif user_role == "San Agustín": st.switch_page("pages/3_San_Agustin.py")
            st.stop()
            
        elif user_role != campus_context:
            st.error(f"**Violación de Privacidad:** Eres un administrador de '{user_role}'. No puedes ingresar y monitorear la información privada del Campus '{campus_context}'.")
            st.stop()

def logout():
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.switch_page("app.py")
