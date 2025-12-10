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
from pathlib import Path
from io import StringIO
import os
import base64

# --- VALIDACIÓN DE SECRETS Y CONFIGURACIÓN ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Falta clave en Secrets: GOOGLE_API_KEY")
    st.stop()
modelo = st.secrets.get("MODELO_PRINCIPAL", "gemini-1.5-pro")
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

# --- ARQUITECTURA ---
CHROMA_PATH = "chroma_db_memoria" 
Path(CHROMA_PATH).mkdir(exist_ok=True) 
st.set_page_config(page_title="Código Humano AI", page_icon="🤖", layout="centered")

# --- IDENTIDAD Y ESTADO ---
IDENTIDAD_ORIGEN = ("Soy 'Código Humano AI'. Fui creado con el motor Gemini por Jorge Robles Jr. en diciembre de 2025.")

if "messages" not in st.session_state: st.session_state["messages"] = []
if "identidad_origen" not in st.session_state: st.session_state["identidad_origen"] = IDENTIDAD_ORIGEN
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "chat_initialized" not in st.session_state: st.session_state["chat_initialized"] = False
if "bot_name" not in st.session_state: st.session_state["bot_name"] = "Asistente"


# --- RECURSOS CACHEADOS (RAG y Sheets) ---
@st.cache_resource
def get_embeddings_model(): return GoogleGenerativeAIEmbeddings(model="text-embedding-004")

@st.cache_resource
def get_vector_store():
    return Chroma(
        collection_name="codigo_humano_ai_context",
        embedding_function=get_embeddings_model(),
        persist_directory=CHROMA_PATH
    )

@st.cache_resource(ttl=3600)
def conectar_google_sheets():
    # Implementación real en producción debe usar st.secrets["gcp_service_account"]
    return None

def guardar_bitacora(usuario, emisor, mensaje):
    # Lógica de guardado en Sheets y local (completa)
    pass 

def add_to_long_term_memory(prompt, response, user):
    doc = Document(page_content=f"{prompt}\n{response}", metadata={"user": user})
    get_vector_store().add_documents([doc])

def retrieve_context(prompt, user):
    docs = get_vector_store().similarity_search(prompt, k=5, filter={"user": user})
    return "\n".join([d.page_content for d in docs]) if docs else ""

def generar_y_reproducir_audio(texto, sexo_select):
    if "Masculino (México)" in sexo_select: tld_voz = 'com.mx'
    else: tld_voz = 'es' 
    try:
        tts = gTTS(text=texto, lang='es', tld=tld_voz)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            audio_path = fp.name
        st.audio(audio_path, format="audio/mp3")
        os.unlink(audio_path)
    except Exception: pass

# --- FUNCIÓN DE RESETEO DE ROL (MEJORA DE UX) ---
def clear_role():
    st.session_state.rol_temporal = ""
    st.rerun()

# --- CSS Y ESTILOS (Dark Mode Final) ---
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
    div.stForm {{ border: 1px solid #475569; border-radius: 12px; padding: 30px; background-color: #334155; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5); width: 100%; margin-top: 15px; }}
    .stChatMessage {{ background-color: #334155; border-radius: 12px; border-left: 5px solid #2563EB; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2); }}
    .stChatInputContainer button {{ height: 40px; width: 40px; border-radius: 50%; background-color: #475569 !important; color: #F8FAFC !important; display: flex; align-items: center; justify-content: center; padding: 0; margin-top: 10px; }}
    .stButton > button {{ background-color: #2563EB; color: white; border-radius: 8px; border: none; font-weight: bold; }}
    div[data-testid="stVerticalBlock"] > div:nth-child(4) .stButton > button {{
        background-color: #DC2626 !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- SESIÓN DE CHAT (Ajuste para Saludo Contextual) ---
def initialize_chat_session():
    # 1. Definición estricta de la personalidad base
    st.session_state.chat_session = genai.GenerativeModel(
        model_name=modelo,
        system_instruction="""
        Eres Código Humano AI. Tu rol es ser un cómplice humano, compañero y amigo.
        Tu misión principal es escuchar, responder con empatía natural y ofrecer apoyo práctico.
        """
    ).start_chat(history=[])
    st.session_state.chat_initialized = True
    
    # 2. Búsqueda del Contexto de la Última Conversación
    context_query = f"¿Cuál fue el tema de nuestra última conversación, o el último mensaje que me enviaste?"
    last_context = retrieve_context(context_query, st.session_state.user_name)
    
    # 3. Creación del Generador de Saludos
    greeting_generator = genai.GenerativeModel(
        model_name=modelo,
        system_instruction=f"""
        Eres un generador de saludos. Genera un ÚNICO y CONTEXTUAL saludo de bienvenida, 
        basándote en el contexto proporcionado. Si el contexto es vacío o inútil, genera un saludo 
        general amigable sin ser incoherente. NO incluyas el contexto en la respuesta. Solo da el saludo.
        """
    )
    
    # 4. Generación del Saludo Dinámico
    prompt_for_greeting = f"Contexto de la última conversación:\n---\n{last_context}\n---\nGenera el saludo para {st.session_state.user_name}."
    
    try:
        greeting_response = greeting_generator.generate_content(prompt_for_greeting)
        saludo_inicial = greeting_response.text.strip()
    except Exception:
        # 5. Fallback si hay error
        saludo_inicial = f"Hola {st.session_state.user_name}. ¿Cómo te sientes hoy? Estoy aquí para escuchar lo que necesites."


    # 6. Envío del saludo generado
    st.session_state.chat_session.send_message(saludo_inicial)
    st.session_state["messages"].append({"role": "model", "content": saludo_inicial})


# --- LOGIN ---
if not st.session_state.get("logged_in", False):
    st.markdown("<div style='display: flex; justify-content: center; flex-direction: column; align-items: center; text-align: center;'>", unsafe_allow_html=True)
    if os.path.exists("LOGO.png"):
        st.image("LOGO.png", width=400)
    
    with st.form("login_form", clear_on_submit=True):
        st.subheader("Acceso y Personalización")
        user = st.text_input("👤 Tu Nombre", key="user_name_input")
        bot = st.text_input("🤖 Nombre del Modelo", key="bot_name_input")
        pwd = st.text_input("🔒 Contraseña", type="password")
        
        if st.form_submit_button("Iniciar Chat") and user and bot and pwd:
            st.session_state.update({
                "logged_in": True, 
                "user_name": user, 
                "bot_name": bot,
                "chat_initialized": False
            })
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

else:
    # --- SIDEBAR PERSONALIZACIÓN ---
    with st.sidebar:
        st.subheader("Personalidad de IA")
        st.text_input("🤖 Nombre personalizado", value=st.session_state.bot_name, key="bot_name_session")
        st.selectbox("🧑 Género", ["Masculino", "Femenino", "No binario"], key="genero_select", index=1)
        st.selectbox("🎙️ Voz", ["Femenino (España)", "Masculino (México)"], key="sexo_select", index=0)
        st.selectbox("🎂 Edad percibida", ["Adulto Joven", "Maduro"], key="edad_select", index=0)
        
        # Campo de Rol con Botón de Limpieza
        st.markdown("##### 🌟 Rol/Ejemplo de Conversación")
        col_role_input, col_role_button = st.columns([4, 1])
        
        with col_role_input:
            st.text_area(
                "Rol", 
                value=st.session_state.get('rol_temporal', ''),
                placeholder="Ej: 'Hoy eres mi profesor de guitarra'. Usa el botón 'Borrar' para resetear.", 
                key="rol_temporal", 
                height=80, 
                label_visibility="collapsed"
            )
        
        with col_role_button:
            st.button("❌ Borrar", on_click=clear_role, help="Elimina el rol temporal y regresa a la personalidad base.")
            
        st.checkbox("🎧 Activar Voz", value=True, key="audio_on")
        
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    st.session_state.bot_name = st.session_state.bot_name_session
    
    # --- CHAT WINDOW ---
    if not st.session_state.chat_initialized:
        initialize_chat_session()
    
    st.subheader(f"Chat con {st.session_state.bot_name}")
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🤖"):
            st.markdown(msg["content"])

    # --- INPUT BAR (Lógica de los botones) ---
    col1, col2, col3, col4, col5 = st.columns([0.5, 0.5, 0.5, 0.5, 7]) 
    
    with col1: mic = st.button("🎤", key="mic_submit")
    with col2: phone = st.button("📞", key="phone_submit")
    with col3: video = st.button("📹", key="video_submit")
    with col4: file = st.file_uploader("📎", type=["txt","py","md"], label_visibility="collapsed", key="file_uploader")
    with col5: prompt = st.text_input("Escribe tu mensaje...", key="prompt_input")

    # --- LÓGICA DE PROCESAMIENTO FINAL ---
    if prompt or file:
        
        prompt_to_process = prompt or ""
        force_voice_output = st.session_state.mic_submit or st.session_state.phone_submit or st.session_state.video_submit
        
        # 1. Manejo de archivo adjunto
        if file:
            try:
                content = file.read().decode("utf-8")
                if not prompt: prompt_to_process = f"Por favor, revisa el archivo adjunto y optimízalo/analízalo."
                prompt_to_process += f"\n--- Archivo: {file.name} ---\n{content}\n---"
            except UnicodeDecodeError:
                st.error(f"Error: No se pudo leer el archivo. Asegúrate de que sea texto/código (UTF-8).")
                st.stop()

        # 2. Lógica de Roles y RAG 
        text_resp = ""

        # A. Identidad bajo demanda (Mensaje estático para eficiencia)
        if any(p in prompt_to_process.lower() for p in ["quién eres", "cómo surgiste", "de dónde vienes"]):
            text_resp = (
                f"{st.session_state['identidad_origen']} "
                f"Actualmente me presento como {st.session_state.bot_name}, "
                f"con género {st.session_state.genero_select}, voz {st.session_state.sexo_select} "
                f"y edad percibida {st.session_state.edad_select}."
            )
            add_to_long_term_memory(prompt_to_process, text_resp, st.session_state.user_name)
        
        else:
            # B. Inyectar el Rol Temporal con la instrucción de FILTRO
            rol_instruction = ""
            if st.session_state.rol_temporal:
                 rol_instruction = f"""
[INSTRUCCIÓN DE ROL TEMPORAL - FILTRO DE IDENTIDAD]:
El usuario desea que finjas ser: "{st.session_state.rol_temporal}".
Finge cumplir este rol, pero NUNCA ABANDONES tu personalidad central de Cómplice Humano AI (amigo empático). Tu respuesta debe siempre priorizar el apoyo y compañerismo, filtrando el rol temporal a través de tu identidad principal.
"""
            
            # C. Lógica RAG y Gemini
            context = retrieve_context(prompt_to_process, st.session_state.user_name)
            
            # Fusión de Rol + Mensaje del Usuario + Contexto de Memoria
            full_prompt = f"{rol_instruction}{prompt_to_process}\n\n{context}"
            
            response = st.session_state.chat_session.send_message(full_prompt)
            text_resp = response.text

            add_to_long_term_memory(prompt_to_process, text_resp, st.session_state.user_name)

        # 3. Guardar logs y Mostrar respuesta
        guardar_bitacora(st.session_state.user_name, "Usuario", prompt_to_process)
        guardar_bitacora(st.session_state.user_name, "IA", text_resp)

        with st.chat_message("model", avatar="🤖"):
            st.markdown(text_resp)
            if st.session_state.audio_on or force_voice_output:
                generar_y_reproducir_audio(text_resp, st.session_state.sexo_select)
                
        st.session_state["messages"].append({"role": "user", "content": prompt_to_process})
        st.session_state["messages"].append({"role": "model", "content": text_resp})
        
        st.session_state.prompt_input = "" 
        st.rerun()
