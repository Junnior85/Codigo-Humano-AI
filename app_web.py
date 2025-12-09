def login_page():
    # Usamos columnas para centrar el contenido
    col_izq, col_centro, col_der = st.columns([1, 4, 1]) 
    
    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- CARGA DEL LOGO ---
        c_img_1, c_img_2, c_img_3 = st.columns([1, 2, 1])
        with c_img_2: 
            try:
                st.image("logo.png", width=250) 
            except:
                st.markdown("<h1 style='text-align: center; color: #FFD700;'>CÓDIGO HUMANO AI</h1>", unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align: center; color: #a0a0ff; margin-bottom: 20px;'>Tu compañero de bienestar emocional</h4>", unsafe_allow_html=True)
        
        # --- PESTAÑAS ---
        tab1, tab2 = st.tabs(["🔓 Iniciar Sesión", "📝 Registrarse"])
        
        # PESTAÑA 1: LOGIN (Ya tienes cuenta)
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            usuario = st.text_input("Usuario", placeholder="Tu nombre", key="login_user")
            password = st.text_input("Contraseña", type="password", key="login_pass")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ENTRAR", key="btn_login"):
                if usuario:
                    # Guardamos sesión
                    st.session_state.authenticated = True
                    st.session_state.user_name = usuario
                    st.success(f"¡Hola de nuevo, {usuario}!")
                    time.sleep(0.5)
                    st.rerun() # <--- ESTO RECARGA LA PÁGINA Y ENTRA AL CHAT
                else:
                    st.error("Escribe tu usuario.")
        
        # PESTAÑA 2: REGISTRO (Cuenta nueva)
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            col_reg1, col_reg2 = st.columns(2)
            with col_reg1:
                new_user = st.text_input("Crear Usuario", key="reg_user")
            with col_reg2:
                email = st.text_input("Email (Opcional)")
                
            new_pass = st.text_input("Crear Contraseña", type="password", key="reg_pass")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- AQUÍ ESTÁ LA MAGIA DEL AUTO-LOGIN ---
            if st.button("REGISTRARSE Y ENTRAR", key="btn_reg"):
                if new_user and new_pass:
                    # 1. Animación
                    st.balloons()
                    
                    # 2. Guardamos los datos en la sesión INMEDIATAMENTE
                    st.session_state.authenticated = True
                    st.session_state.user_name = new_user
                    
                    # 3. Mensaje de éxito breve
                    st.success("¡Cuenta creada con éxito! Entrando...")
                    
                    # 4. Esperamos un segundo para ver los globos y entramos
                    time.sleep(1.5)
                    st.rerun() # <--- TE MANDA DIRECTO AL CHAT
                else:
                    st.warning("Por favor elige un usuario y contraseña.")
