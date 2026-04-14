import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="centered")

# CSS Profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. INICIALIZACIÓN DE ESTADOS
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'datos_usuario' not in st.session_state:
    st.session_state.datos_usuario = None
if 'seccion' not in st.session_state:
    st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 3. CONEXIÓN Y LÓGICA DE ACCESO (Igual a la anterior)
conn = st.connection("gsheets", type=GSheetsConnection)

def validar_email():
    email = st.session_state.email_input.lower().strip()
    try:
        lista_autorizados = st.secrets["usuarios_autorizados"]["emails"]
        if email in [e.lower() for e in lista_autorizados]:
            st.session_state.email_usuario = email
        else:
            st.error("🚫 Correo no autorizado.")
    except:
        st.error("⚠️ Error en Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    if 'email_usuario' not in st.session_state:
        st.text_input("Correo Electrónico:", key="email_input", on_change=validar_email)
        st.stop()

    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
    df_db['Email'] = df_db['Email'].astype(str)
    df_db['Contrasena'] = df_db['Contrasena'].astype(str)
    user_row = df_db[df_db['Email'] == st.session_state.email_usuario]

    if user_row.empty:
        # --- REGISTRO ---
        st.warning("Completa tu registro:")
        with st.form("reg"):
            col1, col2 = st.columns(2)
            dni_in = col1.text_input("DNI:")
            nom = col2.text_input("Nombre:")
            ape = col1.text_input("Apellido:")
            cel = col2.text_input("Celular:")
            pwd = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("Registrar"):
                dni_l = dni_in.replace(".","").strip()
                df_p = conn.read(worksheet="Padron_DNI", ttl=0)
                if dni_l in df_p['DNI'].astype(str).tolist():
                    dni_f = "{:,}".format(int(dni_l)).replace(",", ".")
                    nuevo = pd.DataFrame([{"Email":st.session_state.email_usuario, "Nombre":nom.title(), "Apellido":ape.title(), "Celular":cel, "DNI":dni_f, "Contrasena":pwd}])
                    conn.update(worksheet="DB_Tecnicos", data=pd.concat([df_db, nuevo]))
                    st.success("Registrado correctamente."); time.sleep(1); st.rerun()
                else: st.error("DNI no en padrón.")
        st.stop()
    else:
        # --- LOGIN ---
        datos = user_row.iloc[0]
        p_in = st.text_input(f"Hola {datos['Nombre']}, contraseña:", type="password")
        if st.button("Ingresar"):
            if str(p_in) == str(datos['Contrasena']):
                st.session_state.autenticado = True
                st.session_state.datos_usuario = datos.to_dict()
                st.rerun()
            else: st.error("Incorrecta")
        st.stop()

# --- 4. LÓGICA DE MENÚ DIFERENCIADO POR DNI ---
dni_actual = st.session_state.datos_usuario['DNI'].replace(".", "")

if st.session_state.seccion == "Menu":
    st.title("🏢 SGM - Panel de Gestión")
    st.write(f"Usuario: {st.session_state.datos_usuario['Nombre']}")
    st.divider()

    # SI ES EL DNI ESPECIAL (Limpieza y Librería)
    if dni_actual == "1111111":
        col1, col2 = st.columns(2)
        if col1.button("📚\nInsumos Librería"):
            st.session_state.seccion = "Insumos_Libreria"
            st.rerun()
        if col2.button("🧼\nInsumos Limpieza"):
            st.session_state.seccion = "Insumos_Limpieza"
            st.rerun()
    
    # SI ES CUALQUIER OTRO DNI (Materiales, Herramientas, Indumentaria)
    else:
        col1, col2, col3 = st.columns(3)
        if col1.button("📦\nMateriales"): st.session_state.seccion = "Materiales"; st.rerun()
        if col2.button("🔧\nHerramientas"): st.session_state.seccion = "Herramientas"; st.rerun()
        if col3.button("👕\nIndumentaria"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# --- 5. INTERFAZ DE CARGA UNIVERSAL ---
st.button("⬅️ Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"Sección: {st.session_state.seccion.replace('_', ' ')}")

# Listas de artículos según sección
listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["L001 RESMA A4", "L002 LAPICERA AZUL", "L003 BROCHADORA"],
    "Insumos_Limpieza": ["C001 LAVANDINA", "C002 DETERGENTE", "C003 TRAPO PISO"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 Cargar", "🛒 Mi Pedido"])

with tab1:
    with st.form("f_carga", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.text_input("Cantidad:")
        # Motivos solo para herramientas/ropa
        mot = ""
        if st.session_state.seccion in ["Herramientas", "Indumentaria"]:
            mot = st.radio("Motivo:", ["Cambio", "Desgaste", "Perdido"], horizontal=True)
            
        if st.form_submit_button("➕ AÑADIR"):
            if cant.isdigit() and int(cant) > 0:
                cod = sel.split(" ", 1)[0]
                if not any(i['Codigo'] == cod for i in st.session_state.carrito):
                    st.session_state.carrito.append({
                        "Nombre": st.session_state.datos_usuario['Nombre'],
                        "Apellido": st.session_state.datos_usuario['Apellido'],
                        "DNI": st.session_state.datos_usuario['DNI'],
                        "Codigo": cod,
                        "Articulo": sel.split(" ", 1)[1] if " " in sel else "",
                        "Cantidad": int(cant),
                        "Motivo": mot,
                        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    st.rerun()
                else: st.error("Ya está en el carrito.")

with tab2:
    if not st.session_state.carrito: st.info("Vacio")
    else:
        for i, item in enumerate(st.session_state.carrito):
            st.write(f"**{item['Codigo']}** - {item['Articulo']} (x{item['Cantidad']})")
            if st.button("❌", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        if st.button("🚀 ENVIAR PEDIDO"):
            try:
                df_e = pd.DataFrame(st.session_state.carrito)
                # Guarda en la hoja que coincide con el nombre de la sección
                ex = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
                conn.update(worksheet=st.session_state.seccion, data=pd.concat([ex, df_e]))
                st.success("¡Enviado!"); st.session_state.carrito = []
                st.session_state.seccion = "Menu"; time.sleep(2); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
