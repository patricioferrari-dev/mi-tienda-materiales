import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN DE PÁGINA Y CSS
st.set_page_config(page_title="SGM - Gestión de Pedidos", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 800px; padding-top: 1rem; }
    [data-testid="stForm"] { background-color: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; }
    [data-testid="stHorizontalBlock"] { gap: 0px !important; margin-bottom: -1px !important; }
    div[data-testid="stColumn"] { border: 1px solid #e2e8f0; padding: 2px 8px; background-color: white; min-height: 26px; display: flex; align-items: center; }
    .header-box { background-color: #475569; color: white; font-weight: 700; font-size: 10px; width: 100%; text-align: center; }
    .cell-data { font-size: 12px; color: #334155; margin: 0; line-height: 1.1; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 2. LÓGICA DE CONTROL HORARIO (BUENOS AIRES)
def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    dia_semana = ahora.weekday() # 0=Lun, 2=Mie, 4=Vie
    hora_actual = ahora.hour
    return dia_semana in [0, 2, 4] and 7 <= hora_actual < 15

# 3. ESTADOS DE SESIÓN
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'reestablecer' not in st.session_state: st.session_state.reestablecer = False
if 'user_a_reestablecer' not in st.session_state: st.session_state.user_a_reestablecer = None
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. SISTEMA DE ACCESO (LOGIN / REGISTRO / RESET)
if not st.session_state.autenticado:
    
    # --- MODO REESTABLECER / ASIGNAR PASS ---
    if st.session_state.reestablecer:
        st.title("🔑 Asignar Acceso")
        user = st.session_state.user_a_reestablecer
        st.info(f"Usuario: {user['Nombre']} {user['Apellido']} (DNI: {user['DNI']})")
        with st.form("form_reset"):
            n_mail = st.text_input("Asignar/Confirmar Email:").strip().lower()
            n_cel = st.text_input("Celular de contacto:").strip()
            nueva_p = st.text_input("Nueva Contraseña:", type="password")
            confirm_p = st.text_input("Confirmar Contraseña:", type="password")
            if st.form_submit_button("GUARDAR Y ACTIVAR CUENTA"):
                if nueva_p == confirm_p and len(nueva_p) > 0 and n_mail:
                    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                    # Localizar por DNI (limpio)
                    df_db['DNI_STR'] = df_db['DNI'].astype(str).str.split('.').str[0].str.strip()
                    idx = df_db.index[df_db['DNI_STR'] == str(user['DNI']).split('.')[0]].tolist()[0]
                    
                    df_db.at[idx, 'Contrasena'] = nueva_p
                    df_db.at[idx, 'Email'] = n_mail
                    df_db.at[idx, 'Celular'] = n_cel
                    conn.update(worksheet="DB_Tecnicos", data=df_db.drop(columns=['DNI_STR']))
                    
                    st.success("Cuenta activada. Ya puedes ingresar.")
                    st.session_state.reestablecer = False
                    time.sleep(2); st.rerun()
                else: st.error("Error en los datos o las contraseñas no coinciden.")
        if st.button("Volver"): st.session_state.reestablecer = False; st.rerun()

    # --- MODO REGISTRO (SOLO PADRÓN) ---
    elif st.session_state.modo_registro:
        st.title("📝 Registro de Usuario")
        st.write("Verificaremos si tu DNI está habilitado en el padrón.")
        with st.form("form_padron"):
            dni_input = st.text_input("DNI (Sin puntos):").strip().replace(".", "")
            if st.form_submit_button("VERIFICAR PADRÓN"):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                df_db['DNI_STR'] = df_db['DNI'].astype(str).str.split('.').str[0].str.strip()
                match = df_db[df_db['DNI_STR'] == dni_input]
                
                if not match.empty:
                    st.session_state.user_a_reestablecer = match.iloc[0].to_dict()
                    st.session_state.reestablecer = True
                    st.session_state.modo_registro = False
                    st.rerun()
                else:
                    st.error("🚫 DNI no encontrado en el padrón. Contacte a Soporte/Administración.")
        if st.button("⬅️ Volver al Login"): st.session_state.modo_registro = False; st.rerun()

    # --- MODO LOGIN ---
    else:
        st.title("🔐 Acceso SGM")
        u_id = st.text_input("Email o DNI:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        c1, c2 = st.columns(2)
        
        if c1.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            db['DNI_STR'] = db['DNI'].astype(str).str.split('.').str[0].str.strip()
            # Buscar por mail o por DNI
            user_match = db[(db['Email'].astype(str).str.lower() == u_id) | (db['DNI_STR'] == u_id)]
            
            if not user_match.empty:
                real_pass = str(user_match.iloc[0].get('Contrasena', '')).strip()
                if real_pass.lower() in ["", "nan", "none"]:
                    st.session_state.user_a_reestablecer = user_match.iloc[0].to_dict()
                    st.session_state.reestablecer = True
                    st.rerun()
                elif real_pass == u_pass:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = user_match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
            else: st.error("Usuario no registrado en el padrón.")
                
        if c2.button("Registrarme", use_container_width=True): 
            st.session_state.modo_registro = True
            st.rerun()
    st.stop()

# 5. MENÚ PRINCIPAL
def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

dni_actual = str(st.session_state.datos_usuario.get('DNI', '')).split(".")[0].strip()

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.write(f"Operador: **{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}**")
    
    if dni_actual == "1111111": # Modo Administrador (Librería/Limpieza)
        c1, c2 = st.columns(2)
        if c1.button("📚\nLIBRERÍA"): cambiar_seccion("Insumos_Libreria"); st.rerun()
        if c2.button("🧼\nLIMPIEZA"): cambiar_seccion("Insumos_Limpieza"); st.rerun()
    else: # Modo Técnico
        c1, c2, c3 = st.columns(3)
        # RESTRICCIÓN MATERIALES L-M-V 7-15h
        if es_horario_permitido():
            if c1.button("📦\nMATERIALES"): cambiar_seccion("Materiales"); st.rerun()
        else:
            c1.button("🔒\nMAT. CERRADO", disabled=True, help="Lunes, Miércoles y Viernes de 07:00 a 15:00")
            
        if c2.button("🔧\nHERRAMIENTAS"): cambiar_seccion("Herramientas"); st.rerun()
        if c3.button("👕\nINDUMENTARIA"): cambiar_seccion("Indumentaria"); st.rerun()
    st.stop()

# 6. PANEL DE CARGA DE PRODUCTOS
st.button("⬅️ Menú Principal", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 Sector: {st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO", "FICHAS RJ45"],
    "Herramientas": ["PINZA DE PUNTA", "ALICATE", "DESTORNILLADOR PH", "DESTORNILLADOR PL", "TESTER"],
    "Indumentaria": ["PANTALON T.40", "PANTALON T.42", "CHOMBA L", "CHOMBA XL", "BOTINES"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul", "Carpeta"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente", "Trapo Piso"]
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 SELECCIONAR ARTÍCULOS", "📋 RESUMEN Y ENVIAR"])

with tab1:
    with st.form("f_registro", clear_on_submit=True):
        sel = st.selectbox("Elegir Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        
        # Motivos según sección
        motivo = ""
        if st.session_state.seccion == "Herramientas":
            motivo = st.selectbox("Motivo del pedido:", ["Rotura", "Perdido", "Nunca entregado"])
        elif st.session_state.seccion == "Indumentaria":
            motivo = st.selectbox("Motivo del pedido:", ["Desgaste", "Nunca entregado"])
            
        if st.form_submit_button("AGREGAR AL RESUMEN", use_container_width=True):
            # VALIDACIÓN NO DUPLICADOS (Solo por nombre de artículo)
            if any(i['Articulo'] == sel for i in st.session_state.carrito):
                st.warning(f"⚠️ El artículo '{sel}' ya está en tu resumen de pedido.")
            else:
                st.session_state.carrito.append({
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Email": st.session_state.datos_usuario.get('Email'),
                    "Nombre": st.session_state.datos_usuario.get('Nombre'),
                    "Apellido": st.session_state.datos_usuario.get('Apellido'),
                    "Celular": st.session_state.datos_usuario.get('Celular'),
                    "DNI": st.session_state.datos_usuario.get('DNI'),
                    "Articulo": sel, 
                    "Cantidad": int(cant),
                    "Motivo": motivo
                })
                st.rerun()

with tab2:
    if not st.session_state.carrito:
        st.info("El resumen está vacío.")
    else:
        st.markdown("**Artículos para enviar:**")
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN / MOTIVO</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data" style="text-align:center">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            
            # Mostrar motivo si existe de forma segura
            m_txt = f" ({item.get('Motivo', '')})" if item.get('Motivo') else ""
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}{m_txt}</div>', unsafe_allow_html=True)
            
            if r3.button("X", key=f"del_{idx}"):
                st.session_state.carrito.pop(idx); st.rerun()
        
        st.write("")
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            # Unir y subir
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new], ignore_index=True))
            
            st.success("¡Pedido enviado correctamente al sistema!")
            st.session_state.carrito = []
            time.sleep(1.5); st.rerun()
