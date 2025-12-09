import streamlit as st
import os
from groq import Groq
import time
import json
import asyncio
import edge_tts # Para voz natural
import base64
from datetime import datetime # Para historial

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (Diseño y Estabilidad) ---
st.markdown("""
<style>
    .stApp {background-color: #050814; color: #E0E0E0;}
    [data-testid="stSidebar"] {background-color: #0b101c; border-right: 1px solid #1f293a;}
    div[data-testid="stImage"] img {border-radius: 15px; transition: transform 0.3s;}
    .stButton > button {border: 1px solid #FFD700; color: #FFD700; border-radius: 8px; width: 100%;}
    .stButton > button:hover {background: #FFD700; color: #000; font-weight: bold;}
    .stTextInput > div > div > input {background-color: #151b2b; color: white; border: 1px solid #2a3b55;}
    .welcome-text {text-align: center; color: #4A5568; margin-top: 20%; font-size: 1.5rem;}
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. MEMORIA Y PERSISTENCIA ---
ARCHIVO_HISTORIAL = "historial_chat.json"

def cargar_historial():
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r") as f: return json.load(f)
        except: return []
    return []

def guardar_mensaje(rol, contenido):
    historial = cargar_historial()
    historial.append({"role": rol, "content": contenido, "time": datetime.now().strftime("%H:%M")})
    with open(ARCHIVO_HISTORIAL, "w") as f: json.dump(historial, f)

# --- 4. MOTOR DE VOZ (EDGE TTS - ROBUSTO) ---
async def generar_audio_edge(texto, voz="es-MX-DaliaNeural"):
    """Genera audio rápido y natural usando Edge TTS"""
    comunicador = edge_tts.Communicate(texto, voz)
    archivo_salida = "temp_audio.mp3"
    await comunicador.save(archivo_salida)
    return archivo_salida

def hablar(texto):
    """Llama a la función asíncrona para reproducir audio."""
    try:
        audio_file = asyncio.run(generar_audio_edge(texto))
        if os.path.exists(audio_file):
            st.audio(audio_file, format="audio/mp3", autoplay=True)
            # Limpiar archivo temporal
            os.remove(audio_file)
    except Exception as e:
        # st.toast(f"Error de reproducción de audio: {e}") # Desactivado para UX
        pass

# --- 5. LÓGICA GENERAL ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_name' not in st.session_state: st.session_state.user_name = None
if 'messages' not in st.session_state or not st.session_state.messages:
    st.session_state.messages = cargar_historial()
if 'modo_adjuntar' not in st.session_state: st.session_state.modo_adjuntar = False

# --- 6. PANTALLAS ---

def login_page():
    c1, c2, c3 = st.columns([1,4,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo.png", width=250) 
        except: st.title("CÓDIGO HUMANO AI")
        u = st.text_input("Usuario")
        if st.button("ENTRAR"):
            if u:
                st.session_state.user_name = u
                st.session_state.authenticated = True
                st.session_state.messages = cargar_historial()
                st.rerun()

def main_app():
    # Conexión Groq (solo para texto)
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # SIDEBAR
    with st.sidebar:
        try: st.image("logo.png")
        except: pass
        st.write(f"Usuario: **{st.session_state.user_name}**")
        
        if st.button("➕ Nueva Conversación"):
            st.session_state.messages = []
            if os.path.exists(ARCHIVO_HISTORIAL): os.remove(ARCHIVO_HISTORIAL)
            st.rerun()
            
        st.markdown("---")
        # El modo llamada y video se fusionan en "Visión"
        modo = st.radio("Modo", ["💬 Chat Texto", "🖼️ Modo Visión", "📜 Historial", "👤 Perfil"])
        st.markdown("---")
        if st.button("🔒 Salir"):
            st.session_state.authenticated = False
            st.rerun()

    # --- PANTALLAS ---
    if modo == "💬 Chat Texto":
        # Botones de Acción (Simplificados para estabilidad)
        c1, c2, sp = st.columns([1, 1, 10])
        
        if c1.button("📎", help="Adjuntar archivo"):
            st.session_state.modo_adjuntar = not st.session_state.modo_adjuntar
            st.rerun()

        if c2.button("🔊", help="Activar respuesta de voz"):
            st.toast("La IA hablará. Funciona mejor con auriculares.", icon="🔊")
        
        st.markdown("---")
        
        # Dicatado: Instrucción para dictado nativo
        st.info("Para dictar, usa el micrófono nativo de tu sistema (Ej: Win+H o doble clic en la barra en móvil).")
        
        if st.session_state.modo_adjuntar:
            st.file_uploader("Selecciona archivo (PDF, IMG, TXT)")

        # Historial (Muestra mensajes)
        if not st.session_state.messages:
            st.markdown(f"""<div class="welcome-text"><h3>Hola, {st.session_state.user_name}.</h3></div>""", unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            avatar = "👤" if msg['role'] == 'user' else "🧠"
            with st.chat_message(msg['role'], avatar=avatar):
                st.markdown(msg['content'])

        # Input
        prompt = st.chat_input("Escribe tu mensaje o usa el dictado nativo...")
        
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            guardar_mensaje("user", prompt)
            st.rerun()

    # --- RESPUESTA IA (Se ejecuta al recargar) ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar="🧠"):
            sys = {"role": "system", "content": f"Eres Código Humano AI. Usuario: {st.session_state.user_name}. Empático, recuerda el historial."}
            msgs = [sys] + st.session_state.messages
            
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=msgs,
                stream=True
            )
            
            # Generar texto visual
            response_text = st.write_stream(stream)
            
            # Si se presionó el botón de Audio, hablamos
            if "🔊" in st.session_state.get('toast_queue', {}): # Revisa si el toast de audio está activo
                hablar(response_text)
            
            guardar_mensaje("assistant", response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

    # --- MODO VISIÓN/VIDEO ---
    elif modo == "🖼️ Modo Visión":
        st.title("🖼️ Análisis Visual (Video/Foto)")
        st.info("La IA puede analizar una imagen. Simula tu videollamada enviando una foto.")
        
        imagen = st.camera_input("Capturar Imagen o Subir Archivo")
        
        if imagen:
            prompt_vision = st.text_input("Describe lo que quieres que analice la IA:", value="¿Qué ves y cómo se relaciona con mis sentimientos?")
            
            if st.button("Analizar Imagen"):
                with st.spinner("Analizando Visión..."):
                    descripcion = analizar_imagen(client, imagen.getvalue(), prompt_vision)
                    
                    st.markdown("---")
                    st.subheader("Respuesta de la IA:")
                    st.write(descripcion)
                    hablar(descripcion) # La IA habla la respuesta

                    # Guardar historial
                    msg_log = f"[Visión Analizada]: {prompt_vision}"
                    guardar_mensaje("user", msg_log)
                    guardar_mensaje("assistant", descripcion)


    elif modo == "📜 Historial":
        st.title("📜 Historial Completo")
        for m in st.session_state.messages:
            icono = "👤" if m['role'] == 'user' else "🧠"
            st.text(f"[{m.get('time', 'N/A')}] {icono}: {m['content']}")

    elif modo == "👤 Perfil":
        st.title("👤 Tu Perfil")
        st.text_input("Nombre", value=st.session_state.user_name)

# --- 7. EJECUCIÓN ---
if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
