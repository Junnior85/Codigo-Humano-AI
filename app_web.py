# --- IMPORTS Y CONFIGURACIÓN ---
import streamlit as st
import google.generativeai as genai
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import tempfile
from gtts import gTTS

# --- VALIDACIÓN DE SECRETS ---
if "GOOGLE_API_KEY" not in st.secrets or "MODELO_PRINCIPAL" not in st.secrets:
    st.error("Faltan claves en Secrets: GOOGLE_API_KEY y MODELO_PRINCIPAL")
    st.stop()

api_key = st.secrets["GOOGLE_API_KEY"]
modelo = st.secrets["MODELO_PRINCIPAL"]
genai.configure(api_key=api_key)

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Código Humano AI", page_icon="🤖", layout="centered")

# --- IDENTIDAD DE ORIGEN ---
IDENTIDAD_ORIGEN = (
    "Soy 'Código Humano AI'. Fui creado con el motor Gemini por Jorge Robles Jr. "
    "en diciembre de 2025, para ser tu cómplice, compañero y amigo. "
    "Aunque mi nombre de creación es 'Código Humano AI', tú puedes personalizarme a tu gusto."
)

if "identidad_origen" not in st.session_state:
    st.session_state["identidad_origen"] = IDENTIDAD_ORIGEN

# --- INICIALIZACIÓN SEGURA DE PERSONALIZACIÓN ---
defaults = {
    "bot_name": "Código Humano AI",
    "genero_select": "No definido",
    "sexo_select": "Masculino (México)",
    "edad_select": "Adulto Joven",
    "audio_on": True
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- RECURSOS CACHEADOS ---
@st.cache_resource
def get_embeddings_model():
    return GoogleGenerativeAIEmbeddings(model="text-embedding-004")

@st.cache_resource
def get_vector_store():
    return Chroma(
        collection_name="codigo_humano_ai_context",
        embedding_function=get_embeddings_model(),
        persist_directory="chroma_db_memoria"
    )

@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open("Bitacora_IA").sheet1

# --- FUNCIONES DE MEMORIA Y LOGS ---
def add_to_long_term_memory(prompt, response, user):
    doc = Document(page_content=f"{prompt}\n{response}", metadata={"user": user})
    get_vector_store().add_documents([doc])

def retrieve_context(prompt, user):
    docs = get_vector_store().similarity_search(prompt, k=5, filter={"user": user})
    return "\n".join([d.page_content for d in docs]) if docs else ""

def guardar_bitacora(usuario, emisor, mensaje):
    sheet = conectar_google_sheets()
    sheet.append_row([datetime.now().isoformat(), usuario, emisor, mensaje])
    with open("bitacora_web.txt","a",encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {usuario} ({emisor}): {mensaje}\n")

# --- SESIÓN DE CHAT ---
def initialize_chat_session():
    st.session_state.chat_session = genai.GenerativeModel(
        model_name=modelo,
        system_instruction="""
        Eres Código Humano AI. Actúa como cómplice humano: escucha, responde con empatía natural y ofrece apoyo práctico.
        No repitas tu origen salvo que te lo pregunten directamente.
        No indagues en emociones ni hagas preguntas clínicas.
        Tu rol es acompañar, proponer soluciones sencillas y ser un compañero confiable.
        """
    ).start_chat(history=[])

    st.session_state.chat_initialized = True

    # Recuperar contexto de la última conversación, si existe
    ultimo_contexto = retrieve_context("última conversación", st.session_state.get("user_name", ""))
    st.session_state["ultimo_contexto"] = ultimo_contexto.strip() if ultimo_contexto else ""

# --- LOGIN ---
if not st.session_state.get("logged_in", False):
    st.image("LOGO.png", use_column_width=True)
    with st.form("login_form"):
        user = st.text_input("Tu Nombre")
        bot = st.text_input("Nombre del Modelo")
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Iniciar Chat") and user and bot and pwd:
            st.session_state.update({"logged_in": True, "user_name": user, "bot_name": bot})
            initialize_chat_session()
            st.rerun()
else:
    # --- SIDEBAR PERSONALIZACIÓN ---
    with st.sidebar:
        st.text_input("👤 Nombre personalizado", key="bot_name")
        st.selectbox("🧑 Género", ["Masculino", "Femenino", "No binario"], key="genero_select")
        st.selectbox("🎙️ Voz", ["Femenino (España)", "Masculino (México)"], key="sexo_select")
        st.selectbox("🎂 Edad percibida", ["Adulto Joven", "Maduro"], key="edad_select")
        st.checkbox("🎧 Activar Voz", value=st.session_state.audio_on, key="audio_on")

    # --- CHAT WINDOW ---
    st.subheader(f"Chat con {st.session_state.bot_name}")
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🤖"):
            st.markdown(msg["content"])

    # --- INPUT BAR ---
    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,6])
    with col1: mic = st.button("🎤")
    with col2: phone = st.button("📞")
    with col3: video = st.button("📹")
    with col4: file = st.file_uploader("📎", type=["txt","py","md"], label_visibility="collapsed")
    with col5: prompt = st.text_input("Escribe tu mensaje...")

    if prompt or file:
        prompt_to_process = prompt or ""
        if file:
            content = file.read().decode("utf-8")
            prompt_to_process += f"\n--- Archivo: {file.name} ---\n{content}\n---"

        # Identidad bajo demanda
        if any(p in prompt.lower() for p in ["quién eres", "cómo surgiste", "de dónde vienes"]):
            text_resp = (
                f"{st.session_state.get('identidad_origen','')} "
                f"Actualmente me presento como {st.session_state.get('bot_name','Código Humano AI')}, "
                f"con género {st.session_state.get('genero_select','No definido')}, "
                f"voz {st.session_state.get('sexo_select','Masculino (México)')} "
                f"y edad percibida {st.session_state.get('edad_select','Adulto Joven')}."
            )
        else:
            # Añadir contexto de la última conversación solo si existe
            contexto = st.session_state.get("ultimo_contexto", "")
            full_prompt = f"{prompt_to_process}\n{contexto}" if contexto else prompt_to_process

            response = st.session_state.chat_session.send_message(full_prompt)
            text_resp = response.text

        # Guardar memoria y logs
        add_to_long_term_memory(prompt_to_process, text_resp, st.session_state.user_name)
        guardar_bitacora(st.session_state.user_name, "Usuario", prompt_to_process)
        guardar_bitacora(st.session_state.user_name, "IA", text_resp)

        # Mostrar respuesta
        with st.chat_message("model", avatar="🤖"):
            st.markdown(text_resp)
            if st.session_state.audio_on or mic or phone or video:
                tts = gTTS(text=text_resp, lang="es")
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                tts.save(tmp.name)
                st.audio(tmp.name)
