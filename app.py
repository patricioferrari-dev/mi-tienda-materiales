import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦", layout="centered")

# CSS para ocultar menús
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .stButton > button {padding: 2px 10px; border-radius: 5px;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

# --- LÓGICA DE HORARIO (07:00 A 15:00 ARGENTINA) ---
tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
ahora_arg = datetime.now(tz_arg)
hora_actual = ahora_arg.time()

# Definimos los límites
hora_inicio = datetime.strptime("07:00", "%H:%M").time()
hora_fin = datetime.strptime("15:00", "%H:%M").time()

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def check_login():
    email = st.session_state.email_login.lower().strip()
    try:
        lista = st.secrets["usuarios_autorizados"]["emails"]
        if email in [e.lower() for e in lista]:
            st.session_state.autenticado = True
            st.session_state.email_usuario = email
        else:
            st.error("🚫 Correo no autorizado.")
    except:
        st.error("⚠️ Error en Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    st.text_input("Ingresa tu Email:", key="email_login", on_change=check_login)
    st.stop()

# --- VALIDACIÓN DE RANGO HORARIO ---
# Si la hora actual NO está entre las 07:00 y las 15:00, bloqueamos.
if not (hora_inicio <= hora_actual <= hora_fin):
    st.title("🕒 Sistema Fuera de Horario")
    st.warning(f"Hola {st.session_state.email_usuario}. El sistema opera de **07:00 a 15:00 hs**.")
    st.info(f"Hora actual en Argentina: **{hora_actual.strftime('%H:%M')}**")
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- VERIFICAR BLOQUEO POR PEDIDO PREVIO ---
try:
    df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
    if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
        st.title("🚫 Acceso Restringido")
        st.error("Ya registraste un pedido hoy. Acceso pausado hasta mañana.")
        st.stop()
except:
    pass

# --- FORMULARIO DE CARGA ---
st.title("📦 Formulario de Pedidos")
st.success(f"👷 Técnico: **{st.session_state.email_usuario}**")

materiales_disponibles = [
    "13008 CONTROL REMOTO PARA DECO SAGECOM DCWMI303. CON BOT",
    "30032 CABLE COAXIL RG6 QUADSHIELD NEGRO CON PORTANTE",
    "31025 PRECINTO PLÁSTICO NEGRO (150 X 5.5 MM)",
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

with st.form("formulario_pedido", clear_on_submit=True):
    col_art, col_cant = st.columns([3, 1])
    with col_art:
        seleccion = st.selectbox("Artículo:", materiales_disponibles)
    with col_cant:
        cantidad_str = st.text_input("Cant:", placeholder="0")
    
    if st.form_submit_button("➕ AGREGAR AL RESUMEN"):
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
                st.error("Mínimo 1")
        except ValueError:
            st.error("Ingresa un número")

# --- RESUMEN CON X PARA ELIMINAR ---
if st.session_state.carrito:
    st.markdown("---")
    st.subheader("🛒 Tu Pedido")
    for i, item in enumerate(st.session_state.carrito):
        c1, c2, c3 = st.columns([3, 1, 0.5])
        c1.write(f"{item['Codigo']} - {item['Articulo']}")
        c2.write(f"{item['Cantidad']}")
        if c3.button("❌", key=f"btn_{i}"):
            st.session_state.carrito.pop(i)
            st.rerun()

    st.markdown("---")
    if st.button("🚀 ENVIAR PEDIDO COMPLETO"):
        try:
            df_final = pd.DataFrame(st.session_state.carrito)
            
            # 1. Guardar Pedidos
            try:
                existente = conn.read(worksheet="Pedidos", ttl=0).dropna(how='all')
            except:
                existente = pd.DataFrame(columns=["Tecnico", "Codigo", "Articulo", "Cantidad"])
                
            act_pedidos = pd.concat([existente, df_final], ignore_index=True)
            conn.update(worksheet="Pedidos", data=act_pedidos)
            
            # 2. Registrar Bloqueo
            try:
                ex_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
            except:
                ex_auth = pd.DataFrame(columns=["Email", "Estado"])
            
            nuevo_b = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
            act_auth = pd.concat([ex_auth, nuevo_b], ignore_index=True)
            conn.update(worksheet="Autorizaciones", data=act_auth)
            
            st.balloons()
            st.success("✅ ¡Enviado!")
            st.session_state.carrito = []
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
