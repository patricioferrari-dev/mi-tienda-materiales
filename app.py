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
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. INICIALIZACIÓN DE ESTADOS
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'datos_usuario' not in st.session_state:
    st.session_state.datos_usuario = None
if 'seccion' not in st.session_state:
    st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 3. LÓGICA DE LOGIN Y PERFIL
conn = st.connection("gsheets", type=GSheetsConnection)

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

# --- VERIFICACIÓN DE PERFIL EN BASE DE DATOS ---
try:
    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
    user_info = df_db[df_db['Email'] == st.session_state.email_usuario]
    
    if user_info.empty:
        # REGISTRO POR PRIMERA VEZ
        st.title("📝 Registro de Técnico")
        st.warning("Es tu primer ingreso. Por favor, completa tus datos:")
        with st.form("registro_tecnico"):
            nombre = st.text_input("Nombre:")
            apellido = st.text_input("Apellido:")
            celular = st.text_input("Celular (con código de área):")
            if st.form_submit_button("Guardar Datos"):
                if nombre and apellido and celular:
                    nuevo_perfil = pd.DataFrame([{
                        "Email": st.session_state.email_usuario,
                        "Nombre": nombre.title(),
                        "Apellido": apellido.title(),
                        "Celular": celular
                    }])
                    # Actualizar hoja DB_Tecnicos
                    df_actualizado = pd.concat([df_db, nuevo_perfil], ignore_index=True)
                    conn.update(worksheet="DB_Tecnicos", data=df_actualizado)
                    st.success("Datos guardados. Reingresando...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Todos los campos son obligatorios.")
        st.stop()
    else:
        # Recuperar datos para el autocompletado
        st.session_state.datos_usuario = user_info.iloc[0].to_dict()
except Exception as e:
    st.error(f"Error cargando base de datos: {e}")
    st.stop()

# 4. MENÚ PRINCIPAL
if st.session_state.seccion == "Menu":
    st.title("🏢 SGM - Panel de Gestión")
    st.markdown(f"Técnico: **{st.session_state.datos_usuario['Nombre']} {st.session_state.datos_usuario['Apellido']}**")
    st.caption(f"📱 Cel: {st.session_state.datos_usuario['Celular']} | 📧 {st.session_state.email_usuario}")
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

# 5. VALIDACIONES PARA MATERIALES (L-M-V)
if st.session_state.seccion == "Materiales":
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora_arg = datetime.now(tz_arg)
    if ahora_arg.weekday() not in [0, 2, 4] or not (7 <= ahora_arg.hour < 15):
        st.title("🕒 Cerrado")
        st.warning("L-M-V de 07:00 a 15:00 hs.")
        if st.button("⬅️ Menú"):
            st.session_state.seccion = "Menu"
            st.rerun()
        st.stop()

# 6. LISTADO DE ARTÍCULOS (Acortado para el ejemplo)
listas = {
    "Materiales": ["13008 CONTROL REMOTO", "30032 CABLE COAXIL", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA PUNTA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON CARGO", "I002 CHOMBA L"]
}
items_disponibles = listas.get(st.session_state.seccion, [])

# 7. INTERFAZ DE CARGA
st.button("⬅️ Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"Solicitud: {st.session_state.seccion}")

tab_carga, tab_resumen = st.tabs(["📝 Cargar", "🛒 Mi Pedido"])

with tab_carga:
    with st.form("form_carga", clear_on_submit=True):
        seleccion = st.selectbox("Seleccione Artículo:", items_disponibles)
        motivo = ""
        if st.session_state.seccion in ["Herramientas", "Indumentaria"]:
            opciones = ["Cambio", "Perdido", "Nunca entregado"] if st.session_state.seccion == "Herramientas" else ["Desgaste", "Nunca entregado"]
            motivo = st.radio("Motivo:", opciones, horizontal=True)
            
        cantidad = st.text_input("Cantidad:")
        
        if st.form_submit_button("➕ AÑADIR"):
            if cantidad.isdigit() and int(cantidad) > 0:
                codigo = seleccion.split(" ", 1)[0]
                if any(item['Codigo'] == codigo for item in st.session_state.carrito):
                    st.error("Artículo ya en el carrito.")
                else:
                    st.session_state.carrito.append({
                        "Email": st.session_state.email_usuario,
                        "Nombre": st.session_state.datos_usuario['Nombre'],
                        "Apellido": st.session_state.datos_usuario['Apellido'],
                        "Celular": st.session_state.datos_usuario['Celular'],
                        "Codigo": codigo,
                        "Articulo": seleccion.split(" ", 1)[1],
                        "Cantidad": int(cantidad),
                        "Motivo": motivo,
                        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    st.rerun()

with tab_resumen:
    if not st.session_state.carrito:
        st.info("Carrito vacío.")
    else:
        for i, item in enumerate(st.session_state.carrito):
            st.write(f"**{item['Codigo']}** - {item['Articulo']} (x{item['Cantidad']})")
            if st.button("❌", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        if st.button("🚀 ENVIAR TODO"):
            try:
                hoja = st.session_state.seccion
                df_envio = pd.DataFrame(st.session_state.carrito)
                existente = conn.read(worksheet=hoja, ttl=0).dropna(how='all')
                conn.update(worksheet=hoja, data=pd.concat([existente, df_envio], ignore_index=True))
                
                # Bloqueo (Opcional si es Materiales)
                st.success("¡Pedido enviado!")
                st.session_state.carrito = []
                st.session_state.seccion = "Menu"
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
