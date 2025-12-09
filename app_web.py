import streamlit as st
import os
from groq import Groq
import json
from datetime import datetime
import asyncio
import edge_tts 
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
        st.error("⚠️ Error: Las claves de Supabase no están configuradas en Streamlit Secrets.")
        st.stop()
    except Exception:
        st.error("⚠️ Error al conectar con Supabase. Revisa URL y Key.")
        st.stop()
        
def cargar_historial_db(client: Client, user_id: str):
    """Carga el historial persistente para un usuario desde Supabase."""
    # Filtrar por user_id y ordenar por tiempo
    response = client.table('chat_history').select('role, content').eq('user_id', user_id).order('created_at', ascending=True).execute()
    # Retornar en el formato que Groq espera
    return [{"role": item['role'], "content": item['content']} for item in response.data]

def guardar_mensaje_db(client: Client, rol: str, contenido: str, user_id: str):
    """Guarda un nuevo mensaje en la tabla de Supabase."""
    # El contenido ya debe ser un string limpio (gracias a la corrección de errores).
    client.table('chat_history').insert({
        "role": rol, 
        "content": str(contenido), 
        "user_id": user_id
    }).execute()

def borrar_historial_db(client: Client, user_id: str):
    """Borra el historial completo para un usuario."""
    client.table('chat_history').delete().eq('user_id', user_id).execute()

# --- 4. MOTORES (VOZ Y VISIÓN) ---

async def generar_audio_edge(texto, voz="es-MX-DaliaNeural"):
    """Genera audio rápido y natural usando Edge TTS"""
    comunicador = edge_tts.Communicate(texto, voz)
    archivo_salida = "temp_audio.mp3"
    await comunicador.save(archivo_salida)
    return archivo_salida

def hablar(texto):
    """Llama a la función asíncrona para reproducir audio."""
    try:
        audio_file = asyncio.run(generar_audio_edge(texto))
        if os.path.exists(audio_file):
            st.audio(audio_file, format="audio/mp3", autoplay=True)
            os.remove(audio_file)
    except Exception:
        # Silenciar errores de audio para mantener la UX
        pass

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
            if u:
                st.session_state.user_name = u
                st.session_state.authenticated = True
                # Cargar historial al logear
                st.session_state.messages = cargar_historial_db(get_supabase_client(), u)
                st.rerun()

def main_app():
    # Inicializar clientes
    client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
    client_db = get_supabase_client()

    # SIDEBAR
    with st.sidebar:
        try: st.image("logo.png")
        except: pass
        st.write(f"Usuario: **{st.session_state.user_name}**")
        
        if st.button("➕ Nueva Conversación"):
            borrar_historial_db(client_db, st.session_state.user_name)
            st.session_state.messages = []
            st.rerun()
            
        st.markdown("---")
        modo = st.radio("Modo", ["💬 Chat Texto", "🖼️ Modo Visión", "📜 Historial", "👤 Perfil"])
        st.markdown("---")
        if st.button("🔒 Salir"):
            st.session_state.authenticated = False
            st.rerun()

    # --- CHAT DE TEXTO (MEMORIA PERSISTENTE Y SIN BAD REQUEST) ---
    if modo == "💬 Chat Texto":
        
        c1, c2, sp = st.columns([1, 1, 10])
        if c1.button("📎", help="Adjuntar archivo"): st.session_state.modo_adjuntar = not st.session_state.get('modo_adjuntar', False)
        if c2.button("🔊", help="Activar respuesta de voz"): st.toast("La IA hablará. Funciona mejor con auriculares.", icon="🔊")
        st.markdown("---")
        
        st.info("Para dictar, usa el micrófono nativo de tu sistema (Ej: Win+H).")
        
        if st.session_state.get('modo_adjuntar', False):
            st.file_uploader("Selecciona archivo (PDF, IMG, TXT)")

        # Historial (Muestra mensajes)
        if not st.session_state.messages:
            st.markdown(f"""<div class="welcome-text"><h3>Hola, {st.session_state.user_name}.</h3></div>""", unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            with st.chat_message(msg['role']): st.markdown(msg['content'])

        prompt = st.chat_input("Escribe tu mensaje o usa el dictado nativo...")
        
        if prompt:
            # 1. Guardar y mostrar mensaje del usuario
            guardar_mensaje_db(client_db, "user", prompt, st.session_state.user_name)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 2. Generar Respuesta (Visual)
            with st.chat_message("assistant"):
                
                # --- FILTRADO DE SEGURIDAD (FIX BAD REQUEST) ---
                sys = {"role": "system", "content": f"Eres Código Humano AI. Usuario: {st.session_state.user_name}. Empático, recuerda el historial."}
                cleaned_messages = []
                for msg in st.session_state.messages:
                    if isinstance(msg, dict) and msg.get('role') in ['user', 'assistant'] and msg.get('content'):
                        cleaned_messages.append({"role": msg['role'], "content": msg['content']})
                
                msgs = [sys] + cleaned_messages
                # --- FIN FILTRADO ---
                
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
                    
                    # Si se activó el audio, hablar
                    if "🔊" in st.session_state.get('toast_queue', {}): hablar(full_response_text)
                    
                except Exception as e:
                    st.error(f"Error de conexión con la IA. El modelo falló. Asegúrate de que la clave GROQ sea correcta. Detalle: {type(e).__name__}")
                    
            st.rerun()

    # --- MODO VISIÓN/VIDEO ---
    elif modo == "🖼️ Modo Visión":
        st.title("🖼️ Análisis Visual (Simulador de Videollamada)")
        st.info("La IA puede analizar una imagen. Simula tu videollamada enviando una foto.")
        
        imagen = st.camera_input("Capturar Imagen o Subir Archivo")
        
        if imagen:
            prompt_vision = st.text_input("¿Qué quieres preguntar sobre lo que ves?", value="Descríbeme la escena y dame un mensaje positivo.")
            
            if st.button("Analizar Imagen"):
                with st.spinner("Viendo y analizando..."):
                    bytes_data = imagen.getvalue()
                    descripcion = analizar_imagen(client_groq, bytes_data, prompt_vision)
                    
                    st.markdown("---")
                    st.subheader("Respuesta de la IA:")
                    st.write(descripcion)
                    hablar(descripcion)

                    # Guardar historial (registro del evento)
                    msg_log = f"[Visión Analizada]: {prompt_vision}"
                    guardar_mensaje_db(client_db, "user", msg_log, st.session_state.user_name)
                    guardar_mensaje_db(client_db, "assistant", descripcion, st.session_state.user_name)
                    st.session_state.messages.append({"role": "assistant", "content": descripcion})

    # --- HISTORIAL ---
    elif modo == "📜 Historial":
        st.title("📜 Historial Completo")
        # Mostrar historial cargado al inicio (o recargado)
        for m in st.session_state.messages:
            icono = "👤" if m['role'] == 'user' else "🧠"
            st.text(f"[{m.get('time', 'N/A')}] {icono}: {m['content']}")

    elif modo == "👤 Perfil":
        st.title("👤 Tu Perfil")
        st.text_input("Nombre", value=st.session_state.user_name)

# --- 7. EJECUCIÓN ---
if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
