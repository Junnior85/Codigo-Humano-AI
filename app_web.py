import streamlit as st
import speech_recognition as sr
import pyttsx3
import threading
import time
from datetime import datetime
import queue

# --- CONFIGURACIÓN E INICIALIZACIÓN ---

# Cola para comunicar el hilo de voz con la interfaz visual
if 'chat_queue' not in st.session_state:
    st.session_state.chat_queue = []

# Variable de control para detener el hilo al cerrar
if 'run_assistant' not in st.session_state:
    st.session_state.run_assistant = False

# Variables globales para el manejo de hilos de audio
audio_queue = queue.Queue()
interruption_flag = threading.Event()

def inicializar_motor_voz():
    """Configura el motor de texto a voz"""
    engine = pyttsx3.init()
    # Puedes ajustar la velocidad aquí
    engine.setProperty('rate', 190) 
    return engine

def hablar_con_interrupcion(texto, engine):
    """
    Lee el texto frase por frase, verificando si hay interrupción.
    """
    frases = texto.split('.')
    interruption_flag.clear()
    
    for frase in frases:
        if interruption_flag.is_set():
            print(">>> AUDIO INTERRUMPIDO <<<")
            engine.stop()
            break
        
        if frase.strip():
            engine.say(frase)
            engine.runAndWait()

def logica_del_asistente():
    """
    Este es el 'Cerebro' que corre en segundo plano.
    Escucha -> Procesa -> Habla -> Repite.
    """
    r = sr.Recognizer()
    mic = sr.Microphone()
    engine = inicializar_motor_voz()
    
    # Ajuste inicial de ruido
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=1)

    while True:
        try:
            # 1. ESCUCHAR (Modo pasivo para detectar interrupción o comandos)
            with mic as source:
                # listen_in_background es complejo de manejar con pyttsx3 en el mismo hilo,
                # así que usamos listen con timeout corto para verificar banderas.
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=5)
                except sr.WaitTimeoutError:
                    continue # Nadie habló, seguimos el ciclo

            # Si detectamos audio mientras el asistente hablaba, activamos la bandera
            if engine._inLoop: 
                interruption_flag.set()
                engine.stop()

            # 2. PROCESAR TEXTO
            try:
                texto_usuario = r.recognize_google(audio, language="es-ES")
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Guardar en historial (Session State)
                mensaje_usuario = {"rol": "usuario", "texto": texto_usuario, "hora": timestamp}
                st.session_state.chat_queue.append(mensaje_usuario)
                
                # --- RESPUESTA SIMULADA DEL ASISTENTE ---
                # Aquí conectarías tu lógica de IA real. Por ahora es un eco inteligente.
                respuesta_texto = f"He escuchado que dijiste: {texto_usuario}. Si hablas ahora mismo, me callaré inmediatamente para escucharte de nuevo."
                
                mensaje_asistente = {"rol": "asistente", "texto": respuesta_texto, "hora": timestamp}
                st.session_state.chat_queue.append(mensaje_asistente)

                # 3. HABLAR (Con capacidad de ser interrumpido)
                # Nota: Para una interrupción real perfecta, se necesita un hilo de escucha paralelo.
                # En este script simple, la interrupción ocurre entre frases.
                hablar_con_interrupcion(respuesta_texto, engine)

            except sr.UnknownValueError:
                pass # Ruido no entendido

        except Exception as e:
            print(f"Error en el ciclo de voz: {e}")

# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("🎙️ Asistente de Voz con Historial")
st.write("Dicta tu mensaje. El sistema guarda el historial y permite interrupciones.")

# Botón para iniciar el hilo en segundo plano (Singleton)
if st.button("Iniciar Motor de Voz"):
    if not st.session_state.run_assistant:
        st.session_state.run_assistant = True
        # Ejecutamos la lógica de voz en un hilo separado para no congelar la web
        hilo_voz = threading.Thread(target=logica_del_asistente, daemon=True)
        hilo_voz.start()
        st.success("Sistema escuchando... (Habla al micrófono)")

# Área de Historial (Chat)
st.divider()
st.subheader("Historial de Conversación")

# Contenedor para mensajes
chat_container = st.container()

# Auto-refresco simple para ver los mensajes nuevos que llegan del hilo
if st.session_state.run_assistant:
    time.sleep(1) # Pequeña pausa para no saturar CPU
    st.rerun()

with chat_container:
    # Renderizar mensajes desde la cola
    for msg in st.session_state.chat_queue:
        with st.chat_message(msg["rol"]):
            st.write(f"**[{msg['hora']}]**: {msg['texto']}")
