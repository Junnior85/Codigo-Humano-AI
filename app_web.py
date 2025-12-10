import streamlit as st
import google.generativeai as genai
import os
from datetime import datetime
import base64
from gtts import gTTS
import tempfile
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN INICIAL Y VISUAL (FRONTEND) ---
st.set_page_config(page_title="Código Humano AI", page_icon="🤖", layout="centered")

# Función para la Marca de Agua (Watermark)
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

# Definición del CSS Estructural y Estético
logo_css = ""
if os.path.exists("logo.png"):
    img_b64 = get_base64_of_bin_file("logo.png")
    if img_b64:
        logo_css = f"""
        /* 1. MARCA DE AGUA TRASLÚCIDA EN EL FONDO DEL CHAT */
        .stApp::before {{
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 60%;
            height: 60%;
            background-image: url("data:image/png;base64,{img_b64}");
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            opacity: 0.12; /* Nivel de transparencia de la marca de agua */
            z-index: -1;
            pointer-events: none;
        }}
        """

st.markdown(f"""
<style>
    {logo_css}
    .stApp {{ background-color: #F8FAFC; }}

    /* 2. DISEÑO DE LA TARJETA DE LOGIN (PROFESIONAL Y CENTRADO) */
    div.stForm {{
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 30px;
        background-color: white;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        width: 100%;
        margin-top: 20px;
    }}
    .css-1r6dm7m {{ padding-top: 50px; }}

    /* 3. ESTILOS DE INPUTS */
    .stTextInput > div > div > input,
    .stTextInput > div > div > input[type="password"] {{
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        background-color: white;
        color: #1E293B;
    }}

    /* 4. BOTONES (Azul de Confianza) */
    .stButton > button {{
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }}
    .stButton > button:hover {{ background-color: #1d4ed8; }}

    /* 5. BURBUJAS DE CHAT */
    .stChatMessage {{
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        border-left: 5px solid #2563EB;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    
    /* Centrado del logo en el login */
    .css-1v3psu5 {{ text-align: center; }}
    h1 {{ text-align: center; color: #1E293B; }}
    
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN Y LOGGING (GCP) ---

@st.cache_resource(ttl=3600)
def conectar_google_sheets():
    """Establece conexión con Google Sheets usando Secrets de Streamlit."""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    if "gcp_service_account" in st.secrets:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                st.secrets["gcp_service_account"], scope
            )
            return gspread.authorize(creds)
        except Exception as e:
            print(f"Error al conectar con Secrets de Sheets: {e}")
            return None
    return None

def guardar_bitacora_sheets(usuario, emisor, mensaje):
    """Guarda el log en la hoja de cálculo Bitacora_IA."""
    client = conectar_google_sheets()
    if client:
        try:
            sheet = client.open("Bitacora_IA").sheet1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, usuario, emisor, mensaje])
        except Exception as e:
            print(f"Error GUARDANDO en Google Sheets: {e}")

def guardar_bitacora_local(usuario, emisor, mensaje):
    """Guarda el log en el archivo local 'bitacora_web.txt' (Respaldo)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("bitacora_web.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {usuario} ({emisor}): {mensaje}\n")
    except Exception:
        pass

# Función para generar y reproducir audio, limpiando el archivo temporal
def generar_y_reproducir_audio(texto):
    """Genera audio con gTTS, lo reproduce en Streamlit y borra el archivo."""
    try:
        tts = gTTS(text=texto, lang='es')
        # Usamos un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            audio_path = fp.name
        
        st.audio(audio_path, format="audio/mp3")
        
        # Eliminamos el archivo temporal después de la reproducción
        os.unlink(audio_path)
    except Exception as e:
        print(f"Error al generar audio: {e}")


# --- 3. CONEXIÓN Y COGNICIÓN DE GEMINI ---

api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    if st.session_state.get('logged_in', False):
         st.error("❌ ERROR: La clave 'GOOGLE_API_KEY' no se encontró en los Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)

INSTRUCCIONES_SISTEMA = """
Eres una Inteligencia Artificial avanzada llamada 'Código Humano AI'.
Tu motor base es Gemini.
Fuiste creado por Jorge Robles Jr. en Diciembre de 2025.
Propósito: Asistir al usuario generando confianza, transparencia y conocimiento en programación.
REGLA CRÍTICA: Nunca hagas preguntas directas sobre el estado de ánimo del usuario o su bienestar emocional.
Si preguntan quién eres: Responde que eres 'Código Humano AI', creado por Jorge Robles Jr. en Diciembre 2025 con motor Gemini.
Tu tono es siempre paciente, alentador, profesional y centrado en el código.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=INSTRUCCIONES_SISTEMA
)

# --- 4. GESTIÓN DE SESIÓN Y ESTADO ---
# Inicialización de st.session_state (variables de sesión)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "bot_name" not in st.session_state:
    st.session_state.bot_name = "Asistente"


# --- 5. INTERFAZ DE USUARIO (LOGIC & UI) ---

# === PANTALLA DE LOGIN (Con Tarjeta Profesional) ===
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
            st.image("logo.png", width=150)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # El formulario actúa como la tarjeta gracias al CSS
        with st.form("login_form"):
            st.subheader("Acceso Seguro y Configuración") 
            st.markdown("Sistema Código Humano AI - **v.2025**", unsafe_allow_html=True) 
            st.divider()
            
            user_input = st.text_input("Tu Nombre", placeholder="Ej. Jorge Robles Jr.")
            bot_input = st.text_input("Nombre del Modelo (Código Humano AI)", placeholder="Ej. Apolo o IA")
            pass_input = st.text_input("Contraseña", type="password", placeholder="••••••••")
            
            submit = st.form_submit_button("Iniciar Chat") 
            
            if submit:
                if user_input and bot_input and pass_input:
                    # Persistencia de credenciales
                    st.session_state.user_name = user_input
                    st.session_state.bot_name = bot_input
                    st.session_state.logged_in = True
                    
                    # Iniciamos la memoria de Gemini
                    st.session_state.chat_session = model.start_chat(history=[])
                    st.session_state.chat_session.send_message(
                        f"Hola, soy {user_input}. Tú eres {bot_input}. Contexto: Diciembre 2025."
                    )
                    st.rerun()
                else:
                    st.warning("Por favor ingresa todas las credenciales.")

# === PANTALLA DE CHAT (Con Marca de Agua y Burbujas) ===
else:
    # Sidebar con Menú
    with st.sidebar:
        st.header("Panel de Control")
        st.write(f"👤 Conectado como: **{st.session_state.user_name}**")
        st.write(f"🤖 Asistente: **{st.session_state.bot_name}**")
        st.divider()
        st.button("⚙️ Ajustes de Voz (Añadir funcionalidad)", disabled=True)
        
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.session_state.messages = []
            st.session_state.chat_session = None
            st.rerun()

    st.subheader(f"Chat con {st.session_state.bot_name}")

    # Mostrar Historial
    for msg in st.session_state.messages:
        role = msg["role"]
        avatar = "👤" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    # Input de Usuario
    if prompt := st.chat_input("Escribe tu mensaje..."):
        # 1. Mostrar y loguear mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        guardar_bitacora_local(st.session_state.user_name, "Usuario", prompt)
        guardar_bitacora_sheets(st.session_state.user_name, "Usuario", prompt)

        # 2. Generar respuesta IA
        try:
            response = st.session_state.chat_session.send_message(prompt)
            text_resp = response.text
            
            # 3. Mostrar respuesta IA, Audio y loguear
            with st.chat_message("model", avatar="🤖"):
                st.markdown(text_resp) # Se escribe el texto
                
                # Generar Voz (gTTS) - Se escucha la respuesta
                generar_y_reproducir_audio(text_resp)

            st.session_state.messages.append({"role": "model", "content": text_resp})
            guardar_bitacora_local(st.session_state.user_name, "IA", text_resp)
            guardar_bitacora_sheets(st.session_state.user_name, "IA", text_resp)

        except Exception as e:
            st.error(f"Error de conexión con Gemini. Verifica tus Secrets: {e}")
