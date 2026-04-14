import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SGM - Gestión", page_icon="🏢", layout="wide")

# 2. CSS PARA COMPACIDAD
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 800px; padding-top: 1rem; }
    [data-testid="stForm"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; }
    [data-testid="stHorizontalBlock"] { gap: 0px !important; margin-bottom: -1px !important; }
    div[data-testid="stColumn"] { border: 1px solid #e2e8f0; padding: 1px 8px; background-color: white; min-height: 22px; display: flex; align-items: center; }
    .header-box { background-color: #475569; color: white; font-weight: 700; font-size: 10px; width: 100%; text-align: center; }
    .cell-data { font-size: 12px; color: #334155; margin: 0; line-height: 1; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 5. LOGIN (CORREGIDO)
if not st.session_state.autenticado:
    st.title("🔐 Acceso SGM")
    user_mail = st.text_input("Usuario:")
    user_pass = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
        
        # --- SOLUCIÓN AL ERROR ---
        # Forzamos la columna Email a ser string para evitar el AttributeError
        df_db['Email'] = df_db['Email'].astype(str).fillna('')
        
        valid = df_db[(df_db['Email'].str.lower() == user_mail.lower()) & (df_db['Contrasena'].astype(str) == user_pass)]
        # -------------------------
        
        if not valid.empty:
            st.session_state.autenticado = True
            st.session_state.datos_usuario = valid.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Correo o contraseña incorrectos.")
    st.stop()

# 6. MENÚ PRINCIPAL
dni_val = str(st.session_state.datos_usuario.get('DNI', '')).split(".")[0].replace(" ", "")

def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    if dni_val == "1111111":
        c1, c2 = st.columns(2)
        if c1.button("📚\nINSUMOS LIBRERÍA"): cambiar_seccion("Insumos_Libreria"); st.rerun()
        if c2.button("🧼\nINSUMOS LIMPIEZA"): cambiar_seccion("Insumos_Limpieza"); st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        if c1.button("📦\nMATERIALES"): cambiar_seccion("Materiales"); st.rerun()
        if c2.button("🔧\nHERRAMIENTAS"): cambiar_seccion("Herramientas"); st.rerun()
        if c3.button("👕\nINDUMENTARIA"): cambiar_seccion("Indumentaria"); st.rerun()
    st.stop()

# 7. REGISTRO Y RESUMEN
st.button("⬅️ Volver", on_click=lambda: cambiar_seccion("Menu"))
st.markdown(f"### 📍 {st.session_state.seccion}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni."],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN PEDIDO"])

with t1:
    with st.form("f_reg", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        if st.form_submit_button("AGREGAR", use_container_width=True):
            art_nom = sel.split(" ", 1)[1] if " " in sel and "Insumos" not in st.session_state.seccion else sel
            st.session_state.carrito.append({
                "Fecha": datetime.now().strftime("%d/%m/%Y"),
                "DNI": st.session_state.datos_usuario.get('DNI'),
                "Apellido": st.session_state.datos_usuario.get('Apellido'),
                "Nombre": st.session_state.datos_usuario.get('Nombre'),
                "Articulo": art_nom, "Cantidad": int(cant)
            })
            st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("Lista vacía.")
    else:
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"del_{idx}"):
                st.session_state.carrito.pop(idx); st.rerun()
        
        if st.button("🚀 ENVIAR PEDIDO", use_container_width=True):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new]))
            st.success("Enviado."); st.session_state.carrito = []; time.sleep(1); st.rerun()
