import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SGM - Gestión", page_icon="🏢", layout="wide")

# 2. CSS PARA COMPACIDAD
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

# 3. LÓGICA DE CONTROL HORARIO (BUENOS AIRES)
def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    dia_semana = ahora.weekday() 
    hora_actual = ahora.hour
    return dia_semana in [0, 2, 4] and 7 <= hora_actual < 15

# 4. ESTADOS
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'reestablecer' not in st.session_state: st.session_state.reestablecer = False
if 'user_a_reestablecer' not in st.session_state: st.session_state.user_a_reestablecer = None
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 5. LOGIN, REGISTRO (CON PADRÓN) Y REESTABLECIMIENTO
if not st.session_state.autenticado:
    
    # --- MODO REESTABLECER ---
    if st.session_state.reestablecer:
        st.title("🔑 Asignar Contraseña")
        st.info(f"Usuario: {st.session_state.user_a_reestablecer['Nombre']} {st.session_state.user_a_reestablecer['Apellido']}. Define tu acceso.")
        with st.form("form_reset"):
            n_mail_upd = st.text_input("Confirmar/Asignar Email:").strip().lower()
            nueva_p = st.text_input("Nueva Contraseña:", type="password")
            confirm_p = st.text_input("Confirmar Contraseña:", type="password")
            if st.form_submit_button("GUARDAR DATOS"):
                if nueva_p == confirm_p and len(nueva_p) > 0 and n_mail_upd:
                    df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                    idx = df_db.index[df_db['DNI'].astype(str) == str(st.session_state.user_a_reestablecer['DNI'])].tolist()[0]
                    df_db.at[idx, 'Contrasena'] = nueva_p
                    df_db.at[idx, 'Email'] = n_mail_upd
                    conn.update(worksheet="DB_Tecnicos", data=df_db)
                    st.success("Datos actualizados. Ya puedes ingresar.")
                    st.session_state.reestablecer = False
                    time.sleep(2); st.rerun()
                else: st.error("Revisa los datos ingresados.")
        if st.button("Cancelar"): st.session_state.reestablecer = False; st.rerun()

    # --- MODO REGISTRO (SOLO SI ESTÁ EN PADRÓN) ---
    elif st.session_state.modo_registro:
        st.title("📝 Registro por Padrón")
        st.write("Ingresa tu DNI para verificar si estás habilitado.")
        with st.form("form_padron"):
            check_dni = st.text_input("DNI (Solo números):").strip()
            if st.form_submit_button("VERIFICAR DNI"):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0)
                # Buscamos el DNI en la base
                user_match = df_db[df_db['DNI'].astype(str) == check_dni]
                
                if not user_match.empty:
                    # Si el DNI existe pero no tiene contraseña, mandamos a reestablecer (asignar pass)
                    st.session_state.user_a_reestablecer = user_match.iloc[0].to_dict()
                    st.session_state.reestablecer = True
                    st.session_state.modo_registro = False
                    st.rerun()
                else:
                    st.error("🚫 El DNI ingresado no figura en el padrón habilitado. Contacte al administrador.")
        if st.button("⬅️ Volver"): st.session_state.modo_registro = False; st.rerun()

    # --- MODO LOGIN ---
    else:
        st.title("🔐 Acceso SGM")
        u_mail = st.text_input("Email o DNI:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        c1, c2 = st.columns(2)
        
        if c1.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0)
            # Buscamos por Email o por DNI
            user_data = db[(db['Email'].astype(str).str.lower() == u_mail) | (db['DNI'].astype(str) == u_mail)]
            
            if not user_data.empty:
                pass_excel = str(user_data.iloc[0].get('Contrasena', '')).strip()
                # Si no tiene contraseña o es nula, forzar asignación
                if pass_excel.lower() in ["", "nan", "none"]:
                    st.session_state.user_a_reestablecer = user_data.iloc[0].to_dict()
                    st.session_state.reestablecer = True
                    st.rerun()
                elif pass_excel == u_pass:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = user_data.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
            else: st.error("Usuario no encontrado en el padrón.")
                
        if c2.button("Registrarme", use_container_width=True): 
            st.session_state.modo_registro = True
            st.rerun()
    st.stop()

# 6. MENÚ PRINCIPAL
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
        if es_horario_permitido():
            if c1.button("📦\nMATERIALES"): cambiar_seccion("Materiales"); st.rerun()
        else:
            c1.button("🔒\nMAT. CERRADO", disabled=True, help="LUN-MIE-VIE 07:00 a 15:00")
        if c2.button("🔧\nHERRAMIENTAS"): cambiar_seccion("Herramientas"); st.rerun()
        if c3.button("👕\nINDUMENTARIA"): cambiar_seccion("Indumentaria"); st.rerun()
    st.stop()

# 7. PANEL DE CARGA
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 {st.session_state.seccion.replace('_', ' ')}")

listas = {
    "Materiales": ["13008 CONTROL", "30032 CABLE", "31025 PRECINTO"],
    "Herramientas": ["PINZA DE PUNTA", "ALICATE", "DESTORNILLADOR PH"],
    "Indumentaria": ["PANTALON T.40", "CHOMBA L", "BOTINES"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul"],
    "Insumos_Limpieza": ["Lavandina 5L", "Detergente"]
}
items = listas.get(st.session_state.seccion, [])

t1, t2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN PEDIDO"])

with t1:
    with st.form("f_reg", clear_on_submit=True):
        sel = st.selectbox("Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        motivo = ""
        if st.session_state.seccion == "Herramientas":
            motivo = st.selectbox("Motivo:", ["Rotura", "Perdido", "Nunca entregado"])
        elif st.session_state.seccion == "Indumentaria":
            motivo = st.selectbox("Motivo:", ["Desgaste", "Nunca entregado"])
            
        if st.form_submit_button("AGREGAR AL RESUMEN", use_container_width=True):
            if any(i['Articulo'] == sel for i in st.session_state.carrito):
                st.warning(f"'{sel}' ya está en el resumen.")
            else:
                st.session_state.carrito.append({
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Email": st.session_state.datos_usuario.get('Email'),
                    "Nombre": st.session_state.datos_usuario.get('Nombre'),
                    "Apellido": st.session_state.datos_usuario.get('Apellido'),
                    "Celular": st.session_state.datos_usuario.get('Celular'),
                    "DNI": st.session_state.datos_usuario.get('DNI'),
                    "Articulo": sel, "Cantidad": int(cant), "Motivo": motivo
                })
                st.rerun()

with t2:
    if not st.session_state.carrito:
        st.info("No hay artículos en el pedido.")
    else:
        h1, h2, h3 = st.columns([1, 6, 0.8])
        h1.markdown('<div class="header-box">CANT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">DESCRIPCIÓN / MOTIVO</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">ELIM</div>', unsafe_allow_html=True)
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3 = st.columns([1, 6, 0.8])
            r1.markdown(f'<div class="cell-data" style="text-align:center">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            txt_motivo = f" ({item.get('Motivo', '')})" if item.get('Motivo') else ""
            r2.markdown(f'<div class="cell-data">{item["Articulo"]}{txt_motivo}</div>', unsafe_allow_html=True)
            if r3.button("X", key=f"del_{idx}"):
                st.session_state.carrito.pop(idx); st.rerun()
        
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            df_new = pd.DataFrame(st.session_state.carrito)
            df_old = conn.read(worksheet=st.session_state.seccion, ttl=0).dropna(how='all')
            conn.update(worksheet=st.session_state.seccion, data=pd.concat([df_old, df_new], ignore_index=True))
            st.success("¡Pedido enviado!"); st.session_state.carrito = []; time.sleep(1); st.rerun()
