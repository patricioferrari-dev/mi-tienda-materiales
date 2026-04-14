import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SGM - Gestión", page_icon="🏢", layout="wide")

# 2. CSS (Mantenemos tu estilo compacto)
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

# 3. ESTADOS
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. LÓGICA DE LOGIN Y REGISTRO
if not st.session_state.autenticado:
    if st.session_state.modo_registro:
        # --- PANTALLA DE REGISTRO NUEVO USUARIO ---
        st.title("📝 Registro de Usuario")
        with st.form("form_nuevo_usuario"):
            new_email = st.text_input("Email:").strip().lower()
            new_nombre = st.text_input("Nombre:")
            new_apellido = st.text_input("Apellido:")
            new_dni = st.text_input("DNI (Sin puntos):")
            new_cel = st.text_input("Celular:")
            new_pass = st.text_input("Crea tu Contraseña:", type="password")
            
            if st.form_submit_button("REGISTRARME", use_container_width=True):
                if new_email and new_dni and new_pass:
                    # Verificar si el DNI ya existe
                    df_check = conn.read(worksheet="DB_Tecnicos", ttl=0)
                    if new_dni in df_check['DNI'].astype(str).values:
                        st.error("Este DNI ya está registrado.")
                    else:
                        # Crear fila nueva
                        nuevo_user = pd.DataFrame([{
                            "Email": new_email, "Nombre": new_nombre, "Apellido": new_apellido,
                            "Celular": new_cel, "DNI": new_dni, "Contrasena": new_pass
                        }])
                        updated_db = pd.concat([df_check, nuevo_user], ignore_index=True)
                        conn.update(worksheet="DB_Tecnicos", data=updated_db)
                        st.success("¡Registro exitoso! Ahora puedes ingresar.")
                        st.session_state.modo_registro = False
                        time.sleep(2)
                        st.rerun()
                else:
                    st.warning("Email, DNI y Contraseña son obligatorios.")
        
        if st.button("⬅️ Volver al Login"):
            st.session_state.modo_registro = False
            st.rerun()

    else:
        # --- PANTALLA DE LOGIN ---
        st.title("🔐 Acceso SGM")
        user_mail = st.text_input("Usuario (Email):").strip().lower()
        user_pass = st.text_input("Contraseña:", type="password").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ingresar", use_container_width=True):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                df_db['Email'] = df_db['Email'].astype(str).str.strip().str.lower()
                df_db['Contrasena'] = df_db['Contrasena'].astype(str).str.strip()
                
                match = df_db[(df_db['Email'] == user_mail) & (df_db['Contrasena'] == user_pass)]
                if not match.empty:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Datos incorrectos.")
        
        with col2:
            if st.button("¿No tienes cuenta? Regístrate", use_container_width=True):
                st.session_state.modo_registro = True
                st.rerun()
    st.stop()

# 5. MENÚ PRINCIPAL
def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

dni_raw = str(st.session_state.datos_usuario.get('DNI', '')).split(".")[0].strip()

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.write(f"Operador: **{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}**")
    
    if dni_raw == "1111111":
        c1, c2 = st.columns(2)
        if c1.button("📚\nLIBRERÍA"): cambiar_seccion("Insumos_Libreria"); st.rerun()
        if c2.button("🧼\nLIMPIEZA"): cambiar_seccion("Insumos_Limpieza"); st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        if c1.button("📦\nMATERIALES"): cambiar_seccion("Materiales"); st.rerun()
        if c2.button("🔧\nHERRAMIENTAS"): cambiar_seccion("Herramientas"); st.rerun()
        if c3.button("👕\nINDUMENTARIA"): cambiar_seccion("Indumentaria"); st.rerun()
    st.stop()

# 6. PANEL DE CARGA
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 {st.session_state.seccion}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["H001 PINZA", "H002 ALICATE"],
    "Indumentaria": ["I001 PANTALON", "I002 CHOMBA"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN PEDIDO"])

with t1:
    with st.form("f_registro", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        if st.form_submit_button("AGREGAR", use_container_width=True):
            # Guardamos todos los datos capturados en el login para el registro final
            st.session_state.carrito.append({
                "Fecha": datetime.now().strftime("%d/%m/%Y"),
                "Email": st.session_state.datos_usuario.get('Email'),
                "Nombre": st.session_state.datos_usuario.get('Nombre'),
                "Apellido": st.session_state.datos_usuario.get('Apellido'),
                "Celular": st.session_state.datos_usuario.get('Celular'),
                "DNI": st.session_state.datos_usuario.get('DNI'),
                "Articulo": sel, 
                "Cantidad": int(cant)
            })
            st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("Lista vacía.")
    else:
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"del_{idx}"):
                st.session_state.carrito.pop(idx); st.rerun()
        
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new]))
            st.success("¡Pedido enviado!"); st.session_state.carrito = []; time.sleep(1); st.rerun()
