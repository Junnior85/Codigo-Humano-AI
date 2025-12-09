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

# --- 2. ESTILOS CSS ---
# El error anterior estaba aquí. Asegúrate de copiar hasta el final de este bloque.
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
    
    /* LOGO */
    div[data-testid="stImage"] img {
        border-radius: 15px; 
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
    }

    /* MENSAJE DE BIENVENIDA */
    .welcome-text {
        text-align: center;
        color: #4A5568;
        margin-top: 20%;
        font-size: 1.5rem;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True) 
# ^^^ ESTA LÍNEA DE ARRIBA (linea 64) ES LA QUE FALTABA O ESTABA ROTA

# --- 3. GESTIÓN DE ESTADO ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- 4. FUNCIÓN COLADOR (Limpia la respuesta) ---
def generar_respuestas(chat_completion):
    for chunk in chat_completion:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# --- 5. PANTALLAS ---

def login_page():
    col_izq, col_centro, col_der = st.columns([1, 4, 1]) 
    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            try: st.image("logo.png", width=250) 
            except: st.markdown("<h1 style='text-align: center; color: #FFD700;'>CÓDIGO HUMANO AI</h1>", unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align: center; color: #a0a0ff;'>Tu compañero emocional</h4>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔓 INICIAR SESIÓN", "📝 CREAR CUENTA"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            usuario = st.text_input("Usuario", key="log_user")
            password = st.text_input("Contraseña", type="password", key="log_pass")
            if st.button("ENTRAR", key="btn_login"):
                if usuario:
                    st.session_state.authenticated = True
                    st.session_state.user_name = usuario
                    st.success(f"Bienvenido, {usuario}")
                    time.sleep(0.5)
                    st.rerun()

        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            new_user = st.text_input("Nuevo Usuario", key="reg_user")
            new_pass = st.text_input("Nueva Contraseña", type="password", key="reg_pass")
            if st.button("REGISTRARSE Y ENTRAR"):
                if new_user and new_pass:
                    st.session_state.authenticated = True
                    st.session_state.user_name = new_user
                    st.balloons()
                    st.success("¡Cuenta creada!")
                    time.sleep(1)
                    st.rerun()

def main_app():
    # Conexión Groq
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
    except:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key: client = Groq(api_key=api_key)
        else: st.error("⚠️ Falta API Key"); st.stop()

    # SIDEBAR
    with st.sidebar:
        try: st.image("logo.png") 
        except: st.header("CH-AI")
        st.write(f"Hola, **{st.session_state.user_name}**")
        
        # Botón Nueva Conversación
        if st.button("➕ Nueva Conversación"):
            st.session_state.messages = []
            st.rerun()
            
        st.markdown("---")
        menu = st.radio("Menú", ["💬 Chat", "📜 Historial", "🎨 Personalizar", "👤 Perfil"], label_visibility="collapsed")
        st.markdown("---")
        if st.button("🔒 Cerrar Sesión"):
            st.session_state.authenticated = False; st.session_state.messages = []
            st.rerun()

    # CHAT
    if menu == "💬 Chat":
        c1, c2, c3, c4, sp = st.columns([1,1,1,1, 10])
        with c1: st.button("🎤", help="Voz")
        with c2: st.button("📞", help="Llamada")
        with c3: st.button("📹", help="Video")
        with c4: st.button("📎", help="Adjuntar")
        st.markdown("---")
        
        if not st.session_state.messages:
            st.markdown(f"""<div class="welcome-text"><h3>Hola, {st.session_state.user_name}.</h3><p>¿Cómo te sientes hoy?</p></div>""", unsafe_allow_html=True)

        for message in st.session_state.messages:
            if message["role"] != "system":
                avatar = "👤" if message["role"] == "user" else "🧠"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        prompt = st.chat_input("Escribe aquí...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="🧠"):
                sys_prompt = {"role": "system", "content": f"Eres Código Humano AI. Usuario: {st.session_state.user_name}. Sé empático."}
                msgs = [sys_prompt] + st.session_state.messages
                
                stream_bruto = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=msgs,
                    stream=True
                )
                response = st.write_stream(generar_respuestas(stream_bruto))
            
            st.session_state.messages.append({"role": "assistant", "content": response})

    # HISTORIAL
    elif menu == "📜 Historial":
        st.title("Historial")
        st.info("Tus conversaciones anteriores.")
        if st.session_state.messages:
            st.markdown("### 🕒 Sesión Actual")
            for msg in st.session_state.messages:
                if msg['role'] == 'user':
                    st.caption(f"Tú: {msg['content'][:50]}...")
        else:
            st.write("No hay mensajes recientes.")

    elif menu == "🎨 Personalizar":
        st.title("Personalización")
        st.slider("Nivel de Empatía", 0, 100, 90)

    elif menu == "👤 Perfil":
        st.title("Tu Perfil")
        st.text_input("Nombre", value=st.session_state.user_name)

# --- 6. EJECUCIÓN ---
if __name__ == "__main__":
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()
