import streamlit as st
import os
from groq import Groq
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Código Humano AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILOS CSS ---
st.markdown("""
<style>
    /* FONDO GENERAL */
    .stApp {
        background-color: #050814; 
        color: #E0E0E0;
    }
    
    /* BARRA LATERAL */
    [data-testid="stSidebar"] {
        background-color: #0b101c;
        border-right: 1px solid #1f293a;
    }
    
    /* LOGO */
    div[data-testid="stImage"] img {
        border-radius: 15px; 
        transition: transform 0.3s;
    }
    div[data-testid="stImage"] img:hover {
        transform: scale(1.02); 
    }

    /* BOTONES */
    .stButton > button {
        background-color: transparent;
        color: #FFD700;
        border: 1px solid #FFD700;
        border
