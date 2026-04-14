import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN DE PÁGINA (Debe ser la primera instrucción)
st.set_page_config(page_title="SGM - Gestión de Materiales", page_icon="🏢", layout="centered")

# CSS para profesionalizar la interfaz
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. INICIALIZACIÓN DE ESTADOS DE SESIÓN
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'seccion' not in st.session_state:
    st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 3. LÓGICA DE LOGIN
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
    st.info("Ingresa tu correo para continuar.")
    st.text_input("Correo Electrónico:", key="email_login", on_change=check_login)
    st.stop()

# 4. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 5. MENÚ PRINCIPAL
if st.session_state.seccion == "Menu":
    st.title("🏢 Sistema de Gestión Logística")
    st.caption(f"👷 Usuario: {st.session_state.email_usuario}")
    st.subheader("¿Qué desea solicitar?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📦\nMateriales"):
            st.session_state.seccion = "Materiales"
            st.rerun()
    with col2:
        if st.button("🔧\nHerramientas"):
            st.session_state.seccion = "Herramientas"
            st.rerun()
    with col3:
        if st.button("👕\nIndumentaria"):
            st.session_state.seccion = "Indumentaria"
            st.rerun()
    st.stop()

# 6. VALIDACIONES EXCLUSIVAS PARA MATERIALES
if st.session_state.seccion == "Materiales":
    # Validación Horaria
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora_arg = datetime.now(tz_arg)
    hora_actual = ahora_arg.time()
    hora_inicio = datetime.strptime("07:00", "%H:%M").time()
    hora_fin = datetime.strptime("15:00", "%H:%M").time()

    if not (hora_inicio <= hora_actual <= hora_fin):
        st.title("🕒 Fuera de Horario")
        st.warning("El sistema de Materiales solo opera de 07:00 a 15:00 hs.")
        if st.button("⬅️ Volver al Menú"):
            st.session_state.seccion = "Menu"
            st.rerun()
        st.stop()

    # Validación de Bloqueo por pedido previo
    try:
        df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
        if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
            st.title("🚫 Acceso Restringido")
            st.error("Ya has realizado un pedido de materiales hoy.")
            if st.button("⬅️ Volver al Menú"):
                st.session_state.seccion = "Menu"
                st.rerun()
            st.stop()
    except:
        pass

# 7. DEFINICIÓN DE LISTAS DE ARTÍCULOS
listas = {
    "Materiales": [
        "13008 CONTROL REMOTO SAGECOM", "30032 CABLE COAXIL RG6", "31025 PRECINTO NEGRO",
        "31026 TARUGO 8MM", "31027 PITON CON TOPE", "32085 PASAPARED RG6",
        "32098 SILOC TRANSPARENTE", "35042 PRECINTO S20", "51044 FUENTE DECO HD",
        "70016 CABLE RED UTP", "70098 CABLE HDMI", "87025 CONECTOR RG6",
        "87031 DIVISOR 3 BOCAS", "90002 PILA AAA", "90090 DIVISOR 2 BOCAS"
    ],
    "Herramientas": [
        "H001 PINZA DE PUNTA", "H002 ALICATE", "H003 PELACABLE COAXIL",
        "H004 CRIMPADORA RG6", "H005 TALADRO A BATERIA"
    ],
    "Indumentaria": [
        "I001 PANTALON CARGO T42", "I002 PANTALON CARGO T44", "I003 CHOMBA LOGO L",
        "I004 CHOMBA LOGO XL", "I005 CAMPERA TERMICA", "I006 BOTINES SEGURIDAD"
    ]
}

items_disponibles = listas.get(st.session_state.seccion, [])

# 8. INTERFAZ DE CARGA DE PEDIDO
st.button("⬅️ Volver al Menú", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"Sección: {st.session_state.seccion}")

tab_carga, tab_resumen = st.tabs(["📝 Cargar Material", "🛒 Ver mi Pedido"])

with tab_carga:
    with st.form("formulario_pedido", clear_on_submit=True):
        seleccion = st.selectbox("Artículo:", items_disponibles)
        
        # Campo de Motivo (Solo para Herramientas e Indumentaria)
        motivo_form = ""
        if st.session_state.seccion == "Herramientas":
            motivo_form = st.radio("Motivo:", ["Cambio", "Perdido", "Nunca entregado"], horizontal=True)
        elif st.session_state.seccion == "Indumentaria":
            motivo_form = st.radio("Motivo:", ["Desgaste", "Nunca entregado"], horizontal=True)
            
        cantidad_str = st.text_input("Cantidad:", placeholder="Ej: 1")
        
        if st.form_submit_button("➕ AÑADIR AL PEDIDO"):
            if cantidad_str.isdigit() and int(cantidad_str) > 0:
                partes = seleccion.split(" ", 1)
                st.session_state.carrito.append({
                    "Tecnico": st.session_state.email_usuario,
                    "Codigo": partes[0],
                    "Articulo": partes[1] if len(partes) > 1 else "",
                    "Cantidad": int(cantidad_str),
                    "Motivo": motivo_form,
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                st.toast(f"Añadido: {partes[0]}", icon="✅")
                st.rerun()
            else:
                st.error("Ingrese una cantidad válida mayor a 0.")

with tab_resumen:
    if not st.session_state.carrito:
        st.info("Tu pedido está vacío.")
    else:
        for i, item in enumerate(st.session_state.carrito):
            col_txt, col_cant, col_del = st.columns([3, 1, 0.5])
            with col_txt:
                st.write(f"**{item['Codigo']}** - {item['Articulo']}")
                if item['Motivo']: st.caption(f"Motivo: {item['Motivo']}")
            col_cant.write(f"Cant: {item['Cantidad']}")
            if col_del.button("❌", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        st.divider()
        
        if st.button("🚀 CONFIRMAR Y ENVIAR TODO"):
            with st.spinner("Guardando pedido..."):
                try:
                    df_final = pd.DataFrame(st.session_state.carrito)
                    hoja_destino = st.session_state.seccion 
                    
                    # 1. Guardar en la hoja correspondiente
                    try:
                        existente = conn.read(worksheet=hoja_destino, ttl=0).dropna(how='all')
                        act_pedidos = pd.concat([existente, df_final], ignore_index=True)
                    except:
                        act_pedidos = df_final
                    
                    conn.update(worksheet=hoja_destino, data=act_pedidos)
                    
                    # 2. Registrar Bloqueo SOLO si es Materiales
                    if st.session_state.seccion == "Materiales":
                        try:
                            ex_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                        except:
                            ex_auth = pd.DataFrame(columns=["Email", "Estado"])
                        nuevo_b = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
                        conn.update(worksheet="Autorizaciones", data=pd.concat([ex_auth, nuevo_b], ignore_index=True))
                    
                    st.balloons()
                    st.success("✅ Pedido enviado con éxito.")
                    st.session_state.carrito = []
                    time.sleep(2)
                    st.session_state.seccion = "Menu"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error crítico de conexión: {e}")
