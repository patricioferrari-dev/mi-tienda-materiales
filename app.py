import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦")

st.title("📦 Formulario de Pedidos Online")
st.write("Selecciona los materiales y la cantidad que necesites.")

# 1. Lista de materiales
materiales_disponibles = [
    "13008 CONTROL REMOTO PARA DECO SAGECOM DCWMI303. CON BOT",
    "30032 CABLE COAXIL RG6 QUADSHIELD NEGRO CON PORTANTE",
    "31025 PRECINTO PLÁSTICO NEGRO (150 X 5.5 MM) , CON PROTE",
    "31026 TARUGO DE 8MM PARA LADRILLO HUECO",
    "31027 PITON CON TOPE PARA TARUGO DE 8MM",
    "32085 PASAPARED BLANCO PARA RG6",
    "32098 SILOC TRANSPARENTE CARTUCHO DE 300GR",
    "35042 PRECINTO S20 AZUL FO 2 VIAS",
    "51044 FUENTE P/DECO SAGEMCOM HD",
    "51046 Fuente alimentacion 12V-1,5A / SEI Robotics SEI800",
    "51051 FUENTE 3,1",
    "70016 CABLE DE RED UTP PARA PC (PATCHCORD)",
    "70098 CABLE HDMI",
    "70220 CABLE RCA A PLUG 3,5",
    "87025 CONECTOR DE COMPRESIÓN PARA RG6",
    "87026 O´RING PARA CONECTORES DE RG 6 (SELLO)",
    "87031 DIVISOR DE 3 BOCAS - SPLITTER X3",
    "90002 PILA AAA PARA CONTROL REMOTO",
    "90071 CINTA AUTOVULCANIZANTE",
    "90072 GRAMPA NEGRA CON CLAVO PARA INTERIOR (GRAMPITA)",
    "90090 DIVISOR DE 2 BOCAS",
    "90106 FILTRO PARA ALTOS 102 MHZ",
    "31154 Etiqueta de identificacion para Drop FO (Kit doble)",
    "012009U Fuente Alimentacion 12V - 1A / Extensor Wifi AIRTIES AIR4960X"
]

# Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FORMULARIO DE ENTRADA ---
with st.form("formulario_pedido", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        articulo = st.selectbox("Selecciona el artículo:", materiales_disponibles)
    with col2:
        cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
    
    boton_agregar = st.form_submit_button("Agregar al pedido")
    if boton_agregar:
        st.session_state.carrito.append({"Artículo": articulo, "Cantidad": cantidad})
        st.toast(f"Agregado: {articulo}")

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
        if st.button("Finalizar y Enviar Pedido"):
            try:
                # Establecer conexión con Google Sheets
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # Intentar leer la pestaña 'Pedidos'
                try:
                    # ttl=0 asegura que traiga los datos más recientes y no una copia guardada
                    existente = conn.read(worksheet="Pedidos", ttl=0)
                    # Limpiamos filas vacías si las hubiera
                    existente = existente.dropna(how='all')
                except Exception:
                    # Si la hoja no existe o hay error, empezamos de cero
                    existente = pd.DataFrame(columns=["Artículo", "Cantidad"])
                
                # Unir el pedido actual con lo que ya estaba en el Excel
                # Si 'existente' está vacío, usamos solo df_pedido
                if existente.empty:
                    actualizado = df_pedido
                else:
                    actualizado = pd.concat([existente, df_pedido], ignore_index=True)
                
                # Enviar los datos de vuelta a Google Sheets
                conn.update(worksheet="Pedidos", data=actualizado)
                
                st.balloons()
                st.success("✅ ¡Pedido enviado correctamente a la Hoja de Cálculo!")
                
                # Vaciar el carrito después del éxito
                st.session_state.carrito = []
                # Pequeña pausa para ver el mensaje antes de recargar
                st.info("La lista se limpiará automáticamente...")
                
            except Exception as e:
                st.error(f"Error crítico: {e}")
                st.info("Revisa que el email de la Service Account sea 'Editor' en tu Excel.")
else:
    st.info("El carrito está vacío. Agrega materiales arriba.")
