import streamlit as st
import os
from groq import Groq
import time
import json
from gtts import gTTS # Librería para que la IA hable
import io

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
    historial.append({"role": rol, "content": contenido})
    with open(ARCHIVO_HISTORIAL, "w") as f: json.dump(historial, f)

# --- 4. FUNCIONES DE AUDIO (NUEVO MOTOR) ---

def transcribir_audio(cliente_groq, archivo_audio):
    """Usa el modelo Whisper de Groq para convertir voz a texto"""
    try:
        transcription = cliente_groq.audio.transcriptions.create(
            file=(archivo_audio.name, archivo_audio.read()),
            model="whisper-large-v3", # Modelo de oído
            response_format="json",
            language="es",
            temperature=0.0
        )
        return transcription.text
    except Exception as e:
        return f"Error al escuchar: {e}"

def texto_a_voz(texto):
    """Convierte la respuesta de texto a audio MP3 usando gTTS"""
    try:
        tts = gTTS(text=texto, lang='es')
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes
    except:
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

# Estados de Botones
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
            p = st.text_input("Contraseña", type="password", key="log_p")
            if st.button("ENTRAR", key="b_in"):
                if u:
                    st.session_state.authenticated = True
                    st.session_state.user_name = u
                    st.session_state.messages = cargar_historial()
                    st.rerun()
        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            nu = st.text_input("Usuario", key="reg_u")
            np = st.text_input("Pass", type="password", key="reg_p")
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
            st.session_state.modo_llamada = False
            st.rerun()
        st.markdown("---")
        menu = st.radio("Menú", ["💬 Chat", "📜 Historial", "🎨 Personalizar", "👤 Perfil"], label_visibility="collapsed")
        st.markdown("---")
        if st.button("🔒 Salir"):
            st.session_state.authenticated = False
            st.rerun()

    if menu == "💬 Chat":
        # --- BARRA DE CONTROL ---
        c1, c2, c3, c4, sp = st.columns([1,1,1,1, 10])
        
        # 1. BOTÓN MICRÓFONO (Activa/Desactiva grabadora)
        if c1.button("🎤", help="Dictar mensaje"):
            st.session_state.modo_voz = not st.session_state.modo_voz
            st.session_state.modo_adjuntar = False
            st.rerun()

        # 2. BOTÓN LLAMADA (Activa modo llamada)
        if c2.button("📞", help="Modo Llamada"):
            st.session_state.modo_llamada = not st.session_state.modo_llamada
            st.session_state.modo_voz = False
            st.rerun()

        # 3. BOTÓN VIDEO (Aviso de limitación)
        if c3.button("📹", help="Videollamada"):
            st.toast("⚠️ Videollamada en desarrollo. Usando modo audio.", icon="📹")

        # 4. BOTÓN ADJUNTAR
        if c4.button("📎", help="Adjuntar"):
            st.session_state.modo_adjuntar = not st.session_state.modo_adjuntar
            st.session_state.modo_voz = False
            st.rerun()
            
        st.markdown("---")

        # --- ÁREA DE INPUT POR VOZ (Whisper) ---
        prompt_final = None # Variable para guardar lo que el usuario envía

        if st.session_state.modo_voz:
            st.info("🎤 Grabando... (Haz clic en 'Stop' para enviar)")
            audio_grabado = st.audio_input("Tu voz") # Componente nuevo de Streamlit
            if audio_grabado:
                # Transcribir con Groq
                texto_transcrito = transcribir_audio(client, audio_grabado)
                if texto_transcrito:
                    prompt_final = texto_transcrito # ¡Esto se enviará como mensaje!
                    st.session_state.modo_voz = False # Cerrar micro tras enviar

        if st.session_state.modo_adjuntar:
            st.file_uploader("Subir archivo (PDF, IMG, TXT)")

        if st.session_state.modo_llamada:
             st.markdown("""<div class="call-box"><h3>📞 Llamada Activa</h3><p>Modo de solo audio activado.</p></div>""", unsafe_allow_html=True)


        # --- MOSTRAR CHAT ---
        if not st.session_state.messages:
            st.markdown(f"""<div class="welcome-text"><h3>Hola, {st.session_state.user_name}.</h3></div>""", unsafe_allow_html=True)

        for message in st.session_state.messages:
            avatar = "👤" if message["role"] == "user" else "🧠"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
                # Si el mensaje es del asistente, intentamos mostrar un reproductor de audio pequeño si se desea
                # (Opcional, para no saturar)

        # --- INPUT DE TEXTO (O VOZ YA PROCESADA) ---
        prompt_texto = st.chat_input("Escribe aquí...")
        
        # Prioridad: Si hay voz transcrita, usamos eso. Si no, texto escrito.
        if prompt_texto:
            prompt_final = prompt_texto

        # --- PROCESAMIENTO CENTRAL ---
        if prompt_final:
            # 1. Guardar Usuario
            st.session_state.messages.append({"role": "user", "content": prompt_final})
            guardar_mensaje("user", prompt_final)
            st.rerun() # Recargar para mostrar mensaje usuario

    # --- RESPUESTA IA (Al recargar) ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar="🧠"):
            sys = {"role": "system", "content": f"Eres Código Humano AI. Usuario: {st.session_state.user_name}. Empático. Breve."}
            msgs = [sys] + st.session_state.messages
            
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=msgs,
                stream=True
            )
            
            # Generar texto visual
            texto_respuesta = st.write_stream(generar_respuestas_texto(stream))
            
            # GENERAR AUDIO (La IA habla)
            audio_bytes = texto_a_voz(texto_respuesta)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
        
        # Guardar respuesta
        st.session_state.messages.append({"role": "assistant", "content": texto_respuesta})
        guardar_mensaje("assistant", texto_respuesta)

    elif menu == "📜 Historial":
        st.title("Historial")
        if st.session_state.messages:
            for m in st.session_state.messages:
                st.text(f"{m['role']}: {m['content'][:50]}...")

    elif menu == "🎨 Personalizar":
        st.title("Ajustes")
        st.slider("Empatía", 0, 100, 90)

    elif menu == "👤 Perfil":
        st.title("Perfil")
        st.text_input("Nombre", value=st.session_state.user_name)

if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
