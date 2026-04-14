import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦")

# --- LÓGICA DE LOGIN Y BLOQUEO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'email_usuario' not in st.session_state:
    st.session_state.email_usuario = ""

def verificar_estado_bloqueo(email, conn):
    """Revisa en la hoja 'Autorizaciones' si el técnico está bloqueado"""
    try:
        # Intentamos leer la hoja de autorizaciones
        df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
        # Buscamos si el email está en la lista de bloqueados
        bloqueado = email in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values
        return bloqueado
    except:
        # Si la hoja no existe aún, nadie está bloqueado
        return False

def check_login():
    email_ingresado = st.session_state.email_login.lower().strip()
    try:
        lista_blanca = st.secrets["usuarios_autorizados"]["emails"]
        if email_ingresado in [e.lower() for e in lista_blanca]:
            st.session_state.autenticado = True
            st.session_state.email_usuario = email_ingresado
        else:
            st.error("🚫 Este correo no está autorizado.")
    except Exception:
        st.error("⚠️ Error: Configura los correos en Secrets.")

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    st.text_input("Email:", key="email_login", on_change=check_login)
    st.stop() 

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- VERIFICACIÓN DE AUTORIZACIÓN ---
# Si el técnico ya entró, verificamos si su último pedido lo bloqueó
es_bloqueado = verificar_estado_bloqueo(st.session_state.email_usuario, conn)

if es_bloqueado:
    st.title("🚫 Acceso Restringido")
    st.warning(f"Hola **{st.session_state.email_usuario}**, ya has registrado un pedido hoy.")
    st.info("Tu cuenta se encuentra bloqueada para nuevos pedidos hasta que el administrador te autorice manualmente.")
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()
    st.stop()

# --- SI NO ESTÁ BLOQUEADO, MOSTRAR LA APP NORMAL ---
st.title("📦 Formulario de Pedidos")
st.success(f"👷 Técnico: **{st.session_state.email_usuario}**")

materiales_disponibles = [
    "13008 CONTROL REMOTO PARA DECO SAGECOM DCWMI303",
    "30032 CABLE COAXIL RG6 QUADSHIELD NEGRO",
    "90090 DIVISOR DE 2 BOCAS",
    # ... agrega el resto de tu lista aquí
]

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

with st.form("formulario_pedido", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        seleccion = st.selectbox("Selecciona artículo:", materiales_disponibles)
    with col2:
        cantidad_str = st.text_input("Cantidad:", placeholder="0")
    
    if st.form_submit_button("Agregar al pedido"):
        try:
            cantidad_num = int(cantidad_str)
            if cantidad_num > 0:
                partes = seleccion.split(" ", 1)
                st.session_state.carrito.append({
                    "Tecnico": st.session_state.email_usuario,
                    "Codigo": partes[0],
                    "Articulo": partes[1] if len(partes) > 1 else "",
                    "Cantidad": cantidad_num
                })
                st.rerun()
            else:
                st.warning("La cantidad debe ser mayor a 0.")
        except ValueError:
            st.error("Ingresa solo números.")

if st.session_state.carrito:
    st.subheader("🛒 Resumen")
    df_pedido = pd.DataFrame(st.session_state.carrito)
    st.table(df_pedido)
    
    if st.button("🚀 ENVIAR Y FINALIZAR"):
        try:
            # 1. Guardar el Pedido en la hoja 'Pedidos'
            try:
                existente = conn.read(worksheet="Pedidos", ttl=0).dropna(how='all')
            except:
                existente = pd.DataFrame(columns=["Tecnico", "Codigo", "Articulo", "Cantidad"])
            
            actualizado = pd.concat([existente, df_pedido], ignore_index=True)
            conn.update(worksheet="Pedidos", data=actualizado)
            
            # 2. BLOQUEAR AL USUARIO en la hoja 'Autorizaciones'
            try:
                auth_existente = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
            except:
                auth_existente = pd.DataFrame(columns=["Email", "Estado"])
            
            # Agregamos el nuevo bloqueo
            nuevo_bloqueo = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
            auth_actualizada = pd.concat([auth_existente, nuevo_bloqueo], ignore_index=True)
            conn.update(worksheet="Autorizaciones", data=auth_actualizada)
            
            st.balloons()
            st.success("✅ Pedido enviado. Tu usuario ha sido bloqueado para nuevos pedidos.")
            st.session_state.carrito = []
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {e}")
