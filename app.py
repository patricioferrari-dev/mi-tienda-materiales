import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM", page_icon="🏢", layout="wide")

# 2. CSS PARA ELIMINAR ESPACIOS Y MARGENES EXCESIVOS
st.markdown("""
    <style>
    /* 1. Fondo y Contenedor */
    .stApp { background-color: #f1f5f9; }
    .block-container { max-width: 850px; padding-top: 1.5rem !important; }

    /* 2. Eliminar márgenes entre columnas de Streamlit */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        margin-bottom: -1px !important;
    }

    /* 3. Celdas estilo Excel: Bordes rectos y padding mínimo */
    div[data-testid="stColumn"] {
        border: 1px solid #cbd5e1 !important;
        padding: 2px 8px !important;
        background-color: white;
        min-height: 30px !important;
        display: flex;
        align-items: center;
    }

    /* 4. Encabezados compactos */
    .header-box {
        background-color: #64748b !important;
        color: white !important;
        font-weight: bold;
        font-size: 12px;
        width: 100%;
        text-align: center;
        text-transform: uppercase;
    }

    /* 5. Datos de la celda */
    .cell-data {
        font-size: 13px;
        color: #1e293b;
        margin: 0;
        white-space: nowrap;
    }

    /* 6. Botón X Minimalista (Sin recuadro) */
    div[data-testid="stColumn"] button {
        background-color: transparent !important;
        color: #ef4444 !important;
        border: none !important;
        font-size: 14px !important;
        font-weight: bold !important;
        height: 24px !important;
        width: 100% !important;
        padding: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stColumn"] button:hover {
        background-color: #fee2e2 !important;
    }

    /* 7. Quitar bordes de las pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        padding: 5px 15px !important; 
        font-size: 13px !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 3. ESTADOS
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. ACCESO (Lógica simplificada para el ejemplo)
if not st.session_state.autenticado:
    st.title("🏢 Sistema SGM")
    user = st.text_input("Usuario:")
    pw = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
        valid = df_db[(df_db['Email'].str.lower() == user.lower()) & (df_db['Contrasena'].astype(str) == pw)]
        if not valid.empty:
            st.session_state.autenticado = True
            st.session_state.datos_usuario = valid.iloc[0].to_dict()
            st.rerun()
    st.stop()

# 5. MENÚ PRINCIPAL
dni_raw = str(st.session_state.datos_usuario.get('DNI', ''))
dni_val = dni_raw.split(".")[0].replace(" ", "").replace(".", "")

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Gestión")
    st.write(f"Operador: **{st.session_state.datos_usuario['Nombre']}**")
    st.divider()

    # LÓGICA DE COLUMNAS DINÁMICA
    if dni_val == "1111111":
        # Solo 2 columnas para que no quede el hueco a la derecha
        c1, c2 = st.columns(2)
        if c1.button("📚\nLIBRERÍA"): 
            st.session_state.seccion = "Insumos_Libreria"
            st.rerun()
        if c2.button("🧼\nLIMPIEZA"): 
            st.session_state.seccion = "Insumos_Limpieza"
            st.rerun()
    else:
        # 3 columnas para el resto de los técnicos
        c1, c2, c3 = st.columns(3)
        if c1.button("📦\nMATERIALES"): 
            st.session_state.seccion = "Materiales"
            st.rerun()
        if c2.button("🔧\nHERRAMIENTAS"): 
            st.session_state.seccion = "Herramientas"
            st.rerun()
        if c3.button("👕\nINDUMENTARIA"): 
            st.session_state.seccion = "Indumentaria"
            st.rerun()
    st.stop()

# 6. PANEL COMPACTO
st.button("⬅️ Volver", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.markdown(f"### 📍 {st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR", "📋 PLANILLA"])

with t1:
    with st.form("f", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1)
        if st.form_submit_button("AGREGAR"):
            # Lógica Anti-Duplicados
            art = sel.split(" ", 1)[1] if " " in sel and "Insumos" not in st.session_state.seccion else sel
            if any(i['Articulo'] == art for i in st.session_state.carrito):
                st.error("Ya existe en planilla.")
            else:
                st.session_state.carrito.append({
                    "Articulo": art, "Cantidad": int(cant),
                    "Nombre": st.session_state.datos_usuario['Nombre']
                })
                st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("Planilla vacía.")
    else:
        # ENCABEZADOS (Unificados)
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">X</div>', unsafe_allow_html=True)
        
        # FILAS (Sin separación)
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data" style="width:100%; text-align:center">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"x_{idx}"):
                st.session_state.carrito.pop(idx)
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 SUBIR PLANILLA"):
            df_final = pd.DataFrame(st.session_state.carrito)
            df_hist = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_hist, df_final]))
            st.success("¡Enviado!")
            st.session_state.carrito = []
            time.sleep(1); st.rerun()
