import streamlit as st
import requests
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import time
import re
import uuid

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

# 2. FUNCIONES DE VALIDACIÓN Y AUDITORÍA
def registrar_log(usuario, dni, evento, seccion="-", detalle="-"):
    try:
        tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
        ahora = datetime.now(tz_ba).strftime("%d/%m/%Y %H:%M:%S")
        nuevo_log = pd.DataFrame([{
            "Fecha": ahora,
            "Usuario": usuario,
            "DNI": str(dni),
            "Evento": evento,
            "Seccion": seccion,
            "Detalle": detalle
        }])
        df_logs = conn.read(worksheet="Logs", ttl=0).dropna(how='all')
        conn.update(worksheet="Logs", data=pd.concat([df_logs, nuevo_log], ignore_index=True))
    except:
        pass 

def es_email_valido(email):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, email) is not None

def es_horario_permitido():
    tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ba)
    return 7 <= ahora.hour < 15

def limpiar_dni(valor):
    if pd.isna(valor): return ""
    # Convertimos a string, quitamos el .0 si es float y limpiamos espacios
    v = str(valor).split('.')[0].replace(" ", "").strip()
    return v

# 3. ESTADOS DE SESIÓN
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'modo_registro' not in st.session_state: st.session_state.modo_registro = False
if 'reestablecer' not in st.session_state: st.session_state.reestablecer = False
if 'user_a_reestablecer' not in st.session_state: st.session_state.user_a_reestablecer = None
if 'seccion' not in st.session_state: st.session_state.seccion = "Menu"
if 'carrito' not in st.session_state: st.session_state.carrito = []

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. SISTEMA DE ACCESO
if not st.session_state.autenticado:
    if st.session_state.reestablecer:
        st.title("🔑 Asignar Acceso")
        user = st.session_state.user_a_reestablecer
        dni_limpio_user = limpiar_dni(user.get('DNI', ''))
        st.info(f"Usuario: {user.get('Nombre')} {user.get('Apellido')} (DNI: {dni_limpio_user})")
        
        with st.form("form_reset"):
            n_mail = st.text_input("Asignar Email:").strip().lower()
            n_cel = st.text_input("Celular (10 dígitos):").strip()
            nueva_p = st.text_input("Nueva Contraseña:", type="password")
            confirm_p = st.text_input("Confirmar Contraseña:", type="password")
            
            if st.form_submit_button("GUARDAR Y ACTIVAR CUENTA"):
                cel_limpio = n_cel.replace(" ", "").replace("-", "").replace(".", "")
                
                if not es_email_valido(n_mail): 
                    st.error("⚠️ Email no válido.")
                elif len(cel_limpio) != 10: 
                    st.error("⚠️ El celular debe tener 10 dígitos.")
                elif nueva_p != confirm_p: 
                    st.error("⚠️ Las contraseñas no coinciden.")
                else:
                    with st.spinner("Actualizando base de datos..."):
                        # Leemos la base de datos
                        df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
                        
                        # --- LIMPIEZA DE DECIMALES (.0) Y CONVERSIÓN A TEXTO ---
                        for col in ['DNI', 'Celular', 'Contrasena']:
                            if col in df_db.columns:
                                df_db[col] = df_db[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                        
                        # Buscamos el índice del usuario
                        idx = -1
                        for i, row in df_db.iterrows():
                            if limpiar_dni(row['DNI']) == dni_limpio_user:
                                idx = i
                                break
                        
                        if idx != -1:
                            # Asignamos nuevos valores
                            df_db.at[idx, 'Contrasena'] = str(nueva_p)
                            df_db.at[idx, 'Email'] = str(n_mail)
                            df_db.at[idx, 'Celular'] = str(cel_limpio)
                            
                            # Guardamos en Google Sheets
                            conn.update(worksheet="DB_Tecnicos", data=df_db)
                            
                            registrar_log(f"{user.get('Nombre')} {user.get('Apellido')}", dni_limpio_user, "REGISTRO_EXITOSO", "Acceso", "Cuenta activada")
                            st.success("✅ Cuenta activada.")
                            st.session_state.reestablecer = False
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Error: No se encontró el DNI en la base para actualizar.")

    elif st.session_state.modo_registro:
        st.title("📝 Registro de Usuario")
        with st.form("form_padron"):
            dni_input = st.text_input("DNI (Sin puntos):").strip().replace(".", "")
            if st.form_submit_button("VERIFICAR PADRÓN"):
                df_db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
                encontrado = False
                for _, row in df_db.iterrows():
                    if limpiar_dni(row['DNI']) == dni_input:
                        encontrado = True
                        pass_existente = str(row.get('Contrasena', '')).strip().lower()
                        if pass_existente not in ["", "nan", "none"]:
                            st.error("⚠️ Este DNI ya tiene una cuenta activa.")
                        else:
                            st.session_state.user_a_reestablecer = row.to_dict()
                            st.session_state.reestablecer = True
                            st.session_state.modo_registro = False
                            st.rerun()
                        break
                if not encontrado: st.error("🚫 DNI no encontrado en el padrón.")
        if st.button("⬅️ Volver"): 
            st.session_state.modo_registro = False
            st.rerun()

    else:
        st.title("🔐 Acceso SGM")
        u_id = st.text_input("Email o DNI:").strip().lower()
        u_pass = st.text_input("Contraseña:", type="password").strip()
        c1, c2 = st.columns(2)
        
        if c1.button("Ingresar", use_container_width=True):
            db = conn.read(worksheet="DB_Tecnicos", ttl=0).dropna(how='all')
            user_match = None
            
            # Buscamos coincidencia por Email o DNI
            for _, row in db.iterrows():
                email_db = str(row.get('Email', '')).lower().strip()
                dni_db = limpiar_dni(row.get('DNI', ''))
                if email_db == u_id or dni_db == u_id:
                    user_match = row
                    break
            
            if user_match is not None:
                real_pass = str(user_match.get('Contrasena', '')).strip()
                # Si no tiene contraseña, mandarlo a activar cuenta
                if real_pass.lower() in ["", "nan", "none"]:
                    st.session_state.user_a_reestablecer = user_match.to_dict()
                    st.session_state.reestablecer = True
                    st.rerun()
                elif real_pass == u_pass:
                    st.session_state.autenticado = True
                    st.session_state.datos_usuario = user_match.to_dict()
                    registrar_log(f"{user_match.get('Nombre')} {user_match.get('Apellido')}", u_id, "LOGIN_EXITOSO", "Acceso")
                    st.rerun()
                else: 
                    st.error("❌ Contraseña incorrecta.")
            else: 
                st.error("❌ Usuario no encontrado.")
                
        if c2.button("Registrarme", use_container_width=True): 
            st.session_state.modo_registro = True
            st.rerun()
    st.stop()

# 5. MENÚ PRINCIPAL
def cambiar_seccion(nueva):
    if st.session_state.seccion != nueva:
        st.session_state.carrito = []
        st.session_state.seccion = nueva

# (Tu diccionario de PERMISOS se mantiene igual aquí...)
PERMISOS = {
    "Materiales": ["3333333", "11111111", "1111111111", "3855426", "34556566", "42617418", "43098136", "94715302", "44459597", "40777756", "94061021", "38327668", "94509310", "42375056", "37157151", "22543919", "33786801", "37702546", "29007778", "40244391", "31190690", "37015165", "32379681", "25627805", "94032245", "38512342", "39964904", "31891314", "39515561", "34705748", "95879282", "42572404", "41779740", "41917064", "25897847", "33915674", "37345461", "95859981", "35695574", "40979109", "42013818", "42046209", "43180923", "24768515", "41199185", "46108423", "38562170", "35773829", "42024623", "45356650", "38554456", "28764673", "38945380", "44822585"],
    "Herramientas": ["3333333", "33333333", "111111111", "11111111", "3855426", "34556566", "42617418", "43098136", "94715302", "44459597", "40777756", "94061021", "38327668", "94509310", "42375056", "37157151", "22543919", "33786801", "37702546", "29007778", "40244391", "31190690", "37015165", "32379681", "25627805", "94032245", "38512342", "39964904", "31891314", "39515561", "34705748", "95879282", "42572404", "41779740", "41917064", "25897847", "33915674", "37345461", "95859981", "35695574", "40979109", "42013818", "42046209", "43180923", "24768515", "41199185", "46108423", "38562170", "35773829", "42024623", "45356650", "38554456", "28764673", "38945380", "44822585"],
    "Indumentaria": ["3333333", "55555555", "11111111", "3855426", "34556566", "42617418", "43098136", "94715302", "44459597", "40777756", "94061021", "38327668", "94509310", "42375056", "37157151", "22543919", "33786801", "37702546", "29007778", "40244391", "31190690", "37015165", "32379681", "25627805", "94032245", "38512342", "39964904", "31891314", "39515561", "34705748", "95879282", "42572404", "41779740", "41917064", "25897847", "33915674", "37345461", "95859981", "35695574", "40979109", "42013818", "42046209", "43180923", "24768515", "41199185", "46108423", "38562170", "35773829", "42024623", "45356650", "38554456", "28764673", "38945380", "44822585"],
    "Libreria": ["3333333", "1111111"],
    "Limpieza": ["3333333", "1111111"]
}

dni_actual = limpiar_dni(st.session_state.datos_usuario.get('DNI', ''))
nombre_completo = f"{st.session_state.datos_usuario.get('Nombre')} {st.session_state.datos_usuario.get('Apellido')}"

if st.session_state.seccion == "Menu":
    st.title("🏢 Panel de Control")
    st.info(f"Sesión iniciada: **{nombre_completo}**")
    
    accesos_reales = [sector for sector, dnis in PERMISOS.items() if dni_actual in dnis]

    if not accesos_reales:
        st.warning("⚠️ Sin permisos asignados.")
    else:
        filas = [accesos_reales[i:i + 3] for i in range(0, len(accesos_reales), 3)]
        for fila in filas:
            cols = st.columns(3)
            for i, sector in enumerate(fila):
                with cols[i]:
                    if sector == "Libreria":
                        if st.button("📚\nLIBRERÍA", use_container_width=True): cambiar_seccion("Insumos_Libreria"); st.rerun()
                    elif sector == "Limpieza":
                        if st.button("🧼\nLIMPIEZA", use_container_width=True): cambiar_seccion("Insumos_Limpieza"); st.rerun()
                    elif sector == "Materiales":
                        try:
                            df_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                            autorizado = False
                            for _, row in df_auth.iterrows():
                                if limpiar_dni(row['DNI']) == dni_actual and str(row.get('Estado', '')).lower() == "ok":
                                    autorizado = True
                                    break
                            
                            if not es_horario_permitido(): 
                                st.button("🔒\nMAT. (Horario)", disabled=True, use_container_width=True)
                            elif not autorizado: 
                                st.button("🚫\nMAT. (Bloqueado)", disabled=True, use_container_width=True)
                            else:
                                if st.button("📦\nMATERIALES", use_container_width=True): 
                                    cambiar_seccion("Materiales")
                                    st.rerun()
                        except Exception as e: 
                            st.error(f"Error en Autorizaciones: {e}")
                    
                    elif sector == "Herramientas":
                        if st.button("🔧\nHERRAMIENTAS", use_container_width=True): cambiar_seccion("Herramientas"); st.rerun()
                    elif sector == "Indumentaria":
                        if st.button("👕\nINDUMENTARIA", use_container_width=True): cambiar_seccion("Indumentaria"); st.rerun()

    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()
    st.stop()

# 6. PANEL DE CARGA
# (El resto de tu código de listas e interfaz sigue aquí...)
st.button("⬅️ Menú", on_click=lambda: cambiar_seccion("Menu"))
st.subheader(f"📍 Sector: {st.session_state.seccion}")

listas = {
    "Materiales": [
        "13008 | CONTROL REMOTO PARA DECO SAGECOM DCWMI303. CON BOTONES YT + NETFLIX",
        "30032 | CABLE COAXIL RG6 QUADSHIELD NEGRO CON PORTANTE",
        "30059 | CABLE DROP 1FO 100 M. UN EXTREMO PRECONECTORIZADO SC/APC.",
        "30073 | CABLE DROP 1FO 300 M. UN EXTREMO PRECONECTORIZADO SC/APC.",
        "31025 | PRECINTO PLÁSTICO NEGRO (150 X 5.5 MM) , CON PROTECCIÓN U.V.",
        "31026 | TARUGO DE 8MM",
        "31027 | PITON CON TOPE PARA TARUGO DE 8MM",
        "31034 | MORSETO DE 1 BULON",
        "31154 | ETIQUETA DE IDENTIFICACION PARA DROP FO (KIT DOBLE)",
        "32085 | PASAPARED BLANCO PARA RG6",
        "32098 | SILOC TRANSPARENTE CARTUCHO DE 300GR",
        "35042 | PRECINTO S20 AZUL FO 2 VIAS",
        "51044 | FUENTE P/DECO SAGEMCOM HD",
        "51051 | FUENTE ALIMENTACION MODEM 12V-3.1",
        "51059 | CAJA TERMINAL OPTICA BLANCA DE MONTAJE EN PARED CON 1 ADAPTADOR SC/APC (ROSETA)",
        "70016 | CABLE DE RED UTP PARA PC (PATCHCORD ETHERNET)",
        "70098 | CABLE HDMI",
        "70220 | CABLE RCA A PLUG 3,5",
        "87025 | CONECTOR DE COMPRESIÓN PARA RG6",
        "87026 | O´RING PARA CONECTORES DE RG 6 (SELLO)",
        "87031 | SPLITTER DE 3 BOCAS DESBALANCEADO (DOMICILIARIO)",
        "87099 | (14136787) CONECTOR MECANICO SC/APC PARA CABLE DROP",
        "90002 | PILA AAA PARA CONTROL REMOTO",
        "90071 | CINTA AUTOVULCANIZANTE",
        "90072 | GRAMPA NEGRA CON CLAVO PARA INTERIOR (GRAMPITA)",
        "90090 | DIVISOR DE 2 BOCAS - SPLITTER X2",
        "90106 | FILTRO 102HR"
    ],
    "Herramientas": ["ALARGUE 10 MTS", "ALICATE 8'' STANLEY", "ANTEOJO DE SEGURIDAD", "BOLSO STANLEY 16' PORTAHERRAMIENTAS", "CADENA PARA ESCALERA", "CANDADO", "CARGADOR DE CELULAR", "CASCO DE SEGURIDAD", "CINTA PASACABLE 15MTS", "CINTURON CON CABO DE VIDA", "CONO", "CRIMPEADORA RG6 RG11 COMPRESION", "CUTTER", "DESTORNILLADOR PHILLIP", "DESTORNILLADOR PLANO 6X100MM", "ESCALERA DIELECTRICA PARA POSTE 14 + 14 PELDAÑOS", "LLAVE COMBINADA DE 7/16", "MARTILLO", "MECHA DE 10MM PASANTE", "MECHA DE VIDIA 8MM", "PELA CABLE COAXIAL", "PINZA UNIVERSAL", "PISTOLA CARTUCHO SILICONA", "SACATRAMPAS", "SIM CORPORATIVA", "TALADRO PERCUTOR BOSCH"],
    "Indumentaria": ["REMERA S", "REMERA M", "REMERA L", "REMERA XL", "REMERA XXL", "REMERA XXXL", "REMERA XXXXL", "BUZO S", "BUZO M", "BUZO L", "BUZO XL", "BUZO XXL", "BUZO XXXL", "BUZO XXXXL", "PANTALON 38", "PANTALON 40", "PANTALON 42", "PANTALON 44", "PANTALON 46", "PANTALON 48", "PANTALON 50", "PANTALON 52", "PANTALON 54", "PANTALON 56", "PANTALON 58", "PANTALON 60", "PANTALON 62"],
    "Insumos_Libreria": ["Resma A4", "Lapicera Azul"],
    "Insumos_Limpieza": ["BOLSON HIGIENICO", "BOLSA RESIDUO 100x110", "DESODORANTE PISOS FLORES DE PRIMAVERA 5L", "JABON LIQUIDO 5L", "LAVANDINA CONCENTRADA 5L", "ESPONJA MORTIMER CUADRICULADA", "DESODORANTE DE AMBIENTE EN AEROSOL", "PASTILLA INODORO", "TOALLA INTERCALADAS 20X24CM MANO", "LUSTRAMUEBLES", "FRANELA", "REJILLA", "GUANTES GRANDES N°10", "BOLSA RESIDUO 50x70", "VALLERINA", "CIF BAÑO POWER CREAM GATILLO", "Limpiador Liquido Desinfectante Lysoform", "Mata Cucarachas", "Trapo de Piso", "Mopa", "Secador de piso + Palo mediano"],
}
items = listas.get(st.session_state.seccion, [])

tab1, tab2 = st.tabs(["📝 REGISTRAR", "📋 RESUMEN"])

with tab1:
    with st.form("f_registro", clear_on_submit=True):
        sel = st.selectbox("Elegir Artículo:", items)
        cant = st.number_input("Cantidad:", min_value=1, step=1, value=1)
        motivo = ""
        if st.session_state.seccion in ["Herramientas", "Indumentaria"]:
            motivo = st.selectbox("Motivo:", ["Desgaste", "Perdido", "Nunca entregado"])
            
        if st.form_submit_button("AGREGAR AL RESUMEN", use_container_width=True):
            articulo_limpio = sel.split(" | ")[-1] if " | " in sel else sel
            if any(i['Articulo'] == articulo_limpio for i in st.session_state.carrito):
                st.warning("El artículo ya está en el resumen.")
            else:
                cod_e = sel.split(" | ")[0] if " | " in sel else ""
                tz_ba = pytz.timezone('America/Argentina/Buenos_Aires')
                ahora_ba = datetime.now(tz_ba).strftime("%d/%m/%Y %H:%M")

                st.session_state.carrito.append({
                    "ID_Interno": str(uuid.uuid4())[:8],
                    "Fecha": ahora_ba, 
                    "Email": st.session_state.datos_usuario.get('Email'),
                    "Nombre": st.session_state.datos_usuario.get('Nombre'),
                    "Apellido": st.session_state.datos_usuario.get('Apellido'),
                    "DNI": str(dni_actual),
                    "Codigo": str(cod_e),
                    "Articulo": articulo_limpio, 
                    "Cantidad": int(cant), 
                    "Motivo": motivo
                })
                st.rerun()

with tab2:
    if not st.session_state.carrito:
        st.info("Resumen vacío.")
    else:
        # Encabezados de la tabla
        h1, h2, h3, h4 = st.columns([0.7, 1.2, 5.5, 0.6])
        h1.markdown('<div class="header-box">CT</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">COD</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">DESCRIPCIÓN</div>', unsafe_allow_html=True)
        h4.markdown('<div class="header-box">.</div>', unsafe_allow_html=True)
        
        # Renderizado del carrito actual
        for idx, item in enumerate(st.session_state.carrito):
            r1, r2, r3, r4 = st.columns([0.7, 1.2, 5.5, 0.6])
            r1.markdown(f'<div class="cell-data" style="text-align:center; padding-top:5px;">{item["Cantidad"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="cell-data" style="color:blue; padding-top:5px;">{item["Codigo"]}</div>', unsafe_allow_html=True)
            m_txt = f" - <span style='color:orange;'>{item['Motivo']}</span>" if item['Motivo'] else ""
            r3.markdown(f'<div class="cell-data" style="padding-top:5px;">{item["Articulo"]}{m_txt}</div>', unsafe_allow_html=True)
            if r4.button(".", key=f"del_{idx}", use_container_width=True):
                st.session_state.carrito.pop(idx)
                st.rerun()
        
        st.divider()

        # BOTÓN DE ENVÍO FINAL CON LÓGICA ANTI-SOBREESCRITURA
        if st.button("🚀 ENVIAR PEDIDO FINAL", use_container_width=True):
            with st.spinner("Enviando a la base de datos segura..."):
                try:
                    # 1. TU URL DE FORMRESPONSE (Paso 4)
                    URL_FORM = "https://docs.google.com/forms/d/e/ACA_VA_TU_ID_DE_FORMULARIO/formResponse"

                    # 2. Enviamos cada artículo del carrito
                    for item in st.session_state.carrito:
                        # Reemplazá los números de abajo con tus entry.ids del Paso 3
                        datos_a_enviar = {
                            "entry.1000001": item["ID_Interno"],
                            "entry.1000002": item["Fecha"],
                            "entry.1000003": item["Email"],
                            "entry.1000004": item["Nombre"],
                            "entry.1000005": item["Apellido"],
                            "entry.1000006": item["DNI"],
                            "entry.1000007": item["Codigo"],
                            "entry.1000008": item["Articulo"],
                            "entry.1000009": item["Cantidad"],
                            "entry.1000010": item["Motivo"],
                            "entry.1000011": st.session_state.seccion  # El nombre de la hoja/sector
                        }
                        
                        # Esto envía el dato al formulario
                        respuesta = requests.post(URL_FORM, data=datos_a_enviar)
                        
                        if respuesta.status_code != 200:
                            st.error(f"Error al enviar {item['Articulo']}")

                    # --- BLOQUEO DE SEGURIDAD PARA MATERIALES ---
                    if st.session_state.seccion == "Materiales":
                        try:
                            # Leemos la hoja de autorizaciones para bloquear al usuario
                            df_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                            df_auth['DNI'] = df_auth['DNI'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                            df_auth.loc[df_auth['DNI'] == str(dni_actual), 'Estado'] = "bloqueado"
                            conn.update(worksheet="Autorizaciones", data=df_auth)
                        except:
                            pass # Si falla el bloqueo, al menos el pedido ya se envió

                    st.success("✅ Pedido enviado correctamente.")
                    
                    # Limpiamos todo y volvemos al menú
                    st.session_state.carrito = []
                    time.sleep(1.5)
                    st.session_state.seccion = "Menu"
                    st.rerun()

                except Exception as e:
                    st.error(f"Hubo un problema con la conexión: {e}")
