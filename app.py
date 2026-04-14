import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="wide")

# 2. CSS PROFESIONAL: CONTRASTE, COMPACIDAD Y BOTONES
st.markdown("""
    <style>
    /* Fondo general */
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 850px; padding-top: 2rem; }

    /* --- MENÚ PRINCIPAL --- */
    .stButton>button {
        width: 100%; border-radius: 12px; font-weight: 700;
        min-height: 80px; padding: 10px !important;
        background-color: #ffffff; color: #334155;
        border: 1px solid #e2e8f0; transition: all 0.3s;
        font-size: 1rem !important;
    }
    .stButton>button:hover { 
        border-color: #3b82f6; color: #3b82f6; 
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
    }

    /* --- FORMULARIO DE CARGA (CONTRASTE MEJORADO) --- */
    [data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    /* Resalte para inputs */
    .stSelectbox div[data-baseweb="select"], .stNumberInput div[data-baseweb="input"] {
        background-color: #f1f5f9 !important; /* Gris claro para notar el campo */
        border: 1px solid #cbd5e1 !important;
    }

    /* --- PLANILLA ESTILO EXCEL (ULTRA COMPACTA) --- */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        margin-bottom: -1px !important;
    }
    div[data-testid="stColumn"] {
        border: 1px solid #e2e8f0 !important;
        padding: 4px 10px !important;
        background-color: white;
        min-height: 32px !important;
        display: flex; align-items: center;
    }
    .header-box {
        background-color: #475569 !important;
        color: white !important;
        font-weight: 700; font-size: 11px;
        width: 100%; text-align: center;
    }
    .cell-data { font-size: 13px; color: #334155; margin: 0; }

    /* Botón X Minimalista */
    div[data-testid="stColumn"] button {
        background-color: transparent !important;
        color: #ef4444 !important;
        border: none !important;
        width: 100% !important;
        font-weight: bold !important;
    }
    div[data-testid="stColumn"] button:hover { background-color: #fee2e2 !important; }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 3. ESTADOS E INICIALIZACIÓN
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. LÓGICA DE ACCESO
if not st.session_state.autenticado:
    st.title("🔐 Acceso SGM")
    with st.container():
        user_mail = st.text_input("Correo electrónico:")
        user_pass = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            valid = df_db[(df_db['Email'].str.lower() == user_mail.lower()) & (df_db['Contrasena'].astype(str) == user_pass)]
            if not valid.empty:
                st.session_state.autenticado = True
                st.session_state.datos_usuario = valid.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

# 5. MENÚ PRINCIPAL (CORREGIDO PARA 2 O 3 COLUMNAS)
dni_raw = str(st.session_state.datos_usuario.get('DNI', ''))
dni_val = dni_raw.split(".")[0].replace(" ", "").replace(".", "")

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.write(f"Bienvenido, **{st.session_state.datos_usuario['Nombre']}**")
    st.divider()

    if dni_val == "1111111":
        # Solo 2 columnas para Limpieza y Librería
        c1, c2 = st.columns(2)
        if c1.button("📚\nINSUMOS LIBRERÍA"): 
            st.session_state.seccion = "Insumos_Libreria"; st.rerun()
        if c2.button("🧼\nINSUMOS LIMPIEZA"): 
            st.session_state.seccion = "Insumos_Limpieza"; st.rerun()
    else:
        # 3 columnas para el resto del personal
        c1, c2, c3 = st.columns(3)
        if c1.button("📦\nMATERIALES"): 
            st.session_state.seccion = "Materiales"; st.rerun()
        if c2.button("🔧\nHERRAMIENTAS"): 
            st.session_state.seccion = "Herramientas"; st.rerun()
        if c3.button("👕\nINDUMENTARIA"): 
            st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# 6. PANEL DE TRABAJO (CARGA Y PLANILLA)
st.button("⬅️ Volver al Menú", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.subheader(f"📍 Categoría: {st.session_state.seccion.replace('_', ' ')}")

# Diccionario de productos
listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR CARGA", "📋 VER PLANILLA"])

with t1:
    with st.form("f_registro", clear_on_submit=True):
        st.write("Seleccione el artículo y cantidad:")
        sel = st.selectbox("Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        
        if st.form_submit_button("AGREGAR A PLANILLA", use_container_width=True):
            # Lógica Anti-Duplicados
            art_nom = sel.split(" ", 1)[1] if " " in sel and "Insumos" not in st.session_state.seccion else sel
            if any(i['Articulo'] == art_nom for i in st.session_state.carrito):
                st.warning(f"El artículo '{art_nom}' ya está en la lista.")
            else:
                st.session_state.carrito.append({
                    "Articulo": art_nom, 
                    "Cantidad": int(cant),
                    "Nombre": st.session_state.datos_usuario['Nombre'],
                    "Fecha": datetime.now().strftime("%d/%m/%Y")
                })
                st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("La planilla está vacía.")
    else:
        # CABECERA COMPACTA
        h1, h2, h3 = st.columns([1, 6, 1])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        
        # FILAS SIN ESPACIOS
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 1])
            r1.markdown(f'<div class="cell-data" style="text-align:center; width:100%">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"del_{idx}"):
                st.session_state.carrito.pop(idx)
                st.rerun()

        st.write("")
        if st.button("🚀 CONFIRMAR Y SUBIR TODO", use_container_width=True):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new]))
            st.success("Planilla enviada correctamente.")
            st.session_state.carrito = []
            time.sleep(1)
            st.rerun()
