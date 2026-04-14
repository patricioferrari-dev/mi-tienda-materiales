import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración básica
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦")

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def check_login():
    email = st.session_state.email_login.lower().strip()
    try:
        lista = st.secrets["usuarios_autorizados"]["emails"]
        if email in [e.lower() for e in lista]:
            st.session_state.autenticado = True
            st.session_state.email_usuario = email
    except:
        st.error("Error en configuración de correos.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    st.text_input("Email:", key="email_login", on_change=check_login)
    st.stop()

# --- CONEXIÓN Y BLOQUEO ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
    if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
        st.warning("⚠️ Ya realizaste un pedido. Acceso bloqueado.")
        st.stop()
except:
    pass

st.title("📦 Formulario de Pedidos")

# --- LISTA DE MATERIALES ---
materiales = [
    "--- Seleccionar artículo ---",
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

# --- CARGA DINÁMICA (SIN FORMULARIO PARA GANAR FLUIDEZ) ---
col1, col2 = st.columns([2, 1])

with col1:
    # El usuario elige el artículo
    art_sel = st.selectbox("Artículo:", materiales, key="sel_art")

with col2:
    # Solo si eligió algo distinto al mensaje inicial, habilitamos la cantidad
    if art_sel != "--- Seleccionar artículo ---":
        cant_input = st.text_input("Cantidad:", key="cant_input", placeholder="Ej: 5")
        
        if cant_input: # Si escribió algo, aparece el botón
            if st.button("➕ AGREGAR"):
                try:
                    c_num = int(cant_input)
                    partes = art_sel.split(" ", 1)
                    st.session_state.carrito.append({
                        "Tecnico": st.session_state.email_usuario,
                        "Codigo": partes[0],
                        "Articulo": partes[1] if len(partes) > 1 else "",
                        "Cantidad": c_num
                    })
                    st.rerun() # Limpia todo para el siguiente artículo
                except:
                    st.error("Usa números")

# --- RESUMEN Y ENVÍO ---
if st.session_state.carrito:
    st.subheader("🛒 Pedido actual")
    df_pedido = pd.DataFrame(st.session_state.carrito)
    st.table(df_pedido)
    
    if st.button("🚀 ENVIAR PEDIDO Y FINALIZAR"):
        try:
            # Guardar Pedidos
            ex_p = conn.read(worksheet="Pedidos", ttl=0).dropna(how='all')
            nuevo_p = pd.concat([ex_p, df_pedido], ignore_index=True)
            conn.update(worksheet="Pedidos", data=nuevo_p)
            
            # Registrar Bloqueo
            try:
                ex_a = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
            except:
                ex_a = pd.DataFrame(columns=["Email", "Estado"])
            
            bloqueo = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
            nueva_a = pd.concat([ex_a, bloqueo], ignore_index=True)
            conn.update(worksheet="Autorizaciones", data=nueva_a)
            
            st.balloons()
            st.session_state.carrito = []
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
