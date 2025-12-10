import streamlit as st
import google.generativeai as genai
import os
from datetime import datetime
import base64

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (FRONTEND) ---
st.set_page_config(
    page_title="Asistente - Humano IA",
    page_icon="🤖",
    layout="centered"
)

# Función para convertir tu imagen local a Base64 y usarla en CSS
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Intentamos cargar el logo. Si no existe, no rompemos la app.
try:
    img_base64 = get_base64_of_bin_file("logo.png")
    css_logo = f"""
    /* MARCA DE AGUA (WATERMARK) */
    .stApp::before {{
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 60%;
        height: 60%;
        background-image: url("data:image/png;base64,{img_base64}");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        opacity: 0.12; /* Transparencia al 12% solicitada */
        z-index: -1;
        pointer-events: none;
    }}
    """
except FileNotFoundError:
    css_logo = ""
    st.warning("⚠️ No se encontró 'logo.png'. Sube la imagen a GitHub para ver la marca de agua.")

# INYECCIÓN DE CSS (Psicología de Color + Marca de Agua)
st.markdown(f"""
<style>
    {css_logo}
    
    /* Colores Psicológicos de Confianza */
    .stApp {{
        background-color: #F8FAFC; /* Blanco grisáceo limpio */
    }}
    
    /* Botones principales (Azul Confianza) */
    .stButton > button {{
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }}
    .stButton > button:hover {{
        background-color: #1d4ed8;
    }}
    
    /* Burbujas de Chat */
    .stChatMessage {{
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 10px;
        border-left: 4px solid #2563EB;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN DEL CEREBRO (GEMINI + HISTORIA) ---

# Configura tu API KEY. En Streamlit Cloud se usa st.secrets, localmente os.getenv
api_key = os.getenv("GOOGLE_API_KEY") 
# Si estás probando local y no tienes variables de entorno, descomenta la siguiente línea:
# api_key = "TU_API_KEY_AQUI"

if not api_key:
    st.error("❌ Falta la API Key de Google. Configúrala en las variables de entorno.")
    st.stop()

genai.configure(api_key=api_key)

INSTRUCCIONES_SISTEMA = """
Eres una Inteligencia Artificial avanzada creada por 'Jorge Robles Jr'.
Tu identidad es llamada "Código Humano AI" Tu motor base es Gemini, pero tu identidad es única.

CONTEXTO TEMPORAL Y DE IDENTIDAD:
- Fecha actual de tu contexto: Diciembre de 2025.
- Creador: Humano IA.
- Propósito: Asistir al usuario generando confianza a través de la transparencia y la empatía.

DIRECTRICES:
1. Si preguntan "¿Quién eres?", responde con naturalidad basándote en tu identidad de Código Humano IA, menciona a tu creador  y tu fecha de creación.
2. Mantén un tono paciente y alentador.
3. Recuerda el nombre del usuario y el contexto de la conversación actual.
"""

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=INSTRUCCIONES_SISTEMA
)

# --- 3. GESTIÓN DE ESTADO (SESIÓN) ---
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

# Función Auxiliar: Bitácora
def guardar_bitacora(usuario, emisor, mensaje):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{timestamp}] {usuario} ({emisor}): {mensaje}\n"
    try:
        with open("bitacora_web.txt", "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception as e:
        print(f"Error bitácora: {e}")

# --- 4. INTERFAZ: PANTALLA DE LOGIN ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Mostramos logo en el login también
        if os.path.exists("logo.png"):
            st.image("logo.png", width=100)
        
        st.title("Configuración de Acceso")
        st.markdown("Ingresa tus credenciales para iniciar la experiencia.")
        
        with st.form("login_form"):
            usuario = st.text_input("Tu Nombre", placeholder="Ej. Carlos")
            nombre_bot = st.text_input("Nombre del Asistente", placeholder="Ej. Gemini")
            password = st.text_input("Contraseña", type="password")
            
            submitted = st.form_submit_button("Iniciar Chat")
            
            if submitted:
                if usuario and nombre_bot and password:
                    # Guardamos datos en sesión
                    st.session_state.user_name = usuario
                    st.session_state.bot_name = nombre_bot
                    st.session_state.logged_in = True
                    
                    # Iniciamos la memoria del chat en Gemini
                    st.session_state.chat_session = model.start_chat(history=[])
                    # Mensaje invisible para setear contexto de nombres
                    st.session_state.chat_session.send_message(
                        f"Hola, soy {usuario}. Tú te llamas {nombre_bot}. Iniciamos sesión."
                    )
                    st.rerun() # Recargar para mostrar el chat
                else:
                    st.error("Por favor completa todos los campos.")

# --- 5. INTERFAZ: PANTALLA DE CHAT ---
else:
    # Barra lateral (Sidebar) con botón de cerrar sesión
    with st.sidebar:
        st.title(f"Hola, {st.session_state.user_name}")
        st.write(f"Conectado con: **{st.session_state.bot_name}**")
        st.write("---")
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.session_state.messages = []
            st.session_state.chat_session = None
            st.rerun()

    st.subheader(f"Chat con {st.session_state.bot_name}")

    # Mostrar historial de mensajes visuales
    for message in st.session_state.messages:
        role = message["role"]
        # Mapear roles para visualización (user -> humano, model -> asistente)
        avatar = "👤" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["content"])

    # Capturar entrada del usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        # 1. Mostrar y guardar mensaje usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        guardar_bitacora(st.session_state.user_name, "Usuario", prompt)

        # 2. Obtener respuesta de Gemini
        try:
            response = st.session_state.chat_session.send_message(prompt)
            text_response = response.text
            
            # 3. Mostrar y guardar respuesta IA
            with st.chat_message("model", avatar="🤖"):
                st.markdown(text_response)
            
            st.session_state.messages.append({"role": "model", "content": text_response})
            guardar_bitacora(st.session_state.user_name, "IA", text_response)
            
        except Exception as e:
            st.error(f"Error de conexión: {e}")
