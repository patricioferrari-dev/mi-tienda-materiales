import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Sistema de Pedidos", page_icon="📦")

st.title("📦 Formulario de Pedidos Online")
st.write("Selecciona los materiales y la cantidad que necesites.")

# 1. Lista de materiales y precios (opcional)
materiales_disponibles = {
    "Cemento Gris (Saco 50kg)": 150.00,
    "Arena de Río (m3)": 450.00,
    "Ladrillo Rojo (Millar)": 2800.00,
    "Varilla 3/8 (Tramo)": 120.00,
    "Pintura Blanca (Cubeta)": 1100.00
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