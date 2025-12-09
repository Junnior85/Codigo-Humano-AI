import streamlit as st
import os
from groq import Groq
import json
import base64
from supabase import create_client, Client
from datetime import datetime

# --- 0. FUNCIÓN DE UTILIDAD ---
def obtener_base64(ruta_local):
    """Convierte un archivo local a base64 para incrustarlo en HTML/CSS."""
    try:
        # Verifica si la ruta existe. Si no, intenta buscar en el directorio raíz.
        if not os.path.exists(ruta_local):
            ruta_local = os.path.join(os.path.dirname(__file__), ruta_local)
        with open(ruta_local, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return "" 

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Código Humano AI - Cómplice",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS y ESTILO ---
LOGO_BASE64 = obtener_base64("logo.png")

st.markdown(f"""
<style>
    /* Estilos Generales */
    .stApp {{background-color: #050814; color: #E0E0E0;}}
    [data-testid="stSidebar"] {{background-color: #0b101c; border-right: 1px solid #1f293a;}}
    div[data-testid="stImage"] img {{border-radius: 15px;}}
    
    /* Botones */
    .stButton > button {{border: 1px solid #FFD700; color: #FFD700; border-radius: 8px; width: 100%;}}
    .stButton > button:hover {{background: #FFD700; color: #000; font-weight: bold;}}
    
    /* Inputs */
    .stTextInput > div > div > input {{background-color: #151b2b; color: white; border: 1px solid #2a3b55;}}
    
    /* UX/Estética */
    .welcome-text {{text-align: center; color: #4A5568; margin-top: 15%; font-size: 1.5rem;}}
    .logo-img-login {{
        text-align: center; 
        margin-bottom: 30px; 
        padding-bottom: 20px; 
        border-bottom: 1px solid #1f293a;
    }}
    .logo-img-login img {{width: 250px;}}
    
    /* Footer Fijo (Leyenda Ética) */
    .footer-disclaimer {{
        position: fixed; 
        bottom: 0; 
        left: 0; 
        width: 100%; 
        padding: 10px 0; 
        text-align: center; 
        background-color: #050814; 
        border-top: 1px solid #1f293a; 
        z-index: 1000;
    }}
    .disclaimer-text {{
        color: #718096;
        font-size: 0.8rem;
        margin: 0 auto;
        width: fit-content;
        background-color: transparent; 
        padding: 0;
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
        response = client.table('chat_history').select('role, content').eq('user_id', user_id).order('created_at', ascending=True).execute()
        return [{"role": item['role'], "content": item['content']} for item in response.data]
    except Exception:
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
if 'ai_persona' not in st.session_state: st.session_state.ai_persona = 'Código Humano AI'


# --- 6. PANTALLAS Y FLUJO (UX PROFESIONAL) ---

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

        u = st.text_input("Ingresa tu Nombre de Usuario")
        
        # Campo para asignación de Persona/Género (la clave para la apertura)
        p = st.text_input("Asigna un Nombre y Pronombre al Modelo (Opcional, Ej: Elena/ella, David/él)")

        if st.button("ACCEDER AL CÓMPLICE"):
            if u:
                st.session_state.user_name = u
                
                # Almacenar la persona asignada
                if p:
                    st.session_state.ai_persona = p.strip()
                else:
                    st.session_state.ai_persona = 'Código Humano AI'
                    
                st.session_state.authenticated = True
                st.session_state.messages = cargar_historial_db(get_supabase_client(), u)
                st.rerun()

    # Bloque de Descargo de Responsabilidad FINAL (Footer Fijo)
    st.markdown(
        """
        <div class="footer-disclaimer">
            <div class="disclaimer-text">
                **⚠️ Descargo de Responsabilidad Ética:** CÓDIGO HUMANO AI es una herramienta de **registro emocional y reflexión personal**. 
                **NO** sustituye un diagnóstico, tratamiento o terapia profesional.
            </div>
        </div>
        """, unsafe_allow_html=True)

def main_app():
    # Obtener el nombre de la persona AI para el prompt
    AI_PERSONA_NAME = st.session_state.ai_persona
    
    # Inicializar clientes
    try:
        # Búsqueda robusta de la clave de Groq (Asume sección [groq] en secrets.toml)
        client_groq = Groq(
