import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="wide")

# 2. CSS QUIRÚRGICO: ESTILO PLANILLA COMPACTA
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .block-container { max-width: 900px; padding-top: 2rem; }

    /* Contenedor blanco tipo hoja */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #d1d5db;
    }

    /* FILAS DE TABLA: Sin separación y altura mínima */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        margin-top: -1px !important; /* Une bordes superiores e inferiores */
    }

    /* CELDAS: Bordes finos y alineación perfecta */
    div[data-testid="stColumn"] {
        border: 1px solid #ccc !important;
        padding: 2px 8px !important; /* Espacio mínimo interno */
        min-height: 28px !important;
        display: flex;
        align-items: center;
        background-color: white;
    }

    /* Encabezados con color de oficina */
    .table-header {
        background-color: #e5e7eb !important;
        font-weight: bold;
        font-size: 13px;
        color: #374151;
        width: 100%;
        text-align: center;
    }

    /* Texto de celda pequeño y profesional */
    .cell-data {
        font-size: 13px;
        color: #111827;
        margin: 0;
    }

    /* BOTÓN X: Minimalista total */
    div[data-testid="stColumn"] button {
        background-color: transparent !important;
        color: #ef4444 !important;
        border: none !important;
        font-size: 14px !important;
        font-weight: bold !important;
        height: 20px !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
    }
    
    div[data-testid="stColumn"] button:hover {
        background-color: #fee2e2 !important;
        border-radius: 0px;
    }

    /* Ocultar basurita de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    [data-testid="stFormSubmitButton"] { text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 3. ESTADOS
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. ACCESO
if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    with st.container():
        user_mail = st.text_input("Usuario (Email):")
        user_pass = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            valid = df_db[(df_db['Email'].str.lower() == user_mail.lower()) & (df_db['Contrasena'].astype(str) == user_pass)]
            if not valid.empty:
                st.session_state.autenticado = True
                st.session_state.datos_usuario = valid.iloc[0].to_dict()
                st.rerun()
            else: st.error("Datos incorrectos")
    st.stop()

# 5. MENÚ PRINCIPAL (Botones grandes para dedos, pero en contenedor limpio)
dni_raw = str(st.session_state.datos_usuario.get('DNI', ''))
dni_val = dni_raw.split(".")[0].replace(" ", "")

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Gestión")
    st.write(f"Operador: **{st.session_state.datos_usuario['Nombre']}**")
    st.divider()

    c1, c2, c3 = st.columns(3)
    if dni_val == "1111111":
        if c1.button("📚\nLIBRERÍA"): st.session_state.seccion = "Insumos_Libreria"; st.rerun()
        if c2.button("🧼\nLIMPIEZA"): st.session_state.seccion = "Insumos_Limpieza"; st.rerun()
    else:
        if c1.button("📦\nMATERIALES"): st.session_state.seccion = "Materiales"; st.rerun()
        if c2.button("🔧\nHERRAMIENTAS"): st.session_state.seccion = "Herramientas"; st.rerun()
        if c3.button("👕\nINDUMENTARIA"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# 6. PANELES DE CARGA
st.button("⬅️ Volver al Menú", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.subheader(f"📍 {st.session_state.seccion.replace('_', ' ')}")

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
    with st.form("form_carga", clear_on_submit=True):
        sel = st.selectbox("Seleccione Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, value=1, step=1)
        # Lógica anti-duplicados
        if st.form_submit_button("AÑADIR A PLANILLA"):
            art_nom = sel.split(" ", 1)[1] if " " in sel and "Insumos" not in st.session_state.seccion else sel
            if any(i['Articulo'] == art_nom for i in st.session_state.carrito):
                st.warning("⚠️ Este artículo ya está en la planilla inferior.")
            else:
                st.session_state.carrito.append({
                    "Articulo": art_nom, "Cantidad": int(cant),
                    "Nombre": st.session_state.datos_usuario['Nombre'],
                    "Fecha": datetime.now().strftime("%d/%m/%y")
                })
                st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("Planilla vacía.")
    else:
        # CABECERA DE PLANILLA densa
        h1, h2, h3 = st.columns([1, 6, 1])
        h1.markdown('<div class="table-header">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="table-header">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h3.markdown('<div class="table-header">ELIM</div>', unsafe_allow_html=True)
        
        # FILAS DE PLANILLA
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 1])
            r1.markdown(f'<p class="cell-data" style="text-align:center">{item["Cantidad"]}</p>', unsafe_allow_html=True)
            r2.markdown(f'<p class="cell-data">{item["Articulo"]}</p>', unsafe_allow_html=True)
            if r3.button("X", key=f"x_{idx}"):
                st.session_state.carrito.pop(idx)
                st.rerun()

        st.write("")
        if st.button("🚀 CONFIRMAR TODO Y SUBIR"):
            df_final = pd.DataFrame(st.session_state.carrito)
            df_hist = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_hist, df_final]))
            st.success("Planilla enviada.")
            st.session_state.carrito = []
            time.sleep(1); st.rerun()
