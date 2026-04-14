import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦")

st.title("📦 Formulario de Pedidos Online")
st.write("Selecciona los materiales y la cantidad que necesites.")

# 1. Lista de materiales y precios (opcional)
materiales_disponibles = {
    "13008	CONTROL REMOTO PARA DECO SAGECOM DCWMI303. CON BOT": 
    "30032	CABLE COAXIL RG6 QUADSHIELD NEGRO CON PORTANTE":
    "31025	PRECINTO PLÁSTICO NEGRO (150 X 5.5 MM) , CON PROTE": 
    "31026	TARUGO DE 8MM PARA LADRILLO HUECO": 
    "31027	PITON CON TOPE PARA TARUGO DE 8MM": 
    "32085	PASAPARED BLANCO PARA RG6": 
    "32098	SILOC TRANSPARENTE CARTUCHO DE 300GR": 
    "35042	PRECINTO S20 AZUL FO 2 VIAS": 
    "51044	FUENTE P/DECO SAGEMCOM HD": 
    "51046	Fuente alimentacion 12V-1,5A / SEI Robotics SEI800": 
    "51051	FUENTE 3,1": 
    "70016	CABLE DE RED UTP PARA PC (PATCHCORD)":
    "70098	CABLE HDMI":
    "70220	CABLE RCA A PLUG 3,5":
    "87025	CONECTOR DE COMPRESIÓN PARA RG6":
    "87026	O´RING PARA CONECTORES DE RG 6 (SELLO)":
    "87031	DIVISOR DE 3 BOCAS - SPLITTER X3":
    "90002	PILA AAA PARA CONTROL REMOTO":
    "90071	CINTA AUTOVULCANIZANTE":
    "90072	GRAMPA NEGRA  CON CLAVO PARA INTERIOR (GRAMPITA)":
    "90090	DIVISOR DE 2 BOCAS ":
    "90106	FILTRO PARA ALTOS 102 MHZ":
    "31154	Etiqueta de identificacion para Drop FO (Kit doble)":
    "012009U  Fuente Alimentacion 12V - 1A / Extensor Wifi AIRTIES AIR4960X":
    
    
}

# Inicializar el carrito en la sesión del navegador
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
        precio_unitario = materiales_disponibles[articulo]
        subtotal = precio_unitario * cantidad
        st.session_state.carrito.append({
            "Artículo": articulo,
            "Cantidad": cantidad,
            "Precio Unit.": f"${precio_unitario}",
            "Subtotal": subtotal
        })
        st.success(f"¡{articulo} agregado!")

# --- RESUMEN DEL PEDIDO ---
st.subheader("🛒 Resumen de tu Pedido")

if st.session_state.carrito:
    df = pd.DataFrame(st.session_state.carrito)
    st.table(df)
    
    total = df["Subtotal"].sum()
    st.metric(label="TOTAL A PAGAR", value=f"${total:,.2f}")
    
    if st.button("Limpiar Pedido"):
        st.session_state.carrito = []
        st.rerun()

    # Botón final para simular el envío
    if st.button("Finalizar y Enviar Pedido"):
        st.balloons()
        st.success("✅ Pedido enviado correctamente. ¡Gracias por su compra!")
else:
    st.info("El carrito está vacío.")
