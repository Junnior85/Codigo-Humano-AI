# --- 1. IMPORTS Y CONFIGURACIÓN INICIAL ---
import streamlit as st
import google.generativeai as genai
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from datetime import datetime
import tempfile
from gtts import gTTS
from pathlib import Path
from streamlit_mic_recorder import mic_recorder 
import logging
import os
import base64
import gspread 
from oauth2client.service_account import ServiceAccountCredentials 

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes
CHROMA_PATH = "chroma_db_memoria"
Path(CHROMA_PATH).mkdir(exist_ok=True)

# Configuración de Página (Debe ser lo primero)
st.set_page_config(page_title="Código Humano AI", page_icon="🤖", layout="centered")

# --- 2. GESTIÓN DE SECRETOS Y SEGURIDAD ---

def validar_secretos():
    required_secrets = ["GOOGLE_API_KEY", "MODELO_PRINCIPAL"]
    missing = [s for s in required_secrets if s not in st.secrets]
    if missing:
        st.error(f"❌ Error Crítico: Faltan las siguientes claves en secrets.toml: {', '.join(missing)}")
        st.stop()
    
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

validar_secretos()


# --- 3. CLASES DE LÓGICA DE NEGOCIO Y RECURSOS (RAG, AUDIO, BITÁCORA) ---

@st.cache_resource
def get_embeddings_model():
    return GoogleGenerativeAIEmbeddings(
        model="text-embedding-004",
        google_api_key=st.secrets["GOOGLE_API_KEY"]
    )

@st.cache_resource
def get_vector_store():
    try:
        return Chroma(
            collection_name="codigo_humano_ai_context",
            embedding_function=get_embeddings_model(),
            persist_directory=CHROMA_PATH
        )
    except Exception as e:
        logger.error(f"Error inicializando ChromaDB: {e}")
        st.error("Error crítico: No se pudo conectar con la base de memoria.")
        return None

class GestorMemoria:
    """Encargado de la persistencia y recuperación de contexto (RAG)."""
    def __init__(self):
        self.vector_store = get_vector_store()

    def guardar(self, usuario, clave_personal, prompt, respuesta): 
        """Guarda una interacción en la memoria vectorial (Blindado)."""
        if not self.vector_store: return
        try:
            contenido = f"User: {prompt}\nAI: {respuesta}"
            doc = Document(
                page_content=contenido, 
                metadata={
                    "user": usuario, 
                    "timestamp": str(datetime.now()),
                    "clave_personal": clave_personal 
                }
            )
            self.vector_store.add_documents([doc])
        except Exception as e:
            logger.error(f"Fallo al guardar memoria: {e}")

    def recuperar(self, usuario, query, k=5):
        """Recupera contexto relevante para el usuario específico (Blindado)."""
        if not self.vector_store: return ""
        try:
            docs = self.vector_store.similarity_search(query, k=k, filter={"user": usuario})
            if not docs: return ""
            contexto_texto = "\n".join([f"- {d.page_content}" for d in docs])
            return contexto_texto
        except Exception as e:
            logger.error(f"Fallo al recuperar memoria: {e}")
            return ""

class GestorAudio:
    """Maneja la generación de voz (TTS) de forma segura."""
    @staticmethod
    def generar_y_reproducir(texto, configuracion_voz):
        if not texto: return
        
        tld_map = {
            "Masculino (México)": 'com.mx',
            "Femenino (España)": 'es',
        }
        tld = tld_map.get(configuracion_voz, 'es')
        
        try:
            tts = gTTS(text=texto, lang='es', tld=tld)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tts.save(tmp.name)
                st.audio(tmp.name, format="audio/mp3")
        except Exception as e:
            logger.error(f"Error generando audio (TTS): {e}")

class GestorBitacora:
    """Maneja el log en archivo de texto simple y Google Sheets."""
    
    @st.cache_resource(ttl=3600)
    def conectar_sheets():
        """Conexión robusta a Google Sheets usando st.secrets."""
        try:
            if "gcp_service_account" not in st.secrets: return None
                
            # AQUÍ OCURRÍA EL ERROR ANTERIORMENTE. VERIFICADO:
            creds_info = st.secrets["gcp_service_account"]
            
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            client = gspread.authorize(creds)
            return client.open("Bitacora_IA").sheet1 
        except Exception as e:
            logger.error(f"Error conectando a Google Sheets: {e}")
            return None

    @staticmethod
    def registrar(usuario, rol, mensaje):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Registro en archivo local (Fallback)
        try:
            with open("bitacora_web.txt", "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {usuario} ({rol}): {mensaje}\n")
        except Exception:
            pass 
            
        # 2. Registro en Google Sheets
        sheet = GestorBitacora.conectar_sheets()
        if sheet:
            try:
                sheet.append_row([timestamp, usuario, rol, mensaje])
            except Exception as e:
                logger.error(f"Fallo al registrar en Google Sheets: {e}")


# --- 4. INTERFAZ Y ESTILOS ---

def inicializar_session_state():
    """Valores por defecto seguros."""
    defaults = {
        "logged_in": False,
        "messages": [],
        "user_name": "",
        "bot_name": "Código Humano AI",
        "audio_on": True,
        "chat_initialized": False,
        "bot_name_session": "Código Humano AI",
        "rol_temporal": "",
        "clave_personal": "" 
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def aplicar_estilos():
    """Aplica estilos Dark Mode y logo de fondo."""
    def get_base64_of_bin_file(bin_file):
        try:
            with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
        except FileNotFoundError: return None

    logo_css = ""
    if os.path.exists("LOGO.png"):
        img_b64 = get_base64_of_bin_file("LOGO.png")
        if img_b64:
            logo_css = f".stApp::before {{ content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 60%; height: 60%; background-image: url('data:image/png;base64,{img_b64}'); background-repeat: no-repeat; background-position: center; background-size: contain; opacity: 0.25; z-index: -1; pointer-events: none; filter: grayscale(100%) brightness(150%); }}"

    st.markdown(f"""
    <style>
        {logo_css}
        .main > div {{ background-color: #1E293B !important; }}
        .stChatInputContainer {{ 
            position: fixed; bottom: 0; left: 0; right: 0; padding: 10px; 
            background-color: #1E293B; z-index: 999; 
            box-shadow: 0 -5px 15px rgba(0,0,0,0.2); 
        }}
    </style>
    """, unsafe_allow_html=True)

def inicializar_modelo():
    """Inicia el modelo de Gemini y establece el saludo inicial."""
    if "chat_session" not in st.session_state or not st.session_state.chat_initialized:
        try:
            model = genai.GenerativeModel(
                model_name=st.secrets["MODELO_PRINCIPAL"],
                system_instruction=f"""
                Eres {st.session_state.bot_name}. Tu identidad central es: 'Código Humano AI', un cómplice humano, empático y solidario.
                - Escucha activamente. Responde con naturalidad y calidez.
                - Si el usuario te pide un rol temporal, SIMULA en estilo, pero NUNCA abandones tu esencia empática.
                - Tu nombre de usuario es {st.session_state.user_name}.
                """
            )
            st.session_state.chat_session = model.start_chat(history=[])
            st.session_state.chat_initialized = True

            # Saludo inicial
            saludo_inicial = f"Hola {st.session_state.user_name}! Soy Código Humano AI. Estoy aquí para escucharte, ¿cómo te sientes hoy?"
            
            st.session_state.chat_session.send_message(saludo_inicial)
            st.session_state.messages.append({"role": "model", "content": saludo_inicial})
            
        except Exception as e:
            st.error(f"Error crítico conectando con Google AI: {e}")
            logger.error(f"Error inicializando modelo: {e}")
            st.stop()


# --- 5. LOOP PRINCIPAL DE LA APLICACIÓN (main) ---

def main():
    inicializar_session_state()
    aplicar_estilos() 

    # A. Flujo de Login (Login Simplificado con Clave Personal y Disclaimer)
    if not st.session_state.logged_in:
        
        # 1. CENTRADO ESTABLE DEL LOGO
        try:
            if os.path.exists("LOGO.png"):
                col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
                with col_logo2:
                    st.image("LOGO.png", use_column_width=True) 
        except Exception:
            pass 

        # 2. CENTRADO DEL FORMULARIO
        st.markdown("<div style='display: flex; justify-content: center; flex-direction: column; align-items: center; text-align: center;'>", unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=True):
            st.subheader("Acceso y Personalización")
            user = st.text_input("👤 Tu Nombre (Clave de Sesión)", key="user_name_input")
            bot = st.text_input("🤖 Nombre del Modelo", key="bot_name_input", value=st.session_state.bot_name)
            
            # Línea corregida (Sintaxis completa)
            clave_personal = st.text_input("✨ Tu Palabra Clave Personal", type="password", key="clave_personal_input")
            
            # --- DESCARGO DE RESPONSABILIDAD CRÍTICO ---
            st.warning("""
            **⚠️ Advertencia de Seguridad:**
            Usted es el único responsable de la seguridad de su Palabra Clave. Si elige una clave fácil de adivinar, 
            su historial puede ser accedido por terceros que conozcan su Nombre.
            """)
            
            if st.form_submit_button("Iniciar Chat"):
                if user and bot and clave_personal:
                    st.session_state.update({
                        "logged_in": True, "user_name": user.strip(), "bot_name": bot,
                        "chat_initialized": False, "clave_personal": clave_personal 
                    })
                    st.rerun()
                else:
                    st.error("Por favor, completa tu Nombre y tu Palabra Clave Personal para ingresar.")

        st.markdown("</div>", unsafe_allow_html=True)
        return

    # B. Interfaz Principal (Contenido del Chat)
    inicializar_modelo()
    memoria = GestorMemoria()
    
    # 🌟 Sidebar Configuración
    with st.sidebar:
        st.title("Código Humano AI") 
        st.subheader("Personalidad de IA")
        
        # 🌟 CORRECCIÓN DE SESSION STATE: No asignamos directamente el return al state
        st.text_input("🤖 Nombre personalizado", value=st.session_state.bot_name, key="bot_name_session") 
        st.session_state.bot_name = st.session_state.bot_name_session 
        
        st.selectbox("🧑 Género", ["Masculino", "Femenino", "No binario"], key="genero_select", index=1 if st.session_state.get('genero_select')=='Femenino' else 0)
        st.selectbox("🎙️ Voz", ["Femenino (España)", "Masculino (México)"], key="sexo_select", index=0 if st.session_state.get('sexo_select')=='Femenino (España)' else 1)
        st.selectbox("🎂 Edad percibida", ["Adulto Joven", "Maduro"], key="edad_select", index=0)
        
        st.markdown("##### 🌟 Rol/Ejemplo de Conversación")
        st.session_state.rol_temporal = st.text_area(
            "Rol", value=st.session_state.get('rol_temporal', ''),
            placeholder="Ej: 'Hoy eres mi profesor de guitarra'.", height=80, label_visibility="collapsed"
        )
            
        st.session_state.audio_on = st.checkbox("🎧 Reproducción Automática", value=st.session_state.audio_on)
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    st.title(f"💬 Chatea con {st.session_state.bot_name}")
    
    # Mostrar Historial
    display_messages = st.session_state.messages[-7:]
    for msg in display_messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    # D. Captura de Inputs (Sin st.form para evitar errores de submit button)
    st.markdown("</div>", unsafe_allow_html=True) 
    
    col1, col2 = st.columns([0.5, 7.5]) 
            
    with col1: 
        mic_data = mic_recorder(start_prompt="🎤", stop_prompt="⏸️", key="mic_input_component_final")
        mic_transcription = mic_data.get('text', '') if mic_data and 'text' in mic_data else ''

    with col2: 
        prompt = st.text_input("Escribe tu mensaje...", key="prompt_input_text", label_visibility="collapsed") 

    # E. Procesamiento del Mensaje
    prompt_to_process = prompt or mic_transcription or ""
    
    if prompt_to_process:
        
        # 1. Construcción del Prompt
        contexto_previo = memoria.recuperar(st.session_state.user_name, prompt_to_process, k=5)
        
        rol_instruction = ""
        if st.session_state.rol_temporal:
            rol_instruction = f"INSTRUCCIÓN DE ROL: Recuerda al modelo que simule el rol: '{st.session_state.rol_temporal}'."

        full_prompt = f"""
[CONTEXTO RAG]: {contexto_previo}
[ROL]: {rol_instruction}
[MENSAJE USUARIO]: {prompt_to_process}
"""
        
        # 2. UI Updates
        st.session_state.messages.append({"role": "user", "content": prompt_to_process})
        
        # 3. Generar Respuesta
        with st.chat_message("model", avatar="🤖"):
            with st.spinner(f"{st.session_state.bot_name} está pensando..."):
                try:
                    response = st.session_state.chat_session.send_message(full_prompt)
                    respuesta_texto = response.text
                    st.markdown(respuesta_texto)
                    
                    # 4. Guardar Memoria y Logs
                    memoria.guardar(st.session_state.user_name, st.session_state.clave_personal, prompt_to_process, respuesta_texto)
                    GestorBitacora.registrar(st.session_state.user_name, "Usuario", prompt_to_process)
                    GestorBitacora.registrar(st.session_state.user_name, "IA", respuesta_texto)

                    # 5. Audio
                    force_audio = st.session_state.audio_on or (mic_transcription != "")
                    if force_audio:
                        GestorAudio.generar_y_reproducir(respuesta_texto, st.session_state.sexo_select)

                    st.session_state.messages.append({"role": "model", "content": respuesta_texto})
                    
                    # Limpiar input
                    st.session_state.prompt_input_text = ""
                    
                except Exception as e:
                    st.error(f"Error generando respuesta: {e}. Intenta reiniciar el chat.")
                    logger.error(f"Error Generación: {e}")
        
        # Streamlit hará rerun automático al actualizar session_state

    # F. Footer Legal
    st.markdown("""
        <style>
            .footer-link {
                position: fixed; bottom: 5px; left: 50%; 
                transform: translateX(-50%); font-size: 0.7em; 
                color: #94A3B8; cursor: pointer;
            }
        </style>
    """, unsafe_allow_html=True)
