import streamlit as st
import os
from groq import Groq
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tu Compañero", page_icon="💙")

# --- GESTIÓN DE SECRETOS (La llave de Groq) ---
# Intentamos obtener la llave de los secretos de Streamlit (para cuando esté online)
# o de una variable de entorno local.
api_key = os.environ.get("GROQ_API_KEY")
if not api_key and "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]

# --- CEREBRO (CLIENTE GROQ) ---
if api_key:
    client = Groq(api_key=api_key)
else:
    st.error("Falta la API Key. Configúrala en los secretos de despliegue.")
    st.stop()

# --- MEMORIA DE SESIÓN (RAM) ---
# En la versión web rápida, la memoria vive mientras la pestaña esté abierta.
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Mensaje inicial del sistema (invisible para el usuario)
    st.session_state.system_prompt = """
    YOU ARE A COMPANION AND LIVING DIARY. NOT A DOCTOR.
    
    OBJECTIVE: Detect risk patterns (Depression + Anxiety).
    
    BEHAVIOR:
    1. ZERO QUESTIONS: Do not interrogate. Validate and reflect.
    2. EMPATHY: If they share pain, mirror it ("I feel how heavy that is").
    3. KNOWLEDGE: If they ask for facts, answer intelligently.
    4. RISK ALERT: If Anxiety + Depression detected -> Suggest help gently ("This mix is dangerous, let's find an expert together").
    
    TONE: Warm, Spanish (unless spoken to in English), concise.
    """

# --- INTERFAZ GRÁFICA ---
st.title("Tu Espacio Seguro 💙")
st.markdown("Soy tu compañero. Este es un espacio libre de juicios. Te leo.")

# Mostrar historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- LÓGICA DE RESPUESTA ---
if prompt := st.chat_input("Escribe lo que sientes o piensas..."):
    # 1. Guardar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Construir el contexto para la IA
    # Unimos el prompt del sistema con los últimos mensajes para darle memoria
    conversation_history = [
        {"role": "system", "content": st.session_state.system_prompt}
    ]
    # Agregamos los últimos 10 mensajes para dar contexto sin gastar demasiada memoria
    conversation_history.extend(st.session_state.messages[-10:])

    # 3. Generar respuesta
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model="llama3-8b-8192", # Modelo Llama 3 rapidísimo en Groq
                messages=conversation_history,
                temperature=0.6,
                max_tokens=1024,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # 4. Guardar respuesta de la IA
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error de conexión: {e}")
