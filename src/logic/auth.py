# pyrefly: ignore [missing-import]
import streamlit as st
import hmac
import hashlib
import sqlite3
import os

SECRET_AUTH_KEY = b"everwise_secure_session_key_2026_enterprise"
DB_PATH = "data/everwise.db"

DEFAULT_USERS = [
    ("director", "123", "General", "Director General", "admin@everwise.edu"),
    ("misiones", "123", "Misiones", "Coordinador Misiones", "misiones@everwise.edu"),
    ("nuevosur", "123", "Nuevo Sur", "Coordinador Nuevo Sur", "nuevosur@everwise.edu"),
    ("sanagustin", "123", "San Agustín", "Coordinador San Agustín", "sanagustin@everwise.edu"),
]

def hash_password(password: str) -> str:
    """Genera hash seguro de contraseña usando SHA256 con salt fija."""
    salt = "everwise_crm_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def init_auth_db():
    """Inicializa la tabla de usuarios en SQLite y siembra los usuarios por defecto."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Sembrar usuarios por defecto si no existen
    for u, p, r, n, e in DEFAULT_USERS:
        cursor.execute("SELECT username FROM users WHERE username = ?", (u,))
        if not cursor.fetchone():
            p_hash = hash_password(p)
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, name, email) VALUES (?, ?, ?, ?, ?)",
                (u, p_hash, r, n, e)
            )
    conn.commit()
    conn.close()

# Inicializar BD de autenticación al importar
init_auth_db()

def get_user(username: str):
    """Consulta usuario en SQLite."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password_hash, role, name, email, is_active FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and row[5] == 1:
        return {
            "username": row[0],
            "password_hash": row[1],
            "role": row[2],
            "name": row[3],
            "email": row[4]
        }
    return None

def verify_credentials(username: str, password: str):
    """Verifica usuario y contraseña contra la base de datos."""
    user = get_user(username)
    if not user:
        return None
    if user["password_hash"] == hash_password(password):
        return user
    # Fallback para pruebas rápidas
    if password == "123":
        return user
    return None

def generar_token(username: str) -> str:
    return hmac.new(SECRET_AUTH_KEY, username.encode("utf-8"), hashlib.sha256).hexdigest()

def validar_token(username: str, token: str) -> bool:
    if not username or not token:
        return False
    expected = generar_token(username)
    return hmac.compare_digest(expected, token)

def restaurar_sesion_si_aplica() -> bool:
    """Intenta restaurar la sesión si existen query_params válidos tras refrescar la página."""
    if "auth_user" in st.query_params and "auth_token" in st.query_params:
        username = st.query_params["auth_user"]
        token = st.query_params["auth_token"]
        user = get_user(username)
        if user and validar_token(username, token):
            st.session_state["logged_in"] = True
            st.session_state["username"] = user["username"]
            st.session_state["user_role"] = user["role"]
            st.session_state["user_name"] = user["name"]
            st.session_state["user_email"] = user.get("email", "")
            return True
    return False

def render_login_page():
    st.markdown("""
        <div style='text-align: center; margin-bottom: 2rem;'>
            <h1 style='font-weight: 800; letter-spacing: -1px; margin-bottom: 0.25rem;'>Everwise</h1>
            <p style='color: #64748b; font-size: 0.95rem;'>Sistema Ejecutivo de Inteligencia Educativa y Gestión Institucional</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### Acceso Corporativo")
            username = st.text_input("Usuario", placeholder="director / misiones / nuevosur / sanagustin")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar al Sistema", use_container_width=True, type="primary")
            
            if submitted:
                user = verify_credentials(username.strip().lower(), password)
                if user:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user["username"]
                    st.session_state["user_role"] = user["role"]
                    st.session_state["user_name"] = user["name"]
                    st.session_state["user_email"] = user.get("email", "")
                    
                    # Persistir token en URL para tolerar refrescos
                    st.query_params["auth_user"] = user["username"]
                    st.query_params["auth_token"] = generar_token(user["username"])
                    
                    # Registrar login en bitácora de auditoría
                    try:
                        from src.logic.data_loader import log_audit_event
                        log_audit_event(user["username"], "LOGIN", f"Inicio de sesión exitoso con rol {user['role']}")
                    except Exception:
                        pass
                    
                    role = user["role"]
                    if role == "Misiones":
                        st.switch_page("pages/1_Misiones.py")
                    elif role == "Nuevo Sur":
                        st.switch_page("pages/2_Nuevo_Sur.py")
                    elif role == "San Agustín":
                        st.switch_page("pages/3_San_Agustin.py")
                    else:
                        st.switch_page("app.py")
                else:
                    st.error("Credenciales incorrectas o usuario inactivo.")
                    
        st.markdown("""
            <div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.85rem 1rem; margin-top: 1rem; font-size: 0.85rem; color: #475569;'>
                <strong>Perfiles de Acceso:</strong><br>
                • <code>director</code>: Visión Global Consolidada y Multisede<br>
                • <code>misiones</code>, <code>nuevosur</code>, <code>sanagustin</code>: Aislamiento por Campus<br>
                • <em>Contraseña universal:</em> <code>123</code>
            </div>
        """, unsafe_allow_html=True)

def require_login(campus_context="General"):
    """Valida credenciales y aplica aislamiento estricto por roles (RBAC)."""
    # 1. Intentar restaurar sesión si no está en session_state
    if not st.session_state.get("logged_in", False):
        if not restaurar_sesion_si_aplica():
            render_login_page()
            st.stop()
        
    # 2. RBAC estricto
    user_role = st.session_state.get("user_role", "Invitado")
    
    if user_role != "General":
        if campus_context == "General":
            st.warning(f"**Acceso Restringido:** Tu rol de **{user_role}** no tiene privilegios para acceder al panel Global.")
            btn = st.button(f"Ir a mi Dashboard de {user_role}", type="primary")
            if btn:
                if user_role == "Misiones": st.switch_page("pages/1_Misiones.py")
                elif user_role == "Nuevo Sur": st.switch_page("pages/2_Nuevo_Sur.py")
                elif user_role == "San Agustín": st.switch_page("pages/3_San_Agustin.py")
            st.stop()
            
        elif user_role != campus_context:
            st.error(f"**Aislamiento de Seguridad:** Estás autenticado como administrador de **{user_role}**. No tienes autorización para consultar la información privada del Campus **{campus_context}**.")
            st.stop()

def logout():
    username = st.session_state.get("username", "Desconocido")
    try:
        from src.logic.data_loader import log_audit_event
        log_audit_event(username, "LOGOUT", "Cierre de sesión de usuario")
    except Exception:
        pass

    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["username"] = None
    st.session_state["user_name"] = None
    st.session_state["user_email"] = None
    if "auth_user" in st.query_params:
        del st.query_params["auth_user"]
    if "auth_token" in st.query_params:
        del st.query_params["auth_token"]
    st.switch_page("app.py")

