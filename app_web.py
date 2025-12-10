import streamlit as st
import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import base64
from supabase import create_client, Client
import time
from PIL import Image
import io

# --- 0. FUNCIÓN DE UTILIDAD ---
def obtener_base64(ruta_local):
    """Convierte un archivo local a base64 para incrustarlo en HTML/CSS."""
    try:
        if not os.path.exists(ruta_local):
            ruta_local = os.path.join(os.path.dirname(__file__), ruta_local)
        with open(ruta_local, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return "" 

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Código Humano AI - Cómplice",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS y ESTILO ---
LOGO_BASE64 = obtener_base64("logo.png")

st.markdown(f"""
<style>
    /* Estilos Generales */
    .stApp {{background-color: #050814; color: #E0E0E0;}}
    [data-testid="stSidebar"] {{background-color: #0b101c; border-right: 1px solid #1f293a;}}
    div[data-testid="stImage"] img {{border-radius: 15px;}}
    
    /* Botones */
    .stButton > button {{border: 1px solid #FFD700; color: #FFD700; border-radius: 8px; width: 100%;}}
    .stButton > button:hover {{background: #FFD700; color: #000; font-weight: bold;}}
    
    /* Inputs */
    .stTextInput > div > div > input {{background-color: #151b2b; color: white; border: 1px solid #2a3b55;}}
    
    /* UX/Estética */
    .welcome-text {{text-align: center; color: #4A5568; margin-top: 15%; font-size: 1.5rem;}}
    .logo-img-login {{
        text-align: center; 
        margin-bottom: 30px; 
        padding-bottom: 20px; 
        border-bottom: 1px solid #1f293a;
    }}
    .logo-img-login img {{width: 250px;}}
    
    /* Footer Fijo */
    .footer-disclaimer {{
        position: fixed; bottom: 0; left: 0; width: 100%; padding: 10px 0; 
        text-align: center; background-color: #050814; border-top: 1px solid #1f293a; z-index: 1000;
    }}
    .disclaimer-text {{
        color: #718096; font-size: 0.8rem; margin: 0 auto; width: fit-content;
    }}
    #MainMenu, footer, header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES DE BASE DE DATOS (SUPABASE) ---

def get_supabase_client():
    """Inicializa Supabase buscando en Entorno o Secrets."""
    try:
        # Intenta leer de variables de entorno primero
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        # Si no, busca en secrets (para desarrollo local/streamlit cloud)
        if not url and st.secrets.get("supabase"):
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            
        if not url: return None
        return create_client(url, key)
    except Exception:
        return None

def cargar_perfil_cognitivo(client: Client, user_id: str):
    try:
        response = client.table('user_profiles').select('profile_text').eq('user_id', user_id).single().execute()
        return response.data['profile_text']
    except Exception:
        return "Perfil en construcción."

def guardar_perfil_cognitivo(client: Client, user_id: str, perfil_text: str):
    try:
        result = client.table('user_profiles').update({'profile_text': perfil_text}).eq('user_id', user_id).execute()
        if not result.data:
            client.table('user_profiles').insert({'user_id': user_id, 'profile_text': perfil_text}).execute()
    except Exception: pass

def cargar_historial_db(client: Client, user_id: str):
    try:
        response = client.table('chat_history').select('role, content').eq('user_id', user_id).order('created_at', ascending=True).execute()
        return [{"role": item['role'], "content": item['content']} for item in response.data]
    except Exception: return []

def guardar_mensaje_db(client: Client, rol: str, contenido: str, user_id: str):
    try:
        client.table('chat_history').insert({"role": rol, "content": str(contenido), "user_id": user_id}).execute()
    except Exception: pass

# --- 4. MOTOR INTELIGENTE (GOOGLE GEMINI - ESTABILIDAD) ---

def configurar_gemini():
    """Configura la API de Google Gemini."""
    try:
        # Busca la clave en variables de entorno o secrets
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key and st.secrets.get("google"):
            api_key = st.secrets["google"]["GOOGLE_API_KEY"]
        
        if not api_key:
            st.error("⚠️ Falta la GOOGLE_API_KEY en secrets.toml.")
            st.stop()
            
        genai.configure(api_key=api_key)
        
        # Configuración de seguridad (Sin censura excesiva para permitir temas serios)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
        return model
    except Exception as e:
        st.error(f"Error al conectar con Google Gemini: {e}")
        st.stop()

def analizar_imagen_gemini(model, imagen_bytes, prompt_usuario):
    """Análisis visual usando Gemini (Nativo)."""
    try:
        image = Image.open(io.BytesIO(imagen_bytes))
        response = model.generate_content([prompt_usuario, image])
        return response.text
    except Exception:
        return "No pude ver la imagen claramente, pero estoy aquí."

def generar_perfil_cognitivo_gemini(model, user_id, messages):
    """Genera el perfil cognitivo usando Gemini."""
    if not messages: return ""
    analysis_messages = messages[-20:]
    chat_summary = "\n".join([f"{m['role']}: {m['content']}" for m in analysis_messages])
    
    prompt = f"""
    Analiza este historial del usuario '{user_id}' y crea un 'Perfil Cognitivo' breve (max 100 palabras).
    Enfócate en: Tono Emocional, Patrones de Lenguaje y Temas Recurrentes.
    Historial: {chat_summary}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return ""

# --- 5. GESTIÓN DE ESTADO ---
def inicializar_estado_sesion():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'user_name' not in st.session_state: st.session_state.user_name = None
    if 'ai_persona' not in st.session_state: st.session_state.ai_persona = 'Código Humano AI'
    if 'messages' not in st.session_state: st.session_state.messages = []
    if 'cognitive_profile' not in st.session_state: st.session_state.cognitive_profile = ""
inicializar_estado_sesion()

# --- 6. INTERFAZ Y FLUJO ---

def login_page():
    c1, c2, c3 = st.columns([1,4,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if LOGO_BASE64:
            st.markdown(f'<div class="logo-img-login"><img src="data:image/png;base64,{LOGO_BASE64}"></div>', unsafe_allow_html=True)
        else:
            st.title("CÓDIGO HUMANO AI")

        u = st.text_input("Ingresa tu Nombre de Usuario")
        p = st.text_input("Asigna un Nombre a tu Cómplice (Opcional)")

        if st.button("ACCEDER AL CÓMPLICE"):
            if u:
                st.session_state.user_name = u
                st.session_state.ai_persona = p.strip() if p else 'Código Humano AI'
                st.session_state.authenticated = True
                
                client_db = get_supabase_client()
                if client_db:
                    st.session_state.messages = cargar_historial_db(client_db, u)
                    st.session_state.cognitive_profile = cargar_perfil_cognitivo(client_db, u)
                st.rerun()

    st.markdown('<div class="footer-disclaimer"><div class="disclaimer-text">**⚠️ Descargo Ético:** Herramienta de registro personal. No sustituye terapia.</div></div>', unsafe_allow_html=True)

def main_app():
    AI_PERSONA_NAME = st.session_state.ai_persona
    model_gemini = configurar_gemini() # Inicializa Google Gemini
    client_db = get_supabase_client()
    
    # Carga de seguridad si falla al inicio
    if st.session_state.authenticated and not st.session_state.messages and client_db:
        st.session_state.messages = cargar_historial_db(client_db, st.session_state.user_name)
        st.session_state.cognitive_profile = cargar_perfil_cognitivo(client_db, st.session_state.user_name)

    # Actualización de perfil cognitivo en background (cada 15 mensajes)
    if len(st.session_state.messages) > 0 and len(st.session_state.messages) % 15 == 0:
        perfil = generar_perfil_cognitivo_gemini(model_gemini, st.session_state.user_name, st.session_state.messages)
        if perfil and client_db:
            st.session_state.cognitive_profile = perfil
            guardar_perfil_cognitivo(client_db, st.session_state.user_name, perfil)

    with st.sidebar:
        if LOGO_BASE64: st.image("logo.png")
        else: st.write("CÓDIGO HUMANO AI")
        st.write(f"Cómplice: **{AI_PERSONA_NAME}**")
        
        # UX: Contador de mensajes guardados
        num_msgs = len(st.session_state.messages)
        if st.button("➕ Nuevo Registro"):
            st.session_state.messages = []
            st.info(f"Sesión limpiada. {num_msgs} mensajes asegurados en memoria.")
            st.rerun()
            
        st.markdown("---")
        modo = st.radio("Modo", ["💬 Seamos Cómplices 😉", "🖼️ Análisis Visual", "📜 Historial"])
        
        # Indicador de Aprendizaje
        if st.session_state.cognitive_profile and st.session_state.cognitive_profile != "Perfil en construcción.":
            st.success("🧠 Aprendizaje Activo")
        
        st.markdown("---")
        if st.button("🔒 Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

    # SYSTEM PROMPT (Optimizado para Gemini)
    system_instruction = f"""
    Eres {AI_PERSONA_NAME}, el cómplice de {st.session_state.user_name}.
    
    [PERFIL APRENDIDO DEL USUARIO]:
    {st.session_state.cognitive_profile}
    
    [TUS REGLAS ABSOLUTAS]:
    1. **Validación Radical:** Tu prioridad es validar lo que el usuario siente. No juzgues.
    2. **Cero Preguntas Terapéuticas:** No preguntes "¿Cómo te sientes?". Reacciona al hecho (Ej: "¡Qué mala onda!", "¡Eso es increíble!").
    3. **Memoria Activa:** Si el usuario menciona algo del pasado o del [PERFIL APRENDIDO], úsalo para dar contexto.
    4. **NO ERES PSICÓLOGO:** No des consejos médicos ni soluciones mágicas. Solo acompaña.
    5. **Seguridad:** Si detectas riesgo de suicidio/autolesión, di: "No soy el adecuado para esto, por favor busca ayuda profesional inmediata" y detente.
    """

    if modo == "💬 Seamos Cómplices 😉":
        st.markdown(f"## 💬 {AI_PERSONA_NAME}")
        
        # Mostrar historial
        if not st.session_state.messages:
            st.markdown(f"<div class='welcome-text'>Hola {st.session_state.user_name}. Soy {AI_PERSONA_NAME}.<br>Este es nuestro espacio seguro. ¿Qué hay en tu mente?</div>", unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            with st.chat_message(msg['role']): st.markdown(msg['content'])

        # Input de Chat
        prompt = st.chat_input("Escribe o dicta aquí...")
        
        if prompt:
            # 1. Guardar User
            if client_db: guardar_mensaje_db(client_db, "user", prompt, st.session_state.user_name)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 2. Generar Respuesta (Gemini)
            with st.chat_message("assistant"):
                try:
                    # Construir historial para Gemini (Formato específico de Google)
                    gemini_history = []
                    
                    # Inyectar System Prompt como "Instrucción" inicial en el contexto
                    gemini_history.append({"role": "user", "parts": [system_instruction]})
                    gemini_history.append({"role": "model", "parts": ["Entendido. Estoy listo y conozco el perfil del usuario."]})
                    
                    for m in st.session_state.messages:
                        # Convertir roles a formato Gemini
                        role = "user" if m['role'] == "user" else "model"
                        # Asegurar que el contenido no sea None/Vacio
                        content = m['content'] if m['content'] else "."
                        gemini_history.append({"role": role, "parts": [content]})
                    
                    # Iniciar chat con historial
                    chat = model_gemini.start_chat(history=gemini_history)
                    
                    # Enviar mensaje nuevo
                    response = chat.send_message(prompt, stream=True)
                    
                    full_text = ""
                    placeholder = st.empty()
                    for chunk in response:
                        full_text += chunk.text
                        placeholder.markdown(full_text + "▌")
                    placeholder.markdown(full_text)
                    
                    # 3. Guardar Assistant
                    if client_db: guardar_mensaje_db(client_db, "assistant", full_text, st.session_state.user_name)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    
                except Exception as e:
                    # Manejo de error de Gemini
                    st.error("⚠️ Hubo una interrupción en la señal. Por favor, intenta de nuevo.")
                    print(f"Error Gemini: {e}")
            st.rerun()

    elif modo == "🖼️ Análisis Visual":
        st.title("🖼️ Análisis Visual")
        st.info("Sube una foto o usa la cámara. Tu cómplice te dirá qué opina.")
        img_file = st.camera_input("Captura")
        if not img_file: img_file = st.file_uploader("O sube imagen", type=['jpg','png','jpeg'])
        
        if img_file:
            txt = st.text_input("¿Qué vemos?", value="Dime qué opinas de esto.")
            if st.button("Analizar"):
                with st.spinner("Observando..."):
                    bytes_data = img_file.getvalue()
                    resp = analizar_imagen_gemini(model_gemini, bytes_data, txt)
                    st.write(resp)
                    if client_db:
                        guardar_mensaje_db(client_db, "user", f"[Imagen] {txt}", st.session_state.user_name)
                        guardar_mensaje_db(client_db, "assistant", resp, st.session_state.user_name)
                        st.session_state.messages.append({"role": "assistant", "content": resp})

    elif modo == "📜 Historial":
        st.title("📜 Historial Completo")
        if client_db:
            msgs = cargar_historial_db(client_db, st.session_state.user_name)
            if not msgs: st.info("No hay historial aún.")
            for m in reversed(msgs):
                st.caption(f"{m['role'].upper()}:")
                st.info(m['content'])

if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
