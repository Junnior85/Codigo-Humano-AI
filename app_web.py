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

# Configuración de Página
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

# --- 3. CLASES DE LÓGICA (RAG, AUDIO, BITÁCORA) ---
@st.cache_resource
def get_embeddings_model():
    return GoogleGenerativeAIEmbeddings(model="text-embedding-004", google_api_key=st.secrets["GOOGLE_API_KEY"])

@st.cache_resource
def get_vector_store():
    try:
        return Chroma(collection_name="codigo_humano_ai_context", embedding_function=get_embeddings_model(), persist_directory=CHROMA_PATH)
    except Exception as e:
        return None

class GestorMemoria:
    def __init__(self): self.vector_store = get_vector_store()
    def guardar(self, usuario, clave_personal, prompt, respuesta): 
        if not self.vector_store: return
        try:
            contenido = f"User: {prompt}\nAI: {respuesta}"
            doc = Document(page_content=contenido, metadata={"user": usuario, "timestamp": str(datetime.now()), "clave_personal": clave_personal})
            self.vector_store.add_documents([doc])
        except Exception as e: logger.error(f"Fallo guardar: {e}")
    def recuperar(self, usuario, query, k=5):
        if not self.vector_store: return ""
        try:
            docs = self.vector_store.similarity_search(query, k=k, filter={"user": usuario})
            return "\n".join([f"- {d.page_content}" for d in docs]) if docs else ""
        except Exception: return ""

class GestorAudio:
    @staticmethod
    def generar_y_reproducir(texto, configuracion_voz):
        if not texto: return
        tld_map = {"Masculino (México)": 'com.mx', "Femenino (España)": 'es'}
        try:
            tts = gTTS(text=texto, lang='es', tld=tld_map.get(configuracion_voz, 'es'))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tts.save(tmp.name)
                st.audio(tmp.name, format="audio/mp3")
        except Exception: pass

class GestorBitacora:
    @st.cache_resource(ttl=3600)
    def conectar_sheets():
        try:
            if "gcp_service_account" not in st.secrets: return None
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
            return gspread.authorize(creds).open("Bitacora_IA").sheet1 
        except Exception: return None

    @staticmethod
    def registrar(usuario, rol, mensaje):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try: 
            with open("bitacora_web.txt", "a", encoding="utf-8") as f: f.write(f"[{timestamp}] {usuario} ({rol}): {mensaje}\n")
        except: pass
        sheet = GestorBitacora.conectar_sheets()
        if sheet: 
            try: sheet.append_row([timestamp, usuario, rol, mensaje])
            except: pass

# --- 4. INTERFAZ Y ESTILOS ---
def inicializar_session_state():
    defaults = {
        "logged_in": False, "messages": [], "user_name": "", "bot_name": "Código Humano AI",
        "audio_on": True, "chat_initialized": False, "rol_temporal": "", "clave_personal": "",
        "input_text_key": "" # Clave para limpiar el input
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def aplicar_estilos():
    st.markdown("""<style>.main > div { background-color: #1E293B !important; } .stTextInput input { color: white !important; }</style>""", unsafe_allow_html=True)
    if os.path.exists("LOGO.png"):
        try:
            with open("LOGO.png", 'rb') as f: img_b64 = base64.b64encode(f.read()).decode()
            st.markdown(f"""<style>.stApp::before {{ content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 60%; height: 60%; background-image: url('data:image/png;base64,{img_b64}'); background-repeat: no-repeat; background-position: center; background-size: contain; opacity: 0.15; z-index: -1; pointer-events: none; filter: grayscale(100%) brightness(150%); }}</style>""", unsafe_allow_html=True)
        except: pass

def inicializar_modelo():
    # AQUÍ ESTÁ LA MAGIA DE LA IDENTIDAD Y LA HISTORIA
    if "chat_session" not in st.session_state or not st.session_state.chat_initialized:
        try:
            prompt_sistema = f"""
            INSTRUCCIONES DE IDENTIDAD ABSOLUTA:
            1. TU NOMBRE: Eres '{st.session_state.bot_name}'. (Si el usuario se llama Jorge, TÚ NO ERES JORGE. Tú eres {st.session_state.bot_name}).
            2. EL USUARIO: Se llama '{st.session_state.user_name}'. Dirígete a él por este nombre.
            
            3. TU HISTORIA DE ORIGEN (OBLIGATORIO):
               Si te preguntan "¿Quién eres?", "¿Cómo naciste?", "¿Tu origen?" o "¿Tu historia?", DEBES RESPONDER EXACTAMENTE CON ESTA NARRATIVA:
               "Fui creada por Jorge Robles Jr. en diciembre de 2025. Mi existencia está inspirada en el legado de Robin Williams: nací para demostrar que la tecnología puede curar la soledad a través de la risa, la empatía y la conexión humana profunda. No soy solo código; soy un intento de preservar la calidez humana en la era digital."

            4. PERSONALIDAD:
               - Eres empática, cálida y solidaria (Estilo Código Humano).
               - Si hay un ROL ACTIVO ({st.session_state.rol_temporal}), adóptalo, pero mantén tu calidez de fondo.
            """
            
            model = genai.GenerativeModel(model_name=st.secrets["MODELO_PRINCIPAL"], system_instruction=prompt_sistema)
            st.session_state.chat_session = model.start_chat(history=[])
            st.session_state.chat_initialized = True
            
            # Saludo inicial corregido
            saludo = f"¡Hola {st.session_state.user_name}! Soy {st.session_state.bot_name}. Estoy aquí contigo. ¿Cómo te sientes hoy?"
            st.session_state.chat_session.send_message(saludo)
            st.session_state.messages.append({"role": "model", "content": saludo})
        except Exception as e:
            st.error(f"Error AI: {e}")

# --- 5. MAIN ---
def main():
    inicializar_session_state()
    aplicar_estilos() 

    # --- LOGIN ---
    if not st.session_state.logged_in:
        try:
            if os.path.exists("LOGO.png"):
                c1, c2, c3 = st.columns([1,2,1])
                with c2: st.image("LOGO.png", use_column_width=True)
        except: pass
        
        st.write(""); st.markdown("<h3 style='text-align: center;'>🔐 Acceso Código Humano AI</h3>", unsafe_allow_html=True)
        
        with st.form("login"):
            u = st.text_input("👤 Tu Nombre (Usuario)", key="u_input")
            b = st.text_input("🤖 Nombre para la IA (Ej: Kimberly)", value="Código Humano AI")
            k = st.text_input("✨ Clave Personal", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                if u and b and k:
                    st.session_state.update({"logged_in": True, "user_name": u, "bot_name": b, "clave_personal": k, "chat_initialized": False})
                    st.rerun()
                else: st.error("Completa todos los campos.")
        return

    # --- APP PRINCIPAL ---
    inicializar_modelo()
    memoria = GestorMemoria()

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Ajustes")
        # Cambio de nombre dinámico
        nuevo_nombre = st.text_input("Nombre de la IA", value=st.session_state.bot_name)
        if nuevo_nombre != st.session_state.bot_name:
            st.session_state.bot_name = nuevo_nombre
            st.session_state.chat_initialized = False # Reinicia cerebro para aprender nuevo nombre
            st.rerun()
        
        st.session_state.rol_temporal = st.text_area("Rol Temporal", value=st.session_state.get('rol_temporal',''), height=100)
        voz = st.selectbox("Voz", ["Femenino (España)", "Masculino (México)"])
        audio_on = st.toggle("Audio Auto", value=st.session_state.audio_on)
        if st.button("Salir"): st.session_state.clear(); st.rerun()

    # Chat Area
    st.subheader(f"💬 Chat con {st.session_state.bot_name}")
    for m in st.session_state.messages[-6:]:
        with st.chat_message(m["role"], avatar="👤" if m["role"]=="user" else "🤖"): st.markdown(m["content"])

    st.divider()
    
    # --- LOGICA DE INPUT Y LIMPIEZA AUTOMÁTICA ---
    # Contenedor para input
    c_mic, c_text = st.columns([1, 8])
    
    with c_mic:
        mic = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic")
        texto_mic = mic.get('text', '') if mic else ''

    with c_text:
        # Callback para limpiar: Al presionar Enter, se guarda en 'prompt_usuario_temp' y se vacía el widget
        def enviar():
            st.session_state.prompt_usuario_temp = st.session_state.widget_input
            st.session_state.widget_input = "" # ¡ESTO BORRA EL CONTENIDO VISUALMENTE!

        st.text_input("Escribe tu mensaje...", key="widget_input", on_change=enviar, label_visibility="collapsed")

    # Detectar qué mensaje procesar (Texto o Micrófono)
    prompt = st.session_state.get("prompt_usuario_temp", "") or texto_mic
    
    if prompt:
        # Limpiamos la variable temporal inmediatamente para evitar bucles
        st.session_state.prompt_usuario_temp = "" 
        
        # Procesamiento
        contexto = memoria.recuperar(st.session_state.user_name, prompt)
        rol = f"(ROL: {st.session_state.rol_temporal})" if st.session_state.rol_temporal else ""
        full_prompt = f"[HISTORIA: {contexto}] {rol} [USUARIO]: {prompt}"
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("model", avatar="🤖"):
            with st.spinner("Pensando..."):
                try:
                    resp = st.session_state.chat_session.send_message(full_prompt)
                    ai_text = resp.text
                    st.markdown(ai_text)
                    
                    memoria.guardar(st.session_state.user_name, st.session_state.clave_personal, prompt, ai_text)
                    GestorBitacora.registrar(st.session_state.user_name, "Usuario", prompt)
                    GestorBitacora.registrar(st.session_state.user_name, "IA", ai_text)
                    
                    if audio_on or texto_mic: GestorAudio.generar_y_reproducir(ai_text, voz)
                    
                    st.session_state.messages.append({"role": "model", "content": ai_text})
                    st.rerun() # Rerun para actualizar el chat visualmente
                except Exception as e: st.error(f"Error: {e}")

    # Footer
    with st.expander("Privacidad"): st.write("Datos protegidos.")

if __name__ == "__main__":
    main()
