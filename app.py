import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="wide")

# 2. CSS DE ALTO NIVEL: X Minimalista y Grilla Pulida
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
    }
    .stButton>button:hover { border-color: #3b82f6; color: #3b82f6; transform: translateY(-5px); }

    /* Grilla de Pedidos: Celdas más compactas */
    div[data-testid="stColumn"] {
        border: 1px solid #eef2f6 !important;
        padding: 5px 10px !important;
        display: flex; align-items: center; justify-content: center;
        background-color: #ffffff;
        min-height: 45px !important;
    }

    /* BOTÓN X MINIMALISTA (Corrección de tamaño) */
    div[data-testid="stColumn"] button {
        background-color: transparent !important;
        color: #ff4b4b !important;
        border: 1px solid #ff4b4b !important;
        height: 24px !important;  /* Tamaño similar a la letra */
        width: 24px !important;
        min-width: 24px !important;
        padding: 0px !important;
        font-size: 14px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    div[data-testid="stColumn"] button:hover {
        background-color: #ff4b4b !important;
        color: white !important;
    }

    /* Quitar bordes extra de los tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    
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
    st.title("🔐 Acceso")
    with st.container():
        email_log = st.text_input("Correo:")
        pass_log = st.text_input("Contraseña:", type="password")
        if st.button("Entrar"):
            df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            user = df_db[(df_db['Email'].str.lower() == email_log.lower()) & (df_db['Contrasena'].astype(str) == pass_log)]
            if not user.empty:
                st.session_state.autenticado = True
                st.session_state.datos_usuario = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

# 5. MENÚ PRINCIPAL
dni_raw = str(st.session_state.datos_usuario.get('DNI', ''))
dni_actual = dni_raw.split(".")[0].replace(" ", "").replace(".", "")

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.subheader(f"Hola, {st.session_state.datos_usuario['Nombre']}")
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

# 6. CARGA Y REVISIÓN
col_back, col_title = st.columns([1, 6])
with col_back:
    if st.button("⬅️"): st.session_state.seccion = "Menu"; st.rerun()
with col_title:
    st.title(st.session_state.seccion.replace('_', ' '))

# Listas (puedes ampliar estas listas)
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
    with st.form("carga_f", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.text_input("Cantidad:")
        mot = st.radio("Motivo:", ["Cambio", "Desgaste", "Perdido"], horizontal=True) if st.session_state.seccion in ["Herramientas", "Indumentaria"] else ""
        
        if st.form_submit_button("AÑADIR AL CARRITO"):
            art_final = sel.split(" ", 1)[1] if " " in sel and st.session_state.seccion not in ["Insumos_Libreria", "Insumos_Limpieza"] else sel
            
            # BLOQUEO DE DUPLICADOS
            if any(x['Articulo'] == art_final for x in st.session_state.carrito):
                st.warning(f"El artículo '{art_final}' ya está en la lista.")
            elif cant.isdigit() and int(cant) > 0:
                cod_f = sel.split(" ", 1)[0] if " " in sel and st.session_state.seccion not in ["Insumos_Libreria", "Insumos_Limpieza"] else "S/C"
                st.session_state.carrito.append({
                    "Articulo": art_final, "Codigo": cod_f, "Cantidad": int(cant),
                    "Motivo": mot, "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": st.session_state.datos_usuario['Nombre'], "DNI": st.session_state.datos_usuario['DNI']
                })
                st.success("Añadido correctamente.")
                time.sleep(0.5); st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("El carrito está vacío.")
    else:
        # Encabezados de tabla con bordes
        h1, h2, h3 = st.columns([1, 4, 1])
        h1.markdown("**Cant.**")
        h2.markdown("**Descripción**")
        h3.markdown("**Eliminar**")
        
        for i, item in enumerate(st.session_state.carrito):
            c1, c2, c3 = st.columns([1, 4, 1])
            c1.write(f"{item['Cantidad']}")
            c2.write(f"{item['Articulo']}")
            # Botón X minimalista
            if c3.button("X", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()

        st.write("")
        if st.button("🚀 ENVIAR PEDIDO FINAL"):
            try:
                df_send = pd.DataFrame(st.session_state.carrito)
                df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
                conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_send]))
                st.balloons()
                st.session_state.carrito = []
                st.session_state.seccion = "Menu"
                time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Error al enviar: {e}")
