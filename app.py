import streamlit as st
import requests
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time
import re
import uuid

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y CSS
# ==========================================
st.set_page_config(page_title="SGM - Gestión de Pedidos", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 800px; padding-top: 1rem; }
    [data-testid="stForm"] { background-color: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; }
    [data-testid="stHorizontalBlock"] { gap: 0px !important; margin-bottom: -1px !important; }
    div[data-testid="stColumn"] { border: 1px solid #e2e8f0; padding: 2px 8px; background-color: white; min-height: 15px; display: flex; align-items: center; }
    .header-box { background-color: #475569; color: white; font-weight: 700; font-size: 10px; width: 100%; text-align: center; }
    .cell-data { font-size: 12px; color: #334155; margin: 0; line-height: 1.1; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE APOYO Y VALIDACIÓN
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def registrar_log(usuario, dni, evento, seccion="-", detalle="-"):
    try:
        tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
        ahora = datetime.now(tz_ba).strftime("%d/%m/%Y %H:%M:%S")
        nuevo_log = pd.DataFrame([{
            "Fecha": ahora, "Usuario": usuario, "DNI": str(dni),
            "Evento": evento, "Seccion": seccion, "Detalle": detalle
        }])
        df_logs = conn.read(worksheet="Logs", ttl=0).dropna(how='all')
        conn.update(worksheet="Logs", data=pd.concat([df_logs, nuevo_log], ignore_index=True))
    except: pass 

def es_email_valido(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    return 7 <= ahora.hour < 15

def limpiar_dni(valor):
    if pd.isna(valor): return ""
    return str(valor).split('.')[0].replace(" ", "").strip()

def cambiar_seccion(nombre):
    st.session_state.seccion = nombre

# --- CONFIGURACIÓN DE PERMISOS POR DNI ---
# Agrega aquí los DNIs que tienen acceso a cada sector
PERMISOS = {
    "Materiales": ["12345678", "20334455"], 
    "Herramientas": ["12345678", "20334455"],
    "Indumentaria": ["12345678"],
    "Libreria": ["12345678", "20334455"],
    "Limpieza": ["12345678", "20334455"]
}

# ==========================================
# 3. ESTADOS DE SESIÓN
# ==========================================
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'reestablecer' not in st.session_state: st.session_state.reestablecer = False
if 'user_a_reestablecer' not in st.session_state: st.session_state.user_a_reestablecer = None
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

# ==========================================
# 4. SISTEMA DE ACCESO (LOGIN)
# ==========================================
if not st.session_state.autenticado:
    if st.session_state.reestablecer:
        st.title("🔑 Asignar Acceso")
        user = st.session_state.user_a_reestablecer
        dni_limpio_user = limpiar_dni(user.get('DNI', ''))
        st.info(f"Usuario: {user.get('Nombre')} {user.get('Apellido')} (DNI: {dni_limpio_user})")
        with st.form("form_reset"):
            n_mail = st.text_input("Asignar Email:").strip().lower()
            n_cel = st.text_input("Celular (10 dígitos):").strip()
            nueva_p = st.text_input("Nueva Contraseña:", type="password")
            confirm_p = st.text_input("Confirmar Contraseña:", type="password")
            if st.form_submit_button("GUARDAR Y ACTIVAR CUENTA"):
                if not es_email_valido(n_mail): st.error("Email no válido.")
                elif len(n_cel.replace(" ","")) < 10: st.error("Celular inválido.")
                elif nueva_p != confirm_p: st.error("Las contraseñas no coinciden.")
                else:
                    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
                    idx = df_db.index[df_db['DNI'].apply(limpiar_dni) == dni_limpio_user].tolist()
                    if idx:
                        df_db.at[idx[0], 'Contrasena'] = str(nueva_p)
                        df_db.at[idx[0], 'Email'] = str(n_mail)
                        df_db.at[idx[0], 'Celular'] = str(n_cel)
                        conn.update(worksheet="DB_Tecnicos", data=df_db)
                        st.success("✅ Cuenta activada.")
                        st.session_state.reestablecer = False
                        time.sleep(2); st.rerun()

    elif st.session_state.modo_registro:
        st.title("📝 Registro de Usuario")
        with st.form("form_padron"):
            dni_input = st.text_input("DNI (Sin puntos):").strip().replace(".", "")
            if st.form_submit_button("VERIFICAR PADRÓN"):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
                match = df_db[df_db['DNI'].apply(limpiar_dni) == dni_input]
                if not match.empty:
                    row = match.iloc[0]
                    if str(row.get('Contrasena', '')).strip().lower() not in ["", "nan", "none"]:
                        st.error("⚠️ Este DNI ya tiene una cuenta activa.")
                    else:
                        st.session_state.user_a_reestablecer = row.to_dict()
                        st.session_state.reestablecer = True
                        st.session_state.modo_registro = False
                        st.rerun()
                else: st.error("🚫 DNI no encontrado.")
        if st.button("⬅️ Volver"): 
            st.session_state.modo_registro = False; st.rerun()
    else:
        st.title("🔐 Acceso SGM")
        u_id = st.text_input("Email o DNI:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        c1, c2 = st.columns(2)
        if c1.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
            user_match = None
            for _, row in db.iterrows():
                if str(row.get('Email','')).lower() == u_id or limpiar_dni(row.get('DNI')) == u_id:
                    user_match = row; break
            if user_match is not None and str(user_match.get('Contrasena','')) == u_pass:
                st.session_state.autenticado = True
                st.session_state.datos_usuario = user_match.to_dict()
                st.rerun()
            else: st.error("❌ Credenciales incorrectas.")
        if c2.button("Registrarme", use_container_width=True): 
            st.session_state.modo_registro = True; st.rerun()
    st.stop()

# ==========================================
# 5. INTERFAZ DE USUARIO AUTENTICADO
# ==========================================
dni_actual = limpiar_dni(st.session_state.datos_usuario.get('DNI', ''))
nombre_completo = f"{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}"

with st.sidebar:
    st.header("SGM")
    st.write(f"👤 **{nombre_completo}**")
    st.caption(f"DNI: {dni_actual}")
    st.divider()
    if st.button("🏠 Menú Principal", use_container_width=True):
        cambiar_seccion("Menu"); st.rerun()
    if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        st.session_state.autenticado = False; st.rerun()

# --- LÓGICA DE NAVEGACIÓN ---
if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.info("Seleccione un sector")
    accesos_reales = [s for s, dnis in PERMISOS.items() if dni_actual in dnis]
    
    if not accesos_reales:
        st.warning("⚠️ Sin permisos. Contacte a soporte.")
    else:
        filas = [accesos_reales[i:i + 3] for i in range(0, len(accesos_reales), 3)]
        for fila in filas:
            cols = st.columns(3)
            for i, sector in enumerate(fila):
                with cols[i]:
                    if st.button(f"📦\n{sector.upper()}", use_container_width=True):
                        if sector == "Libreria": cambiar_seccion("Insumos_Libreria")
                        elif sector == "Limpieza": cambiar_seccion("Insumos_Limpieza")
                        else: cambiar_seccion(sector)
                        st.rerun()
else:
    # --- PANEL DE CARGA DE ARTÍCULOS ---
    st.subheader(f"📍 Sector: {st.session_state.seccion}")
    
    listas = {
        "Materiales": ["13008 | CONTROL REMOTO", "30032 | CABLE COAXIL", "30059 | CABLE DROP", "31025 | PRECINTO", "31026 | TARUGO", "87099 | CONECTOR MECANICO"],
        "Herramientas": ["ALARGUE 10 MTS", "ALICATE 8''", "ANTEOJO SEGURIDAD", "ESCALERA DIELECTRICA", "TALADRO BOSCH"],
        "Indumentaria": ["REMERA M", "REMERA L", "PANTALON 42", "PANTALON 44", "BUZO L"],
        "Insumos_Libreria": ["Resma A4", "Lapicera Azul"],
        "Insumos_Limpieza": ["BOLSON HIGIENICO", "LAVANDINA 5L", "JABON LIQUIDO 5L"],
    }
    
    items = listas.get(st.session_state.seccion, [])
    tab1, tab2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN"])

    with tab1:
        with st.form("f_registro", clear_on_submit=True):
            sel = st.selectbox("Elegir Artículo:", items)
            cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
            motivo = st.selectbox("Motivo:", ["Uso Normal", "Desgaste", "Perdido"]) if st.session_state.seccion in ["Herramientas", "Indumentaria"] else ""
            if st.form_submit_button("AGREGAR AL RESUMEN", use_container_width=True):
                art_limpio = sel.split(" | ")[-1] if " | " in sel else sel
                cod_e = sel.split(" | ")[0] if " | " in sel else ""
                st.session_state.carrito.append({
                    "ID_Interno": str(uuid.uuid4())[:8], "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Email": st.session_state.datos_usuario.get('Email'), "Nombre": st.session_state.datos_usuario.get('Nombre'),
                    "Apellido": st.session_state.datos_usuario.get('Apellido'), "DNI": dni_actual,
                    "Codigo": cod_e, "Articulo": art_limpio, "Cantidad": cant, "Motivo": motivo
                })
                st.rerun()

    with tab2:
        if not st.session_state.carrito:
            st.info("Resumen vacío.")
        else:
            for idx, item in enumerate(st.session_state.carrito):
                c1, c2, c3 = st.columns([1, 4, 1])
                c1.write(f"x{item['Cantidad']}")
                c2.write(f"{item['Articulo']}")
                if c3.button("🗑️", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx); st.rerun()
            
            if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
                with st.spinner("Enviando..."):
                    try:
                        nombre_hoja = st.session_state.seccion
                        df_dest = conn.read(worksheet=nombre_hoja, ttl=0).dropna(how='all')
                        df_final = pd.concat([df_dest, pd.DataFrame(st.session_state.carrito)], ignore_index=True)
                        conn.update(worksheet=nombre_hoja, data=df_final)
                        st.success("✅ Pedido enviado!"); st.session_state.carrito = []
                        time.sleep(1); st.session_state.seccion = "Menu"; st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                    
