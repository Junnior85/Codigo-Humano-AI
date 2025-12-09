import streamlit as st
import os
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTIÓN DE TEMAS Y DISEÑO ---
# Definimos los colores basados en psicología del color
temas = {
    "Modo Calma (Predeterminado)": {
        "bg": "#0e1117",          # Oscuro profundo (reduce fatiga visual)
        "sidebar": "#161b24",     # Ligeramente más claro
        "text": "#e0e0e0",        # Blanco suave
        "accent": "#00d4ff",      # Azul cián (Esperanza/Futuro)
        "watermark": "rgba(255, 255, 255, 0.04)"
    },
    "Modo Luz (Claridad)": {
        "bg": "#ffffff",
        "sidebar": "#f0f2f6",
        "text": "#31333F",
        "accent": "#2E86C1",
        "watermark": "rgba(0, 0, 0, 0.04)"
    },
    "Modo Noche (Descanso)": {
        "bg": "#000000",
        "sidebar": "#111111",
        "text": "#a0a0a0",
        "accent": "#8e44ad",     # Violeta (Introspección)
        "watermark": "rgba(255, 255, 255, 0.05)"
    }
}

# --- 3. BARRA LATERAL (MENÚ Y PERSONALIZACIÓN) ---
with st.sidebar:
    st.markdown("## 🧠 CÓDIGO HUMANO AI")
    st.caption("Tu compañero de bienestar emocional.")
    st.markdown("---")
    
    opcion_menu = st.radio(
        "Menú", 
        ["💬 Chat", "🎨 Personalizar", "📊 Historial", "👤 Perfil"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Lógica de Personalización (dentro del sidebar para acceso rápido)
    if opcion_menu == "🎨 Personalizar":
        st.subheader("Ajustes de Entorno")
        tema_seleccionado = st.selectbox("Apariencia", list(temas.keys()))
        estilo = temas[tema_seleccionado]
        
        st.subheader("Personalidad de la IA")
        nombre_ia = st.text_input("Nombre de tu compañero", value="Diario")
        nivel_empatia = st.slider("Nivel de Empatía", 0, 100, 95)
        st.selectbox("Voz mental", ["Femenina - Cálida", "Masculina - Protectora", "Neutra - Lógica"])
        
    else:
        # Tema por defecto si no estamos en personalizar
        tema_seleccionado = "Modo Calma (Predeterminado)"
        estilo = temas[tema_seleccionado]
        nombre_ia = "Diario"

    if st.button("🔒 Cerrar Sesión"):
        st.session_state.messages = []
        st.rerun()

# --- 4. INYECCIÓN DE CSS DINÁMICO ---
# Esto aplica los colores elegidos y la marca de agua
st.markdown(f"""
<style>
    /* Aplicar colores del tema */
    .stApp {{
        background-color: {estilo['bg']};
        color: {estilo['text']};
    }}
    [data-testid="stSidebar"] {{
        background-color: {estilo['sidebar']};
    }}
    
    /* Marca de Agua "CÓDIGO HUMANO AI" */
    .stApp::before {{
        content: "CÓDIGO HUMANO AI";
        position: fixed;
        top: 50%;
        left: 58%; 
        transform: translate(-50%, -50%);
        font-size: 8vh;
        font-weight: 900;
        color: {estilo['watermark']};
        pointer-events: none;
        z-index: 0;
        font-family: 'Arial', sans-serif;
    }}
    
    /* Botones de acción circulares */
    .stButton > button {{
        border-radius: 50%;
        width: 45px;
        height: 45px;
        border: 1px solid {estilo['accent']};
        background: transparent;
        color: {estilo['text']};
        transition: 0.3s;
    }}
    .stButton > button:hover {{
        background: {estilo['accent']};
        color: {estilo['bg']};
    }}
    
    /* Input de chat estilizado */
    .stChatInputContainer textarea {{
        border-radius: 20px !important;
        border: 1px solid {estilo['accent']} !important;
    }}
    
    header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# --- 5. CONFIGURACIÓN CLIENTE GROQ (CEREBRO) ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    st.warning("⚠️ Esperando configuración de API Key...")
    st.stop()

client = Groq(api_key=api_key)

# --- 6. INTERFAZ PRINCIPAL ---

# Si seleccionó Historial
if opcion_menu == "📊 Historial":
    st.title("📅 Tu Historial Emocional")
    st.write("Aquí se mostrará el análisis longitudinal de tus patrones (Próximamente con base de datos).")
    st.info("Por ahora, tu historial vive en la memoria de esta sesión.")

# Si seleccionó Perfil
elif opcion_menu == "👤 Perfil":
    st.title("👤 Tu Espacio")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.text_input("Tu Nombre", value="Usuario")
        st.text_input("Ocupación")
    with col_p2:
        st.text_input("Teléfono de emergencia")
        st.file_uploader("Foto de perfil")

# Si seleccionó Chat (Principal)
else:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Barra de botones de acción (Funcionales visualmente)
    # Se colocan justo encima del chat para simular integración
    st.markdown("<br><br>", unsafe_allow_html=True) 
    c1, c2, c3, c4, c5 = st.columns([1,1,1,1,12])
    with c1: st.button("🎤", help="Dictado")
    with c2: st.button("📞", help="Llamada de Apoyo")
    with c3: st.button("📹", help="Video Sesión")
    with c4: st.button("📎", help="Adjuntar registro")

    # Mostrar mensajes
    for message in st.session_state.messages:
        if message["role"] != "system":
            avatar = "👤" if message["role"] == "user" else "🧠"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

    # Entrada de Chat
    prompt = st.chat_input(f"Habla con {nombre_ia}...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Prompt del Sistema (Psicología)
        system_prompt = {
            "role": "system",
            "content": f"""
            Eres {nombre_ia}, una IA diseñada para apoyo emocional y detección temprana de patrones de riesgo (ansiedad/depresión).
            Tu tono es empático, validante y seguro. 
            NO juzgues. Escucha activamente.
            Si detectas riesgo alto de suicidio, sugiere sutilmente ayuda profesional.
            Usa respuestas concisas pero cálidas.
            """
        }

        messages_model = [system_prompt] + st.session_state.messages

        with st.chat_message("assistant", avatar="🧠"):
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", # MODELO ACTUALIZADO Y POTENTE
                messages=messages_model,
                temperature=0.6,
                max_tokens=1024,
                stream=True,
            )
            response = st.write_stream(stream)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
