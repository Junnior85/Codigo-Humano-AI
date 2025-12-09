import streamlit as st
import os
from groq import Groq
import time
import json # Importamos JSON para guardar la memoria en un archivo

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILOS CSS ---
st.markdown("""
<style>
    .stApp {background-color: #050814; color: #E0E0E0;}
    [data-testid="stSidebar"] {background-color: #0b101c; border-right: 1px solid #1f293a;}
    div[data-testid="stImage"] img {border-radius: 15px; transition: transform 0.3s;}
    div[data-testid="stImage"] img:hover {transform: scale(1.02);}
    .stButton > button {background-color: transparent; color: #FFD700; border: 1px solid #FFD700; border-radius: 8px; width: 100%;}
    .stButton > button:hover {background-color: #FFD700; color: #000; font-weight: bold;}
    .stTextInput > div > div > input {background-color: #151b2b; color: white; border: 1px solid #2a3b55;}
    .call-box {background-color: #1a202c; border: 2px solid #FFD700; border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 20px; animation: fadeIn 0.5s;}
    @keyframes fadeIn {from {opacity: 0;} to {opacity: 1;}}
    .welcome-text {text-align: center; color: #4A5568; margin-top: 20%; font-size: 1.5rem;}
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES DE MEMORIA (PERSISTENCIA) ---
ARCHIVO_HISTORIAL = "historial_chat.json"

def cargar_historial():
    """Carga el historial desde un archivo JSON local si existe."""
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r") as f:
                return json.load(f)
        except:
            return [] # Si falla, retorna vacío
    return []

def guardar_mensaje(rol, contenido):
    """Guarda un nuevo mensaje en el archivo JSON."""
    # 1. Cargar lo que ya existe
    historial = cargar_historial()
    # 2. Agregar el nuevo mensaje
    historial.append({"role": rol, "content": contenido})
    # 3. Escribir de nuevo en el archivo
    with open(ARCHIVO_HISTORIAL, "w") as f:
        json.dump(historial, f)

# --- 4. GESTIÓN DE ESTADO ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_name' not in st.session_state: st.session_state.user_name = None

# CARGAMOS LA MEMORIA AL INICIO
if 'messages' not in st.session_state or not st.session_state.messages:
    st.session_state.messages = cargar_historial()

# Estados Toggle
if 'show_upload' not in st.session_state: st.session_state.show_upload = False
if 'show_audio' not in st.session_state: st.session_state.show_audio = False
if 'call_active' not in st.session_state: st.session_state.call_active = False

# --- 5. FUNCIÓN COLADOR ---
def generar_respuestas(chat_completion):
    texto_completo = ""
    for chunk in chat_completion:
        if chunk.choices[0].delta.content:
            texto = chunk.choices[0].delta.content
            texto_completo += texto
            yield texto
    return texto_completo

# --- 6. PANTALLAS ---
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
                    # Recargar historial al entrar
                    st.session_state.messages = cargar_historial()
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
                    st.session_state.messages = [] # Usuario nuevo empieza vacío
                    st.balloons()
                    st.success("¡Cuenta creada!")
                    time.sleep(1)
                    st.rerun()

def main_app():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
    except:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key: client = Groq(api_key=api_key)
        else: st.error("⚠️ Falta API Key"); st.stop()

    with st.sidebar:
        try: st.image("logo.png") 
        except: st.header("CH-AI")
        st.write(f"Hola, **{st.session_state.user_name}**")
        
        if st.button("➕ Nueva Conversación"):
            # Borramos memoria en sesión Y en archivo
            st.session_state.messages = []
            if os.path.exists(ARCHIVO_HISTORIAL):
                os.remove(ARCHIVO_HISTORIAL) # Borrar archivo físico
            st.session_state.call_active = False
            st.rerun()
            
        st.markdown("---")
        menu = st.radio("Menú", ["💬 Chat", "📜 Historial", "🎨 Personalizar", "👤 Perfil"], label_visibility="collapsed")
        st.markdown("---")
        if st.button("🔒 Cerrar Sesión"):
            st.session_state.authenticated = False
            # No borramos messages aquí para que persistan, solo salimos
            st.rerun()

    if menu == "💬 Chat":
        c1, c2, c3, c4, sp = st.columns([1,1,1,1, 10])
        if c1.button("🎤", help="Voz"): st.session_state.show_audio = not st.session_state.show_audio; st.session_state.show_upload = False; st.rerun()
        if c2.button("📞", help="Llamada"): st.session_state.call_active = not st.session_state.call_active; st.rerun()
        if c3.button("📹", help="Video"): st.toast("Cámara requerida"); st.session_state.call_active = True; st.rerun()
        if c4.button("📎", help="Adjuntar"): st.session_state.show_upload = not st.session_state.show_upload; st.session_state.show_audio = False; st.rerun()
        st.markdown("---")

        if st.session_state.call_active:
            st.markdown("""<div class="call-box"><h3>📞 Llamada en curso</h3><p>Escuchando...</p><div style="font-size: 40px;">🔉  ▂▃▅▆▇</div><br></div>""", unsafe_allow_html=True)
            if st.button("Colgar"): st.session_state.call_active = False; st.rerun()

        if st.session_state.show_upload:
            st.info("📎 Adjuntar archivo")
            st.file_uploader("Selecciona archivo", label_visibility="collapsed")

        if st.session_state.show_audio:
            st.info("🎤 Habla ahora")
            st.audio_input("Grabar")

        # --- CHAT VISIBLE ---
        if not st.session_state.messages and not st.session_state.call_active:
            st.markdown(f"""<div class="welcome-text"><h3>Hola, {st.session_state.user_name}.</h3><p>¿Seguimos donde lo dejamos?</p></div>""", unsafe_allow_html=True)

        for message in st.session_state.messages:
            if message["role"] != "system":
                avatar = "👤" if message["role"] == "user" else "🧠"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        prompt = st.chat_input("Escribe aquí...")
        
        if prompt:
            # 1. MOSTRAR Y GUARDAR USUARIO
            st.session_state.messages.append({"role": "user", "content": prompt})
            guardar_mensaje("user", prompt) # <--- GUARDAR EN ARCHIVO
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            # 2. RESPUESTA IA
            with st.chat_message("assistant", avatar="🧠"):
                # Enviamos TODO el historial (contexto)
                sys_prompt = {"role": "system", "content": f"Eres Código Humano AI. Usuario: {st.session_state.user_name}. Sé empático y recuerda lo que te cuenta el usuario."}
                msgs = [sys_prompt] + st.session_state.messages
                
                stream_bruto = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=msgs,
                    stream=True
                )
                
                # Usamos un contenedor vacío para ir llenando el texto
                res_box = st.empty()
                texto_completo = ""
                
                # Iteramos el generador para obtener el texto final completo
                for fragmento in generar_respuestas(stream_bruto):
                    texto_completo += fragmento
                    res_box.markdown(texto_completo + "▌") # Efecto cursor
                
                res_box.markdown(texto_completo) # Texto final limpio
            
            # 3. GUARDAR RESPUESTA IA
            st.session_state.messages.append({"role": "assistant", "content": texto_completo})
            guardar_mensaje("assistant", texto_completo) # <--- GUARDAR EN ARCHIVO

    elif menu == "📜 Historial":
        st.title("Historial Completo")
        st.info("Este historial se guarda automáticamente.")
        if st.session_state.messages:
            for msg in st.session_state.messages:
                icono = "👤" if msg['role'] == 'user' else "🧠"
                st.text(f"{icono}: {msg['content'][:80]}...") # Vista previa
        else:
            st.write("Historial vacío.")

    elif menu == "🎨 Personalizar":
        st.title("Personalización")
        st.slider("Empatía", 0, 100, 90)

    elif menu == "👤 Perfil":
        st.title("Perfil")
        st.text_input("Nombre", value=st.session_state.user_name)

# --- 7. EJECUCIÓN ---
if __name__ == "__main__":
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()
