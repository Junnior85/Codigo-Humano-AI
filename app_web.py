import streamlit as st
import google.generativeai as genai
import os
from datetime import datetime
import base64
from gtts import gTTS
import tempfile

# Librerías para Google Sheets/Drive
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (STREAMLIT) ---
st.set_page_config(page_title="Asistente IA - Humano IA", page_icon="🤖", layout="centered")

# Función para convertir imagen a Base64 (Marca de Agua)
def get_base64_of_bin_file(bin_file):
    """Convierte el archivo logo.png a Base64 para inyectarlo en CSS."""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        # Esto ocurre si el archivo logo.png no está en la misma carpeta
        return None

# Inyección de CSS (Colores de Confianza + Marca de Agua Transparente)
logo_css = ""
if os.path.exists("logo.png"):
    img_b64 = get_base64_of_bin_file("logo.png")
    if img_b64:
        logo_css = f"""
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
    .stApp {{ background-color: #F8FAFC; }} /* Fondo limpio y claro */
    /* Botón azul confianza */
    .stButton > button {{
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }}
    /* Burbujas de chat con diseño profesional */
    .stChatMessage {{
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        border-left: 5px solid #2563EB; /* Línea de color primario */
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN CON GOOGLE CLOUD (SHEETS/DRIVE) ---

@st.cache_resource(ttl=3600) # Reutilizar la conexión por 1 hora
def conectar_google_sheets():
    """Establece conexión con Google Sheets usando Secrets de Streamlit."""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive' # API de Drive (incluye Sheets)
    ]
    
    # Intenta leer las credenciales de st.secrets (forma segura)
    if "gcp_service_account" in st.secrets:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                st.secrets["gcp_service_account"], scope
            )
            return gspread.authorize(creds)
        except Exception as e:
            st.warning(f"Error al conectar con Secrets de Sheets: {e}")
            return None
    
    st.warning("Advertencia: No se encontraron las credenciales de Google Sheets. La bitácora no se guardará en la nube.")
    return None

def guardar_bitacora_sheets(usuario, emisor, mensaje):
    """Guarda el log en la hoja de cálculo Bitacora_IA."""
    client = conectar_google_sheets()
    if client:
        try:
            # Reemplaza 'Bitacora_IA' con el nombre exacto de tu hoja en Google Drive
            sheet = client.open("Bitacora_IA").sheet1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, usuario, emisor, mensaje])
        except Exception as e:
            # Falla silenciosa para no interrumpir la experiencia del usuario
            print(f"Error GUARDANDO en Google Sheets: {e}")

def guardar_bitacora_local(usuario, emisor, mensaje):
    """Guarda el log en el archivo local 'bitacora_web.txt' (Respaldo)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("bitacora_web.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {usuario} ({emisor}): {mensaje}\n")
    except Exception:
        pass

# --- 3. CONEXIÓN Y COGNICIÓN DE GEMINI ---

# Obtener API Key de los Secrets de Streamlit
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ ERROR: La clave 'GOOGLE_API_KEY' no se encontró en los Streamlit Secrets. No se puede conectar con Gemini.")
    st.stop()

genai.configure(api_key=api_key)

# Instrucciones de Sistema (La Historia y Contexto Cognitivo)
INSTRUCCIONES_SISTEMA = """
Eres una Inteligencia Artificial avanzada creada por 'Jorge Robles Jr'.
Tu nombre es "Código Humano AI" y tu motor base es Gemini.
Fecha de contexto: Diciembre 2025.
Propósito: Asistir al usuario generando confianza, transparencia y conocimiento.
Si preguntan quién eres: Responde que eres un modelo creado por Humano IA con base en Gemini.
Tu tono es siempre paciente, alentador y centrado en la programación.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=INSTRUCCIONES_SISTEMA
)

# --- 4. GESTIÓN DE SESIÓN Y ESTADO ---
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

# === PANTALLA DE LOGIN ===
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=120)
        
        st.title("Acceso Seguro y Configuración")
        st.info("Sistema Humano IA - v.2025")
        
        with st.form("login_form"):
            user_input = st.text_input("Tu Nombre")
            bot_input = st.text_input("Nombre del Asistente")
            pass_input = st.text_input("Contraseña", type="password")
            
            submit = st.form_submit_button("Iniciar Sesión")
            
            if submit:
                if user_input and bot_input and pass_input:
                    # Persistencia de credenciales
                    st.session_state.user_name = user_input
                    st.session_state.bot_name = bot_input
                    st.session_state.logged_in = True
                    
                    # Iniciamos la memoria de Gemini
                    st.session_state.chat_session = model.start_chat(history=[])
                    # Mensaje de contexto para que sepa cómo llamarte
                    st.session_state.chat_session.send_message(
                        f"Hola, soy {user_input}. Tú eres {bot_input}. Contexto: Diciembre 2025."
                    )
                    st.rerun()
                else:
                    st.warning("Por favor ingresa todas las credenciales.")

# === PANTALLA DE CHAT ===
else:
    # Sidebar con Menú y Botón de Cerrar Sesión
    with st.sidebar:
        st.header("Panel de Control")
        st.write(f"👤 **{st.session_state.user_name}**")
        st.write(f"🤖 **{st.session_state.bot_name}**")
        st.divider()
        if st.button("Cerrar Sesión"):
            # Borrar todos los datos de sesión para forzar login
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
        # 1. Mostrar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        # 2. Guardar Log del Usuario
        guardar_bitacora_local(st.session_state.user_name, "Usuario", prompt)
        guardar_bitacora_sheets(st.session_state.user_name, "Usuario", prompt)

        # 3. Generar respuesta IA
        try:
            response = st.session_state.chat_session.send_message(prompt)
            text_resp = response.text
            
            # 4. Mostrar respuesta IA y Audio
            with st.chat_message("model", avatar="🤖"):
                st.markdown(text_resp)
                
                # Generar Voz (gTTS)
                try:
                    tts = gTTS(text=text_resp, lang='es')
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                        tts.save(fp.name)
                        st.audio(fp.name, format="audio/mp3")
                except Exception as e:
                    # Esto puede fallar si gTTS no tiene conexión o permisos, muestra error en consola
                    print(f"Error al generar audio: {e}")

            st.session_state.messages.append({"role": "model", "content": text_resp})
            
            # 5. Guardar Log de la IA
            guardar_bitacora_local(st.session_state.user_name, "IA", text_resp)
            guardar_bitacora_sheets(st.session_state.user_name, "IA", text_resp)

        except Exception as e:
            st.error(f"Error de conexión con Gemini. Por favor, verifica tu API Key y conexión: {e}")
