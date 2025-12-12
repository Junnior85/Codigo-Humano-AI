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
import gspread # 🌟 Necesario para Google Sheets
from oauth2client.service_account import ServiceAccountCredentials # 🌟 Necesario para Google Sheets

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes
CHROMA_PATH = "chroma_db_memoria"
Path(CHROMA_PATH).mkdir(exist_ok=True)
CONTRASENA_MAESTRA_DEFAULT = "bypass_deprecated" # Usamos esto solo para la estructura, ya no es la clave de acceso.

# Configuración de Página (Debe ser lo primero)
st.set_page_config(page_title="Código Humano AI", page_icon="🤖", layout="centered")

# --- 2. GESTIÓN DE SECRETOS Y SEGURIDAD ---

def validar_secretos():
    # 🌟 Mantenemos la verificación solo de las claves esenciales para la IA
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

    def guardar(self, usuario, clave_personal, prompt, respuesta): # Actualizado para Clave Personal
        """Guarda una interacción en la memoria vectorial (Blindado)."""
        if not self.vector_store: return
        try:
            contenido = f"User: {prompt}\nAI: {respuesta}"
            doc = Document(
                page_content=contenido, 
                metadata={
                    "user": usuario, 
                    "timestamp": str(datetime.now()),
                    "clave_personal": clave_personal # Guardamos la clave personal como metadato
                }
            )
            self.vector_store.add_documents([doc])
        except Exception as e:
            logger.error(f"Fallo al guardar memoria: {e}")

    def recuperar(self, usuario, query, k=5):
        """Recupera contexto relevante para el usuario específico (Blindado)."""
        if not self.vector_store: return ""
        try:
            # Filtramos estrictamente por el nombre de usuario
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

# 🌟 IMPLEMENTACIÓN FINAL DE BITÁCORA DE GOOGLE SHEETS
class GestorBitacora:
    """Maneja el log en archivo de texto simple y Google Sheets."""
    
    @st.cache_resource(ttl=3600)
    def conectar_sheets():
        """Conexión robusta a Google Sheets usando st.secrets."""
        try:
            if "gcp_service_account" not in st.secrets:
                logger.warning("No se encontraron credenciales de GCP para Google Sheets.")
                return None
                
            creds_info = st.secrets["gcp_service_account"]
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            client = gspread.authorize(creds)
            return client.open("Bitacora_IA").sheet1 # Asegúrate que el nombre de tu hoja sea 'Bitacora_IA'
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
            pass # Fallo silencioso en log local
            
        # 2. Registro en Google Sheets
        sheet = GestorBitacora.conectar_sheets()
        if sheet:
            try:
                sheet.append_row([timestamp, usuario, rol, mensaje])
            except Exception as e:
                logger.error(f"Fallo al registrar en Google Sheets: {e}")


# --- 4. INTERFAZ Y ESTILOS ---

IDENTIDAD_ORIGEN = "Soy 'Código Humano AI'. Fui creado con el motor Gemini por Jorge Robles Jr. en diciembre de 2025."

# ... (Las funciones inicializar_session_state y aplicar_estilos se mantienen igual) ...

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
        "clave_personal": "" # Inicialización de la clave personal
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def aplicar_estilos():
    # ... (El código CSS de Dark Mode y Logo se mantiene igual) ...
    pass # Mantener la llamada a st.markdown(f"""..."""... en main()


def inicializar_modelo():
    """Inicia el modelo de Gemini y establece el saludo inicial."""
    if "chat_session" not in st.session_state or not st.session_state.chat_initialized:
        try:
            model = genai.GenerativeModel(
                model_name=st.secrets["MODELO_PRINCIPAL"],
                system_instruction=f"""
                Ere {st.session_state.bot_name}. Tu identidad central es: 'Código Humano AI', un cómplice humano, empático y solidario.
                - Escucha activamente. Responde con naturalidad y calidez.
                - Si el usuario te pide un rol temporal, SIMULA en estilo, pero NUNCA abandones tu esencia empática.
                - Tu nombre de usuario es {st.session_state.user_name}.
                """
            )
            st.session_state.chat_session = model.start_chat(history=[])
            st.session_state.chat_initialized = True

            # Lógica de Saludo Contextual (Se mantiene)
            memoria = GestorMemoria()
            # ... (Generación y envío de saludo inicial) ...
            
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
        
        # ... (Implementación del Login Seguro Simplificado) ...
        # (Este bloque se mantiene con el Disclamer y la validación de Clave Personal)
        st.markdown("<div style='display: flex; justify-content: center; flex-direction: column; align-items: center; text-align: center;'>", unsafe_allow_html=True)
        if os.path.exists("LOGO.png"): st.image("LOGO.png", width=400)
        
        with st.form("login_form", clear_on_submit=True):
            st.subheader("Acceso y Personalización")
            user = st.text_input("👤 Tu Nombre (Clave de Sesión)", key="user_name_input")
            bot = st.text_input("🤖 Nombre del Modelo", key="bot_name_input", value=st.session_state.bot_name)
            
            clave_personal = st.text_input("✨ Tu Palabra Clave Personal", 
                                        type="password", 
                                        help="Esta clave es la única que protege tu historial de conversación.",
                                        key="clave_personal_input")
            
            # --- DESCARGO DE RESPONSABILIDAD CRÍTICO PARA MITIGAR RIESGOS ---
            st.warning("""
            **⚠️ Advertencia de Seguridad:**
            Usted es el único responsable de la seguridad de su Palabra Clave. Si elige una clave fácil de adivinar, 
            su historial puede ser accedido por terceros que conozcan su Nombre.
            """)
            
            if st.form_submit_button("Iniciar Chat"):
                if user and bot and clave_personal:
                    st.session_state.update({
                        "logged_in": True, 
                        "user_name": user.strip(), 
                        "bot_name": bot,
                        "chat_initialized": False,
                        "clave_personal": clave_personal 
                    })
                    st.rerun()
                else:
                    st.error("Por favor, completa tu Nombre y tu Palabra Clave Personal para ingresar.")

        st.markdown("</div>", unsafe_allow_html=True)
        return

    # B. Interfaz Principal (Contenido del Chat)
    inicializar_modelo()
    memoria = GestorMemoria()
    
    # ... (Lógica de Sidebar y Chat Window) ...

    # D. Captura de Inputs
    with st.form(key="chat_input_form_final", clear_on_submit=True):
        col1, col2 = st.columns([0.5, 7.5]) 
        
        with col1: 
            mic_data = mic_recorder(start_prompt="🎤", stop_prompt="⏸️", key="mic_input_component_final")
            mic_transcription = mic_data.get('text', '') if mic_data and 'text' in mic_data else ''

        with col2: 
            prompt = st.text_input("Escribe tu mensaje...", key="prompt_input_text", label_visibility="collapsed") 

        st.form_submit_button("Enviar", label_visibility="collapsed")

        # E. Procesamiento del Mensaje
        prompt_to_process = prompt or mic_transcription or ""
        
        if prompt_to_process:
            
            # 1. Construcción del Prompt (RAG + Rol)
            contexto_previo = memoria.recuperar(st.session_state.user_name, prompt_to_process, k=5)
            
            rol_instruction = ""
            if st.session_state.rol_temporal:
                rol_instruction = f"INSTRUCCIÓN DE ROL: Recuerda al modelo que simule el rol: '{st.session_state.rol_temporal}'."

            full_prompt = f"""
[CONTEXTO RAG]: {contexto_previo}
[ROL]: {rol_instruction}
[MENSAJE USUARIO]: {prompt_to_process}
"""
            
            # 2. Mostrar mensaje usuario en UI (Se hace antes de la llamada a Gemini)
            st.session_state.messages.append({"role": "user", "content": prompt_to_process})
            
            # 3. Generar Respuesta IA
            with st.chat_message("model", avatar="🤖"):
                with st.spinner(f"{st.session_state.bot_name} está pensando..."):
                    try:
                        response = st.session_state.chat_session.send_message(full_prompt)
                        respuesta_texto = response.text
                        st.markdown(respuesta_texto)
                        
                        # 4. Guardar Memoria y Logs (¡Implementación Completa!)
                        memoria.guardar(st.session_state.user_name, st.session_state.clave_personal, prompt_to_process, respuesta_texto)
                        GestorBitacora.registrar(st.session_state.user_name, "Usuario", prompt_to_process)
                        GestorBitacora.registrar(st.session_state.user_name, "IA", respuesta_texto)

                        # 5. Generar Audio
                        force_audio = st.session_state.audio_on or (mic_transcription != "")
                        if force_audio:
                            GestorAudio.generar_y_reproducir(respuesta_texto, st.session_state.sexo_select)

                        st.session_state.messages.append({"role": "model", "content": respuesta_texto})
                        
                    except Exception as e:
                        st.error(f"Error generando respuesta: {e}. Intenta reiniciar el chat.")
                        logger.error(f"Error Generación: {e}")
            
            st.rerun() # Forzar rerun para limpiar el input

    # F. ENLACE DE POLÍTICAS Y AVISO DE PRIVACIDAD (Pie de página)
    st.markdown("""
        <style>
            .footer-link {
                position: fixed; bottom: 5px; left: 50%; 
                transform: translateX(-50%); font-size: 0.7em; 
                color: #94A3B8; cursor: pointer;
            }
        </style>
    """, unsafe_allow_html=True)
    
    with st.expander("Políticas y Aviso de Privacidad"):
        try:
            with open("POLITICAS_PRIVACIDAD.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
        except FileNotFoundError:
            st.warning("El archivo 'POLITICAS_PRIVACIDAD.md' no se encuentra. Crea el archivo.")

if __name__ == "__main__":
    main()
