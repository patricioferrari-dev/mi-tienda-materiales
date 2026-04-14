import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time
import re

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

# 2. FUNCIONES DE VALIDACIÓN
def es_email_valido(email):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, email) is not None

def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    dia_semana = ahora.weekday() 
    hora_actual = ahora.hour
    # Lunes=0, Miércoles=2, Viernes=4. Horario 07:00 a 15:00
    return dia_semana in [0, 2, 4] and 7 <= hora_actual < 15

# 3. ESTADOS DE SESIÓN
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'reestablecer' not in st.session_state: st.session_state.reestablecer = False
if 'user_a_reestablecer' not in st.session_state: st.session_state.user_a_reestablecer = None
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. SISTEMA DE ACCESO (LOGIN / REGISTRO)
if not st.session_state.autenticado:
    if st.session_state.reestablecer:
        st.title("🔑 Configurar Acceso")
        user = st.session_state.user_a_reestablecer
        with st.form("form_reset"):
            n_mail = st.text_input("Email:").strip().lower()
            n_cel = st.text_input("Celular (10 dígitos):").strip()
            nueva_p = st.text_input("Contraseña:", type="password")
            confirm_p = st.text_input("Confirmar:", type="password")
            if st.form_submit_button("ACTIVAR CUENTA"):
                cel_l = n_cel.replace(" ", "").replace("-", "")
                if not es_email_valido(n_mail): st.error("Email inválido.")
                elif len(cel_l) != 10: st.error("Celular debe tener 10 dígitos.")
                elif nueva_p != confirm_p: st.error("Pass no coinciden.")
                else:
                    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                    for col in ['Email', 'Contrasena', 'Celular']: df_db[col] = df_db[col].astype(object)
                    dni_target = str(user['DNI']).split('.')[0].strip()
                    df_db['DNI_STR'] = df_db['DNI'].astype(str).str.split('.').str[0].str.strip()
                    idx = df_db.index[df_db['DNI_STR'] == dni_target].tolist()
                    if idx:
                        df_db.at[idx[0], 'Contrasena'] = str(nueva_p)
                        df_db.at[idx[0], 'Email'] = str(n_mail)
                        df_db.at[idx[0], 'Celular'] = str(cel_l)
                        conn.update(worksheet="DB_Tecnicos", data=df_db.drop(columns=['DNI_STR']))
                        st.success("Activado."); st.session_state.reestablecer = False; time.sleep(2); st.rerun()
        if st.button("Volver"): st.session_state.reestablecer = False; st.rerun()

    elif st.session_state.modo_registro:
        st.title("📝 Registro")
        with st.form("f_padron"):
            dni_in = st.text_input("DNI:").strip().replace(".", "")
            if st.form_submit_button("VERIFICAR"):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                df_db['DNI_STR'] = df_db['DNI'].astype(str).str.split('.').str[0].str.strip()
                match = df_db[df_db['DNI_STR'] == dni_in]
                if not match.empty:
                    st.session_state.user_a_reestablecer = match.iloc[0].to_dict()
                    st.session_state.reestablecer = True
                    st.session_state.modo_registro = False; st.rerun()
                else: st.error("DNI no encontrado.")
        if st.button("⬅️ Volver"): st.session_state.modo_registro = False; st.rerun()

    else:
        st.title("🔐 Acceso SGM")
        u_id = st.text_input("Email o DNI:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            db['DNI_STR'] = db['DNI'].astype(str).str.split('.').str[0].str.strip()
            user_match = db[(db['Email'].astype(str).str.lower() == u_id) | (db['DNI_STR'] == u_id)]
            if not user_match.empty:
                rp = str(user_match.iloc[0].get('Contrasena', '')).strip()
                if rp.lower() in ["", "nan"]:
                    st.session_state.user_a_reestablecer = user_match.iloc[0].to_dict()
                    st.session_state.reestablecer = True; st.rerun()
                elif rp == u_pass:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = user_match.iloc[0].to_dict(); st.rerun()
                else: st.error("Contraseña incorrecta.")
        if st.button("Registrarme"): st.session_state.modo_registro = True; st.rerun()
    st.stop()

# 5. MENÚ PRINCIPAL (LÓGICA DE BLOQUEO)
def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

dni_actual = str(st.session_state.datos_usuario.get('DNI', '')).split(".")[0].strip()

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.write(f"Operador: **{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}**")
    
    if dni_actual == "1111111":
        c1, c2 = st.columns(2)
        if c1.button("📚\nLIBRERÍA"): cambiar_seccion("Insumos_Libreria"); st.rerun()
        if c2.button("🧼\nLIMPIEZA"): cambiar_seccion("Insumos_Limpieza"); st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        
        # --- CONSULTA ESTADO EN "Autorizaciones" ---
        df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
        df_auth['DNI_STR'] = df_auth['DNI'].astype(str).str.split('.').str[0].str.strip()
        auth_row = df_auth[df_auth['DNI_STR'] == dni_actual]
        
        # El botón de materiales solo sirve si el estado es OK
        autorizado_ok = not auth_row.empty and str(auth_row.iloc[0].get('Estado', '')).upper() == "OK"

        # Lógica de botón MATERIALES
        if not es_horario_permitido():
            c1.button("🔒\nMAT. CERRADO", disabled=True, help="L-M-V 07:00 a 15:00")
        elif not autorizado_ok:
            c1.button("🚫\nBLOQUEADO", disabled=True, help="Ya realizaste un pedido. Espera habilitación.")
        else:
            if c1.button("📦\nMATERIALES"): cambiar_seccion("Materiales"); st.rerun()
            
        if c2.button("🔧\nHERRAMIENTAS"): cambiar_seccion("Herramientas"); st.rerun()
        if c3.button("👕\nINDUMENTARIA"): cambiar_seccion("Indumentaria"); st.rerun()
    st.stop()

# 6. PANEL DE CARGA Y ENVÍO
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 Sector: {st.session_state.seccion}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["PINZA DE PUNTA", "ALICATE", "DESTORNILLADOR PH"],
    "Indumentaria": ["PANTALON T.40", "CHOMBA L", "BOTINES"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN"])

with t1:
    with st.form("f_reg", clear_on_submit=True):
        sel = st.selectbox("Elegir Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        motivo = st.selectbox("Motivo:", ["Rotura", "Desgaste", "Nuevo"]) if st.session_state.seccion != "Materiales" else ""
        if st.form_submit_button("AGREGAR AL RESUMEN"):
            st.session_state.carrito.append({
                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": st.session_state.datos_usuario.get('Nombre'),
                "Apellido": st.session_state.datos_usuario.get('Apellido'),
                "DNI": dni_actual,
                "Articulo": sel, "Cantidad": int(cant), "Motivo": motivo
            })
            st.rerun()

with t2:
    if not st.session_state.carrito: st.info("Resumen vacío.")
    else:
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 1])
            r1.write(item["Cantidad"])
            r2.write(f"{item['Articulo']} {item['Motivo']}")
            if r3.button("X", key=f"d{idx}"): st.session_state.carrito.pop(idx); st.rerun()
        
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            # Guardar pedido
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new], ignore_index=True))
            
            # --- BLOQUEO AUTOMÁTICO EN LA HOJA AUTORIZACIONES ---
            if st.session_state.seccion == "Materiales":
                df_auth_up = conn.read(worksheet="Autorizaciones", ttl=0)
                df_auth_up['DNI_STR'] = df_auth_up['DNI'].astype(str).str.split('.').str[0].str.strip()
                idx_auth = df_auth_up.index[df_auth_up['DNI_STR'] == dni_actual].tolist()
                if idx_auth:
                    df_auth_up.at[idx_auth[0], 'Estado'] = "BLOQUEADO"
                    conn.update(worksheet="Autorizaciones", data=df_auth_up.drop(columns=['DNI_STR']))

            st.success("Pedido enviado y acceso bloqueado hasta nueva autorización."); st.session_state.carrito = []
            time.sleep(2); st.session_state.seccion = "Menu"; st.rerun()
