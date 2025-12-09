import streamlit as st
import os
from groq import Groq
import json
from datetime import datetime # Para timestamp
import base64
import asyncio # Mantenemos asyncio por si quieres reactivar edge-tts/TTS

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS y ESTILO ---
st.markdown("""
<style>
    .stApp {background-color: #050814; color: #E0E0E0;}
    [data-testid="stSidebar"] {background-color: #0b101c; border-right: 1px solid #1f293a;}
    div[data-testid="stImage"] img {border-radius: 15px;}
    .stButton > button {border: 1px solid #FFD700; color: #FFD700; border-radius: 8px; width: 100%;}
    .stButton > button:hover {background: #FFD700; color: #000; font-weight: bold;}
    .stTextInput > div > div > input {background-color: #151b2b; color: white; border: 1px solid #2a3b55;}
    .welcome-text {text-align: center; color: #4A5568; margin-top: 20%; font-size: 1.5rem;}
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. MEMORIA Y PERSISTENCIA (FIXED JSON SERIALIZATION) ---
ARCHIVO_HISTORIAL = "historial_chat.json"

def cargar_historial():
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r") as f: return json.load(f)
        except: return []
    return []

def guardar_mensaje(rol, contenido):
    """Guarda el contenido (PURO STRING) con un timestamp."""
    historial = cargar_historial()
    # Aseguramos que el contenido sea STRING antes de guardar (FIX de TypeError)
    historial.append({"role": rol, "content": str(contenido), "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
    with open(ARCHIVO_HISTORIAL, "w") as f: json.dump(historial, f)

# --- 4. MOTORES DE AUDIO/VISIÓN (SIMPLIFICADOS) ---

# Implementación de Visión
def analizar_imagen(cliente, imagen_bytes, prompt_usuario):
    # Usaremos el modelo Visión de Llama 3.2 para analizar la imagen
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    try:
        response = cliente.chat.completions.create(
            model="llama-3.2-11b-vision-preview", # MODELO QUE VE
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt_usuario},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error de visión: {str(e)}"

# --- 5. GESTIÓN DE ESTADO ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_name' not in st.session_state: st.session_state.user_name = None
if 'messages' not in st.session_state or not st.session_state.messages:
    st.session_state.messages = cargar_historial()

# --- 6. PANTALLAS Y FLUJO ---

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
        modo = st.radio("Modo", ["💬 Chat Texto", "🖼️ Modo Visión", "📜 Historial", "👤 Perfil"])
        st.markdown("---")
        if st.button("🔒 Salir"):
            st.session_state.authenticated = False
            st.rerun()

    # --- CHAT DE TEXTO (MODO ESTABLE) ---
    if modo == "💬 Chat Texto":
        # Botones de Acción (Simplificados)
        c1, c2, sp = st.columns([1, 1, 10])
        if c1.button("📎", help="Adjuntar archivo"): st.session_state.modo_adjuntar = not st.session_state.modo_adjuntar
        if c2.button("🔊", help="Activar respuesta de voz"): st.toast("La IA hablará.", icon="🔊")
        st.markdown("---")
        
        st.info("Para dictar, usa el micrófono nativo de tu sistema (Ej: Win+H).")
        
        if st.session_state.get('modo_adjuntar', False):
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
            # 1. Guardar y mostrar mensaje del usuario
            st.session_state.messages.append({"role": "user", "content": prompt})
            guardar_mensaje("user", prompt)
            
            # 2. Generar Respuesta (Visual)
            with st.chat_message("assistant", avatar="🧠"):
                sys = {"role": "system", "content": f"Eres Código Humano AI. Usuario: {st.session_state.user_name}. Empático, recuerda el historial."}
                msgs = [sys] + st.session_state.messages
                
                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=msgs,
                    stream=True
                )
                
                # --- CAPTURA DE TEXTO CONFIABLE Y VISUAL ---
                full_response_text = ""
                response_container = st.empty()
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response_text += content
                        response_container.markdown(full_response_text + "▌") # Efecto de escritura
                
                response_container.markdown(full_response_text) # Texto final limpio

            # 3. Guardar y Hablar (Si se activó el audio)
            guardar_mensaje("assistant", full_response_text)
            st.session_state.messages.append({"role": "assistant", "content": full_response_text})
            
            # Solo para debug:
            # if "🔊" in st.session_state.get('toast_queue', {}): hablar(full_response_text) 
            
            st.rerun() # Refrescar

    # --- MODO VISIÓN/VIDEO ---
    elif modo == "🖼️ Modo Visión":
        st.title("🖼️ Análisis Visual (Simulador de Videollamada)")
        st.info("La IA puede analizar una imagen. Toma una foto para enviarla.")
        
        imagen = st.camera_input("Capturar Imagen o Subir Archivo")
        
        if imagen:
            prompt_video = st.text_input("¿Qué quieres preguntar sobre lo que ves?", value="Descríbeme la escena y dame un mensaje positivo.")
            
            if st.button("Analizar Imagen"):
                with st.spinner("Viendo y analizando..."):
                    # Usamos el MODELO DE VISIÓN (Llama 3.2 11B Vision)
                    bytes_data = imagen.getvalue()
                    descripcion = analizar_imagen(client, bytes_data, prompt_video)
                    
                    st.markdown("---")
                    st.subheader("Respuesta de la IA:")
                    st.write(descripcion)

                    # Guardar historial
                    msg_log = f"[Visión Analizada]: {prompt_video}"
                    guardar_mensaje("user", msg_log)
                    guardar_mensaje("assistant", descripcion)
                    st.session_state.messages.append({"role": "assistant", "content": descripcion})

    # --- HISTORIAL ---
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
