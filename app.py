import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="centered")

# CSS Profesional mejorado para los botones de eliminación
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; }
    /* Estilo para el botón X de eliminar */
    .stButton>button[kind="secondary"] {
        color: white;
        background-color: #ff4b4b;
        border: none;
        height: 2.2em;
        width: 2.2em;
        border-radius: 5px;
    }
    .stButton>button[kind="secondary"]:hover {
        background-color: #d33;
        border: none;
    }
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

# 3. CONEXIÓN Y ACCESO
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
        st.error("⚠️ Error en configuración de Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    if 'email_usuario' not in st.session_state:
        st.text_input("Correo Electrónico:", key="email_input", on_change=validar_email)
        st.stop()

    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
    user_row = df_db[df_db['Email'].astype(str).str.lower() == st.session_state.email_usuario]

    if user_row.empty:
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
                lista_dnis = df_p['DNI'].astype(str).str.replace(".0", "", regex=False).str.replace(".", "", regex=False).tolist()
                
                if dni_l in lista_dnis:
                    dni_f = "{:,}".format(int(dni_l)).replace(",", ".")
                    nuevo = pd.DataFrame([{"Email":st.session_state.email_usuario, "Nombre":nom.title(), "Apellido":ape.title(), "Celular":cel, "DNI":dni_f, "Contrasena":pwd}])
                    conn.update(worksheet="DB_Tecnicos", data=pd.concat([df_db, nuevo]))
                    st.success("Registrado correctamente."); time.sleep(1); st.rerun()
                else: st.error("DNI no autorizado.")
        st.stop()
    else:
        datos = user_row.iloc[0]
        p_in = st.text_input(f"Hola {datos['Nombre']}, ingresa tu contraseña:", type="password")
        if st.button("Ingresar"):
            if str(p_in) == str(datos['Contrasena']):
                st.session_state.autenticado = True
                st.session_state.datos_usuario = datos.to_dict()
                st.rerun()
            else: st.error("Contraseña incorrecta")
        st.stop()

# --- 4. LÓGICA DE MENÚ ---
raw_dni = str(st.session_state.datos_usuario.get('DNI', ''))
dni_actual = raw_dni.split(".")[0].replace(" ", "").replace(".", "") 

if st.session_state.seccion == "Menu":
    st.session_state.carrito = []
    st.title("🏢 SGM - Panel de Gestión")
    st.markdown(f"Usuario: **{st.session_state.datos_usuario['Nombre']} {st.session_state.datos_usuario['Apellido']}**")
    st.divider()

    if dni_actual == "1111111":
        col1, col2 = st.columns(2)
        if col1.button("📚\nInsumos Librería"):
            st.session_state.seccion = "Insumos_Libreria"
            st.rerun()
        if col2.button("🧼\nInsumos Limpieza"):
            st.session_state.seccion = "Insumos_Limpieza"
            st.rerun()
    else:
        col1, col2, col3 = st.columns(3)
        if col1.button("📦\nMateriales"): st.session_state.seccion = "Materiales"; st.rerun()
        if col2.button("🔧\nHerramientas"): st.session_state.seccion = "Herramientas"; st.rerun()
        if col3.button("👕\nIndumentaria"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# --- 5. INTERFAZ DE CARGA ---
st.button("⬅️ Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"Sección: {st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Universitario", "Cinta de Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo de Piso", "Bolsas de Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 Cargar Artículos", "🛒 Mi Pedido"])

with tab1:
    with st.form("f_carga", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.text_input("Cantidad:")
        mot = ""
        if st.session_state.seccion in ["Herramientas", "Indumentaria"]:
            mot = st.radio("Motivo:", ["Cambio", "Desgaste", "Perdido"], horizontal=True)
            
        if st.form_submit_button("➕ AÑADIR"):
            if cant.isdigit() and int(cant) > 0:
                if st.session_state.seccion in ["Insumos_Libreria", "Insumos_Limpieza"]:
                    codigo_final = "S/C"
                    articulo_final = sel
                else:
                    codigo_final = sel.split(" ", 1)[0]
                    articulo_final = sel.split(" ", 1)[1] if " " in sel else ""

                st.session_state.carrito.append({
                    "Nombre": st.session_state.datos_usuario['Nombre'],
                    "Apellido": st.session_state.datos_usuario['Apellido'],
                    "DNI": st.session_state.datos_usuario['DNI'],
                    "Codigo": codigo_final,
                    "Articulo": articulo_final,
                    "Cantidad": int(cant),
                    "Motivo": mot,
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                st.success(f"Añadido: {articulo_final}")
                time.sleep(0.5)
                st.rerun()

with tab2:
    if not st.session_state.carrito:
        st.info("El carrito está vacío.")
    else:
        st.subheader("Resumen del Pedido")
        
        # --- ENCABEZADOS DE "TABLA" MANUAL ---
        h1, h2, h3 = st.columns([1, 4, 1])
        h1.write("**Cant.**")
        h2.write("**Descripción**")
        h3.write("**Elim.**")
        st.divider()

        # --- FILAS DE PRODUCTOS ---
        for i, item in enumerate(st.session_state.carrito):
            c1, c2, c3 = st.columns([1, 4, 1])
            
            # Columna 1: Cantidad
            c1.write(f"{item['Cantidad']}")
            
            # Columna 2: Artículo (con código si existe)
            if item['Codigo'] == "S/C":
                c2.write(f"{item['Articulo']}")
            else:
                c2.write(f"[{item['Codigo']}] {item['Articulo']}")
            
            # Columna 3: Botón X Rojo
            # Usamos kind="secondary" para el estilo CSS personalizado de arriba
            if c3.button("✖", key=f"del_{i}", kind="secondary"):
                st.session_state.carrito.pop(i)
                st.rerun()
            
            st.markdown("---") # Línea divisoria entre celdas

        # --- ACCIONES FINALES ---
        if st.button("🚀 CONFIRMAR Y ENVIAR PEDIDO"):
            try:
                df_e = pd.DataFrame(st.session_state.carrito)
                ex = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
                conn.update(worksheet=st.session_state.seccion, data=pd.concat([ex, df_e]))
                st.balloons()
                st.success("¡Pedido enviado correctamente!")
                st.session_state.carrito = []
                st.session_state.seccion = "Menu"
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
