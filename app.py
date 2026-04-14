# --- INTERFAZ DE CARGA ---
st.button("⬅️ Volver al Menú", on_click=lambda: setattr(st.session_state, 'seccion', 'Menu'))
st.title(f"📝 Pedido de {st.session_state.seccion}")

tab_carga, tab_resumen = st.tabs(["📝 Cargar", "🛒 Carrito"])

with tab_carga:
    with st.form("form_pedido", clear_on_submit=True):
        # 1. Selección de artículo
        seleccion = st.selectbox("Seleccione Artículo:", items_disponibles)
        
        # 2. LÓGICA DE MOTIVOS CONDICIONALES
        motivo_seleccionado = ""
        if st.session_state.seccion == "Herramientas":
            motivo_seleccionado = st.radio("Motivo del pedido:", ["Cambio", "Perdido", "Nunca entregado"], horizontal=True)
        elif st.session_state.seccion == "Indumentaria":
            motivo_seleccionado = st.radio("Motivo del pedido:", ["Desgaste", "Nunca entregado"], horizontal=True)
        
        # 3. Cantidad
        cantidad_str = st.text_input("Cantidad:")
        
        if st.form_submit_button("➕ AÑADIR"):
            if cantidad_str.isdigit() and int(cantidad_str) > 0:
                partes = seleccion.split(" ", 1)
                st.session_state.carrito.append({
                    "Tecnico": st.session_state.email_usuario,
                    "Codigo": partes[0],
                    "Articulo": partes[1] if len(partes) > 1 else "",
                    "Cantidad": int(cantidad_str),
                    "Motivo": motivo_seleccionado, # Se agrega el motivo al diccionario
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.toast("Añadido correctamente")
                st.rerun()
            else:
                st.error("Ingrese una cantidad válida")

with tab_resumen:
    if not st.session_state.carrito:
        st.info("El carrito está vacío.")
    else:
        # Mostrar resumen con el motivo incluido
        for i, item in enumerate(st.session_state.carrito):
            col_t, col_c, col_d = st.columns([3, 1, 0.5])
            with col_t:
                st.write(f"**{item['Codigo']}** - {item['Articulo']}")
                if item['Motivo']: # Si tiene motivo (Herramientas/Indumentaria), mostrarlo abajo
                    st.caption(f"Motivo: {item['Motivo']}")
            
            col_c.write(f"x{item['Cantidad']}")
            
            if col_d.button("❌", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        st.divider()
        
        if st.button("🚀 CONFIRMAR ENVÍO"):
            with st.spinner("Procesando..."):
                try:
                    df_nuevo = pd.DataFrame(st.session_state.carrito)
                    hoja_destino = st.session_state.seccion 
                    
                    try:
                        # Leemos la hoja actual (asegúrate que la hoja en Excel tenga la columna 'Motivo')
                        existente = conn.read(worksheet=hoja_destino, ttl=0).dropna(how='all')
                        act_data = pd.concat([existente, df_nuevo], ignore_index=True)
                    except:
                        act_data = df_nuevo
                    
                    conn.update(worksheet=hoja_destino, data=act_data)
                    
                    # Bloqueo solo para Materiales
                    if st.session_state.seccion == "Materiales":
                        try:
                            ex_auth = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                        except:
                            ex_auth = pd.DataFrame(columns=["Email", "Estado"])
                        nuevo_b = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
                        conn.update(worksheet="Autorizaciones", data=pd.concat([ex_auth, nuevo_b], ignore_index=True))
                    
                    st.success("¡Pedido enviado con éxito!")
                    st.session_state.carrito = []
                    time.sleep(2)
                    st.session_state.seccion = "Menu"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
