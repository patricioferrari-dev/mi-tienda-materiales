import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz  # Librería para manejar zonas horarias
import time

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SGM - Gestión", page_icon="🏢", layout="wide")

# 2. CSS PARA COMPACIDAD Y ESTILO
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

# 3. LÓGICA DE CONTROL HORARIO (BUENOS AIRES)
def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    dia_semana = ahora.weekday() # 0=Lunes, 2=Miércoles, 4=Viernes
    hora_actual = ahora.hour
    
    # Días permitidos: Lunes (0), Miércoles (2), Viernes (4)
    dias_ok = dia_semana in [0, 2, 4]
    # Hora permitida: de 07:00 a 14:59 (antes de las 15:00)
    hora_ok = 7 <= hora_actual < 15
    
    return dias_ok and hora_ok

# 4. ESTADOS
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 5. LOGIN Y REGISTRO
if not st.session_state.autenticado:
    if st.session_state.modo_registro:
        st.title("📝 Registro de Usuario")
        with st.form("form_reg"):
            n_email = st.text_input("Email:").strip().lower()
            n_nom = st.text_input("Nombre:")
            n_ape = st.text_input("Apellido:")
            n_dni = st.text_input("DNI:")
            n_cel = st.text_input("Celular:")
            n_pas = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("REGISTRARME"):
                df_check = conn.read(worksheet="DB_Tecnicos", ttl=0)
                if n_dni in df_check['DNI'].astype(str).values:
                    st.error("DNI ya registrado.")
                else:
                    nuevo = pd.DataFrame([{"Email": n_email, "Nombre": n_nom, "Apellido": n_ape, "Celular": n_cel, "DNI": n_dni, "Contrasena": n_pas}])
                    conn.update(worksheet="DB_Tecnicos", data=pd.concat([df_check, nuevo], ignore_index=True))
                    st.success("Registrado correctamente."); st.session_state.modo_registro = False; time.sleep(1); st.rerun()
        if st.button("⬅️ Volver"): st.session_state.modo_registro = False; st.rerun()
    else:
        st.title("🔐 Acceso SGM")
        u_mail = st.text_input("Email:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        c1, c2 = st.columns(2)
        if c1.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            db['Email'] = db['Email'].astype(str).str.strip().str.lower()
            db['Contrasena'] = db['Contrasena'].astype(str).str.strip()
            m = db[(db['Email'] == u_mail) & (db['Contrasena'] == u_pass)]
            if not m.empty:
                st.session_state.autenticado = True; st.session_state.datos_usuario = m.iloc[0].to_dict(); st.rerun()
            else: st.error("Datos incorrectos.")
        if c2.button("Registrarse", use_container_width=True): st.session_state.modo_registro = True; st.rerun()
    st.stop()

# 6. MENÚ PRINCIPAL
def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

dni_raw = str(st.session_state.datos_usuario.get('DNI', '')).split(".")[0].strip()

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.write(f"Operador: **{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}**")
    
    if dni_raw == "1111111":
        c1, c2 = st.columns(2)
        if c1.button("📚\nLIBRERÍA"): cambiar_seccion("Insumos_Libreria"); st.rerun()
        if c2.button("🧼\nLIMPIEZA"): cambiar_seccion("Insumos_Limpieza"); st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        
        # --- LÓGICA DE BLOQUEO DE MATERIALES ---
        permitido = es_horario_permitido()
        if permitido:
            if c1.button("📦\nMATERIALES"): cambiar_seccion("Materiales"); st.rerun()
        else:
            c1.button("🔒\nMATERIALES (CERRADO)", disabled=True, help="Pedidos: Lunes, Miércoles y Viernes de 07:00 a 15:00")
            st.warning("⚠️ El sector Materiales solo abre LUN-MIE-VIE de 07:00 a 15:00.")
            
        if c2.button("🔧\nHERRAMIENTAS"): cambiar_seccion("Herramientas"); st.rerun()
        if c3.button("👕\nINDUMENTARIA"): cambiar_seccion("Indumentaria"); st.rerun()
    st.stop()

# 7. PANEL DE CARGA
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 {st.session_state.seccion}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN PEDIDO"])

with t1:
    with st.form("f_reg", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        if st.form_submit_button("AGREGAR"):
            st.session_state.carrito.append({
                "Fecha": datetime.now().strftime("%d/%m/%Y"),
                "Email": st.session_state.datos_usuario.get('Email'),
                "Nombre": st.session_state.datos_usuario.get('Nombre'),
                "Apellido": st.session_state.datos_usuario.get('Apellido'),
                "Celular": st.session_state.datos_usuario.get('Celular'),
                "DNI": st.session_state.datos_usuario.get('DNI'),
                "Articulo": sel, "Cantidad": int(cant)
            })
            st.rerun()

with t2:
    if not st.session_state.carrito: st.info("Lista vacía.")
    else:
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"del_{idx}"): st.session_state.carrito.pop(idx); st.rerun()
        
        if st.button("🚀 ENVIAR PEDIDO", use_container_width=True):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new]))
            st.success("Enviado!"); st.session_state.carrito = []; time.sleep(1); st.rerun()
