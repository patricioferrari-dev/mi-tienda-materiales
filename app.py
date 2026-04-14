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

# 3. LÓGICA DE ACCESO Y CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

def validar_email():
    email = st.session_state.email_input.lower().strip()
    try:
        lista_autorizados = st.secrets["usuarios_autorizados"]["emails"]
        if email in [e.lower() for e in lista_autorizados]:
            st.session_state.email_usuario = email
        else:
            st.error("🚫 Correo no autorizado en la lista blanca.")
    except:
        st.error("⚠️ Error: Configura 'usuarios_autorizados' en Secrets.")

# --- FLUJO DE LOGIN / REGISTRO ---
if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if 'email_usuario' not in st.session_state:
        st.text_input("Correo Electrónico:", key="email_input", on_change=validar_email)
        st.stop()

    # Leer DB de técnicos registrados y el Padrón de DNIs autorizados
    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
    user_info = df_db[df_db['Email'] == st.session_state.email_usuario]

    if user_info.empty:
        # --- PROCESO DE REGISTRO ---
        st.warning(f"Hola {st.session_state.email_usuario}, no estás registrado. Completa tus datos:")
        
        with st.form("registro_nuevo"):
            col_a, col_b = st.columns(2)
            dni_reg = col_a.text_input("DNI (Sin puntos):")
            nombre = col_b.text_input("Nombre:")
            apellido = col_a.text_input("Apellido:")
            celular = col_b.text_input("Celular:")
            password = st.text_input("Crea una Contraseña:", type="password")
            
            if st.form_submit_button("Validar y Finalizar Registro"):
                if all([nombre, apellido, dni_reg, celular, password]):
                    # VALIDACIÓN DE DNI CONTRA EL PADRÓN
                    try:
                        df_padron = conn.read(worksheet="Padron_DNI", ttl=0).dropna(how='all')
                        # Convertimos a string para comparar sin errores de tipo
                        lista_dnis_validos = df_padron['DNI'].astype(str).tolist()
                        
                        if dni_reg.strip() in lista_dnis_validos:
                            # Proceder al registro
                            nuevo_perfil = pd.DataFrame([{
                                "Email": st.session_state.email_usuario,
                                "Nombre": nombre.title(),
                                "Apellido": apellido.title(),
                                "Celular": celular,
                                "DNI": dni_reg.strip(),
                                "Contrasena": password
                            }])
                            df_actualizado = pd.concat([df_db, nuevo_perfil], ignore_index=True)
                            conn.update(worksheet="DB_Tecnicos", data=df_actualizado)
                            st.success("✅ DNI Verificado. Registro exitoso.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ El DNI ingresado no figura en el padrón de personal autorizado. Contacte al supervisor.")
                    except Exception as e:
                        st.error(f"Error al validar DNI: {e}")
                else:
                    st.error("Todos los campos son obligatorios.")
        st.stop()
    else:
        # --- PROCESO DE LOGIN ---
        pwd_input = st.text_input(f"Hola {user_info.iloc[0]['Nombre']}, ingresa tu contraseña:", type="password")
        if st.button("Ingresar"):
            if str(pwd_input) == str(user_info.iloc[0]['Contrasena']):
                st.session_state.autenticado = True
                st.session_state.datos_usuario = user_info.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta.")
        st.stop()

# 4. MENÚ PRINCIPAL
if st.session_state.seccion == "Menu":
    st.title("🏢 SGM - Panel de Gestión")
    st.markdown(f"Bienvenido: **{st.session_state.datos_usuario['Nombre']} {st.session_state.datos_usuario['Apellido']}**")
    st.caption(f"🆔 DNI: {st.session_state.datos_usuario['DNI']} | 📱 Cel: {st.session_state.datos_usuario['Celular']}")
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

# 5. VALIDACIONES PARA MATERIALES (L-M-V | 07:00 a 15:00)
if st.session_state.seccion == "Materiales":
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora_arg = datetime.now(tz_arg)
    if ahora_arg.weekday() not in [0, 2, 4] or not (7 <= ahora_arg.hour < 15):
        st.error("🕒 Materiales solo L-M-V de 07:00 a 15:00 hs.")
        if st.button("⬅️ Menú"):
            st.session_state.seccion = "Menu"
            st.rerun()
        st.stop()

# 6. LISTAS DE ARTÍCULOS
listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE", "H003 PELACABLE"],
    "Indumentaria": ["I001 PANTALON T42", "I002 CHOMBA L"]
}
items_disponibles = listas.get(st.session_state.seccion, [])

# 7. INTERFAZ DE CARGA
st.button("⬅️ Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"Sección: {st.session_state.seccion}")

tab_carga, tab_resumen = st.tabs(["📝 Cargar", "🛒 Mi Pedido"])

with tab_carga:
    with st.form("form_p", clear_on_submit=True):
        seleccion = st.selectbox("Artículo:", items_disponibles)
        motivo = ""
        if st.session_state.seccion in ["Herramientas", "Indumentaria"]:
            opciones = ["Cambio", "Perdido", "Nunca entregado"] if st.session_state.seccion == "Herramientas" else ["Desgaste", "Nunca entregado"]
            motivo = st.radio("Motivo:", opciones, horizontal=True)
        
        cantidad = st.text_input("Cantidad:")
        
        if st.form_submit_button("➕ AÑADIR"):
            if cantidad.isdigit() and int(cantidad) > 0:
                codigo = seleccion.split(" ", 1)[0]
                if any(i['Codigo'] == codigo for i in st.session_state.carrito):
                    st.error("Ya está en el carrito.")
                else:
                    st.session_state.carrito.append({
                        "Nombre": st.session_state.datos_usuario['Nombre'],
                        "Apellido": st.session_state.datos_usuario['Apellido'],
                        "DNI": st.session_state.datos_usuario['DNI'],
                        "Celular": st.session_state.datos_usuario['Celular'],
                        "Codigo": codigo,
                        "Articulo": seleccion.split(" ", 1)[1] if " " in seleccion else "",
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
                
                st.success("¡Pedido enviado!")
                st.session_state.carrito = []
                st.session_state.seccion = "Menu"
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
