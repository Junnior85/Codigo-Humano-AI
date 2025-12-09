import streamlit as st
import os
from groq import Groq
import json
import asyncio
import edge_tts
import base64

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Código Humano AI", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS & JAVASCRIPT (MODO DICTADO NATIVO) ---
st.markdown("""
<style>
    .stApp {background-color: #050814; color: #E0E0E0;}
    [data-testid="stSidebar"] {background-color: #0b101c; border-right: 1px solid #1f293a;}
    div[data-testid="stImage"] img {border-radius: 15px;}
    .stButton > button {border: 1px solid #FFD700; color: #FFD700; background: transparent; border-radius: 8px; width: 100%;}
    .stButton > button:hover {background: #FFD700; color: #000;}
    /* Ocultar elementos molestos */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Animación de Llamada */
    .pulse {
        animation: pulse-animation 2s infinite;
        border-radius: 50%;
        height: 100px; width: 100px;
        background: rgba(255, 215, 0, 0.2);
        margin: 0 auto;
        display: flex; align-items: center; justify-content: center;
        font-size: 40px;
    }
    @keyframes pulse-animation {
        0% {box-shadow: 0 0 0 0px rgba(255, 215, 0, 0.5);}
        100% {box-shadow: 0 0 0 20px rgba(255, 215, 0, 0);}
    }
</style>

<script>
    // Script simple para intentar activar dictado nativo si el navegador lo soporta
    function startDictation() {
        if (window.hasOwnProperty('webkitSpeechRecognition')) {
            var recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = "es-MX";
            recognition.start();
            recognition.onresult = function(e) {
                document.getElementById('speech_result').value = e.results[0][0].transcript;
                recognition.stop();
            };
        }
    }
</script>
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

# --- 4. MOTORES (VOZ, AUDIO, VISIÓN) ---

# A. TEXTO A VOZ (RÁPIDO)
async def generar_audio_edge(texto, voz="es-MX-DaliaNeural"):
    if not texto: return None
    comunicador = edge_tts.Communicate(texto, voz)
    archivo = "temp_audio.mp3"
    await comunicador.save(archivo)
    return archivo

def hablar(texto):
    try:
        asyncio.run(generar_audio_edge(texto))
        st.audio("temp_audio.mp3", format="audio/mp3", autoplay=True)
    except: pass

# B. VOZ A TEXTO (OÍDO)
def transcribir_audio(cliente, audio_file):
    try:
        return cliente.audio.transcriptions.create(
            file=(audio_file.name, audio_file.read()),
            model="whisper-large-v3",
            response_format="json",
            language="es"
        ).text
    except: return None

# C. VISIÓN (VER IMÁGENES)
def analizar_imagen(cliente, imagen_bytes, prompt_usuario):
    # Convertir imagen a base64
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    try:
        response = cliente.chat.completions.create(
            model="llama-3.2-11b-vision-preview", # MODELO QUE VE
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_usuario},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error de visión: {str(e)}"

# --- 5. LOGIN ---
def login_page():
    c1, c2, c3 = st.columns([1,4,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo.png", width=250) 
        except: st.title("CÓDIGO HUMANO AI")
        st.info("Inicia sesión para continuar")
        u = st.text_input("Usuario")
        if st.button("ENTRAR"):
            if u:
                st.session_state.user_name = u
                st.session_state.authenticated = True
                st.session_state.messages = cargar_historial()
                st.rerun()

# --- 6. APP PRINCIPAL ---
def main_app():
    # API KEY
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
        modo = st.radio("Modo", ["💬 Chat Texto", "📞 Llamada Voz", "📹 Videollamada", "📜 Historial"])
        st.markdown("---")
        if st.button("🔒 Salir"):
            st.session_state.authenticated = False
            st.rerun()

    # --- LÓGICA POR MODOS ---

    # 1. CHAT DE TEXTO + DICTADO
    if modo == "💬 Chat Texto":
        # Mostrar historial
        for msg in st.session_state.messages:
            avatar = "👤" if msg['role'] == 'user' else "🧠"
            with st.chat_message(msg['role'], avatar=avatar):
                st.markdown(msg['content'])

        # ZONA DE ENTRADA
        c_mic, c_input = st.columns([1, 8])
        
        # Botón Dictado (Simulado con Audio Input por estabilidad)
        # Nota: El dictado real tiempo real puro requiere WebSocket server, 
        # esto es lo más rápido posible en Streamlit Cloud.
        with c_mic:
            audio_dictado = st.audio_input("Dictar", label_visibility="collapsed")
        
        prompt = st.chat_input("Escribe aquí...")

        # Lógica: Si hay audio, lo transcribimos y lo tratamos como texto
        texto_final = None
        
        if audio_dictado:
            transcripcion = transcribir_audio(client, audio_dictado)
            if transcripcion:
                # Mostrar lo que entendió antes de enviar (opcional, aquí lo enviamos directo para rapidez)
                texto_final = transcripcion
        
        if prompt:
            texto_final = prompt

        # PROCESAR MENSAJE
        if texto_final:
            # Guardar User
            st.session_state.messages.append({"role": "user", "content": texto_final})
            guardar_mensaje("user", texto_final)
            
            # Generar Respuesta
            with st.chat_message("assistant", avatar="🧠"):
                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Eres Código Humano AI. Empático y breve."}] + st.session_state.messages,
                    stream=True
                )
                response = st.write_stream(stream)
            
            # Guardar Assistant
            st.session_state.messages.append({"role": "assistant", "content": response})
            guardar_mensaje("assistant", response)
            st.rerun()

    # 2. LLAMADA DE VOZ (FULL DUPLEX SIMULADO)
    elif modo == "📞 Llamada Voz":
        st.title("📞 Llamada Activa")
        st.markdown("""<div class="pulse">🔊</div><p style='text-align:center'>Habla claro, te escucho...</p>""", unsafe_allow_html=True)
        
        # Input de audio permanente para la llamada
        audio_llamada = st.audio_input("Hablar")
        
        if audio_llamada:
            # 1. Transcribir
            texto_usuario = transcribir_audio(client, audio_llamada)
            if texto_usuario:
                st.caption(f"Tú dijiste: {texto_usuario}") # Feedback visual sutil
                
                # Guardar en historial (invisible en esta pantalla pero queda grabado)
                st.session_state.messages.append({"role": "user", "content": texto_usuario})
                guardar_mensaje("user", texto_usuario)

                # 2. Pensar respuesta
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Estás en una llamada telefónica. Sé muy breve, cálido y conversacional."}] + st.session_state.messages
                ).choices[0].message.content

                # Guardar respuesta
                st.session_state.messages.append({"role": "assistant", "content": resp})
                guardar_mensaje("assistant", resp)

                # 3. HABLAR (Audio automático)
                st.caption(f"IA: {resp}")
                hablar(resp)

    # 3. VIDEOLLAMADA (CON VISIÓN REAL)
    elif modo == "📹 Videollamada":
        st.title("📹 Videollamada (Visión)")
        st.info("La IA puede VER lo que le muestras. Toma una foto para hablar.")
        
        c_cam, c_chat = st.columns([1, 1])
        
        with c_cam:
            # Usamos camera_input. Es lo único que permite enviar la imagen a la IA en la nube.
            imagen = st.camera_input("Cámara")
        
        with c_chat:
            if imagen:
                # Si hay imagen, preguntamos qué ve o seguimos la charla
                prompt_video = st.text_input("¿Qué quieres preguntar sobre esto?", value="¿Qué ves aquí y cómo me puedes ayudar?")
                
                if st.button("Analizar y Responder"):
                    with st.spinner("Viendo..."):
                        # Usamos el MODELO DE VISIÓN (Llama 3.2 11B Vision)
                        descripcion = analizar_imagen(client, imagen.getvalue(), prompt_video)
                        
                        # Guardar contexto visual en historial
                        msg_visual = f"[Usuario mostró imagen]: {prompt_video}"
                        st.session_state.messages.append({"role": "user", "content": msg_visual})
                        guardar_mensaje("user", msg_visual)
                        
                        st.session_state.messages.append({"role": "assistant", "content": descripcion})
                        guardar_mensaje("assistant", descripcion)
                        
                        st.write(descripcion)
                        hablar(descripcion)

    # 4. HISTORIAL
    elif modo == "📜 Historial":
        st.title("Historial Completo")
        for m in st.session_state.messages:
            st.text(f"{m['role'].upper()}: {m['content']}")

# --- 7. EJECUCIÓN ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_name' not in st.session_state: st.session_state.user_name = None

if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
