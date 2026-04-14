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

def check_login():
    email_ingresado = st.session_state.email_login.lower().strip()
    try:
        lista_blanca = st.secrets["usuarios_autorizados"]["emails"]
        if email_ingresado in [e.lower() for e in lista_blanca]:
            st.session_state.autenticado = True
            st.session_state.email_usuario = email_ingresado
    except:
        st.error("Error en Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    st.text_input("Email:", key="email_login", on_change=check_login)
    st.stop()

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# --- VERIFICACIÓN DE BLOQUEO ---
try:
    df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
    if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
        st.warning("⚠️ Usuario bloqueado. Pedido ya realizado.")
        st.stop()
except:
    pass

st.title("📦 Formulario de Pedidos")
st.caption(f"Conectado como: {st.session_state.email_usuario}")

# --- LISTA DE MATERIALES ---
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

# --- TRUCO DE FLUIDEZ: SELECCIÓN FUERA DEL FORMULARIO ---
# Al seleccionar aquí, la app se recarga y el foco baja al siguiente input
seleccion = st.selectbox("1. Selecciona el artículo:", ["--- Elegir material ---"] + materiales_disponibles)

if seleccion != "--- Elegir material ---":
    # Formulario solo para la cantidad y el botón
    with st.form("form_cantidad", clear_on_submit=True):
        # El text_input vacío permite escribir de inmediato
        cantidad_str = st.text_input("2. Escribe la cantidad:", placeholder="Ingresa número...")
        
        btn_agregar = st.form_submit_button("➕ AGREGAR AL CARRITO")
        
        if btn_agregar:
            try:
                can_num = int(cantidad_str)
                if can_num > 0:
                    partes = seleccion.split(" ", 1)
                    st.session_state.carrito.append({
                        "Tecnico": st.session_state.email_usuario,
                        "Codigo": partes[0],
                        "Articulo": partes[1] if len(partes) > 1 else "",
                        "Cantidad": can_num
                    })
                    st.success(f"Añadido: {partes[0]}")
                    st.rerun() # Esto limpia el formulario y vuelve arriba
                else:
                    st.error("Mínimo 1")
            except ValueError:
                st.error("Escribe solo números")

# --- RESUMEN Y ENVÍO ---
if st.session_state.carrito:
    st.divider()
    st.subheader("🛒 Tu pedido actual")
    df_p = pd.DataFrame(st.session_state.carrito)
    st.table(df_p)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Vaciar"):
            st.session_state.carrito = []
            st.rerun()
    with col2:
        if st.button("🚀 ENVIAR Y BLOQUEAR ACCESO"):
            try:
                # Guardar Pedidos
                ex_ped = conn.read(worksheet="Pedidos", ttl=0).dropna(how='all')
                act_ped = pd.concat([ex_ped, df_p], ignore_index=True)
                conn.update(worksheet="Pedidos", data=act_ped)
                
                # Bloquear Usuario
                try:
                    ex_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                except:
                    ex_auth = pd.DataFrame(columns=["Email", "Estado"])
                
                nuevo_b = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
                act_auth = pd.concat([ex_auth, nuevo_b], ignore_index=True)
                conn.update(worksheet="Autorizaciones", data=act_auth)
                
                st.balloons()
                st.session_state.carrito = []
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
