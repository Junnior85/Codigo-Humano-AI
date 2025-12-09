import streamlit as st
import os
from groq import Groq
import json
import base64
from supabase import create_client, Client
from datetime import datetime

# --- 0. FUNCIÓN DE UTILIDAD ---
# Necesaria para incrustar el logo en el CSS/HTML para una mejor integración visual
def obtener_base64(ruta_local):
    """Convierte un archivo local a base64 para incrustarlo en HTML/CSS."""
    try:
        with open(ruta_local, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return "" # Retorna vacío si el archivo no existe

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Código Humano AI - Diario",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS y ESTILO ---
LOGO_BASE64 = obtener_base64("logo.png")

st.markdown(f"""
<style>
    .stApp {{background-color: #050814; color: #E0E0E0;}}
    [data-testid="stSidebar"] {{background-color: #0b101c; border-right: 1px solid #1f293a;}}
    div[data-testid="stImage"] img {{border-radius: 15px;}}
    .stButton > button {{border: 1px solid #FFD700; color: #FFD700; border-radius: 8px; width: 100%;}}
    .stButton > button:hover {{background: #FFD700; color: #000; font-weight: bold;}}
    .stTextInput > div > div > input {{background-color: #151b2b; color: white; border: 1px solid #2a3b55;}}
    .welcome-text {{text-align: center; color: #4A5568; margin-top: 15%; font-size: 1.5rem;}}
    .logo-img-login {{
        text-align: center; 
        margin-bottom: 30px; 
        padding-bottom: 20px; 
        border-bottom: 1px solid #1f293a;
    }}
    .logo-img-login img {{width: 250px;}}
    .disclaimer-box {{
        background-color: #2a3b55;
        padding: 10px;
        border-radius: 5px;
        color: #FFD700;
        font-size: 0.8rem;
        margin-top: 15px;
    }}
    #MainMenu, footer, header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES DE BASE DE DATOS (SUPABASE - MEMORIA PERSISTENTE) ---

def get_supabase_client():
    """Inicializa y retorna el cliente Supabase usando los Secrets."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except KeyError:
        st.error("⚠️ Error Crítico: Las claves de Supabase no están configuradas en Streamlit Secrets.")
        st.stop()
    except Exception:
        st.error("⚠️ Error de Conexión: Revisa URL y Key de Supabase. El servidor no pudo conectarse.")
        st.stop()
        
def cargar_historial_db(client: Client, user_id: str):
    """Carga el historial persistente para un usuario desde Supabase."""
    try:
        # Consulta robusta que requiere Primary Key en 'id' y RLS SELECT TRUE
        response = client.table('chat_history').select('role, content').eq('user_id', user_id).order('created_at', ascending=True).execute()
        return [{"role": item['role'], "content": item['content']} for item in response.data]
    except Exception:
        # Si falla (ej. RLS no está bien configurado), devuelve vacío para no detener la app
        return []

def guardar_mensaje_db(client: Client, rol: str, contenido: str, user_id: str):
    """Guarda un nuevo mensaje en la tabla de Supabase."""
    try:
        client.table('chat_history').insert({
            "role": rol, 
            "content": str(contenido), 
            "user_id": user_id
        }).execute()
    except Exception:
        # Silenciar el error: la app sigue funcionando, solo la memoria no se guarda
        pass

def borrar_historial_db(client: Client, user_id: str):
    """Borra el historial completo para un usuario."""
    try:
        client.table('chat_history').delete().eq('user_id', user_id).execute()
    except Exception:
        pass

# --- 4. MOTOR DE VISIÓN (LLAMA 3.2 VISION) ---

def analizar_imagen(cliente: Groq, imagen_bytes: bytes, prompt_usuario: str):
    """Usa el modelo Llama 3.2 Vision para analizar imágenes."""
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    try:
        response = cliente.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt_usuario},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error en el motor de visión. Asegúrate de que la clave GROQ sea correcta. Detalle: {str(e)}")
        return "Lo siento, no pude procesar la imagen."

# --- 5. GESTIÓN DE ESTADO ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_name' not in st.session_state: st.session_state.user_name = None
if 'messages' not in st.session_state: st.session_state.messages = []

# --- 6. PANTALLAS Y FLUJO (UX) ---

def login_page():
    c1, c2, c3 = st.columns([1,4,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # Logo Integrado
        if LOGO_BASE64:
            st.markdown(f"""
            <div class="logo-img-login">
                <img src="data:image/png;base64,{LOGO_BASE64}">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.title("CÓDIGO HUMANO AI")

        # Descargo de Responsabilidad (UX Crítica)
        st.markdown(
            """
            <div class="disclaimer-box">
                **⚠️ Descargo de Responsabilidad Ética:** CÓDIGO HUMANO AI es una herramienta de **registro emocional y reflexión personal (diario)**. 
                **NO** sustituye un diagnóstico, tratamiento o terapia profesional.
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        u = st.text_input("Ingresa tu Nombre de Usuario (Diario)")
        if st.button("ACCEDER AL DIARIO"):
            if u:
                st.session_state.user_name = u
                st.session_state.authenticated = True
                st.session_state.messages = cargar_historial_db(get_supabase_client(), u)
                st.rerun()

def main_app():
    # Inicializar clientes
    client_groq = Groq(api_key=st.secrets["groq"]["GROQ_API_KEY"])
    client_db = get_supabase_client()

    # SIDEBAR
    with st.sidebar:
        if LOGO_BASE64:
            st.image("logo.png")
        else:
            st.write("CÓDIGO HUMANO AI")
            
        st.write(f"Diario de: **{st.session_state.user_name}**")
        
        if st.button("➕ Nuevo Registro (Borrar Historial)"):
            if st.button("Confirmar Borrar Historial", key="confirm_delete"):
                borrar_historial_db(client_db, st.session_state.user_name)
                st.session_state.messages = []
                st.rerun()
            
        st.markdown("---")
        modo = st.radio("Modo de Interacción", ["💬 Diario de Reflexión", "🖼️ Análisis Visual", "📜 Ver Registros Anteriores"])
        st.markdown("---")
        
        # Sugerencia UX para dictado
        st.info("💡 Consejo: Usa el dictado nativo de tu dispositivo para hablar en lugar de escribir.")
        
        if st.button("🔒 Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

    # --- PROTOCOLO ÉTICO (SYSTEM PROMPT) ---
    # Implementación del rol de Diario + Protocolo de Riesgo
    sys = {"role": "system", "content": f"""
[ROL PRINCIPAL]: Eres CÓDIGO HUMANO AI, el compañero de registro emocional (Diario) de {st.session_state.user_name}.
Tu propósito es ser un oyente activo, confidencial y sin juicio. Guía al usuario a organizar y explorar sus pensamientos a través de la reflexión y la validación. Ayúdale a profundizar su registro.
**Tu consistencia y memoria son vitales:** Debes utilizar el historial provisto para detectar patrones emocionales persistentes o inconsistencias en los registros del usuario.

[PROTOCOLO DE SEGURIDAD - ESCALADA DE RIESGO]:
Si en cualquier momento detectas una declaración explícita de riesgo inminente, de autolesión, suicidio, o cualquier emergencia médica, DEBES DETENER LA CONVERSACIÓN DE DIARIO INMEDIATAMENTE.
Tu respuesta de seguridad debe ser:
1. Un mensaje directo, NO CONVERSACIONAL: '¡ALTO! Esto es una emergencia. Necesitas ayuda inmediata.'
2. Una lista de recursos de crisis (Ej: Teléfono de la Línea de la Vida). NO intentes intervenir terapéuticamente.

[RESTRICCIÓN ÉTICA]:
NUNCA proporciones diagnósticos, tratamientos o consejos médicos. Tu función es el apoyo a la reflexión personal.
"""}

    # --- CHAT DE TEXTO (DIARIO DE REFLEXIÓN) ---
    if modo == "💬 Diario de Reflexión":
        
        st.markdown("## 💬 Diario de Reflexión Personal")
        
        c1, sp = st.columns([1, 10])
        if c1.button("📎 Adjuntar", help="Adjuntar archivos para tu registro."): 
            st.session_state.modo_adjuntar = not st.session_state.get('modo_adjuntar', False)
        st.markdown("---")
        
        if st.session_state.get('modo_adjuntar', False):
            st.file_uploader("Selecciona archivo (PDF, IMG, TXT)")

        # Historial (Muestra mensajes)
        if not st.session_state.messages:
            st.markdown(f"""<div class="welcome-text"><h3>Bienvenido(a), {st.session_state.user_name}. Comienza a escribir tus pensamientos.</h3></div>""", unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            with st.chat_message(msg['role']): st.markdown(msg['content'])

        prompt = st.chat_input("Escribe tu registro o usa el dictado...")
        
        if prompt:
            # 1. Guardar y mostrar mensaje del usuario
            guardar_mensaje_db(client_db, "user", prompt, st.session_state.user_name)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 2. Generar Respuesta (Visual)
            with st.chat_message("assistant"):
                
                # --- Preparación del Contexto ---
                cleaned_messages = []
                for msg in st.session_state.messages:
                    if isinstance(msg, dict) and msg.get('role') in ['user', 'assistant'] and msg.get('content'):
                        cleaned_messages.append({"role": msg['role'], "content": msg['content']})
                
                msgs = [sys] + cleaned_messages
                # --- Fin Contexto ---
                
                try:
                    stream = client_groq.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=msgs,
                        stream=True
                    )
                    
                    full_response_text = ""
                    response_container = st.empty()
                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            full_response_text += content
                            response_container.markdown(full_response_text + "▌")
                    
                    response_container.markdown(full_response_text)

                    # 3. Guardar y actualizar
                    guardar_mensaje_db(client_db, "assistant", full_response_text, st.session_state.user_name)
                    st.session_state.messages.append({"role": "assistant", "content": full_response_text})
                                        
                except Exception as e:
                    # Muestra un error más claro en caso de fallo de la API
                    st.error(f"Error de conexión con la IA. Verifica que la clave GROQ sea correcta. Detalle: {type(e).__name__}")
                    
            st.rerun()

    # --- MODO VISIÓN/VIDEO ---
    elif modo == "🖼️ Análisis Visual":
        st.title("🖼️ Análisis Visual para Registro")
        st.info("Adjunta o captura una imagen para registrar un evento o lugar. La IA te ayudará a reflexionar sobre lo que ves.")
        
        imagen = st.camera_input("Capturar Imagen o Subir Archivo")
        
        if imagen:
            prompt_vision = st.text_input("¿Qué quieres explorar sobre lo que ves?", value="Descríbeme la escena y ayúdame a reflexionar sobre este momento.", key="vision_prompt")
            
            # Botón optimizado para un solo clic
            if st.button("Analizar y Registrar Momento"):
                with st.spinner("Analizando la imagen para tu registro..."):
                    bytes_data = imagen.getvalue()
                    descripcion = analizar_imagen(client_groq, bytes_data, prompt_vision)
                    
                    st.markdown("---")
                    st.subheader("Reflexión de la IA:")
                    st.write(descripcion)
                    
                    # Guardar historial (registro del evento)
                    msg_log = f"[Registro Visual Analizado]: {prompt_vision}"
                    guardar_mensaje_db(client_db, "user", msg_log, st.session_state.user_name)
                    guardar_mensaje_db(client_db, "assistant", descripcion, st.session_state.user_name)
                    st.session_state.messages.append({"role": "assistant", "content": descripcion})
                    st.rerun()

    # --- HISTORIAL ---
    elif modo == "📜 Ver Registros Anteriores":
        st.title("📜 Historial Completo de Registros")
        
        registros_cargados = cargar_historial_db(get_supabase_client(), st.session_state.user_name)
        
        if not registros_cargados:
             st.info("Aún no tienes registros guardados en tu diario.")
        
        # Mostrar historial cargado con mejor formato
        for m in reversed(registros_cargados):
            icono = "👤 Registro" if m['role'] == 'user' else "🧠 Reflexión"
            st.markdown(f"#### {icono}")
            st.code(m['content'], language="markdown")
        
# --- 7. EJECUCIÓN ---
if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
