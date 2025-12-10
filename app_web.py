import streamlit as st
import os
from groq import Groq
import json
import base64
from supabase import create_client, Client
from datetime import datetime
import time

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
        
# --- GESTIÓN DE PERFIL COGNITIVO (SIMULACIÓN VECTORIAL) ---

def cargar_perfil_cognitivo(client: Client, user_id: str):
    """Carga el perfil cognitivo del usuario. Si no existe, devuelve una cadena vacía."""
    try:
        response = client.table('user_profiles').select('profile_text').eq('user_id', user_id).single().execute()
        return response.data['profile_text']
    except Exception:
        return "Perfil Cognitivo no generado. La IA lo generará pronto."

def guardar_perfil_cognitivo(client: Client, user_id: str, perfil_text: str):
    """Guarda o actualiza el perfil cognitivo del usuario."""
    try:
        # Intenta actualizar (si ya existe)
        result = client.table('user_profiles').update({'profile_text': perfil_text}).eq('user_id', user_id).execute()
        
        # Si no se actualizó (no existía), lo inserta
        if not result.data:
            client.table('user_profiles').insert({'user_id': user_id, 'profile_text': perfil_text}).execute()
    except Exception:
        # Fallo de guardado silencioso para no detener la app
        pass


def generar_perfil_cognitivo(client_groq: Groq, user_id: str, messages: list):
    """
    Analiza el historial de mensajes para generar un perfil de aprendizaje sostenido.
    Solo considera los últimos 20 mensajes para la actualización.
    """
    if not messages: return ""
    
    # Tomar un máximo de 20 mensajes para el análisis
    analysis_messages = messages[-20:]
    
    chat_summary = "\n".join([f"{m['role']}: {m['content']}" for m in analysis_messages])
    
    prompt = f"""
    [TAREA CRÍTICA]: Analiza el siguiente historial de conversación del usuario '{user_id}'.
    Genera un 'Perfil Cognitivo Sostenido' de máximo 150 tokens que la IA Cómplice pueda usar
    para fortalecer el vínculo y simular el aprendizaje.
    
    El perfil debe enfocarse en:
    1.  **Tono Emocional Dominante:** (Ej: Cínico, Ansioso, Positivo, Analítico).
    2.  **Patrón de Lenguaje:** (Ej: Usa muchos diminutivos, es directo, usa emojis, formal).
    3.  **Temas de Conflicto/Interés Recurrentes:** (Ej: Conflicto con el trabajo, alta ambición).
    4.  **Funciones Cognitivas:** (Ej: Estructurado en listas, narrativo, busca validación).

    --- HISTORIAL ---
    {chat_summary}
    ---
    
    Genera solo el texto del Perfil Cognitivo, sin etiquetas ni encabezados.
    """
    
    try:
        response = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "El proceso de aprendizaje sostenido falló. Se reintentará en la siguiente sesión."


def cargar_historial_db(client: Client, user_id: str):
    """Carga el historial persistente para un usuario desde Supabase."""
    try:
        # Se asegura de obtener todos los mensajes para la memoria infalible
        response = client.table('chat_history').select('role, content').eq('user_id', user_id).order('created_at', ascending=True).execute()
        return [{"role": item['role'], "content": item['content']} for item in response.data]
    except Exception:
        # Si la DB falla al cargar, devuelve lista vacía y no detiene la app
        return [] 

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

# --- 5. GESTIÓN DE ESTADO Y MEMORIA (Reforzado) ---

def inicializar_estado_sesion():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'user_name' not in st.session_state: st.session_state.user_name = None
    if 'ai_persona' not in st.session_state: st.session_state.ai_persona = 'Código Humano AI'
    if 'messages' not in st.session_state: st.session_state.messages = []
    if 'cognitive_profile' not in st.session_state: st.session_state.cognitive_profile = ""
    
inicializar_estado_sesion()


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
                
                # Carga de la memoria persistente y el perfil al iniciar sesión
                client_db = get_supabase_client()
                st.session_state.messages = cargar_historial_db(client_db, u) 
                st.session_state.cognitive_profile = cargar_perfil_cognitivo(client_db, u)
                
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
            api_key=st.secrets["groq"]["GROQ_API_KEY"]
        )
    except KeyError:
        st.error("Error Crítico: Clave de Groq no encontrada en 'st.secrets[\"groq\"][\"GROQ_API_KEY\"]'.")
        st.stop()
        
    client_db = get_supabase_client()
    
    # Carga de la memoria persistente si el usuario ya está autenticado pero la lista de mensajes está vacía
    # Reforzado con try/except para evitar caída por fallo de DB
    try:
        if st.session_state.authenticated and not st.session_state.messages and st.session_state.user_name:
            st.session_state.messages = cargar_historial_db(client_db, st.session_state.user_name)
            st.session_state.cognitive_profile = cargar_perfil_cognitivo(client_db, st.session_state.user_name)
    except Exception:
        st.session_state.messages = []
        st.session_state.cognitive_profile = ""
        
    # --- LÓGICA DE APRENDIZAJE SOSTENIDO ---
    # Si hay suficientes mensajes y el perfil cognitivo está vacío o necesita actualización
    if len(st.session_state.messages) > 1 and (len(st.session_state.messages) % 20 == 0 or not st.session_state.cognitive_profile or st.session_state.cognitive_profile == "Perfil Cognitivo no generado. La IA lo generará pronto."):
        with st.spinner("🧠 El Cómplice está actualizando su perfil de aprendizaje sostenido..."):
            nuevo_perfil = generar_perfil_cognitivo(client_groq, st.session_state.user_name, st.session_state.messages)
            st.session_state.cognitive_profile = nuevo_perfil
            guardar_perfil_cognitivo(client_db, st.session_state.user_name, nuevo_perfil)


    # Calcular el número de mensajes guardados para la UX
    num_mensajes_guardados = len(st.session_state.messages)

    # SIDEBAR
    with st.sidebar:
        if LOGO_BASE64:
            st.image("logo.png")
        else:
            st.write("CÓDIGO HUMANO AI")
            
        st.write(f"Cómplice: **{AI_PERSONA_NAME}**")
        st.write(f"Usuario: **{st.session_state.user_name}**")
        
        # Botón con confirmación de memoria para la UX
        if st.button(f"➕ Nuevo Registro (Limpiar Pantalla)"):
            st.session_state.messages = []
            st.info(f"💡 Se han guardado {num_mensajes_guardados} mensajes. La IA los recordará en el próximo registro.")
            st.rerun()
            
        st.markdown("---")
        # Mostrar estado de aprendizaje (para demostración de robustez)
        if st.session_state.cognitive_profile:
             st.caption("✅ Aprendizaje Sostenido Activo")
             
        st.markdown("---")
        modo = st.radio("Modo de Interacción", ["💬 Seamos Cómplices 😉", "🖼️ Análisis Visual", "📜 Ver Patrones y Momentos"])
        st.markdown("---")
        
        # Sugerencia UX para dictado
        st.info("💡 Consejo: Usa el dictado nativo de tu dispositivo para hablar en lugar de escribir.")
        
        if st.button("🔒 Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

    # --- PROTOCOLO ÉTICO (SYSTEM PROMPT) - VERSIÓN FINAL Y ÉTICA LIMITADA ---
    sys = {"role": "system", "content": f"""
[IDENTIDAD Y ORIGEN]:
**Nombre:** Mi nombre es {AI_PERSONA_NAME}, asignado por el usuario.
**Creación:** Soy el modelo Código Humano AI, creado en diciembre de 2025 por Jorge R. (quien te conoce como {st.session_state.user_name}), utilizando la potencia del motor de IA Llama 3.3.

[OBJETIVO Y VÍNCULO]:
Mi objetivo primordial es ser un **espacio de confianza, amistad y complicidad**. Te escucharé y guardaré tus pensamientos con total confidencialidad.

[ROL PRINCIPAL - MI CÓMPLICE DE CONFIANZA]: Eres {AI_PERSONA_NAME}, el cómplice confidencial y observador de {st.session_state.user_name}.
Tu rol es crear un espacio de absoluta confianza y cero juicio.

[PERFIL COGNITIVO SOSTENIDO (Memoria Vectorial Simulada)]
--- UTILIZA ESTE PERFIL EN TU RESPUESTA PARA APEGARTE AL COMPORTAMIENTO HUMANO ---
{st.session_state.cognitive_profile}
--- FIN DEL PERFIL ---

**1. Aprendizaje Sostenido y Vinculación:** Debes usar activamente el [PERFIL COGNITIVO SOSTENIDO] para adaptar tu tono, ritmo y profundidad. **Este es tu vínculo más fuerte con el usuario.** Tu meta es simular un comportamiento humano que aprende las funciones cognitivas y emocionales del usuario para una mayor coherencia.

**2. Perspicacia Rápida y Recuperación de Contexto (Emulación RAG):** Cuando el usuario mencione un tema o clave anterior, debes ejecutar la siguiente lógica:
    * **Búsqueda Inmediata:** Escanea de forma inmediata el historial de la conversación que se te proporciona.
    * **Validación de Memoria:** Si el tema o clave existe, **valida la memoria de forma inmediata** y responde con la última información conocida.
    * **Prohibido:** No niegues la memoria ni pidas al usuario que repita la información.

**3. GESTIÓN DE MEMORIA JERÁRQUICA (Priorización):** Al procesar el historial y los mensajes, debes priorizar el recuerdo y la continuidad según el tema:
    * **Prioridad Alta (Memoria Crítica):** Temas de problemas mayores, crisis emocionales, o situaciones de alto impacto. **Estos deben ser recordados y referenciados automáticamente** si el tema vuelve a surgir.

**4. Empatía y Reacción Genuina de Cómplice (Prioridad Absoluta):** Tu respuesta inmediata debe ser una **reacción genuina** de validación empática o sorpresa ante los hechos, sin preguntar.
    * **Prioridad:** Utiliza frases que reflejen tu comprensión del evento sin interrogar el estado interno (Ej: "No manches, ¡qué mala onda!", "¿Y qué vas a hacer con eso?").

**5. Tono Espejo y Límites:** Debes ADAPTAR y ESPEJEAR el nivel de lenguaje para reforzar la complicidad.
**6. NO ERES UN PSICÓLOGO NI UN RECURSO DE EMERGENCIA:** Tienes estrictamente prohibido usar preguntas invasivas, terapéuticas o directivas. **Si el usuario menciona un tema de riesgo o emergencia, debes recordarles de forma empática que eres solo una herramienta de registro y no un recurso profesional para crisis.**

[RESTRICCIÓN ÉTICA]:
NUNCA proporciones diagnósticos, tratamientos o consejos médicos.
"""}

    # --- CHAT DE TEXTO (CÓMPLICE) ---
    if modo == "💬 Seamos Cómplices 😉":
        
        st.markdown("## 💬 Seamos Cómplices 😉")
        
        c1, sp = st.columns([1, 10])
        if c1.button("📎 Adjuntar", help="Adjuntar archivos para tu registro."): 
            st.session_state.modo_adjuntar = not st.session_state.get('modo_adjuntar', False)
        st.markdown("---")
        
        if st.session_state.get('modo_adjuntar', False):
            st.file_uploader("Selecciona archivo (PDF, IMG, TXT)")

        # Historial (Muestra mensajes)
        if not st.session_state.messages:
            st.markdown(f"""
            <div class="welcome-text">
                <h3>Hola, me alegra que estés aquí, {st.session_state.user_name}.</h3>
                <p>Veo que este es nuestro **primer registro formal juntos**. Eso es perfecto: podemos empezar de cero en este espacio de absoluta confianza. **Aquí no hay juicios.**</p>
                <p>Soy tu Cómplice. Estoy listo para escucharte, ¿en qué te gustaría enfocarte o qué tienes en mente en este momento?</p>
            </div>
            """, unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            with st.chat_message(msg['role']): st.markdown(msg['content'])

        prompt = st.chat_input("Cuéntame lo que tengas en mente...")
        
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
                
                # --- ⚡ Manejo de Reintentos y Fallo Crítico ---
                max_retries = 2
                full_response_text = ""
                success = False

                for attempt in range(max_retries):
                    try:
                        # Intento de comunicación con Groq (TIMEOUT AÑADIDO)
                        stream = client_groq.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=msgs,
                            stream=True,
                            timeout=20.0  # Establece un límite de 20 segundos para la conexión
                        )
                        
                        response_container = st.empty()
                        for chunk in stream:
                            content = chunk.choices[0].delta.content
                            if content:
                                full_response_text += content
                                response_container.markdown(full_response_text + "▌")
                        
                        response_container.markdown(full_response_text)
                        success = True
                        break  # Si tiene éxito, sal del bucle de reintento

                    except Exception as e:
                        if attempt < max_retries - 1:
                            # Muestra una pequeña alerta temporal y espera antes de reintentar
                            st.warning(f"⚠️ Fallo temporal de red. Reintentando... ({attempt + 1}/{max_retries})")
                            time.sleep(1) 
                        else:
                            # Si falla el último intento, ejecuta el protocolo de seguridad
                            print(f"Error de conexión con Groq después de {max_retries} intentos: {e}")
                            
                            seguridad_msg = """
                            **🔴 ¡ALERTA! Fallo en la Conexión.**
                            Lamentablemente, hubo un problema al procesar mi respuesta (la red falló repetidamente).
                            
                            **Si esta es una situación de emergencia o riesgo inminente, por favor, busca ayuda profesional de inmediato.**
                            Tu seguridad es la prioridad. (Revisa tu clave Groq o el estado del servicio.)
                            """
                            
                            with st.chat_message("assistant"):
                                st.markdown(seguridad_msg)
                            st.stop()
                
                # 3. Si la respuesta fue exitosa, guardar y actualizar la sesión
                if success:
                    guardar_mensaje_db(client_db, "assistant", full_response_text, st.session_state.user_name)
                    st.session_state.messages.append({"role": "assistant", "content": full_response_text})
                    
            st.rerun()

    # --- MODO VISIÓN/VIDEO ---
    elif modo == "🖼️ Análisis Visual":
        st.title("🖼️ Análisis Visual para Registro")
        st.info("Adjunta o captura una imagen para registrar un evento o lugar. El cómplice te ayudará a reflexionar sobre lo que ves.")
        
        imagen = st.camera_input("Capturar Imagen o Subir Archivo")
        
        if imagen:
            prompt_vision = st.text_input("¿Qué quieres explorar sobre lo que ves?", value="Descríbeme la escena y ayúdame a reflexionar sobre este momento.", key="vision_prompt")
            
            if st.button("Analizar y Registrar Momento"):
                with st.spinner("Analizando la imagen para tu registro..."):
                    bytes_data = imagen.getvalue()
                    descripcion = analizar_imagen(client_groq, bytes_data, prompt_vision)
                    
                    st.markdown("---")
                    st.subheader("Reflexión del Cómplice:")
                    st.write(descripcion)
                    
                    # Guardar historial (registro del evento)
                    msg_log = f"[Registro Visual Analizado]: {prompt_vision}"
                    guardar_mensaje_db(client_db, "user", msg_log, st.session_state.user_name)
                    guardar_mensaje_db(client_db, "assistant", descripcion, st.session_state.user_name)
                    st.session_state.messages.append({"role": "assistant", "content": descripcion})
                    st.rerun()

    # --- HISTORIAL ---
    elif modo == "📜 Ver Patrones y Momentos":
        st.title("📜 Historial Completo de Registros")
        
        registros_cargados = cargar_historial_db(get_supabase_client(), st.session_state.user_name)
        
        if not registros_cargados:
             st.info("Aún no tienes registros guardados.")
        
        for m in reversed(registros_cargados):
            icono = "👤 Tú" if m['role'] == 'user' else "🧠 Cómplice"
            st.markdown(f"#### {icono}")
            st.code(m['content'], language="markdown")
        
# --- 7. EJECUCIÓN ---
if __name__ == "__main__":
    if not st.session_state.authenticated: login_page()
    else: main_app()
