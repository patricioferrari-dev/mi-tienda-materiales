import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión", page_icon="🏢", layout="wide")

# 2. CSS PARA COMPACIDAD MÁXIMA Y DISEÑO LIMPIO
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 800px; padding-top: 1rem; }

    /* Formulario de carga */
    [data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        padding: 15px !important;
        border-radius: 10px !important;
    }
    .stSelectbox div[data-baseweb="select"], .stNumberInput div[data-baseweb="input"] {
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
    }

    /* Planilla Ultra Compacta */
    [data-testid="stHorizontalBlock"] { gap: 0px !important; margin-bottom: -1px !important; }
    div[data-testid="stColumn"] {
        border: 1px solid #e2e8f0 !important;
        padding: 1px 8px !important;
        background-color: white;
        min-height: 22px !important;
        display: flex; align-items: center;
    }
    .header-box {
        background-color: #475569 !important;
        color: white !important;
        font-weight: 700; font-size: 10px;
        width: 100%; text-align: center;
    }
    .cell-data { font-size: 12px; color: #334155; margin: 0; line-height: 1; }

    /* Botón X Minimalista */
    div[data-testid="stColumn"] button {
        background-color: transparent !important;
        color: #ef4444 !important;
        border: none !important;
        width: 100% !important;
        height: 18px !important;
        font-size: 11px !important;
        font-weight: bold !important;
        padding: 0 !important;
    }
    div[data-testid="stColumn"] button:hover { background-color: #fee2e2 !important; }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 3. FUNCIONES DE CAMBIO DE SECCIÓN (Para evitar mezclar datos)
def cambiar_seccion(nueva_seccion):
    # Si cambiamos de menú, vaciamos el carrito para no mezclar artículos
    if st.session_state.seccion != nueva_seccion:
        st.session_state.carrito = []
        st.session_state.seccion = nueva_seccion

# 4. ESTADOS INICIALES
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 5. LOGIN
if not st.session_state.autenticado:
    st.title("🔐 Acceso SGM")
    user_mail = st.text_input("Usuario:")
    user_pass = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
        valid = df_db[(df_db['Email'].str.lower() == user_mail.lower()) & (df_db['Contrasena'].astype(str) == user_pass)]
        if not valid.empty:
            st.session_state.autenticado = True
            st.session_state.datos_usuario = valid.iloc[0].to_dict()
            st.rerun()
    st.stop()

# 6. MENÚ PRINCIPAL
dni_val = str(st.session_state.datos_usuario.get('DNI', '')).split(".")[0].replace(" ", "")

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.write(f"Operador: **{st.session_state.datos_usuario['Nombre']}**")
    
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

# 7. PANEL DE CARGA Y RESUMEN
st.button("⬅️ Volver al Menú", on_click=lambda: cambiar_seccion("Menu"))
st.markdown(f"### 📍 {st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR CARGA", "📋 RESUMEN PEDIDO"])

with t1:
    with st.form("f_registro", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        if st.form_submit_button("AGREGAR", use_container_width=True):
            # Limpiar nombre artículo
            art_nom = sel.split(" ", 1)[1] if " " in sel and "Insumos" not in st.session_state.seccion else sel
            
            # Evitar duplicados en la lista actual
            if any(i['Articulo'] == art_nom for i in st.session_state.carrito):
                st.error("Este artículo ya está en la lista.")
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
        st.info(f"No hay artículos para {st.session_state.seccion.replace('_', ' ')}.")
    else:
        # Cabecera
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        
        # Filas (usando copia para evitar errores de índice al borrar)
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data" style="text-align:center; width:100%">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"btn_{st.session_state.seccion}_{idx}"):
                st.session_state.carrito.pop(idx)
                st.rerun()

        st.write("")
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            try:
                df_new = pd.DataFrame(st.session_state.carrito)
                # Se envía solo a la hoja correspondiente a la sección actual
                df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
                conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new]))
                
                st.success(f"Pedido de {st.session_state.seccion.replace('_', ' ')} enviado.")
                st.session_state.carrito = [] # Limpiar tras enviar
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
