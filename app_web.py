import streamlit as st  # <--- ESTA LÍNEA ES VITAL QUE ESTÉ AL PRINCIPIO
import os
from groq import Groq
import time

# --- 1. CONFIGURACIÓN DE PÁGINA (Debe ser el primer comando de Streamlit) ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS PERSONALIZADO (AZUL PROFUNDO, DORADO Y LOGO AJUSTADO) ---
st.markdown("""
<style>
    /* FONDO GENERAL */
    .stApp {
        background-color: #050814; 
        color: #E0E0E0;
    }
    
    /* BARRA LATERAL */
    [data-testid="stSidebar"] {
        background-color: #0b101c;
        border-right: 1px solid #1f293a;
    }
    
    /* ESTILO PARA EL LOGO EN EL LOGIN (Redondeado y con brillo) */
    /* Esto evita que se vea como una imagen pegada a la fuerza */
    div[data-testid="stImage"] img {
        border-radius: 20px; 
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.15); 
        transition: transform 0.3s;
    }
    div[data-testid="stImage"] img:hover {
        transform: scale(1.02); 
    }

    /* BOTONES */
    .stButton > button {
        background-color: transparent;
        color: #FFD700;
        border: 1px solid #FFD700;
        border-radius: 8px;
        width: 100%; 
    }
    .stButton > button:hover {
        background-color: #FFD700;
        color: #000;
        font-weight: bold;
    }

    /* INPUTS */
    .stTextInput > div > div > input {
        background-color: #151b2b;
        color: white;
        border: 1px solid #2a3b55;
        border-radius: 8px;
    }
    
    /* OCULTAR ELEMENTOS EXTRA */
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
    # Usamos columnas para centrar el contenido vertical y horizontalmente
    col_izq, col_centro, col_der = st.columns([1, 4, 1]) 
    
    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- CARGA DEL LOGO CONTROLADA ---
        # Columnas internas para centrar la imagen pequeña
        c_img_1, c_img_2, c_img_3 = st.columns([1, 2, 1])
        
        with c_img_2: 
            try:
                # AQUÍ ESTÁ EL AJUSTE: width=250 evita que sea gigante
                st.image("logo.png", width=250) 
            except:
                st.markdown("<h1 style='text-align: center; color: #FFD700;'>CÓDIGO HUMANO AI</h1>", unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align: center; color: #a0a0ff; margin-bottom: 20px;'>Tu compañero de bienestar emocional</h4>", unsafe_allow_html=True)
        
        # --- PESTAÑAS DE ACCESO ---
        tab1, tab2 = st.tabs(["🔓 Iniciar Sesión", "📝 Registrarse"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            usuario = st.text_input("Usuario", placeholder="Escribe tu nombre...", key="login_user")
            password = st.text_input("Contraseña", type="password", key="login_pass")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("INGRESAR", key="btn_login"):
                if usuario:
                    st.session_state.authenticated = True
                    st.session_state.user_name = usuario
                    st.success(f"¡Bienvenido de nuevo, {usuario}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Por favor ingresa tu usuario.")
        
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            col_reg1, col_reg2 = st.columns(2)
            with col_reg1:
                new_user = st.text_input("Usuario Nuevo", key="reg_user")
            with col_reg2:
                email = st.text_input("Email (Opcional)")
                
            new_pass = st.text_input("Crear Contraseña", type="password", key="reg_pass")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("CREAR CUENTA", key="btn_reg"):
                if new_user and new_pass:
                    st.success("¡Cuenta creada! Ve a la pestaña 'Iniciar Sesión' para entrar.")
                    st.balloons()
                else:
                    st.warning("El usuario y la contraseña son obligatorios.")

def main_app():
    # --- CLIENTE GROQ ---
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
    except:
        # Fallback para entorno local si no hay secrets
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            client = Groq(api_key=api_key)
        else:
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
