import streamlit as st
import datetime
import os
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
import tempfile

# 1. Configuración Inicial
load_dotenv() # Carga las contraseñas del archivo .env
st.set_page_config(page_title="Terminal Personal", page_icon="📓", layout="centered")

# Configurar la IA (Google Gemini)
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

# --- FUNCIONES AUXILIARES ---

def guardar_bitacora(texto):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("bitacora_web.txt", "a", encoding="utf-8") as f:
        f.write(f"[{fecha}] {texto}\n")

def texto_a_audio(texto):
    """Convierte la respuesta de la IA a audio (voz amigable)"""
    tts = gTTS(text=texto, lang='es')
    # Guardamos en un archivo temporal para reproducirlo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        return fp.name

# --- INTERFAZ GRÁFICA (Streamlit) ---

st.title("SISTEMA DE REGISTRO v3.0")
st.markdown("---")

# Usamos pestañas para separar las funciones (Privacidad vs Ayuda)
tab1, tab2, tab3 = st.tabs(["💾 Bitácora", "🔥 Modo Volátil", "🤖 Compañero"])

# --- TAB 1: BITÁCORA (El Diario Clásico) ---
with tab1:
    st.header("Archivo Permanente")
    st.caption("Lo que escribas aquí quedará guardado para siempre.")
    
    entrada = st.text_area("Escribe tu día:", height=150, key="input_bitacora")
    
    if st.button("Guardar en Disco", type="primary"):
        if entrada:
            guardar_bitacora(entrada)
            st.success("✅ Entrada registrada en la memoria del sistema.")
        else:
            st.warning("El campo está vacío.")

    # Ver historial
    with st.expander("Ver Historial Reciente"):
        if os.path.exists("bitacora_web.txt"):
            with open("bitacora_web.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    st.text(line.strip())
        else:
            st.info("No hay registros aún.")

# --- TAB 2: MODO VOLÁTIL (El Desahogo) ---
with tab2:
    st.header("Buffer Temporal (RAM)")
    st.caption("Escribe para soltar. Los datos serán eliminados al procesar.")
    
    desahogo = st.text_area("Zona de descarga mental:", height=150, key="input_volatil")
    
    if st.button("Liberar y Borrar", type="secondary"):
        if desahogo:
            st.info("Procesando datos...")
            # Aquí no guardamos nada. Simplemente limpiamos.
            st.empty() 
            st.error("🗑️ Datos eliminados permanentemente del sistema.")
            # Un pequeño truco psicológico: reiniciar la app para borrar visualmente
            st.rerun()

# --- TAB 3: COMPAÑERO (La IA Empática) ---
with tab3:
    st.header("Interfaz de Asistencia")
    st.caption("Si necesitas retroalimentación, el sistema está escuchando.")
    
    consulta = st.text_input("¿Qué tienes en mente?", key="input_ai")
    
    if st.button("Enviar al Asistente"):
        if not model:
            st.error("⚠️ Error: No se detectó la API KEY de Google en el archivo .env")
        elif consulta:
            with st.spinner("Analizando..."):
                # Instrucción para que la IA sea como la "novia perfecta/amigo comprensivo"
                prompt_sistema = f"""
                Actúa como un compañero empático, paciente y comprensivo. 
                El usuario te dice: "{consulta}".
                No des consejos técnicos ni soluciones frías. 
                Responde de forma cálida, valida sus sentimientos y sé breve.
                """
                response = model.generate_content(prompt_sistema)
                respuesta_ai = response.text
                
                st.success(respuesta_ai)
                
                # Generar audio de la respuesta
                audio_file = texto_a_audio(respuesta_ai)
                st.audio(audio_file, format="audio/mp3")
