st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)








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
        else:
            st.error("🚫 Correo no autorizado.")
    except Exception:
        st.error("⚠️ Error: Configura los correos en los Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    st.text_input("Email:", key="email_login", on_change=check_login)
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection)

# Verificación de Bloqueo
try:
    df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
    if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
        st.title("🚫 Acceso Restringido")
        st.warning(f"Hola {st.session_state.email_usuario}, ya registraste un pedido.")
        st.stop()
except Exception:
    pass

st.title("📦 Formulario de Pedidos")
st.success(f"👷 Técnico: **{st.session_state.email_usuario}**")

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

# --- EL TRUCO PARA LA FLUIDEZ ---
# Al poner el selectbox fuera del form (o con on_change), obligamos al usuario a interactuar.
# Aquí lo mantenemos simple para que no pierdas el estilo:

with st.form("formulario_pedido", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        # El cambio de artículo no saltará solo, pero el diseño invita a seguir a la derecha.
        seleccion = st.selectbox("1. Selecciona Artículo:", materiales_disponibles)
    with col2:
        # El placeholder ayuda a saber que este es el siguiente paso.
        cantidad_str = st.text_input("2. Cantidad:", placeholder="Escribe aquí...")
    
    if st.form_submit_button("➕ AGREGAR AL PEDIDO"):
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

# Resumen y Envío
if st.session_state.carrito:
    st.subheader("🛒 Resumen")
    df_pedido = pd.DataFrame(st.session_state.carrito)
    st.table(df_pedido)
    
    if st.button("🚀 ENVIAR Y FINALIZAR"):
        try:
            # Guardar Pedidos
            try:
                existente = conn.read(worksheet="Pedidos", ttl=0).dropna(how='all')
            except Exception:
                existente = pd.DataFrame(columns=["Tecnico", "Codigo", "Articulo", "Cantidad"])
            
            actualizado = pd.concat([existente, df_pedido], ignore_index=True)
            conn.update(worksheet="Pedidos", data=actualizado)
            
            # Bloquear
            try:
                auth_ex = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
            except Exception:
                auth_ex = pd.DataFrame(columns=["Email", "Estado"])
            
            nuevo_b = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
            auth_act = pd.concat([auth_ex, nuevo_b], ignore_index=True)
            conn.update(worksheet="Autorizaciones", data=auth_act)
            
            st.balloons()
            st.success("✅ Pedido enviado y acceso bloqueado.")
            st.session_state.carrito = []
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
