with col_b:
        if st.button("🚀 ENVIAR Y FINALIZAR"):
            try:
                # 1. Guardar Pedidos en la hoja 'Pedidos'
                try:
                    existente = conn.read(worksheet="Pedidos", ttl=0).dropna(how='all')
                except Exception:
                    existente = pd.DataFrame(columns=["Tecnico", "Codigo", "Articulo", "Cantidad"])
                
                actualizado = pd.concat([existente, df_pedido], ignore_index=True)
                conn.update(worksheet="Pedidos", data=actualizado)
                
                # 2. Registrar Bloqueo en la hoja 'Autorizaciones'
                try:
                    auth_ex = conn.read(worksheet="Autorizaciones", ttl=0).dropna(how='all')
                except Exception:
                    auth_ex = pd.DataFrame(columns=["Email", "Estado"])
                
                nuevo_bloqueo = pd.DataFrame([{"Email": st.session_state.email_usuario, "Estado": "Bloqueado"}])
                auth_final = pd.concat([auth_ex, nuevo_bloqueo], ignore_index=True)
                conn.update(worksheet="Autorizaciones", data=auth_final)
                
                st.balloons()
                st.success("✅ ¡Pedido enviado con éxito!")
                st.session_state.carrito = []
                st.rerun()
                
            except Exception as e:
                st.error(f"Error crítico al guardar: {e}")
