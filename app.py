import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="centered")

# 2. CSS AVANZADO: Cuadrícula, líneas punteadas y botones
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* Botones grandes del menú */
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; }
    
    /* Estructura de Cuadrícula en el Pedido */
    [data-testid="stHorizontalBlock"] {
        border-bottom: 1px dashed #bbb;
        padding: 5px 0px !important;
        align-items: center;
        gap: 0px !important;
    }

    /* Líneas verticales punteadas */
    div[data-testid="stColumn"] {
        border-right: 1px dashed #bbb;
        padding: 0px 10px !important;
        display: flex;
        align-items: center;
    }

    /* Quitar línea vertical en la última columna (donde está la X) */
    div[data-testid="stColumn"]:last-child {
        border-right: none;
    }

    /* Botón X Rojo Mini */
    div[data-testid="stColumn"] button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        height: 25px !important;
        width: 25px !important;
        min-width: 25px !important;
        padding: 0px !important;
        margin: 0px auto !important;
        border-radius: 4px !important;
        font-size: 12px !important;
        line-height: 1 !important;
    }
    
    div[data-testid="stColumn"] button:hover {
        background-color: #d33 !important;
    }

    .compact-text {
        font-size: 14px !important;
        margin: 0px !important;
        padding: 0px !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 3. INICIALIZACIÓN DE ESTADOS
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'datos_usuario' not in st.session_state:
    st.session_state.datos_usuario = None
if 'seccion' not in st.session_state:
    st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 4. CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

# 5. LÓGICA DE ACCESO
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
                else: st.error("DNI no en padrón.")
        st.stop()
    else:
        datos = user_row.iloc[0]
        p_in = st.text_input(f"Hola {datos['Nombre']}, contraseña:", type="password")
        if st.button("Ingresar"):
            if str(p_in) == str(datos['Contrasena']):
                st.session_state.autenticado = True
                st.session_state.datos_usuario = datos.to_dict()
                st.rerun()
            else: st.error("Incorrecta")
        st.stop()

# 6. LÓGICA DE MENÚ (DNI SEGURO)
raw_dni = str(st.session_state.datos_usuario.get('DNI', ''))
dni_actual = raw_dni.split(".")[0].replace(" ", "").replace(".", "")

if st.session_state.seccion == "Menu":
    st.session_state.carrito = [] # Limpiar carrito al volver al menú
    st.title("🏢 SGM - Gestión")
    st.write(f"Usuario: {st.session_state.datos_usuario['Nombre']}")
    st.divider()

    if dni_actual == "1111111":
        col1, col2 = st.columns(2)
        if col1.button("📚\nInsumos Librería"): st.session_state.seccion = "Insumos_Libreria"; st.rerun()
        if col2.button("🧼\nInsumos Limpieza"): st.session_state.seccion = "Insumos_Limpieza"; st.rerun()
    else:
        col1, col2, col3 = st.columns(3)
        if col1.button("📦\nMateriales"): st.session_state.seccion = "Materiales"; st.rerun()
        if col2.button("🔧\nHerramientas"): st.session_state.seccion = "Herramientas"; st.rerun()
        if col3.button("👕\nIndumentaria"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# 7. INTERFAZ DE CARGA
st.button("⬅️ Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"{st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 Cargar", "🛒 Pedido"])

with tab1:
    with st.form("f_carga", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.text_input("Cantidad:")
        mot = st.radio("Motivo:", ["Cambio", "Desgaste", "Perdido"], horizontal=True) if st.session_state.seccion in ["Herramientas", "Indumentaria"] else ""
            
        if st.form_submit_button("➕ AÑADIR"):
            if cant.isdigit() and int(cant) > 0:
                if st.session_state.seccion in ["Insumos_Libreria", "Insumos_Limpieza"]:
                    cod_f, art_f = "S/C", sel
                else:
                    cod_f = sel.split(" ", 1)[0]
                    art_f = sel.split(" ", 1)[1] if " " in sel else ""

                st.session_state.carrito.append({
                    "Nombre": st.session_state.datos_usuario['Nombre'],
                    "Apellido": st.session_state.datos_usuario['Apellido'],
                    "DNI": st.session_state.datos_usuario['DNI'],
                    "Codigo": cod_f, "Articulo": art_f, "Cantidad": int(cant),
                    "Motivo": mot, "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                st.rerun()

with tab2:
    if not st.session_state.carrito:
        st.info("Vacío")
    else:
        # Encabezados con líneas verticales punteadas
        h1, h2, h3 = st.columns([1, 4, 1])
        h1.markdown("<p class='compact-text'><b>Cant</b></p>", unsafe_allow_html=True)
        h2.markdown("<p class='compact-text'><b>Artículo</b></p>", unsafe_allow_html=True)
        h3.markdown("<p class='compact-text'><b>X</b></p>", unsafe_allow_html=True)
        
        for i, item in enumerate(st.session_state.carrito):
            row_c1, row_c2, row_c3 = st.columns([1, 4, 1])
            row_c1.markdown(f"<p class='compact-text'>{item['Cantidad']}</p>", unsafe_allow_html=True)
            desc = f"[{item['Codigo']}] {item['Articulo']}" if item['Codigo'] != "S/C" else item['Articulo']
            row_c2.markdown(f"<p class='compact-text'>{desc}</p>", unsafe_allow_html=True)
            if row_c3.button("✖", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()

        st.write("")
        if st.button("🚀 ENVIAR PEDIDO"):
            try:
                df_e = pd.DataFrame(st.session_state.carrito)
                ex = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
                conn.update(worksheet=st.session_state.seccion, data=pd.concat([ex, df_e]))
                st.success("¡Pedido enviado!"); st.session_state.carrito = []; st.session_state.seccion = "Menu"
                time.sleep(1.5); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
