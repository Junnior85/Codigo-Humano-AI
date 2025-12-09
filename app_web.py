import streamlit as st
import os
from groq import Groq
import json
from datetime import datetime
import base64
from supabase import create_client, Client # <-- Importamos el cliente Supabase

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS y ESTILO ---
st.markdown("""
<style>
    .stApp {background-color: #050814; color: #E0E0E0;}
    [data-testid="stSidebar"] {background-color: #0b101c; border-right: 1px solid #1f293a;}
    div[data-testid="stImage"] img {border-radius: 15px;}
    .stButton > button {border: 1px solid #FFD700; color: #FFD700; border-radius: 8px; width: 100%;}
    .stButton > button:hover {background: #FFD700; color: #000; font-weight: bold;}
    .stTextInput > div > div > input {background-color: #151b2b; color: white; border: 1px solid #2a3b55;}
    .welcome-text {text-align: center; color: #4A5568; margin-top: 20%; font-size: 1.5rem;}
    #MainMenu, footer, header {visibility: hidden;}
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
        # Esto ocurre si falta [supabase], url o key en Streamlit Secrets
        st.error("⚠️ Error: Las claves de Supabase no están configuradas correctamente en Streamlit Secrets.")
        st.stop()
    except Exception:
        # Esto ocurre si la URL o la Key son incorrectas y la conexión inicial falla
        st.error("⚠️ Error al conectar con Supabase. Revisa URL y Key.")
        st.stop()
        
def cargar_historial_db(client: Client, user_id: str):
    """Carga el historial persistente para un usuario desde Supabase."""
    try:
        # Consulta que requiere Primary Key en 'id' y RLS SELECT TRUE
        response = client.table('chat_history').select('role, content').eq('user_id', user_id).order('created_at', ascending=True).execute()
        return [{"role": item['role'], "content": item['content']} for item in response.data]
    except Exception as e:
        # Maneja el caso de que la tabla esté vacía o RLS falle inicialmente (si no detuvo el st.stop())
        print(f"Error al cargar historial: {e}")
        return []

def guardar_mensaje_db(client: Client, rol: str, contenido: str, user_id: str):
    """Guarda un nuevo mensaje en la tabla de Supabase."""
    try:
        # Requiere RLS INSERT TRUE
        client.table('chat_history').insert({
            "role": rol, 
            "content": str(contenido), 
            "user_id": user_id
        }).execute()
    except Exception as e:
        # Silenciar el error si el guardado falla, pero registrarlo
        print(f"Error al guardar mensaje: {e}")

def borrar_historial_db(client: Client, user_id: str):
    """Borra el historial completo para un usuario."""
    # Requiere RLS DELETE TRUE
    client.table('chat_history').delete().eq('user_id', user_id).execute()

# --- 4. MOTOR DE VISIÓN ---

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
        st.error(f"Error en el motor de visión: {str(e)}")
        return "Lo siento, no pude procesar la imagen."

# --- 5. GESTIÓN DE ESTADO ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_name' not in st.session_state: st.session_state.user_name = None
if 'messages' not in st.session_state: st.session_state.messages = []

# --- 6. PANTALLAS Y FLUJO ---

def login_page():
    c1, c2, c3 = st.columns([1,4,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try: st.image("logo.png", width=250) 
        except: st.title("CÓDIGO HUMANO AI")
        u = st.text_input("Usuario")
        if st.button("ENTRAR"):
