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
if os.path.exists("LOGO.png"):
    img_b64 = get_base64_of_bin_file("LOGO.png")
    if img_b64:
        logo_css = f"""
        /* 1. MARCA DE AGUA TRASLÚCIDA EN EL FONDO DEL CHAT (Ajustado para fondo oscuro) */
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
            opacity: 0.25; /* Aumentamos la opacidad para que se vea sobre el fondo oscuro */
            z-index: -1;
            pointer-events: none;
            /* Filtro opcional: invertir colores o hacerlo gris para que contraste menos */
            filter: grayscale(100%) brightness(150%); 
        }}
        """

# Inyección de CSS (DARK MODE PROFESIONAL Y CONTRASTE)
st.markdown(f"""
<style>
    {logo_css}
    /* 1. FONDO PRINCIPAL OSCURO */
    .stApp {{ background-color: #1E293B; color: #F8FAFC; }} /* Fondo Negro/Gris Oscuro */

    /* 2. DISEÑO DE LA TARJETA DE LOGIN (PROFESIONAL Y CENTRADO) */
    div.stForm {{
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 30px;
        background-color: #334155; /* Tarjeta Gris Oscuro */
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        width: 100%;
        margin-top: 15px; 
    }}
    /* Ajustes de espaciado y centrado */
    .css-1r6dm7m {{ padding-top: 50px; }} 

    /* 3. ESTILOS DE INPUTS (Visibilidad y Tema Oscuro) */
    .stTextInput > div > div > input,
    .stTextInput > div > div > input[type="password"],
    .stTextInput label,
    .stTextInput input,
    .stMarkdown, .stSidebar * {{
        /* Asegurar color de texto claro sobre inputs oscuros */
        color: #F8FAFC !important; /* Texto Blanco */
        background-color: #475569 !important; /* Fondo de Input Gris más oscuro */
        border: 1px solid #64748B;
        border-radius: 8px;
    }}
    
    /* Títulos y Subtítulos (Asegurar que sean claros) */
    h1, h2, h3, h4 {{ color: #F8FAFC !important; }}

    /* 4. BOTONES (Azul de Confianza) */
    .stButton > button {{
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }}
    .stButton > button:hover {{ background-color: #1d4ed8; }}

    /* 5. BURBUJAS DE CHAT (Claras sobre fondo oscuro) */
    .stChatMessage {{
        background-color: #334155; /* Burbujas de chat oscuras */
        border-radius: 12px;
        border-left: 5px solid #2563EB;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }}
    
    /* Centrado del logo en el login */
    .stImage > img {{ 
        margin-left: auto;
        margin-right: auto;
        display: block; 
    }}
    
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN Y LOGGING (GCP) ---

@st.cache_resource(ttl=3600)
def conectar_google_sheets():
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
    client = conectar_google_sheets()
    if client:
        try:
            sheet = client.open("Bitacora_IA").sheet1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, usuario, emisor, mensaje])
        except Exception as e:
            print(f"Error GUARDANDO en Google Sheets: {e}")

def guardar_bitacora_local(usuario, emisor, mensaje):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("bitacora_web.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {usuario} ({emisor}): {mensaje}\n")
    except Exception:
        pass

def generar_y_reproducir_audio(texto):
    try:
        tts = gTTS(text=texto, lang='es')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            audio_path = fp.name
        
        st.audio(audio_path, format="audio/mp3")
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

# === PANTALLA DE LOGIN (DARK MODE) ===
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        LOGO_LOGIN_FILE = "LOGO.png" # Usamos el nombre de archivo exacto: LOGO.png
        
        if os.path.exists(LOGO_LOGIN_FILE):
            # 1. LOGO GRANDE Y SÓLIDO (Punto focal atractivo)
            st.markdown("<div style='text-align: center; margin-bottom: 20px;'>", unsafe_allow_html=True)
            st.image(LOGO_LOGIN_FILE, use_column_width=True) 
            st.markdown("</div>", unsafe_allow_html=True)
        
        # 2. CUESTIONARIO: El formulario (tarjeta de login) INMEDIATAMENTE debajo
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
                    st.session_state.user_name = user_input
                    st.session_state.bot_name = bot_input
                    st.session_state.logged_in = True
                    
                    st.session_state.chat_session = model.start_chat(history=[])
                    st.session_state.chat_session.send_message(
                        f"Hola, soy {user_input}. Tú eres {bot_input}. Contexto: Diciembre 2025."
                    )
                    st.rerun()
                else:
                    st.warning("Por favor ingresa todas las credenciales.")

# === PANTALLA DE CHAT (DARK MODE CON MARCA DE AGUA) ===
else:
    # Sidebar con Menú
    with st.sidebar:
        st.header("Panel de Control")
        st.write(f"👤 Conectado como: **{st.session_state.user_name}**")
        st.write(f"🤖 Asistente: **{st.session_state.bot_name}**")
        st.divider()
        st.button("⚙️ Ajustes de Voz", disabled=True)
        
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
            
            # 3. Mostrar respuesta IA, Audio y loguear (Multimodalidad)
            with st.chat_message("model", avatar="🤖"):
                st.markdown(text_resp) # Se escribe el texto
                generar_y_reproducir_audio(text_resp) # Se reproduce el audio

            st.session_state.messages.append({"role": "model", "content": text_resp})
            guardar_bitacora_local(st.session_state.user_name, "IA", text_resp)
            guardar_bitacora_sheets(st.session_state.user_name, "IA", text_resp)

        except Exception as e:
            st.error(f"Error de conexión con Gemini. Verifica tus Secrets: {e}")
