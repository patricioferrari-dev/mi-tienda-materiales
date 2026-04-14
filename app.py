import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="centered")

# CSS Profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. INICIALIZACIÓN DE ESTADOS
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
        st.error("⚠️ Error: Configura 'usuarios_autorizados' en Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    st.text_input("Correo Electrónico:", key="email_login", on_change=check_login)
    st.stop()

# 4. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 5. MENÚ PRINCIPAL
if st.session_state.seccion == "Menu":
    st.title("🏢 SGM - Panel de Gestión")
    st.write(f"Bienvenido técnico: **{st.session_state.email_usuario}**")
    st.divider()
    
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

# 6. VALIDACIONES EXCLUSIVAS PARA MATERIALES (L-M-V | 07:00 a 15:00)
if st.session_state.seccion == "Materiales":
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora_arg = datetime.now(tz_arg)
    
    dia_semana = ahora_arg.weekday() # 0=Lunes, 2=Miércoles, 4=Viernes
    hora_actual = ahora_arg.time()
    hora_inicio = datetime.strptime("07:00", "%H:%M").time()
    hora_fin = datetime.strptime("15:00", "%H:%M").time()

    if dia_semana not in [0, 2, 4] or not (hora_inicio <= hora_actual <= hora_fin):
        st.title("🕒 Sistema Cerrado")
        st.warning("Materiales solo disponible Lunes, Miércoles y Viernes de 07:00 a 15:00 hs.")
        if st.button("⬅️ Volver al Menú"):
            st.session_state.seccion = "Menu"
            st.rerun()
        st.stop()

    # Bloqueo por pedido realizado hoy
    try:
        df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
        if st.session_state.email_usuario in df_auth[df_auth['Estado'] == 'Bloqueado']['Email'].values:
            st.error("🚫 Ya realizaste un pedido de materiales en esta jornada.")
            if st.button("⬅️ Volver"):
                st.session_state.seccion = "Menu"
                st.rerun()
            st.stop()
    except:
        pass

# 7. LISTADO DE ARTÍCULOS
listas = {
    "Materiales": [
        "13008 CONTROL REMOTO SAGECOM", "30032 CABLE COAXIL RG6", "31025 PRECINTO NEGRO",
        "31026 TARUGO 8MM", "31027 PITON CON TOPE", "87025 CONECTOR RG6", "90002 PILA AAA"
    ],
    "Herramientas": [
        "H001 PINZA PUNTA", "H002 ALICATE", "H003 PELACABLE", "H004 TALADRO", "H005 CRIMPADORA"
    ],
    "Indumentaria": [
        "I001 PANTALON CARGO T44", "I002 CHOMBA LOGO L", "I003 BOTINES SEGURIDAD", "I004 CAMPERA"
    ]
}
items_disponibles = listas.get(st.session_state.seccion, [])

# 8. INTERFAZ DE CARGA
st.button("⬅️ Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"Solicitud de {st.session_state.seccion}")

tab_carga, tab_resumen = st.tabs(["📝 Cargar", "🛒 Mi Pedido"])

with tab_carga:
    with st.form("form_carga", clear_on_submit=True):
        seleccion = st.selectbox("Seleccione Artículo:", items_disponibles)
        
        # Motivos dinámicos
        motivo_envio = ""
        if st.session_state.seccion == "Herramientas":
            motivo_envio = st.radio("Motivo:", ["Cambio", "Perdido", "Nunca entregado"], horizontal=True)
        elif st.session_state.seccion == "Indumentaria":
            motivo_envio = st.radio("Motivo:", ["Desgaste", "Nunca entregado"], horizontal=True)
            
        cantidad = st.text_input("Cantidad:")
        
        if st.form_submit_button("➕ AÑADIR AL PEDIDO"):
            if cantidad.isdigit() and int(cantidad) > 0:
                codigo_nuevo = seleccion.split(" ", 1)[0]
                
                # Prohibir duplicados
                ya_esta = any(item['Codigo'] == codigo_nuevo for item in st.session_state.carrito)
                
                if ya_esta:
                    st.error(f"❌ El artículo {codigo_nuevo} ya está en el carrito.")
                else:
                    partes = seleccion.split(" ", 1)
                    st.session_state.carrito.append({
                        "Tecnico": st.session_state.email_usuario,
                        "Codigo": codigo_nuevo,
                        "Articulo": partes[1] if len(partes) > 1 else "",
                        "Cantidad": int(cantidad),
                        "Motivo": motivo_envio,
                        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    st.toast("¡Añadido!")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.error("Ingrese una cantidad válida.")

with tab_resumen:
    if not st.session_state.carrito:
        st.info("El carrito está vacío.")
    else:
        for i, item in enumerate(st.session_state.carrito):
            c1, c2, c3 = st.columns([3, 1, 0.5])
            c1.write(f"**{item['Codigo']}** - {item['Articulo']}")
            if item['Motivo']: c1.caption(f"Motivo: {item['Motivo']}")
            c2.write(f"Cant: {item['Cantidad']}")
            if c3.button("❌", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        if st.button("🚀 CONFIRMAR Y ENVIAR"):
            with st.spinner("Enviando..."):
                try:
                    df_envio = pd.DataFrame(st.session_state.carrito)
                    hoja = st.session_state.seccion
                    
                    # Leer y concatenar
                    try:
                        ex = conn.read(worksheet=hoja, ttl=0).dropna(how='all')
                        res = pd.concat([ex, df_envio], ignore_index=True)
                    except:
                        res = df_envio
                    
                    conn.update(worksheet=hoja, data=res)
                    
                    # Bloqueo si es materiales
                    if st.session_state.seccion == "Materiales":
                        try:
                            auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                        except:
                            auth = pd.DataFrame(columns=["Email", "Estado"])
                        nuevo = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
                        conn.update(worksheet="Autorizaciones", data=pd.concat([auth, nuevo], ignore_index=True))
                    
                    st.balloons()
                    st.success("¡Pedido enviado correctamente!")
                    st.session_state.carrito = []
                    time.sleep(2)
                    st.session_state.seccion = "Menu"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
