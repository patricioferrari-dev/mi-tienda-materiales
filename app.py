import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦")

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def check_login():
    email_ingresado = st.session_state.email_login.lower().strip()
    # Obtenemos la lista desde los Secrets
    lista_blanca = st.secrets["usuarios_autorizados"]["emails"]
    
    if email_ingresado in [e.lower() for e in lista_blanca]:
        st.session_state.autenticado = True
    else:
        st.error("🚫 Este correo no está autorizado. Contacta al administrador.")

# Pantalla de Login
if not st.session_state.autenticado:
    st.title("🔐 Acceso Restringido")
    st.text_input("Ingresa tu email para continuar:", key="email_login", on_change=check_login)
    st.stop() # Detiene la ejecución aquí si no está autenticado

# --- SI LLEGA AQUÍ, ESTÁ AUTENTICADO ---

st.title("📦 Formulario de Pedidos Online")
st.write(f"Sesión iniciada como: **{st.session_state.email_login}**")

# Botón para cerrar sesión
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# --- CONFIGURACIÓN DE LISTAS ---
# Mantenemos tu lista de nombres para el Excel (o puedes usar el email directamente)
lista_tecnicos = [
    "Seleccionar...",
    "Juan Pérez",
    "Ricardo Gómez",
    "Marcos Rodríguez",
    "Esteban Quito",
    "Christian Díaz"
]

materiales_disponibles = [
    "13008 CONTROL REMOTO PARA DECO SAGECOM DCWMI303. CON BOT",
    "30032 CABLE COAXIL RG6 QUADSHIELD NEGRO CON PORTANTE",
    "31025 PRECINTO PLÁSTICO NEGRO (150 X 5.5 MM) , CON PROTE",
    "31026 TARUGO DE 8MM PARA LADRILLO HUECO",
    "31027 PITON CON TOPE PARA TARUGO DE 8MM",
    "32085 PASAPARED BLANCO PARA RG6",
    "32098 SILOC TRANSPARENTE CARTUCHO DE 300GR",
    "35042 PRECINTO S20 AZUL FO 2 VIAS",
    "51044 FUENTE P/DECO SAGEMCOM HD",
    "51046 Fuente alimentacion 12V-1,5A / SEI Robotics SEI800",
    "51051 FUENTE 3,1",
    "70016 CABLE DE RED UTP PARA PC (PATCHCORD)",
    "70098 CABLE HDMI",
    "70220 CABLE RCA A PLUG 3,5",
    "87025 CONECTOR DE COMPRESIÓN PARA RG6",
    "87026 O´RING PARA CONECTORES DE RG 6 (SELLO)",
    "87031 DIVISOR DE 3 BOCAS - SPLITTER X3",
    "90002 PILA AAA PARA CONTROL REMOTO",
    "90071 CINTA AUTOVULCANIZANTE",
    "90072 GRAMPA NEGRA CON CLAVO PARA INTERIOR (GRAMPITA)",
    "90090 DIVISOR DE 2 BOCAS",
    "90106 FILTRO PARA ALTOS 102 MHZ",
    "31154 Etiqueta de identificacion para Drop FO (Kit doble)",
    "012009U Fuente Alimentacion 12V - 1A / Extensor Wifi AIRTIES AIR4960X"
]

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# Bloqueo de nombre de técnico si hay items
esta_bloqueado = len(st.session_state.carrito) > 0
tecnico = st.selectbox("👷 Nombre del Técnico:", lista_tecnicos, disabled=esta_bloqueado)

# --- FORMULARIO DE ENTRADA ---
with st.form("formulario_pedido", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        seleccion = st.selectbox("Selecciona el artículo:", materiales_disponibles)
    with col2:
        cantidad = st.number_input("Cantidad:", min_value=1, step=1, value=None)
    
    boton_agregar = st.form_submit_button("Agregar al pedido")
    
    if boton_agregar:
        if tecnico == "Seleccionar...":
            st.error("⚠️ Selecciona tu nombre de técnico.")
        elif cantidad is None:
            st.error("⚠️ Ingresa una cantidad.")
        else:
            partes = seleccion.split(" ", 1)
            cod = partes[0]
            nom = partes[1] if len(partes) > 1 else ""

            st.session_state.carrito.append({
                "Tecnico": tecnico,
                "Codigo": cod,
                "Articulo": nom,
                "Cantidad": cantidad,
                "Email_Validado": st.session_state.email_login # Agregamos el email al registro
            })
            st.rerun()

# --- RESUMEN Y ENVÍO ---
if st.session_state.carrito:
    st.subheader(f"🛒 Pedido actual: {tecnico}")
    df_pedido = pd.DataFrame(st.session_state.carrito)
    st.table(df_pedido)
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Borrar todo"):
            st.session_state.carrito = []
            st.rerun()

    with col_b:
        if st.button("🚀 ENVIAR PEDIDO"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                try:
                    existente = conn.read(worksheet="Pedidos", ttl=0)
                    existente = existente.dropna(how='all')
                except Exception:
                    # Agregamos la columna Email_Validado al Excel
                    existente = pd.DataFrame(columns=["Tecnico", "Codigo", "Articulo", "Cantidad", "Email_Validado"])
                
                actualizado = pd.concat([existente, df_pedido], ignore_index=True)
                conn.update(worksheet="Pedidos", data=actualizado)
                
                st.balloons()
                st.success("✅ ¡Enviado!")
                st.session_state.carrito = []
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("Carga materiales para comenzar.")
