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
                
            creds_info = st.secrets["gcp_service_
