import streamlit as st
import os
from groq import Groq
import time
import json
import asyncio
import edge_tts # NUEVA LIBRERÍA DE VOZ (Más rápida y natural)

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS ---
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

# --- 3. MEMORIA ---
ARCHIVO_HISTORIAL = "historial_chat.json"

def cargar_historial():
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r") as f: return json.load(f)
        except: return []
    return []

def guardar_mensaje(rol, contenido):
    historial = cargar_historial()
    historial.append({"role": rol, "content": contenido})
    with open(ARCHIVO_HISTORIAL, "w") as f: json.dump(historial, f)

# --- 4. NUEVO MOTOR DE VOZ (EDGE TTS) ---
# Diccionario de voces disponibles
VOCES = {
    "Mujer (México) - Dalia": "es-MX-DaliaNeural",
    "Hombre (México) - Jorge": "es-MX-JorgeNeural",
    "Mujer (España) - Elvira": "es-ES-ElviraNeural",
    "Hombre (España) - Alvaro": "es-ES-AlvaroNeural",
    "Mujer (Argentina) - Elena": "es-AR-ElenaNeural",
    "Hombre (Argentina) - Tomas": "es-AR-TomasNeural"
}

async def generar_audio_edge(texto, voz_elegida):
    """Genera audio rápido y natural usando Edge TTS"""
    comunicador = edge_tts.Communicate(texto, voz_elegida)
    # Guardamos en un archivo temporal
    archivo_salida = "respuesta_audio.mp3"
    await comunicador.save(archivo_salida)
    return archivo_salida

def reproducir_audio_ia(texto):
    """Función auxiliar para ejecutar el async en Streamlit"""
    # Obtenemos la voz configurada por el usuario
    voz_usuario = st.session_state.get('voz_seleccionada', "es-MX-DaliaNeural")
    
    # Ejecutamos la generación de audio
    try:
        asyncio.run(generar_audio_edge(texto, voz_usuario))
        if os.path.exists("respuesta_audio.mp3"):
            st.audio("respuesta_audio.mp3", format="audio/mp3", autoplay=True)
    except Exception as e:
        st.error(f"Error de audio: {e}")

# Transcripción (Oído)
def transcribir_audio(cliente_groq, archivo_audio):
    try:
        transcription = cliente_groq.audio.transcriptions.create(
            file=(archivo_audio.name, archivo_audio.read()),
            model="whisper-large-v3",
            response_format="json",
            language="es",
            temperature=0.0
        )
        return transcription.text
    except Exception as e:
        return None

def generar_respuestas_texto(chat_completion):
    texto_completo = ""
    for chunk in chat_completion:
        if chunk.choices[0].delta.content:
            texto = chunk.choices[0].delta.content
            texto_completo += texto
            yield texto
    return texto_completo

# --- 5. ESTADOS ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_name' not in st.session_state: st.session_state.user_name = None
if 'messages' not in st.session_state or not st.session_state.messages:
    st.session_state.messages = cargar_historial()

# Configuración por defecto de voz
if 'voz_seleccionada' not in st.session_state: st.session_state.voz_seleccionada = "es-MX-DaliaNeural"

# Toggle de botones
if 'modo_voz' not in st.session_state: st.session_state.modo_voz = False
if 'modo_adjuntar' not in st.session_state: st.session_state.modo_adjuntar = False
if 'modo_llamada' not in st.session_state: st.session_state.modo_llamada = False

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
            u = st.text_input("Usuario", key="log_u")
            if st.button("ENTRAR", key="b_in"):
                if u:
                    st.session_state.authenticated = True
                    st.session_state.user_name = u
                    st.session_state.messages = cargar_historial()
                    st.rerun()
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            nu = st.text_input("Usuario", key="reg_u")
            if st.button("REGISTRARSE"):
                if nu:
                    st.session_state.authenticated = True
                    st.session_state.user_name = nu
                    st.session_state.messages = []
                    st.rerun()

def main_app():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
    except:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key: client = Groq(api_key=api_key)
        else: st.error("Falta API Key"); st.stop()

    with st.sidebar:
        try: st.image("logo.png") 
        except: st.header("CH-AI")
        st.write(f"Hola, **{st.session_state.user_name}**")
        if st.button("➕ Nueva Conversación"):
            st.session_state.messages = []
            if os.path.exists(ARCHIVO_HISTORIAL): os.remove(ARCHIVO_HISTORIAL)
            st.rerun()
        st.markdown("---")
        menu = st.radio("Menú", ["💬 Chat", "📜 Historial", "🎨 Personalizar", "👤 Perfil"], label_visibility="collapsed")
        st.markdown("---")
        if st.button("🔒 Salir"):
            st.session_state.authenticated = False
            st.rerun()

    if menu == "💬 Chat":
        c1, c2, c3, c4, sp = st.columns([1,1,1,1, 10])
        
        # BOTONES DE ACCIÓN
        if c1.button("🎤", help="Dictar"):
            st.session_state.modo_voz = not st.session_state.modo_voz
            st.rerun()
        if c2.button("📞", help="Llamada"):
            st.session_state.modo_llamada = not st.session_state.modo_llamada
            st.rerun()
        if c3.button("📹", help="Video"):
            st.toast("Videollamada en Beta.")
        if c4.button("📎", help="Adjuntar"):
            st.session_state.modo_adjuntar = not st.session_state.modo_adjuntar
            st.rerun()
            
        st.markdown("---")

        prompt_final = None

        # --- MODO DICTADO (ARREGLADO) ---
        if st.session_state.modo_voz:
            st.info("🎤 Grabando... Presiona 'Stop' para procesar.")
            # Nota: Streamlit no puede hacer streaming letra por letra.
            # Primero graba, luego transcribe.
            audio_grabado = st.audio_input("Voz") 
            if audio_grabado:
                texto = transcribir_audio(client, audio_grabado)
                if texto:
                    st.success(f"Escuchado: {texto}")
                    if st.button("📩 Enviar transcripción"):
                        prompt_final = texto
                        st.session_state.modo_voz = False # Cerrar micro

        # --- MODO LLAMADA (FLUJO CONTINUO) ---
        if st.session_state.modo_llamada:
            st.markdown("""<div class="call-box"><h3>📞 Llamada Activa</h3><p>Habla y espera la respuesta...</p></div>""", unsafe_allow_html=True)
            # En modo llamada usamos el audio input directo para conversar
            audio_llamada = st.audio_input("Hablar en llamada")
            if audio_llamada:
                texto_llamada = transcribir_audio(client, audio_llamada)
                if texto_llamada:
                    prompt_final = texto_llamada # Se envía directo

        # --- MOSTRAR CHAT ---
        if not st.session_state.messages:
            st.markdown(f"""<div class="welcome-text"><h3>Hola, {st.session_state.user_name}.</h3></div>""", unsafe_allow_html=True)

        for message in st.session_state.messages:
            avatar = "👤" if message["role"] == "user" else "🧠"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

        # Input Texto
        prompt_texto = st.chat_input("Escribe aquí...")
        if prompt_texto: prompt_final = prompt_texto

        # --- PROCESAMIENTO CENTRAL ---
        if prompt_final:
            # 1. Guardar User
            st.session_state.messages.append({"role": "user", "content": prompt_final})
            guardar_mensaje("user", prompt_final)
            st.rerun() # Refrescar para mostrar mensaje usuario

    # --- RESPUESTA IA ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar="🧠"):
            sys = {"role": "system", "content": f"Eres Código Humano AI. Usuario: {st.session_state.user_name}. Breve y cálido."}
            msgs = [sys] + st.session_state.messages
            
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=msgs,
                stream=True
            )
            
            texto_respuesta = st.write_stream(generar_respuestas_texto(stream))
            
            # --- AUDIO AUTOMÁTICO (RÁPIDO) ---
            # Solo habla si estamos en Modo Llamada o si el usuario quiere
            if st.session_state.modo_llamada or st.session_state.modo_voz:
                reproducir_audio_ia(texto_respuesta)
        
        st.session_state.messages.append({"role": "assistant", "content": texto_respuesta})
        guardar_mensaje("assistant", texto_respuesta)

    elif menu == "🎨 Personalizar":
        st.title("Ajustes de Voz y Personalidad")
        st.slider("Nivel de Empatía", 0, 100, 90)
        
        # --- SELECTOR DE VOZ REAL ---
        st.subheader("🔊 Selección de Voz")
        nombre_voz = st.selectbox("Elige la voz de tu IA:", list(VOCES.keys()))
        
        # Guardar selección
        st.session_state.voz_seleccionada = VOCES[nombre_voz]
        st.success(f"Voz configurada: {nombre_voz}")
        
        if st.button("🔊 Probar Voz"):
            asyncio.run(generar_audio_edge("Hola, soy Código Humano, estoy aquí para escucharte.", st.session_state.voz_seleccionada))
            st.audio("respuesta_audio.mp3", autoplay=True)

    elif menu == "📜 Historial":
        st.title("Historial")
        if st.session_state.messages:
            for m in st.session_state.messages:
                st.text(f"{m['role']}: {m['content'][:80]}...")

    elif menu == "👤 Perfil":
        st.title("Perfil")
        st.text_input("Nombre", value=st.session_state.user_name)

if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
