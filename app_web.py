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
    
    /* ESTILO PARA EL LOGO EN EL LOGIN (Redondeado y con brillo) */
    div[data-testid="stImage"] img {
        border-radius: 20px; /* Redondea las esquinas del cuadro azul */
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.15); /* Sutil brillo dorado alrededor */
        transition: transform 0.3s;
    }
    div[data-testid="stImage"] img:hover {
        transform: scale(1.02); /* Efecto zoom sutil al pasar el mouse */
    }

    /* BOTONES */
    .stButton > button {
        background-color: transparent;
        color: #FFD700;
        border: 1px solid #FFD700;
        border-radius: 8px;
        width: 100%; 
    }
    .stButton > button:hover {
        background-color: #FFD700;
        color: #000;
        font-weight: bold;
    }

    /* INPUTS */
    .stTextInput > div > div > input {
        background-color: #151b2b;
        color: white;
        border: 1px solid #2a3b55;
        border-radius: 8px;
    }
    
    /* OCULTAR ELEMENTOS EXTRA */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)
