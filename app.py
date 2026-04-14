import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦", layout="centered")

# CSS para ocultar menús, botón de código y marca de agua
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'email_usuario' not in st.session_state:
    st.session_state.email_usuario = ""

def check_login():
    email_ingresado = st.session_state.email_login.lower().strip()
    try:
        lista_blanca = st.secrets["usuarios_autorizados"]["emails"]
        if email_ingresado in [e.lower() for e in lista_blanca]:
            st.session_state.autenticado = True
            st.session_state.email_usuario = email_ingresado
        else:
            st.error("🚫 Correo no autorizado.")
    except Exception:
        st.error("⚠️ Error: Configura 'usuarios_autorizados' en los Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    st.text_input("Ingresa tu Email:", key="email_login", on_change=check_login)
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- VERIFICAR BLOQUEO ---
try:
    df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
    if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
        st.title("🚫 Acceso Restringido")
        st.warning(f"Hola {st.session_state.email_usuario}, ya registraste un pedido.")
        st.info("Tu cuenta está bloqueada. Contacta al administrador para nueva carga.")
        st.stop()
except Exception:
    pass

# --- FORMULARIO DE PEDIDO ---
st.title("📦 Formulario de Pedidos")
st.success(f"👷 Técnico: **{st.session_state.email_usuario}**")

materiales_disponibles = [
    "13008 CONTROL REMOTO PARA DECO SAGECOM DCWMI303. CON BOT",
    "30032 CABLE COAXIL RG6 QUADSHIELD NEGRO CON PORTANTE",
    "31025 PRECINTO PLÁSTICO NEGRO (150 X 5.5 MM) , CON PROTE",
    "
