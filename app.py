import streamlit as st
import pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SGM - Gestión Integral", page_icon="🏢", layout="centered")

# 2. CSS AVANZADO: Diseño de Tarjetas (Cards) y Grilla Técnica
st.markdown("""
    <style>
    /* Fondo general de la app */
    .stApp {
        background-color: #f0f2f6;
    }
    
    /* Contenedor principal tipo Tarjeta */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #e1e4e8;
        margin-bottom: 1rem;
    }

    /* Botones del menú principal */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        font-weight: bold;
        height: 4em;
        background-color: #ffffff;
        border: 1px solid #d1d5db;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .stButton>button:hover {
        border-color: #4CAF50;
        color: #4CAF50;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

    /* Estilo de Celdas para la Tabla de Pedidos */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        margin-bottom: -1px !important;
    }

    div[data-testid="stColumn"] {
        border: 1px solid #dee2e6 !important;
        padding: 12px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
    }

    div[data-testid="stColumn"]:nth-of-type(2) {
        justify-content: flex-start !important;
    }

    /* Botón Eliminar Estilizado */
    div[data-testid="stColumn"] button {
        background-color: transparent !important;
        color: #dc3545 !important;
        border: 1px solid #dc3545 !important;
        height: 28px !important;
        width: auto !important;
        padding: 0px 12px !important;
        font-size: 11px !important;
        text-transform: uppercase;
        font-weight: bold !important;
        border-radius: 6px !important;
    }
    
    div[data-testid="stColumn"] button:hover {
        background-color: #dc3545 !important;
        color: white !important;
    }

    .compact-text {
        font-size: 14px !important;
        margin: 0px !important;
        color: #333;
    }

    /* Ocultar elementos innecesarios */
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
            ape = col2.text_input("Apellido:")
            cel = col1.text_input("Celular:")
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

# 6. LÓGICA DE MENÚ
raw_dni = str(st.session_state.datos_usuario.get('DNI', ''))
dni_actual = raw_dni.split(".")[0].replace(" ", "").replace(".", "")

if st.session_state.seccion == "Menu":
    st.session_state.carrito = [] 
    st.title("🏢 Panel de Control")
    st.subheader(f"Bienvenido, {st.session_state.datos_usuario['Nombre']}")
    st.divider()

    # Los botones dentro de este bloque ahora tendrán el fondo blanco y sombra
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
st.button("⬅️ Volver al Menú Principal", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"{st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Cuaderno Uni.", "Cinta Embalar"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso", "Bolsas Consorcio"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 Cargar Artículos", "🛒 Revisar Pedido"])

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
        st.info("El carrito está vacío actualmente.")
    else:
        # Encabezados de Tabla
        h1, h2, h3 = st.columns([1, 3.5, 1.5])
        h1.markdown("<p class='compact-text'><b>Cant.</b></p>", unsafe_allow_html=True)
        h2.markdown("<p class='compact-text'><b>Descripción</b></p>", unsafe_allow_html=True)
        h3.markdown("<p class='compact-text'><b>Acción</b></p>", unsafe_allow_html=True)
        
        for i, item in enumerate(st.session_state.carrito):
            row_c1, row_c2, row_c3 = st.columns([1, 3.5, 1.5])
            row_c1.markdown(f"<p class='compact-text'>{item['Cantidad']}</p>", unsafe_allow_html=True)
            desc = f"[{item['Codigo']}] {item['Articulo']}" if item['Codigo'] != "S/C" else item['Articulo']
            row_c2.markdown(f"<p class='compact-text'>{desc}</p>", unsafe_allow_html=True)
            
            if row_c3.button("Eliminar", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()

        st.write("")
        if st.button("🚀 ENVIAR PEDIDO FINAL"):
            try:
                df_e = pd.DataFrame(st.session_state.carrito)
                ex = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
                conn.update(worksheet=st.session_state.seccion, data=pd.concat([ex, df_e]))
                st.balloons()
                st.success("¡Pedido enviado con éxito!"); st.session_state.carrito = []; st.session_state.seccion = "Menu"
                time.sleep(2); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
