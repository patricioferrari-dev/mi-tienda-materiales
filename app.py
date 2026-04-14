import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="wide")

# 2. CSS DE ALTO NIVEL: Centrado, Sombras Suaves y Botones Modernos
st.markdown("""
    <style>
    /* Fondo con degradado sutil */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Centrado del contenedor principal */
    .block-container {
        max-width: 800px;
        padding-top: 5rem;
        padding-bottom: 5rem;
    }

    /* Tarjeta Principal (Glassmorphism) */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        padding: 3rem;
        border-radius: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 1px solid rgba(255, 255, 255, 0.3);
        text-align: center;
    }

    /* Títulos y Subtítulos */
    h1 {
        color: #1e293b;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }
    
    .stSubheader p {
        color: #64748b !important;
        font-weight: 500;
    }

    /* Botones del Menú Principal */
    .stButton>button {
        width: 100%;
        border-radius: 16px;
        font-weight: 700;
        height: 5em;
        background-color: #ffffff;
        color: #334155;
        border: 1px solid #e2e8f0;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        font-size: 1.1rem;
    }
    
    .stButton>button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(59, 130, 246, 0.15);
    }

    /* Tabla de Pedidos tipo Grid */
    div[data-testid="stColumn"] {
        border: 1px solid #e2e8f0 !important;
        padding: 15px !important;
        background-color: #ffffff;
        border-radius: 4px;
    }

    /* Botón Eliminar Minimalista */
    div[data-testid="stColumn"] button {
        background-color: #fff1f2 !important;
        color: #e11d48 !important;
        border: 1px solid #fecdd3 !important;
        height: 32px !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="stColumn"] button:hover {
        background-color: #e11d48 !important;
        color: white !important;
    }

    /* Ocultar elementos de Streamlit */
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
        st.error("⚠️ Error en configuración de Secrets.")

if not st.session_state.autenticado:
    st.title("🔐 Acceso")
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
            ape = col2.text_input("Apellido:")
            cel = col1.text_input("Celular:")
            pwd = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("Finalizar Registro"):
                dni_l = dni_in.replace(".","").strip()
                df_p = conn.read(worksheet="Padron_DNI", ttl=0)
                lista_dnis = df_p['DNI'].astype(str).str.replace(".0", "", regex=False).str.replace(".", "", regex=False).tolist()
                if dni_l in lista_dnis:
                    dni_f = "{:,}".format(int(dni_l)).replace(",", ".")
                    nuevo = pd.DataFrame([{"Email":st.session_state.email_usuario, "Nombre":nom.title(), "Apellido":ape.title(), "Celular":cel, "DNI":dni_f, "Contrasena":pwd}])
                    conn.update(worksheet="DB_Tecnicos", data=pd.concat([df_db, nuevo]))
                    st.success("¡Registro exitoso!"); time.sleep(1); st.rerun()
                else: st.error("DNI no habilitado.")
        st.stop()
    else:
        datos = user_row.iloc[0]
        st.subheader(f"Hola, {datos['Nombre']}")
        p_in = st.text_input("Ingresa tu contraseña:", type="password")
        if st.button("Entrar"):
            if str(p_in) == str(datos['Contrasena']):
                st.session_state.autenticado = True
                st.session_state.datos_usuario = datos.to_dict()
                st.rerun()
            else: st.error("Contraseña incorrecta")
        st.stop()

# 6. LÓGICA DE MENÚ
raw_dni = str(st.session_state.datos_usuario.get('DNI', ''))
dni_actual = raw_dni.split(".")[0].replace(" ", "").replace(".", "")

if st.session_state.seccion == "Menu":
    st.session_state.carrito = [] 
    st.title("🏢 Panel de Control")
    st.subheader(f"Bienvenido al sistema de gestión")
    st.write("---")

    if dni_actual == "1111111":
        col1, col2 = st.columns(2)
        if col1.button("📚\nINSUMOS LIBRERÍA"): st.session_state.seccion = "Insumos_Libreria"; st.rerun()
        if col2.button("🧼\nINSUMOS LIMPIEZA"): st.session_state.seccion = "Insumos_Limpieza"; st.rerun()
    else:
        col1, col2, col3 = st.columns(3)
        if col1.button("📦\nMATERIALES"): st.session_state.seccion = "Materiales"; st.rerun()
        if col2.button("🔧\nHERRAMIENTAS"): st.session_state.seccion = "Herramientas"; st.rerun()
        if col3.button("👕\nINDUMENTARIA"): st.session_state.seccion = "Indumentaria"; st.rerun()
    st.stop()

# 7. INTERFAZ DE CARGA
col_back, col_title = st.columns([1, 4])
with col_back:
    if st.button("⬅️"): st.session_state.seccion = "Menu"; st.rerun()
with col_title:
    st.title(st.session_state.seccion.replace('_', ' '))

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 CARGAR ARTÍCULOS", "🛒 REVISAR PEDIDO"])

with tab1:
    with st.form("f_carga", clear_on_submit=True):
        sel = st.selectbox("Seleccione Artículo:", items)
        cant = st.text_input("Ingrese Cantidad:")
        mot = st.radio("Motivo:", ["Cambio", "Desgaste", "Perdido"], horizontal=True) if st.session_state.seccion in ["Herramientas", "Indumentaria"] else ""
            
        if st.form_submit_button("➕ AÑADIR AL CARRITO"):
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
        st.info("No has añadido artículos todavía.")
    else:
        # Encabezados
        h1, h2, h3 = st.columns([1, 3.5, 1.5])
        h1.markdown("**Cant.**")
        h2.markdown("**Descripción**")
        h3.markdown("**Acción**")
        
        for i, item in enumerate(st.session_state.carrito):
            row_c1, row_c2, row_c3 = st.columns([1, 3.5, 1.5])
            row_c1.write(f"{item['Cantidad']}")
            desc = f"[{item['Codigo']}] {item['Articulo']}" if item['Codigo'] != "S/C" else item['Articulo']
            row_c2.write(desc)
            if row_c3.button("Eliminar", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()

        st.write("---")
        if st.button("🚀 ENVIAR PEDIDO FINAL"):
            try:
                df_e = pd.DataFrame(st.session_state.carrito)
                ex = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
                conn.update(worksheet=st.session_state.seccion, data=pd.concat([ex, df_e]))
                st.balloons()
                st.success("¡Pedido enviado!"); st.session_state.carrito = []; st.session_state.seccion = "Menu"
                time.sleep(1.5); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
