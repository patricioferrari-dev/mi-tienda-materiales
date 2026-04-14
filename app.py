import streamlit as st
import pandas as pd
import urllib.parse

# Configuración de la página
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦")

st.title("📦 Formulario de Pedidos Online")
st.write("Selecciona los materiales y la cantidad que necesites.")

# 1. Lista de materiales
materiales_disponibles = {
    "13008 CONTROL REMOTO PARA DECO SAGECOM DCWMI303. CON BOT": 0,
    "30032 CABLE COAXIL RG6 QUADSHIELD NEGRO CON PORTANTE": 0,
    "31025 PRECINTO PLÁSTICO NEGRO (150 X 5.5 MM) , CON PROTE": 0,
    "31026 TARUGO DE 8MM PARA LADRILLO HUECO": 0,
    "31027 PITON CON TOPE PARA TARUGO DE 8MM": 0,
    "32085 PASAPARED BLANCO PARA RG6": 0,
    "32098 SILOC TRANSPARENTE CARTUCHO DE 300GR": 0,
    "35042 PRECINTO S20 AZUL FO 2 VIAS": 0,
    "51044 FUENTE P/DECO SAGEMCOM HD": 0,
    "51046 Fuente alimentacion 12V-1,5A / SEI Robotics SEI800": 0,
    "51051 FUENTE 3,1": 0,
    "70016 CABLE DE RED UTP PARA PC (PATCHCORD)": 0,
    "70098 CABLE HDMI": 0,
    "70220 CABLE RCA A PLUG 3,5": 0,
    "87025 CONECTOR DE COMPRESIÓN PARA RG6": 0,
    "87026 O´RING PARA CONECTORES DE RG 6 (SELLO)": 0,
    "87031 DIVISOR DE 3 BOCAS - SPLITTER X3": 0,
    "90002 PILA AAA PARA CONTROL REMOTO": 0,
    "90071 CINTA AUTOVULCANIZANTE": 0,
    "90072 GRAMPA NEGRA CON CLAVO PARA INTERIOR (GRAMPITA)": 0,
    "90090 DIVISOR DE 2 BOCAS": 0,
    "90106 FILTRO PARA ALTOS 102 MHZ": 0,
    "31154 Etiqueta de identificacion para Drop FO (Kit doble)": 0,
    "012009U Fuente Alimentacion 12V - 1A / Extensor Wifi AIRTIES AIR4960X": 0
}

# Inicializar el carrito
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FORMULARIO DE ENTRADA ---
with st.form("formulario_pedido"):
    col1, col2 = st.columns([2, 1])
    with col1:
        articulo = st.selectbox("Selecciona el artículo:", list(materiales_disponibles.keys()))
    with col2:
        cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
    
    boton_agregar = st.form_submit_button("Agregar al pedido")
    if boton_agregar:
        st.session_state.carrito.append({"Artículo": articulo, "Cantidad": cantidad})
        st.success(f"✅ ¡{articulo} agregado!")

# --- RESUMEN DEL PEDIDO ---
st.subheader("🛒 Resumen de tu Pedido")

if st.session_state.carrito:
    df_pedido = pd.DataFrame(st.session_state.carrito)
    st.table(df_pedido)
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Limpiar Pedido"):
            st.session_state.carrito = []
            st.rerun()

    with col_b:
        # --- LÓGICA DE WHATSAPP ---
        # 1. Configura tu número aquí (con código de país, ej: 549 para Argentina)
        mi_numero = "1121591930" # <--- CAMBIA ESTO POR TU NÚMERO
        
        # 2. Construir el texto del mensaje
        texto = "📦 *NUEVO PEDIDO DE MATERIALES*\n\n"
        for i, row in df_pedido.iterrows():
            texto += f"• {row['Artículo']} -> *{row['Cantidad']} unidades*\n"
        
        # 3. Codificar para URL
        texto_codificado = urllib.parse.quote(texto)
        link_wa = f"https://wa.me/{mi_numero}?text={texto_codificado}"
        
        # 4. Botón de envío
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 10px; text-align: center; border-radius: 5px; font-weight: bold;">
                    🚀 FINALIZAR Y ENVIAR POR WHATSAPP
                </div>
            </a>
        """, unsafe_allow_html=True)

else:
    st.info("El carrito está vacío.")
