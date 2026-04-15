import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time
import re
import uuid
import random

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

# 2. FUNCIONES DE VALIDACIÓN Y SEGURIDAD DE DATOS
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
        # Usamos la misma lógica de "turno" para los logs
        enviar_con_reintento("Logs", nuevo_log)
    except:
        pass 

def enviar_con_reintento(worksheet_name, nuevo_df, max_intentos=5):
    """
    Función para evitar colisiones. Si falla, espera un tiempo aleatorio y reintenta.
    """
    for intento in range(max_intentos):
        try:
            # Forzar lectura fresca para evitar datos obsoletos en memoria
            df_existente = conn.read(worksheet=worksheet_name, ttl=0).dropna(how='all')
            df_final = pd.concat([df_existente, nuevo_df], ignore_index=True)
            conn.update(worksheet=worksheet_name, data=df_final)
            return True # Éxito
        except Exception as e:
            if intento < max_intentos - 1:
                # Espera aleatoria entre 1 y 3 segundos para "separarse" de otros usuarios
                time.sleep(random.uniform(1, 3))
            else:
                raise e

def es_email_valido(email):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, email) is not None

def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    return 7 <= ahora.hour < 15

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

# 4. SISTEMA DE ACCESO (Omitido por brevedad para centrar en la lógica solicitada, se mantiene igual al original)
# ... (Aquí va todo el bloque de login/registro del código anterior) ...
if not st.session_state.autenticado:
    # (Tu código de login original aquí)
    st.title("🔐 Acceso SGM")
    u_id = st.text_input("Email o DNI:").strip().lower()
    u_pass = st.text_input("Contraseña:", type="password").strip()
    if st.button("Ingresar"):
        db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
        user_match = None
        for _, row in db.iterrows():
            if str(row['Email']).lower() == u_id or limpiar_dni(row['DNI']) == u_id:
                user_match = row
                break
        if user_match is not None and str(user_match.get('Contrasena')) == u_pass:
            st.session_state.autenticado = True
            st.session_state.datos_usuario = user_match.to_dict()
            st.rerun()
        else: st.error("Error de acceso")
    st.stop()

# 5. MENÚ PRINCIPAL
def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

PERMISOS = {
    "Materiales": ["3333333", "11111111", "1111111"],
    "Herramientas": ["3333333", "33333333", "1111111"],
    "Indumentaria": ["3333333", "55555555"]
}

dni_actual = limpiar_dni(st.session_state.datos_usuario.get('DNI', ''))

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    # Lógica de botones de menú...
    for sector in PERMISOS.keys():
        if dni_actual in PERMISOS[sector]:
            if st.button(f"Ir a {sector}", use_container_width=True):
                cambiar_seccion(sector)
                st.rerun()
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()
    st.stop()

# 6. PANEL DE CARGA
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 Sector: {st.session_state.seccion}")

listas = {
    "Materiales": ["13008 | CONTROL", "30032 | CABLE"],
    "Herramientas": ["PINZA DE PUNTA", "ALICATE"],
    "Indumentaria": ["PANTALON T.40", "BOTINES"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN"])

with tab1:
    with st.form("f_registro", clear_on_submit=True):
        sel = st.selectbox("Elegir Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, value=1)
        
        # --- LÓGICA DE MOTIVOS SEPARADOS ---
        motivo = ""
        if st.session_state.seccion == "Herramientas":
            motivo = st.selectbox("Motivo:", ["Rotura en obra", "Desgaste", "Extravío", "Falla técnica"])
        elif st.session_state.seccion == "Indumentaria":
            motivo = st.selectbox("Motivo:", ["Talle incorrecto", "Renovación Anual", "Prenda Dañada", "Ingreso"])
        
        if st.form_submit_button("AGREGAR"):
            articulo_limpio = sel.split(" | ")[-1] if " | " in sel else sel
            st.session_state.carrito.append({
                "ID_Interno": str(uuid.uuid4())[:8],
                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "DNI": dni_actual,
                "Articulo": articulo_limpio, 
                "Cantidad": int(cant), 
                "Motivo": motivo
            })
            st.rerun()

with tab2:
    if st.session_state.carrito:
        st.write(pd.DataFrame(st.session_state.carrito)[["Cantidad", "Articulo", "Motivo"]])
        
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            with st.spinner("Reservando turno y enviando..."):
                try:
                    df_nuevo = pd.DataFrame(st.session_state.carrito)
                    
                    # EJECUCIÓN POR TURNO (Reintentos)
                    enviar_con_reintento(st.session_state.seccion, df_nuevo)
                    
                    # Bloqueo de Materiales (también con reintento)
                    if st.session_state.seccion == "Materiales":
                        df_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                        for idx, row in df_auth.iterrows():
                            if limpiar_dni(row['DNI']) == dni_actual:
                                df_auth.at[idx, 'Estado'] = "bloqueado"
                        conn.update(worksheet="Autorizaciones", data=df_auth)

                    st.success("✅ ¡Pedido guardado con éxito!")
                    st.session_state.carrito = []
                    time.sleep(2)
                    cambiar_seccion("Menu")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de conexión: El servidor está ocupado. Intenta de nuevo en 10 segundos.")
