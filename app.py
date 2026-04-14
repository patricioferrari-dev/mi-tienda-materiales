import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="wide")

# 2. CSS DE ALTO NIVEL: Diseño de Celdas y Botón X
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    
    .block-container { max-width: 900px; padding-top: 4rem; }

    /* Tarjeta Principal */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        padding: 2.5rem;
        border-radius: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* Botones Menú Principal */
    .stButton>button {
        width: 100%; border-radius: 18px; font-weight: 700;
        min-height: 100px; padding: 15px 25px !important;
        background-color: #ffffff; color: #334155;
        border: 1px solid #e2e8f0; transition: all 0.4s ease;
        font-size: 1.1rem !important;
    }
    .stButton>button:hover { border-color: #3b82f6; color: #3b82f6; transform: translateY(-5px); }

    /* Grilla de Pedidos (Celdas) */
    div[data-testid="stColumn"] {
        border: 1px solid #dee2e6 !important;
        padding: 10px !important;
        display: flex; align-items: center; justify-content: center;
        background-color: #ffffff;
    }

    /* Estilo para la X de eliminación */
    div[data-testid="stColumn"] button[kind="secondary"] {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        height: 25px !important;
        width: 25px !important;
        min-width: 25px !important;
        border-radius: 5px !important;
        padding: 0px !important;
        font-weight: bold !important;
        line-height: 1 !important;
    }
    
    div[data-testid="stColumn"] button[kind="secondary"]:hover {
        background-color: #d33 !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 3. ESTADOS
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. ACCESO (Simplificado para brevedad, mantiene tu lógica de Secrets)
if not st.session_state.autenticado:
    st.title("🔐 Acceso")
    email_log = st.text_input("Correo:")
    pass_log = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
        user = df_db[(df_db['Email'] == email_log) & (df_db['Contrasena'] == pass_log)]
        if not user.empty:
            st.session_state.autenticado = True
            st.session_state.datos_usuario = user.iloc[0].to_dict()
            st.rerun()
        else: st.error("Datos incorrectos")
    st.stop()

# 5. MENÚ PRINCIPAL
dni_actual = str(st.session_state.datos_usuario['DNI']).split(".")[0]

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.write(f"Usuario: {st.session_state.datos_usuario['Nombre']}")
    st.divider()

    if dni_actual == "1111111":
        c1, c2 = st.columns(2)
        if c1.button("📚\nINSUMOS\nLIBRERÍA"): st.session_state.seccion = "Insumos_Libreria"; st.rerun()
        if c2.button("🧼\nINSUMOS\nLIMPIEZA"): st.session_state.seccion = "Insumos_Limpieza"; st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        if c1.button("📦\nMATERIALES"): st.session_state.seccion = "Materiales"; st.rerun()
        if c2.button("🔧\nHERRAMIENTAS"): st.session_state.seccion = "Herramientas"; st.rerun()
        if c3.button("👕\nINDUMENTARIA"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# 6. CARGA DE ARTÍCULOS
st.button("⬅️ Volver", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(st.session_state.seccion.replace('_', ' '))

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 CARGAR", "🛒 REVISAR"])

with t1:
    with st.form("carga_form", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.text_input("Cantidad:")
        mot = st.radio("Motivo:", ["Cambio", "Desgaste", "Perdido"], horizontal=True) if st.session_state.seccion in ["Herramientas", "Indumentaria"] else ""
        
        if st.form_submit_button("AÑADIR"):
            # Lógica Anti-Duplicados
            art_nombre = sel.split(" ", 1)[1] if " " in sel and st.session_state.seccion not in ["Insumos_Libreria", "Insumos_Limpieza"] else sel
            existe = any(item['Articulo'] == art_nombre for item in st.session_state.carrito)
            
            if existe:
                st.warning(f"⚠️ El artículo '{art_nombre}' ya está en el pedido. Elimínalo si deseas cambiar la cantidad.")
            elif cant.isdigit() and int(cant) > 0:
                cod_f = sel.split(" ", 1)[0] if " " in sel and st.session_state.seccion not in ["Insumos_Libreria", "Insumos_Limpieza"] else "S/C"
                st.session_state.carrito.append({
                    "Articulo": art_nombre, "Codigo": cod_f, "Cantidad": int(cant),
                    "Motivo": mot, "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": st.session_state.datos_usuario['Nombre'], "DNI": st.session_state.datos_usuario['DNI']
                })
                st.success("Añadido."); time.sleep(0.5); st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("Vacío")
    else:
        # Encabezados
        h1, h2, h3 = st.columns([1, 4, 1])
        h1.write("**Cant**")
        h2.write("**Artículo**")
        h3.write("**X**")
        
        for i, item in enumerate(st.session_state.carrito):
            c1, c2, c3 = st.columns([1, 4, 1])
            c1.write(f"{item['Cantidad']}")
            c2.write(f"{item['Articulo']}")
            if c3.button("X", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()

        if st.button("🚀 ENVIAR TODO"):
            df_final = pd.DataFrame(st.session_state.carrito)
            actual = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([actual, df_final]))
            st.balloons()
            st.session_state.carrito = []
            st.session_state.seccion = "Menu"
            time.sleep(1); st.rerun()
