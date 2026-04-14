import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="wide")

# 2. CSS PARA ESTILO HOJA DE CÁLCULO (EXCEL STYLE)
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .block-container { max-width: 950px; padding-top: 2rem; }

    /* Contenedor principal */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }

    /* ESTILO TABLA COMPACTA */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        margin-bottom: -1px !important; /* Une las celdas */
    }

    div[data-testid="stColumn"] {
        border: 1px solid #d1d5db !important;
        padding: 4px 10px !important; /* Padding mínimo como Excel */
        min-height: 32px !important;
        display: flex;
        align-items: center;
        background-color: white;
    }

    /* Encabezados de tabla */
    .header-cell {
        background-color: #f8fafc !important;
        font-weight: bold;
        color: #475569;
        font-size: 0.85rem;
    }

    /* BOTÓN X ESTILO CELDA */
    div[data-testid="stColumn"] button {
        background-color: transparent !important;
        color: #ef4444 !important;
        border: none !important;
        height: 22px !important;
        width: 100% !important;
        font-size: 14px !important;
        font-weight: bold !important;
        padding: 0px !important;
        margin: 0px !important;
    }
    
    div[data-testid="stColumn"] button:hover {
        background-color: #fee2e2 !important;
        border-radius: 4px;
    }

    .cell-text {
        font-size: 0.9rem;
        color: #1e293b;
        margin: 0;
    }

    #MainMenu, footer, header {visibility: hidden;}
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
    email = st.text_input("Email:")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
        user = df_db[(df_db['Email'].str.lower() == email.lower()) & (df_db['Contrasena'].astype(str) == pwd)]
        if not user.empty:
            st.session_state.autenticado = True
            st.session_state.datos_usuario = user.iloc[0].to_dict()
            st.rerun()
    st.stop()

# 5. MENÚ
dni_actual = str(st.session_state.datos_usuario['DNI']).split(".")[0]

if st.session_state.seccion == "Menu":
    st.title("🏢 Gestión de Stock")
    st.write(f"Usuario: **{st.session_state.datos_usuario['Nombre']}**")
    
    # Botones de menú grandes
    c1, c2, c3 = st.columns(3)
    if dni_actual == "1111111":
        if c1.button("📚\nLIBRERÍA"): st.session_state.seccion = "Insumos_Libreria"; st.rerun()
        if c2.button("🧼\nLIMPIEZA"): st.session_state.seccion = "Insumos_Limpieza"; st.rerun()
    else:
        if c1.button("📦\nMATERIALES"): st.session_state.seccion = "Materiales"; st.rerun()
        if c2.button("🔧\nHERRAMIENTAS"): st.session_state.seccion = "Herramientas"; st.rerun()
        if c3.button("👕\nINDUMENTARIA"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# 6. CARGA Y TABLA
st.button("⬅️ Menú", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.subheader(f"Sección: {st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 CARGAR ARTÍCULO", "📊 REVISAR PLANILLA"])

with t1:
    with st.form("carga_f", clear_on_submit=True):
        sel = st.selectbox("Seleccione:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1)
        if st.form_submit_button("AÑADIR"):
            # Lógica Anti-Duplicados
            art_final = sel.split(" ", 1)[1] if " " in sel and "Insumos" not in st.session_state.seccion else sel
            if any(item['Articulo'] == art_final for item in st.session_state.carrito):
                st.error("Este artículo ya está en la lista.")
            else:
                cod_f = sel.split(" ", 1)[0] if " " in sel and "Insumos" not in st.session_state.seccion else "S/C"
                st.session_state.carrito.append({
                    "Articulo": art_final, "Codigo": cod_f, "Cantidad": int(cant),
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Nombre": st.session_state.datos_usuario['Nombre']
                })
                st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("No hay datos cargados.")
    else:
        # ENCABEZADOS ESTILO EXCEL
        h1, h2, h3 = st.columns([1, 5, 1])
        h1.markdown('<div class="header-cell">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-cell">DESCRIPCIÓN DEL ARTÍCULO</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-cell">ELIM</div>', unsafe_allow_html=True)
        
        # FILAS
        for i, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 5, 1])
            r1.markdown(f'<p class="cell-text">{item["Cantidad"]}</p>', unsafe_allow_html=True)
            r2.markdown(f'<p class="cell-text">{item["Articulo"]}</p>', unsafe_allow_html=True)
            if r3.button("X", key=f"btn_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()

        st.write("")
        if st.button("🚀 CONFIRMAR Y ENVIAR PLANILLA"):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_db = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_db, df_new]))
            st.success("Enviado con éxito.")
            st.session_state.carrito = []
            time.sleep(1); st.rerun()
