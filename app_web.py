import streamlit as st
import datetime
import os
import google.generativeai as genai
from gtts import gTTS
import tempfile

# 1. Configuración de la Página
st.set_page_config(page_title="Terminal Personal", page_icon="📓", layout="centered")

# 2. Configuración de Seguridad (API KEY)
# Esta lógica busca la llave en los Secrets de Streamlit (Nube)
# Si no la encuentra, intenta buscarla en el entorno local (por si lo corres en tu PC)

api_key = None

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    # Fallback para local: intenta cargar .env solo si existe
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
    except ImportError:
        pass

# Configurar Gemini si hay llave
if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        st.error(f"Error al configurar la IA: {e}")
        model = None
else:
    model = None

# --- FUNCIONES AUXILIARES ---

def guardar_bitacora(texto):
    """
    NOTA IMPORTANTE PARA STREAMLIT CLOUD:
    Los archivos de texto (.txt) en Streamlit Cloud son 'efímeros'.
    Si la app se reinicia (lo hace una vez al día aprox), este archivo se borra.
    Para persistencia real a largo plazo, en el futuro necesitaremos una Base de Datos externa.
    """
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("bitacora_web.txt", "a", encoding="utf-8") as f:
        f.write(f"[{fecha}] {texto}\n")

def texto_a_audio(texto):
    """Convierte la respuesta de la IA a audio"""
    try:
        tts = gTTS(text=texto, lang='es')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"Error generando audio: {e}")
        return None

# --- INTERFAZ GRÁFICA ---

st.title("SISTEMA DE REGISTRO v3.0")
st.markdown("---")

if not api_key:
    st.warning("⚠️ No se detectó la API Key. Configura 'GOOGLE_API_KEY' en los Secrets de Streamlit.")

tab1, tab2, tab3 = st.tabs(["💾 Bitácora", "🔥 Modo Volátil", "🤖 Compañero"])

# --- TAB 1: BITÁCORA ---
with tab1:
    st.header("Archivo Permanente")
    st.caption("Registro de eventos.")
    
    entrada = st.text_area("Escribe tu día:", height=150, key="input_bitacora")
    
    if st.button("Guardar en Disco", type="primary"):
        if entrada:
            guardar_bitacora(entrada)
            st.success("✅ Entrada registrada localmente.")
        else:
            st.warning("El campo está vacío.")

    with st.expander("Ver Historial de Sesión"):
        if os.path.exists("bitacora_web.txt"):
            with open("bitacora_web.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    st.text(line.strip())
        else:
            st.info("No hay registros en esta sesión.")

# --- TAB 2: MODO VOLÁTIL ---
with tab2:
    st.header("Buffer Temporal (RAM)")
    st.caption("Escribe para soltar. Los datos serán eliminados.")
    
    desahogo = st.text_area("Zona de descarga mental:", height=150, key="input_volatil")
    
    if st.button("Liberar y Borrar", type="secondary"):
        if desahogo:
            st.info("Procesando datos...")
            st.empty() 
            st.error("🗑️ Datos eliminados permanentemente.")
            # Botón manual para reiniciar y limpiar visualmente
            if st.button("Reiniciar Terminal"):
                st.rerun()

# --- TAB 3: COMPAÑERO ---
with tab3:
    st.header("Interfaz de Asistencia")
    st.caption("Sistema de escucha activa.")
    
    consulta = st.text_input("Mensaje de entrada:", key="input_ai")
    
    if st.button("Transmitir"):
        if not model:
            st.error("⚠️ Sistema de IA no disponible (Falta API Key).")
        elif consulta:
            with st.spinner("Procesando respuesta..."):
                prompt_sistema = f"""
                Actúa como un compañero empático, leal y paciente. 
                El usuario dice: "{consulta}".
                Responde de forma corta, cálida y validadora. 
                No des soluciones a menos que se pidan. Sé humano.
                """
                try:
                    response = model.generate_content(prompt_sistema)
                    respuesta_ai = response.text
                    
                    st.success(respuesta_ai)
                    
                    audio_file = texto_a_audio(respuesta_ai)
                    if audio_file:
                        st.audio(audio_file, format="audio/mp3")
                except Exception as e:
                    st.error(f"Error de conexión con la IA: {e}")
