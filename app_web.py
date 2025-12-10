###############################################################################
# BLOQUE 1: IMPORTACIONES Y CONFIGURACIÓN INICIAL
###############################################################################
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import tempfile

# Configuración de la página debe ser siempre lo primero
st.set_page_config(
    page_title="Asistente IA Web",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

###############################################################################
# BLOQUE 2: GESTIÓN DE SECRETOS Y AUTENTICACIÓN
###############################################################################
def configurar_google_services():
    """
    Conecta con Gemini y Google Sheets usando st.secrets de Streamlit Cloud.
    Retorna: (cliente_sheets, status_ok)
    """
    try:
        # 1. Configurar Gemini AI
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)

        # 2. Configurar Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Convertir secretos TOML a diccionario
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Autenticar
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        return client, True

    except Exception as e:
        st.error(f"❌ Error crítico en credenciales: {e}")
        return None, False

# Inicializamos la conexión al cargar la app
client_sheets, conexion_exitosa = configurar_google_services()

###############################################################################
# BLOQUE 3: FUNCIONES DE LÓGICA (IA, AUDIO, BD)
###############################################################################

def obtener_respuesta_gemini(prompt):
    """Envía el texto a Gemini Pro y retorna la respuesta."""
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en la IA: {e}"

def texto_a_audio(texto):
    """Convierte texto a voz y retorna la ruta del archivo temporal."""
    try:
        tts = gTTS(text=texto, lang='es')
        # Usamos tempfile para evitar problemas de permisos en la nube
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        st.warning(f"No se pudo generar audio: {e}")
        return None

def registrar_en_sheets(prompt, respuesta):
    """Guarda la interacción en la hoja de cálculo."""
    if not conexion_exitosa:
        return # No intentar si no hay conexión
    
    nombre_hoja = "AQUI_PON_EL_NOMBRE_EXACTO_DE_TU_HOJA" # <--- ¡EDITAR ESTO!
    
    try:
        sheet = client_sheets.open(nombre_hoja).sheet1
        sheet.append_row([str(prompt), str(respuesta)])
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ Error: No encuentro la hoja '{nombre_hoja}'.")
    except Exception as e:
        st.error(f"❌ Error al guardar datos: {e}")
    return False

###############################################################################
# BLOQUE 4: INTERFAZ DE USUARIO (MAIN)
###############################################################################

def main():
    # --- Encabezado ---
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=100)
        else:
            st.write("🤖")
    with col_titulo:
        st.title("Asistente Virtual")
        st.caption("Conectado a Gemini AI & Google Sheets")

    st.markdown("---")

    # --- Área de Entrada ---
    st.subheader("¿En qué puedo ayudarte?")
    consulta = st.text_area("Escribe tu pregunta aquí:", height=100)
    
    enviar_btn = st.button("Procesar Consulta", type="primary", use_container_width=True)

    # --- Área de Procesamiento y Salida ---
    if enviar_btn:
        if not consulta:
            st.warning("Por favor escribe algo antes de enviar.")
        else:
            if not conexion_exitosa:
                st.error("No se puede procesar: Falló la conexión con Google.")
                return

            with st.spinner("🧠 Pensando y consultando la base de conocimientos..."):
                # 1. IA
                respuesta = obtener_respuesta_gemini(consulta)
                
                # 2. Mostrar Resultado
                st.success("Respuesta Generada:")
                st.write(respuesta)
                
                # 3. Audio
                audio_path = texto_a_audio(respuesta)
                if audio_path:
                    st.audio(audio_path, format="audio/mp3")
                
                # 4. Guardado
                guardado = registrar_en_sheets(consulta, respuesta)
                if guardado:
                    st.toast("Interacción guardada en la bitácora", icon="✅")

# Ejecutar la aplicación
if __name__ == "__main__":
    main()
