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
    dia_semana = ahora.weekday() # 0=Lunes, 2=Miércoles, 4=Viernes
    hora_actual = ahora.hour
    return dia_semana in [0, 2, 4] and 7 <= hora_actual < 15

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
        st.info(f"Usuario: {user.get('Nombre')} {user.get('Apellido')} (DNI: {str(user['DNI']).split('.')[0]})")
        
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
                    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                    for col in ['Email', 'Contrasena', 'Celular']:
                        df_db[col] = df_db[col].astype(str).replace('nan', '')
                    
                    df_db['DNI_STR'] = df_db['DNI'].astype(str).str.split('.').str[0].str.strip()
                    dni_target = str(user['DNI']).split('.')[0].strip()
                    idx_list = df_db.index[df_db['DNI_STR'] == dni_target].tolist()
                    
                    if idx_list:
                        df_db.loc[idx_list[0], 'Contrasena'] = str(nueva_p)
                        df_db.loc[idx_list[0], 'Email'] = str(n_mail)
                        df_db.loc[idx_list[0], 'Celular'] = str(cel_limpio)
                        conn.update(worksheet="DB_Tecnicos", data=df_db.drop(columns=['DNI_STR']))
                        st.success("✅ Cuenta activada.")
                        st.session_state.reestablecer = False
                        time.sleep(2); st.rerun()

    elif st.session_state.modo_registro:
        st.title("📝 Registro de Usuario")
        with st.form("form_padron"):
            dni_input = st.text_input("DNI (Sin puntos):").strip().replace(".", "")
            if st.form_submit_button("VERIFICAR PADRÓN"):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                df_db['DNI_STR'] = df_db['DNI'].astype(str).str.split('.').str[0].str.strip()
                match = df_db[df_db['DNI_STR'] == dni_input]
                
                if not match.empty:
                    # NUEVA VALIDACIÓN: Si ya tiene contraseña, no puede volver a registrarse
                    pass_existente = str(match.iloc[0].get('Contrasena', '')).strip().lower()
                    if pass_existente not in ["", "nan", "none"]:
                        st.error("⚠️ Este DNI ya tiene una cuenta activa. Por favor, inicia sesión.")
                        time.sleep(2)
                        st.session_state.modo_registro = False
                        st.rerun()
                    else:
                        st.session_state.user_a_reestablecer = match.iloc[0].to_dict()
                        st.session_state.reestablecer = True
                        st.session_state.modo_registro = False
                        st.rerun()
                else: st.error("🚫 DNI no encontrado en el padrón.")
        if st.button("⬅️ Volver"): st.session_state.modo_registro = False; st.rerun()

    else:
        st.title("🔐 Acceso SGM")
        u_id = st.text_input("Email o DNI:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        c1, c2 = st.columns(2)
        if c1.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            db['DNI_STR'] = db['DNI'].astype(str).str.split('.').str[0].str.strip()
            user_match = db[(db['Email'].astype(str).str.lower() == u_id) | (db['DNI_STR'] == u_id)]
            if not user_match.empty:
                real_pass = str(user_match.iloc[0].get('Contrasena', '')).strip()
                if real_pass.lower() in ["", "nan", "none"]:
                    st.session_state.user_a_reestablecer = user_match.iloc[0].to_dict()
                    st.session_state.reestablecer = True; st.rerun()
                elif real_pass == u_pass:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = user_match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
        if c2.button("Registrarme", use_container_width=True): st.session_state.modo_registro = True; st.rerun()
    st.stop()

# 5. MENÚ PRINCIPAL
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
        df_auth = conn.read(worksheet="Autorizaciones", ttl=0)
        df_auth['DNI_STR'] = df_auth['DNI'].astype(str).str.split('.').str[0].str.strip()
        auth_row = df_auth[df_auth['DNI_STR'] == dni_actual]
        es_ok = not auth_row.empty and str(auth_row.iloc[0].get('Estado', '')).lower() == "ok"

        if not es_horario_permitido():
            c1.button("🔒\nMAT. CERRADO", disabled=True, help="L-M-V 07:00 a 15:00")
        elif not es_ok:
            c1.button("🚫\nYA PEDIDO / BLOQUEADO", disabled=True, help="Máximo 1 pedido permitido.")
        else:
            if c1.button("📦\nMATERIALES"): cambiar_seccion("Materiales"); st.rerun()
            
        if c2.button("🔧\nHERRAMIENTAS"): cambiar_seccion("Herramientas"); st.rerun()
        if c3.button("👕\nINDUMENTARIA"): cambiar_seccion("Indumentaria"); st.rerun()
    st.stop()

# 6. PANEL DE CARGA
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 Sector: {st.session_state.seccion}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["PINZA DE PUNTA", "ALICATE", "DESTORNILLADOR PH"],
    "Indumentaria": ["PANTALON T.40", "CHOMBA L", "BOTINES"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN"])

with tab1:
    with st.form("f_registro", clear_on_submit=True):
        sel = st.selectbox("Elegir Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        
        motivo = ""
        if st.session_state.seccion == "Herramientas":
            motivo = st.selectbox("Motivo:", ["Rotura", "Perdido", "Nunca entregado"])
        elif st.session_state.seccion == "Indumentaria":
            motivo = st.selectbox("Motivo:", ["Desgaste", "Nunca entregado"])
            
        if st.form_submit_button("AGREGAR AL RESUMEN", use_container_width=True):
            if any(i['Articulo'] == sel for i in st.session_state.carrito):
                st.warning(f"El artículo {sel} ya está en el resumen.")
            else:
                st.session_state.carrito.append({
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Email": st.session_state.datos_usuario.get('Email'),
                    "Nombre": st.session_state.datos_usuario.get('Nombre'),
                    "Apellido": st.session_state.datos_usuario.get('Apellido'),
                    "DNI": dni_actual,
                    "Articulo": sel, "Cantidad": int(cant), "Motivo": motivo
                })
                st.rerun()

with tab2:
    if not st.session_state.carrito:
        st.info("Resumen vacío.")
    else:
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN / MOTIVO</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data" style="text-align:center">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            m_txt = f" ({item.get('Motivo', '')})" if item.get('Motivo') else ""
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}{m_txt}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"del_{idx}"):
                st.session_state.carrito.pop(idx); st.rerun()
        
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new], ignore_index=True))
            
            if st.session_state.seccion == "Materiales":
                df_up = conn.read(worksheet="Autorizaciones", ttl=0)
                df_up['DNI_STR'] = df_up['DNI'].astype(str).str.split('.').str[0].str.strip()
                idx_auth = df_up.index[df_up['DNI_STR'] == dni_actual].tolist()
                if idx_auth:
                    df_up.at[idx_auth[0], 'Estado'] = "bloqueado"
                    conn.update(worksheet="Autorizaciones", data=df_up.drop(columns=['DNI_STR']))

            st.success("✅ Pedido enviado. Se ha bloqueado tu acceso a Materiales.")
            st.session_state.carrito = []
            time.sleep(2); cambiar_seccion("Menu"); st.rerun()
