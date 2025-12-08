import streamlit as st
import os
from groq import Groq
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (MARCA DE AGUA Y DISEÑO) ---
st.markdown("""
<style>
    /* Marca de agua de fondo */
    .stApp {
        background-image: url("https://img.freepik.com/premium-vector/artificial-intelligence-logo-design-vector-symbol-icon-braint-technology-concept-background_754655-572.jpg");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    /* Capa blanca semitransparente para leer mejor el texto */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.85);
        padding: 2rem;
        border-radius: 10px;
        margin-top: 2rem;
    }
    /* Ocultar menú de hamburguesa estándar de Streamlit para limpiar la vista */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DEL CLIENTE GROQ ---
# Intenta obtener la clave de secretos, si falla, busca en variables de entorno (para local)
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    api_key = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=api_key)

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://img.freepik.com/premium-vector/artificial-intelligence-logo-design-vector-symbol-icon-braint-technology-concept-background_754655-572.jpg", width=100)
    st.title("Código Humano AI")
    st.markdown("---")
    
    # 1. Personalizar
    with st.expander("🎨 Personalizar", expanded=True):
        tema = st.selectbox("Modo", ["Claro", "Oscuro", "Color Dinámico"])
        nombre_ia = st.text_input("Nombre de tu IA", value="Diario")
        personalidad = st.slider("Nivel de Empatía", 0, 100, 90)
        voz = st.selectbox("Voz (Simulada)", ["Femenina - Suave", "Masculina - Profunda", "Neutra"])
    
    # 2. Historial
    with st.expander("📅 Historial"):
        st.write("Sesión actual iniciada:")
        st.write(datetime.now().strftime("%Y-%m-%d %H:%M"))
        if st.button("Borrar conversación actual"):
            st.session_state.messages = []
            st.rerun()

    # 3. Perfil
    with st.expander("👤 Perfil de Usuario"):
        nombre_usuario = st.text_input("Tu Nombre", value="Amigo")
        st.text_input("Domicilio (Opcional)")
        st.text_input("Teléfono (Opcional)")
        st.file_uploader("Foto de perfil", type=["png", "jpg"])

    # 4. Cerrar Sesión
    st.markdown("---")
    if st.button("🔒 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# --- LÓGICA DE MEMORIA Y MENSAJES ---
if "messages" not in st.session_state:
    # Mensaje inicial del sistema (Instrucciones ocultas para la IA)
    st.session_state.messages = []

# --- INTERFAZ PRINCIPAL ---

st.title(f"Hola, {nombre_usuario}. Estoy aquí para escucharte.")
st.markdown("### Espacio seguro de validación y apoyo emocional.")

# Mostrar mensajes anteriores
for message in st.session_state.messages:
    # No mostrar el mensaje del sistema (instrucciones ocultas)
    if message["role"] != "system":
        avatar = "👤" if message["role"] == "user" else "🧠"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

# --- BARRA DE HERRAMIENTAS DE CHAT (Botones funcionales) ---
col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
with col1:
    st.button("🎤", help="Dictado por voz (Próximamente)")
with col2:
    st.button("📞", help="Llamada de voz (Próximamente)")
with col3:
    st.button("📹", help="Videollamada (Próximamente)")
with col4:
    archivo = st.file_uploader("📎 Adjuntar", label_visibility="collapsed")

# --- ENTRADA DE CHAT ---
prompt = st.chat_input(f"Escribe aquí, {nombre_usuario}...")

if prompt:
    # 1. Guardar y mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 2. Preparar el contexto para la IA (System Prompt mejorado)
    system_prompt = {
        "role": "system",
        "content": f"""
        Actúa como {nombre_ia}, un compañero de IA altamente empático, compasivo y validador emocional. 
        Tu objetivo es ofrecer apoyo, escuchar activamente y detectar patrones de ansiedad o depresión de manera sutil.
        El usuario se llama {nombre_usuario}.
        Nivel de empatía configurado: {personalidad}/100.
        NO eres un médico, pero eres un confidente seguro. 
        Usa un tono cálido, humano y cercano. Valida sus sentimientos.
        """
    }
    
    # Construir historial para enviar al modelo
    messages_for_model = [system_prompt] + st.session_state.messages

    # 3. Generar respuesta con el MODELO VANGUARDISTA
    with st.chat_message("assistant", avatar="🧠"):
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # <--- MODELO MÁS POTENTE ACTUAL
            messages=messages_for_model,
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )
        response = st.write_stream(stream)
    
    # 4. Guardar respuesta de la IA
    st.session_state.messages.append({"role": "assistant", "content": response})
