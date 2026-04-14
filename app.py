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

# 3. CONEXIÓN Y LÓGICA DE ACCESO
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

# --- FLUJO DE LOGIN / REGISTRO / RESETEO ---
if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    
    if 'email_usuario' not in st.session_state:
        st.text_input("Correo Electrónico:", key="email_input", on_change=validar_email)
        st.stop()

    # Leer Base de Datos de Técnicos
    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
    # Forzar columnas críticas a texto para evitar TypeErrors de Pandas
    df_db['Email'] = df_db['Email'].astype(str)
    df_db['Contrasena'] = df_db['Contrasena'].astype(str)
    
    user_row = df_db[df_db['Email'] == st.session_state.email_usuario]

    if user_row.empty:
        # --- CASO: REGISTRO NUEVO ---
        st.warning(f"Hola {st.session_state.email_usuario}, completa tu registro:")
        with st.form("registro_nuevo"):
            col_a, col_b = st.columns(2)
            dni_input = col_a.text_input("DNI (puedes usar puntos):")
            nombre = col_b.text_input("Nombre:")
            apellido = col_a.text_input("Apellido:")
            celular = col_b.text_input("Celular:")
            password = st.text_input("Crea una Contraseña:", type="password")
            
            if st.form_submit_button("Validar y Finalizar Registro"):
                if all([nombre, apellido, dni_input, celular, password]):
                    dni_limpio = dni_input.replace(".", "").replace(" ", "").strip()
                    try:
                        # Validar contra Padrón oficial
                        df_padron = conn.read(worksheet="Padron_DNI", ttl=0).dropna(how='all')
                        lista_dnis = df_padron['DNI'].astype(str).str.replace(".0", "", regex=False).str.replace(".", "", regex=False).tolist()
                        
                        if dni_limpio in lista_dnis:
                            dni_formato = "{:,}".format(int(dni_limpio)).replace(",", ".")
                            nuevo_perfil = pd.DataFrame([{
                                "Email": st.session_state.email_usuario,
                                "Nombre": nombre.title(),
                                "Apellido": apellido.title(),
                                "Celular": celular,
                                "DNI": dni_formato,
                                "Contrasena": password
                            }])
                            conn.update(worksheet="DB_Tecnicos", data=pd.concat([df_db, nuevo_perfil], ignore_index=True))
                            st.success("✅ Registro exitoso.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ El DNI no figura en el padrón de personal autorizado.")
                    except Exception as e:
                        st.error(f"Error de validación: {e}")
                else:
                    st.error("Complete todos los campos.")
        st.stop()
    else:
        # --- CASO: USUARIO EXISTE ---
        datos_fila = user_row.iloc[0]
        pwd_db = str(datos_fila['Contrasena']).strip()

        # Verificar si la contraseña fue borrada (Reseteo)
        if pwd_db == "" or pwd_db.lower() in ["nan", "none"]:
            st.info(f"Hola {datos_fila['Nombre']}, tu contraseña ha sido reseteada. Genera una nueva:")
            with st.form("reset_pwd"):
                nueva_pwd = st.text_input("Nueva Contraseña:", type="password")
                confirmar_pwd = st.text_input("Confirmar Nueva Contraseña:", type="password")
                if st.form_submit_button("Actualizar"):
                    if nueva_pwd and nueva_pwd == confirmar_pwd:
                        # Evitar TypeError convirtiendo a object antes de asignar
                        df_db['Contrasena'] = df_db['Contrasena'].astype(object)
                        df_db.loc[df_db['Email'] == st.session_state.email_usuario, 'Contrasena'] = str(nueva_pwd)
                        conn.update(worksheet="DB_Tecnicos", data=df_db)
                        st.success("✅ Contraseña actualizada.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Las contraseñas no coinciden.")
            st.stop()
        else:
            # Login normal
            pwd_input = st.text_input(f"Hola {datos_fila['Nombre']}, ingresa tu contraseña:", type="password")
            if st.button("Ingresar"):
                if str(pwd_input) == pwd_db:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = datos_fila.to_dict()
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
            st.stop()

# 4. MENÚ PRINCIPAL
if st.session_state.seccion == "Menu":
    st.title("🏢 SGM - Panel de Gestión")
    st.markdown(f"Técnico: **{st.session_state.datos_usuario['Nombre']} {st.session_state.datos_usuario['Apellido']}**")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    if col1.button("📦\nMateriales"): st.session_state.seccion = "Materiales"; st.rerun()
    if col2.button("🔧\nHerramientas"): st.session_state.seccion = "Herramientas"; st.rerun()
    if col3.button("👕\nIndumentaria"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# 5. VALIDACIONES PARA MATERIALES (L-M-V)
if st.session_state.seccion == "Materiales":
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora_arg = datetime.now(tz_arg)
    if ahora_arg.weekday() not in [0, 2, 4] or not (7 <= ahora_arg.hour < 15):
        st.error("🕒 Materiales solo disponible L-M-V de 07:00 a 15:00 hs.")
        if st.button("⬅️ Volver"): st.session_state.seccion = "Menu"; st.rerun()
        st.stop()

# 6. DEFINICIÓN DE ARTÍCULOS
listas = {
    "Materiales": ["13008 CONTROL REMOTO", "30032 CABLE COAXIL", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA PUNTA", "H002 ALICATE", "H003 PELACABLE"],
    "Indumentaria": ["I001 PANTALON CARGO", "I002 CHOMBA TALLE L"]
}
items_disponibles = listas.get(st.session_state.seccion, [])

# 7. INTERFAZ DE CARGA
st.button("⬅️ Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"Solicitud: {st.session_state.seccion}")

tab_carga, tab_resumen = st.tabs(["📝 Cargar", "🛒 Mi Pedido"])

with tab_carga:
    with st.form("form_carga", clear_on_submit=True):
        seleccion = st.selectbox("Artículo:", items_disponibles)
        motivo = ""
        if st.session_state.seccion in ["Herramientas", "Indumentaria"]:
            opciones = ["Cambio", "Perdido", "Nunca entregado"] if st.session_state.seccion == "Herramientas" else ["Desgaste", "Nunca entregado"]
            motivo = st.radio("Motivo:", opciones, horizontal=True)
        cantidad = st.text_input("Cantidad:")
        
        if st.form_submit_button("➕ AÑADIR AL PEDIDO"):
            if cantidad.isdigit() and int(cantidad) > 0:
                cod = seleccion.split(" ", 1)[0]
                if any(i['Codigo'] == cod for i in st.session_state.carrito):
                    st.error(f"❌ El código {cod} ya está en el pedido.")
                else:
                    st.session_state.carrito.append({
                        "Nombre": st.session_state.datos_usuario['Nombre'],
                        "Apellido": st.session_state.datos_usuario['Apellido'],
                        "DNI": st.session_state.datos_usuario['DNI'],
                        "Celular": st.session_state.datos_usuario['Celular'],
                        "Codigo": cod,
                        "Articulo": seleccion.split(" ", 1)[1] if " " in seleccion else "",
                        "Cantidad": int(cantidad),
                        "Motivo": motivo,
                        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    st.rerun()
            else:
                st.error("Ingrese una cantidad válida.")

with tab_resumen:
    if not st.session_state.carrito:
        st.info("No hay artículos cargados.")
    else:
        for i, item in enumerate(st.session_state.carrito):
            col_x, col_y = st.columns([4, 1])
            col_x.write(f"**{item['Codigo']}** - {item['Articulo']} (Cant: {item['Cantidad']})")
            if col_y.button("❌", key=f"btn_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        if st.button("🚀 CONFIRMAR Y ENVIAR"):
            try:
                hoja = st.session_state.seccion
                df_envio = pd.DataFrame(st.session_state.carrito)
                existente = conn.read(worksheet=hoja, ttl=0).dropna(how='all')
                conn.update(worksheet=hoja, data=pd.concat([existente, df_envio], ignore_index=True))
                st.balloons()
                st.success("✅ Pedido enviado correctamente.")
                st.session_state.carrito = []
                st.session_state.seccion = "Menu"
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error al enviar: {e}")
