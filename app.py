import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión", page_icon="🏢", layout="centered")

# CSS Profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'seccion' not in st.session_state:
    st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

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
        st.error("⚠️ Error: Configura los correos en Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    st.text_input("Correo Electrónico:", key="email_login", on_change=check_login)
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- MENÚ PRINCIPAL ---
if st.session_state.seccion == "Menu":
    st.title("🏢 Sistema de Gestión")
    st.subheader(f"Bienvenido, {st.session_state.email_usuario}")
    st.write("Seleccione el tipo de pedido que desea realizar:")
    
    col1, col2, col3 = st.columns(3)
    
    if col1.button("📦\nMateriales"):
        st.session_state.seccion = "Materiales"
        st.rerun()
    
    if col2.button("🔧\nHerramientas"):
        st.session_state.seccion = "Herramientas"
        st.rerun()
        
    if col3.button("👕\nIndumentaria"):
        st.session_state.seccion = "Indumentaria"
        st.rerun()
    st.stop()

# --- LÓGICA ESPECÍFICA PARA MATERIALES (BLOQUEOS) ---
if st.session_state.seccion == "Materiales":
    # Validación de Horario
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    hora_actual = datetime.now(tz_arg).time()
    hora_inicio = datetime.strptime("07:00", "%H:%M").time()
    hora_fin = datetime.strptime("15:00", "%H:%M").time()

    if not (hora_inicio <= hora_actual <= hora_fin):
        st.title("🕒 Fuera de Horario")
        st.warning("El sistema de Materiales opera de 07:00 a 15:00 hs.")
        if st.button("Volver al Menú"):
            st.session_state.seccion = "Menu"
            st.rerun()
        st.stop()

    # Validación de Bloqueo por pedido previo
    try:
        df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
        if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
            st.title("🚫 Acceso Restringido")
            st.error("Ya has realizado un pedido de materiales hoy.")
            if st.button("Volver al Menú"):
                st.session_state.seccion = "Menu"
                st.rerun()
            st.stop()
    except:
        pass

# --- CONFIGURACIÓN DE LISTAS SEGÚN SECCIÓN ---
diccionario_listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"], # (Truncado por brevedad)
    "Herramientas": ["H001 Pinza de fuerza", "H002 Destornillador Phillips", "H003 Taladro Percutor"],
    "Indumentaria": ["I001 Pantalón Talle 42", "I002 Camisa Talle L", "I003 Botines Talle 43"]
}

items_disponibles = diccionario_listas.get(st.session_state.seccion, [])

# --- INTERFAZ DE CARGA ---
st.button("⬅️ Volver al Menú", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"📝 Pedido de {st.session_state.seccion}")

tab_carga, tab_resumen = st.tabs(["📝 Cargar", "🛒 Carrito"])

with tab_carga:
    with st.form("form_pedido", clear_on_submit=True):
        seleccion = st.selectbox("Seleccione Artículo:", items_disponibles)
        cantidad_str = st.text_input("Cantidad:")
        if st.form_submit_button("➕ AÑADIR"):
            if cantidad_str.isdigit() and int(cantidad_str) > 0:
                partes = seleccion.split(" ", 1)
                st.session_state.carrito.append({
                    "Tecnico": st.session_state.email_usuario,
                    "Codigo": partes[0],
                    "Articulo": partes[1] if len(partes) > 1 else "",
                    "Cantidad": int(cantidad_str),
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.toast("Añadido correctamente")
                st.rerun()

with tab_resumen:
    if not st.session_state.carrito:
        st.info("El carrito está vacío.")
    else:
        for i, item in enumerate(st.session_state.carrito):
            col_t, col_c, col_d = st.columns([3, 1, 0.5])
            col_t.write(f"{item['Codigo']} - {item['Articulo']}")
            col_c.write(f"x{item['Cantidad']}")
            if col_d.button("❌", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        if st.button("🚀 CONFIRMAR ENVÍO"):
            with st.spinner("Procesando..."):
                try:
                    df_nuevo = pd.DataFrame(st.session_state.carrito)
                    hoja_destino = st.session_state.seccion 
                    
                    # Intentar leer la hoja correspondiente
                    try:
                        # Se cierra correctamente el paréntesis de read()
                        existente = conn.read(worksheet=hoja_destino, ttl=0).dropna(how='all')
                        act_data = pd.concat([existente, df_nuevo], ignore_index=True)
                    except Exception:
                        # Si la hoja está vacía o no existe, el nuevo df es el inicial
                        act_data = df_nuevo
                    
                    # Actualizar la hoja en Google Sheets
                    conn.update(worksheet=hoja_destino, data=act_data)
                    
                    # Lógica de bloqueo solo para Materiales
                    if st.session_state.seccion == "Materiales":
                        try:
                            ex_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                        except Exception:
                            ex_auth = pd.DataFrame(columns=["Email", "Estado"])
                            
                        nuevo_b = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
                        act_auth = pd.concat([ex_auth, nuevo_b], ignore_index=True)
                        conn.update(worksheet="Autorizaciones", data=act_auth)
                    
                    st.success("¡Pedido enviado con éxito!")
                    st.session_state.carrito = []
                    time.sleep(2)
                    st.session_state.seccion = "Menu"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error crítico al guardar: {e}")
