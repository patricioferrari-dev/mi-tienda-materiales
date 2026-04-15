import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time
import re
import uuid

# 1. CONFIGURACIÓN DE PÁGINA Y CSS
st.set_page_config(page_title="SGM - Gestión de Pedidos", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 800px; padding-top: 1rem; }
    [data-testid="stForm"] { background-color: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; }
    [data-testid="stHorizontalBlock"] { gap: 0px !important; margin-bottom: -1px !important; }
    div[data-testid="stColumn"] { border: 1px solid #e2e8f0; padding: 2px 8px; background-color: white; min-height: 26px; display: flex; align-items: center; }
    .header-box { background-color: #475569; color: white; font-weight: 700; font-size: 10px; width: 100%; text-align: center; }
    .cell-data { font-size: 12px; color: #334155; margin: 0; line-height: 1.1; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES DE VALIDACIÓN Y AUDITORÍA
def registrar_log(usuario, dni, evento, seccion="-", detalle="-"):
    try:
        tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
        ahora = datetime.now(tz_ba).strftime("%d/%m/%Y %H:%M:%S")
        nuevo_log = pd.DataFrame([{
            "Fecha": ahora,
            "Usuario": usuario,
            "DNI": str(dni),
            "Evento": evento,
            "Seccion": seccion,
            "Detalle": detalle
        }])
        df_logs = conn.read(worksheet="Logs", ttl=0).dropna(how='all')
        conn.update(worksheet="Logs", data=pd.concat([df_logs, nuevo_log], ignore_index=True))
    except:
        pass 

def es_email_valido(email):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, email) is not None

def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    return 7 <= ahora.hour < 15

# Función crítica: Limpia el DNI de cualquier formato (.0, espacios, etc)
def limpiar_dni(valor):
    return str(valor).split('.')[0].replace(" ", "").strip()

# 3. ESTADOS DE SESIÓN
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'reestablecer' not in st.session_state: st.session_state.reestablecer = False
if 'user_a_reestablecer' not in st.session_state: st.session_state.user_a_reestablecer = None
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. SISTEMA DE ACCESO
if not st.session_state.autenticado:
    if st.session_state.reestablecer:
        st.title("🔑 Asignar Acceso")
        user = st.session_state.user_a_reestablecer
        dni_limpio_user = limpiar_dni(user['DNI'])
        st.info(f"Usuario: {user.get('Nombre')} {user.get('Apellido')} (DNI: {dni_limpio_user})")
        
        with st.form("form_reset"):
            n_mail = st.text_input("Asignar Email:").strip().lower()
            n_cel = st.text_input("Celular (10 dígitos):").strip()
            nueva_p = st.text_input("Nueva Contraseña:", type="password")
            confirm_p = st.text_input("Confirmar Contraseña:", type="password")
            
            if st.form_submit_button("GUARDAR Y ACTIVAR CUENTA"):
                cel_limpio = n_cel.replace(" ", "").replace("-", "")
                if not es_email_valido(n_mail): st.error("⚠️ Email no válido.")
                elif len(cel_limpio) != 10: st.error("⚠️ El celular debe tener 10 dígitos.")
                elif nueva_p != confirm_p: st.error("⚠️ Las contraseñas no coinciden.")
                else:
                    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
                    # Buscamos por DNI limpio para no fallar
                    idx = -1
                    for i, row in df_db.iterrows():
                        if limpiar_dni(row['DNI']) == dni_limpio_user:
                            idx = i
                            break
                    
                    if idx != -1:
                        df_db.at[idx, 'Contrasena'] = str(nueva_p)
                        df_db.at[idx, 'Email'] = str(n_mail)
                        df_db.at[idx, 'Celular'] = str(cel_limpio)
                        conn.update(worksheet="DB_Tecnicos", data=df_db)
                        registrar_log(f"{user.get('Nombre')} {user.get('Apellido')}", dni_limpio_user, "REGISTRO_EXITOSO", "Acceso", "Cuenta activada")
                        st.success("✅ Cuenta activada.")
                        st.session_state.reestablecer = False
                        time.sleep(2); st.rerun()

    elif st.session_state.modo_registro:
        st.title("📝 Registro de Usuario")
        with st.form("form_padron"):
            dni_input = st.text_input("DNI (Sin puntos):").strip().replace(".", "")
            if st.form_submit_button("VERIFICAR PADRÓN"):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
                encontrado = False
                for _, row in df_db.iterrows():
                    if limpiar_dni(row['DNI']) == dni_input:
                        encontrado = True
                        pass_existente = str(row.get('Contrasena', '')).strip().lower()
                        if pass_existente not in ["", "nan", "none"]:
                            st.error("⚠️ Este DNI ya tiene una cuenta activa.")
                        else:
                            st.session_state.user_a_reestablecer = row.to_dict()
                            st.session_state.reestablecer = True
                            st.session_state.modo_registro = False
                            st.rerun()
                        break
                if not encontrado: st.error("🚫 DNI no encontrado.")
        if st.button("⬅️ Volver"): st.session_state.modo_registro = False; st.rerun()

    else:
        st.title("🔐 Acceso SGM")
        u_id = st.text_input("Email o DNI:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        c1, c2 = st.columns(2)
        if c1.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
            user_match = None
            for _, row in db.iterrows():
                if str(row['Email']).lower() == u_id or limpiar_dni(row['DNI']) == u_id:
                    user_match = row
                    break
            
            if user_match is not None:
                real_pass = str(user_match.get('Contrasena', '')).strip()
                if real_pass.lower() in ["", "nan", "none"]:
                    st.session_state.user_a_reestablecer = user_match.to_dict()
                    st.session_state.reestablecer = True; st.rerun()
                elif real_pass == u_pass:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = user_match.to_dict()
                    registrar_log(f"{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}", u_id, "LOGIN_EXITOSO", "Acceso")
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
            else: st.error("Usuario no encontrado.")
        if c2.button("Registrarme", use_container_width=True): st.session_state.modo_registro = True; st.rerun()
    st.stop()

# 5. MENÚ PRINCIPAL
def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

PERMISOS = {
    "Materiales": ["3333333", "11111111", "1111111"],
    "Herramientas": ["3333333", "33333333", "1111111"],
    "Indumentaria": ["3333333", "55555555"],
    "Libreria": ["3333333", "1111111"],
    "Limpieza": ["3333333", "1111111"]
}

dni_actual = limpiar_dni(st.session_state.datos_usuario.get('DNI', ''))
nombre_completo = f"{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}"

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.info(f"Sesión iniciada: **{nombre_completo}**")
    
    accesos_reales = [sector for sector, dnis in PERMISOS.items() if dni_actual in dnis]

    if not accesos_reales:
        st.warning("⚠️ Sin permisos asignados.")
    else:
        filas = [accesos_reales[i:i + 3] for i in range(0, len(accesos_reales), 3)]
        for fila in filas:
            cols = st.columns(3)
            for i, sector in enumerate(fila):
                with cols[i]:
                    if sector == "Libreria":
                        if st.button("📚\nLIBRERÍA", use_container_width=True): cambiar_seccion("Insumos_Libreria"); st.rerun()
                    elif sector == "Limpieza":
                        if st.button("🧼\nLIMPIEZA", use_container_width=True): cambiar_seccion("Insumos_Limpieza"); st.rerun()
                    elif sector == "Materiales":
                        try:
                            # Lógica de Autorización robusta
                            df_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                            # Buscamos si existe el DNI y si su estado es OK
                            autorizado = False
                            for _, row in df_auth.iterrows():
                                if limpiar_dni(row['DNI']) == dni_actual and str(row.get('Estado', '')).lower() == "ok":
                                    autorizado = True
                                    break
                            
                            if not es_horario_permitido(): 
                                st.button("🔒\nMAT. (Horario)", disabled=True, use_container_width=True)
                            elif not autorizado: 
                                st.button("🚫\nMAT. (Bloqueado)", disabled=True, use_container_width=True)
                            else:
                                if st.button("📦\nMATERIALES", use_container_width=True): 
                                    cambiar_seccion("Materiales")
                                    st.rerun()
                        except Exception as e: 
                            st.error(f"Error en Autorizaciones: {e}")
                    
                    elif sector == "Herramientas":
                        if st.button("🔧\nHERRAMIENTAS", use_container_width=True): cambiar_seccion("Herramientas"); st.rerun()
                    elif sector == "Indumentaria":
                        if st.button("👕\nINDUMENTARIA", use_container_width=True): cambiar_seccion("Indumentaria"); st.rerun()

    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()
    st.stop()

# 6. PANEL DE CARGA
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 Sector: {st.session_state.seccion}")

# Listas de items (Mantenido igual)
listas = {"Materiales": ["13008 | CONTROL", "30032 | CABLE"], "Herramientas": ["ALICATE"]}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN"])

with tab1:
    with st.form("f_registro", clear_on_submit=True):
        sel = st.selectbox("Elegir Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        if st.form_submit_button("AGREGAR AL RESUMEN"):
            articulo_limpio = sel.split(" | ")[-1] if " | " in sel else sel
            st.session_state.carrito.append({
                "ID_Interno": str(uuid.uuid4())[:8],
                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "DNI": dni_actual,
                "Articulo": articulo_limpio, 
                "Cantidad": int(cant)
            })
            st.rerun()

with tab2:
    if not st.session_state.carrito:
        st.info("Resumen vacío.")
    else:
        # Mostrar carrito...
        st.write(pd.DataFrame(st.session_state.carrito))
        
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            with st.spinner("Enviando..."):
                try:
                    df_new = pd.DataFrame(st.session_state.carrito)
                    
                    # LLAMADA A LA FUNCIÓN DE REINTENTO (Ya definida arriba)
                    enviar_con_reintento(st.session_state.seccion, df_new)
                    
                    st.success("✅ Pedido enviado con éxito.")
                    st.session_state.carrito = []
                    time.sleep(1.5)
                    cambiar_seccion("Menu")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al enviar: {e}")
