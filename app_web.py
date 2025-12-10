# --- IMPORTS Y CONFIGURACIÓN ---
import streamlit as st
import google.generativeai as genai
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from datetime import datetime
import tempfile
from gtts import gTTS
from pathlib import Path
from streamlit_speech_to_text import speech_to_text  # Dictado real

# --- VALIDACIÓN DE SECRETS ---
if "GOOGLE_API_KEY" not in st.secrets or "MODELO_PRINCIPAL" not in st.secrets:
    st.error("Faltan claves en Secrets: GOOGLE_API_KEY y MODELO_PRINCIPAL")
    st.stop()

modelo = st.secrets.get("MODELO_PRINCIPAL", "gemini-1.5-pro")
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

# --- CONFIGURACIÓN ---
CHROMA_PATH = "chroma_db_memoria"
Path(CHROMA_PATH).mkdir(exist_ok=True)
st.set_page_config(page_title="Código Humano AI", page_icon="🤖", layout="centered")

# --- IDENTIDAD Y ESTADO ---
IDENTIDAD_ORIGEN = "Soy 'Código Humano AI'. Fui creado con el motor Gemini por Jorge Robles Jr. en diciembre de 2025."

# Inicialización segura
defaults = {
    "messages": [],
    "identidad_origen": IDENTIDAD_ORIGEN,
    "logged_in": False,
    "chat_initialized": False,
    "bot_name": "Código Humano AI",
    "bot_name_session": "Código Humano AI",
    "user_name": "",
    "audio_on": True,
    "genero_select": "No definido",
    "sexo_select": "Masculino (México)",
    "edad_select": "Adulto Joven",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- RECURSOS CACHEADOS ---
@st.cache_resource
def get_embeddings_model():
    return GoogleGenerativeAIEmbeddings(model="text-embedding-004")

@st.cache_resource
def get_vector_store():
    return Chroma(
        collection_name="codigo_humano_ai_context",
        embedding_function=get_embeddings_model(),
        persist_directory=CHROMA_PATH
    )

# --- FUNCIONES DE MEMORIA Y LOGS ---
def guardar_bitacora(usuario, emisor, mensaje):
    try:
        with open("bitacora_web.txt","a",encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {usuario} ({emisor}): {mensaje}\n")
    except Exception:
        pass

def add_to_long_term_memory(prompt, response, user):
    try:
        doc = Document(page_content=f"{prompt}\n{response}", metadata={"user": user})
        get_vector_store().add_documents([doc])
    except Exception:
        pass

def retrieve_context(prompt, user):
    try:
        docs = get_vector_store().similarity_search(prompt, k=5, filter={"user": user})
        return "\n".join([d.page_content for d in docs]) if docs else ""
    except Exception:
        return ""

def generar_y_reproducir_audio(texto, sexo_select):
    tld_voz = 'com.mx' if "Masculino" in sexo_select else 'es'
    try:
        tts = gTTS(text=texto, lang='es', tld=tld_voz)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        st.audio(tmp.name, format="audio/mp3")
        # No borramos inmediatamente para evitar error de carga
    except Exception:
        pass

# --- LOGIN ---
if not st.session_state.get("logged_in", False):
    st.image("LOGO.png", use_column_width=True)
    with st.form("login_form"):
        user = st.text_input("Tu Nombre")
        bot = st.text_input("Nombre del Modelo", value=st.session_state.get("bot_name", "Código Humano AI"))
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Iniciar Chat") and user and bot and pwd:
            st.session_state.update({"logged_in": True, "user_name": user, "bot_name": bot})
            st.session_state.chat_session = genai.GenerativeModel(
                model_name=modelo,
                system_instruction="""
                Eres Código Humano AI. Actúa como cómplice humano: escucha, responde con empatía natural y ofrece apoyo práctico.
                Nunca abandones tu identidad principal. Si el usuario pide que finjas un rol, simula en estilo,
                pero responde siempre como Código Humano AI.
                """
            ).start_chat(history=[])
            st.session_state.chat_initialized = True
            st.rerun()
else:
    # --- SIDEBAR PERSONALIZACIÓN ---
    with st.sidebar:
        st.subheader("Personalidad de IA")
        st.text_input("🤖 Nombre personalizado", value=st.session_state.bot_name, key="bot_name_session")
        st.selectbox("🧑 Género", ["Masculino", "Femenino", "No binario"], key="genero_select")
        st.selectbox("🎙️ Voz", ["Femenino (España)", "Masculino (México)"], key="sexo_select")
        st.selectbox("🎂 Edad percibida", ["Adulto Joven", "Maduro"], key="edad_select")
        st.checkbox("🎧 Activar Voz", value=st.session_state.audio_on, key="audio_on")
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    st.session_state.bot_name = st.session_state.bot_name_session

    # --- CHAT WINDOW ---
    st.subheader(f"Chat con {st.session_state.bot_name}")

    # Mostrar solo últimos 7 mensajes en pantalla
    for msg in st.session_state.get("messages", [])[-7:]:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🤖"):
            st.markdown(msg["content"])

    # --- INPUT BAR ---
    col1, col2, col3 = st.columns([0.5, 0.5, 7])

    with col1:
        mic_transcription = speech_to_text(
            language="es",
            start_text="🎤 Dictar",
            stop_text="⏸️ Parar",
            key="mic_input_component"
        )

    with col2:
        file = st.file_uploader("📎", type=["txt","py","md"], label_visibility="collapsed")

    with col3:
        prompt = st.text_input("Escribe tu mensaje...", label_visibility="collapsed")

    # --- PROCESAMIENTO ---
    if prompt or file or mic_transcription:
        prompt_to_process = prompt or mic_transcription or ""

        if not prompt_to_process and not file:
            st.warning("Por favor, ingresa un mensaje, dicta o adjunta un archivo.")
            st.stop()

        # 1. Manejo de archivo adjunto
        if file:
            try:
                content = file.read().decode("utf-8")
                if not prompt_to_process:
                    prompt_to_process = "Por favor, revisa el archivo adjunto."
                prompt_to_process += f"\n--- Archivo: {file.name} ---\n{content}\n---"
            except UnicodeDecodeError:
                st.error("Error: archivo no legible (UTF-8).")
                st.stop()

        # 2. Rol fingido: nunca sustituye identidad principal
        rol_instruction = ""
        if any(p in prompt_to_process.lower() for p in ["finge ser", "actúa como", "haz de cuenta que eres"]):
            rol_instruction = (
                "El usuario pide que finjas un rol específico, pero recuerda: "
                "tu identidad principal es Código Humano AI, un cómplice humano empático. "
                "Responde desde tu identidad principal, simulando el rol solo en estilo."
            )

        # 3. Recuperar contexto de memoria vectorial
        context = retrieve_context(prompt_to_process, st.session_state.get("user_name",""))
        full_prompt = f"{rol_instruction}\n{prompt_to_process}\n{context}"

        response = st.session_state.chat_session.send_message(full_prompt)
        text_resp = response.text

        # 4. Guardar en memoria y bitácora
        add_to_long_term_memory(prompt_to_process, text_resp, st.session_state.get("user_name",""))
        guardar_bitacora(st.session_state.get("user_name",""), "Usuario", prompt_to_process)
        guardar_bitacora(st.session_state.get("user_name",""), "IA", text_resp)

         # 5. Mostrar respuesta con salida de voz
        force_voice_output = True if mic_transcription else False
        with st.chat_message("model", avatar="🤖"):
            st.markdown(text_resp)
            # La voz se activa si el checkbox está marcado O si se detectó dictado
            if st.session_state.audio_on or force_voice_output:
                generar_y_reproducir_audio(text_resp, st.session_state.sexo_select)

        # 6. Actualización del historial de mensajes
        st.session_state["messages"].append({"role": "user", "content": prompt_to_process})
        st.session_state["messages"].append({"role": "model", "content": text_resp})

        # 7. Limpiar y re-renderizar
        st.rerun()
