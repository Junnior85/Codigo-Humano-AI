import streamlit as st
import os
from groq import Groq
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS PERSONALIZADO (AZUL PROFUNDO Y DORADO) ---
st.markdown("""
<style>
    /* FONDO GENERAL */
    .stApp {
        background-color: #050814; /* Azul muy oscuro casi negro */
        color: #E0E0E0;
    }
    
    /* BARRA LATERAL */
    [data-testid="stSidebar"] {
        background-color: #0b101c;
        border-right: 1px solid #1f293a;
    }
    
    /* BOTONES (Estilo Dorado/Elegante) */
    .stButton > button {
        background-color: transparent;
        color: #FFD700; /* Dorado */
        border: 1px solid #FFD700;
        border-radius: 8px;
        transition: all 0.3s;
        width: 100%; 
    }
    .stButton > button:hover {
        background-color: #FFD700;
        color: #000;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
    }

    /* INPUTS DE TEXTO */
    .stTextInput > div > div > input {
        background-color: #151b2b;
        color: white;
        border: 1px solid #2a3b55;
        border-radius: 8px;
    }
    
    /* OCULTAR ELEMENTOS EXTRA DE STREAMLIT */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIÓN DE ESTADO (LOGIN) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# --- 4. FUNCIONES DE INTERFAZ ---

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # --- CARGA DEL LOGO ---
        # Si tu archivo se llama diferente, cambia "logo.png" aquí abajo:
        try:
            st.image("logo.png", use_column_width=True) 
        except:
            # Si falla la imagen, muestra texto dorado
            st.markdown("<h1 style='text-align: center; color: #FFD700;'>CÓDIGO HUMANO AI</h1>", unsafe_allow_html=True)
            
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>Bienvenido</h3>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
        
        with tab1:
            usuario = st.text_input("Usuario", key="login_user")
            # Para pruebas rápidas, cualquier contraseña funciona por ahora
            password = st.text_input("Contraseña", type="password", key="login_pass")
            if st.button("Entrar", key="btn_login"):
                if usuario:
                    st.session_state.authenticated = True
                    st.session_state.user_name = usuario
                    st.success("¡Acceso concedido!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Ingresa un nombre de usuario.")
        
        with tab2:
            st.text_input("Nuevo Usuario")
            st.text_input("Correo Electrónico")
            st.text_input("Crear Contraseña", type="password")
            if st.button("Crear Cuenta"):
                st.success("¡Cuenta registrada! Ahora inicia sesión.")

def main_app():
    # --- CLIENTE GROQ ---
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
    except:
        st.error("⚠️ Falta la API KEY en Secrets.")
        st.stop()

    # --- SIDEBAR CON LOGO ---
    with st.sidebar:
        try:
            st.image("logo.png")
        except:
            st.header("CÓDIGO HUMANO AI")
            
        st.write(f"Conectado como: **{st.session_state.user_name}**")
        st.markdown("---")
        
        menu = st.radio("Menú", ["💬 Chat", "🎨 Personalizar", "📊 Historial", "👤 Perfil"])
        
        st.markdown("---")
        if st.button("🔒 Cerrar Sesión"):
            st.session_state.authenticated = False
            st.session_state.messages = []
            st.rerun()

    # --- PANTALLAS ---
    if menu == "💬 Chat":
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Barra de Iconos
        c1, c2, c3, c4, spacer = st.columns([1,1,1,1, 10])
        with c1: st.button("🎤", help="Dictado")
        with c2: st.button("📞", help="Llamada")
        with c3: st.button("📹", help="Video")
        with c4: st.button("📎", help="Adjuntar")
        
        st.markdown("---")

        # Historial de chat
        for message in st.session_state.messages:
            if message["role"] != "system":
                avatar = "👤" if message["role"] == "user" else "🧠"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        # Input
        prompt = st.chat_input(f"Habla con nosotros...")
        
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            # Prompt del Sistema (Terapéutico)
            system_prompt = {
                "role": "system",
                "content": f"""Eres Código Humano AI. Tu usuario es {st.session_state.user_name}.
                Tu objetivo es validar emociones, reducir la ansiedad y escuchar activamente.
                Usa un tono cálido y profesional. Modelo: Llama 3.3 Versatile."""
            }
            messages_model = [system_prompt] + st.session_state.messages

            with st.chat_message("assistant", avatar="🧠"):
                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_model,
                    stream=True,
                )
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})

    elif menu == "🎨 Personalizar":
        st.title("Ajustes")
        st.slider("Nivel de Empatía", 0, 100, 95)
        st.selectbox("Voz", ["Humana", "Robot", "Neutra"])

    elif menu == "👤 Perfil":
        st.title("Perfil de Usuario")
        st.text_input("Nombre", value=st.session_state.user_name)

# --- 5. CONTROL PRINCIPAL ---
if not st.session_state.authenticated:
    login_page()
else:
    main_app()
