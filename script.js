// Constantes para LocalStorage
const STORAGE_KEY = 'humano_ia_session';

// 1. Al cargar la página, verificamos si ya existe sesión
document.addEventListener('DOMContentLoaded', () => {
    const sessionData = localStorage.getItem(STORAGE_KEY);
    
    if (sessionData) {
        // Si hay datos, restaurar sesión directamente
        const data = JSON.parse(sessionData);
        iniciarInterfazChat(data.userName, data.botName);
    } else {
        // Si no hay datos, asegurarse de que se vea el login
        document.getElementById('login-screen').style.display = 'flex';
        document.getElementById('chat-screen').style.display = 'none';
    }
});

// 2. Función de Login (Botón "Iniciar Chat")
function login() {
    const userName = document.getElementById('user-name').value;
    const botName = document.getElementById('bot-name').value;
    const password = document.getElementById('password').value;

    // Validación simple
    if (!userName || !botName || !password) {
        alert("Por favor completa todos los campos.");
        return;
    }

    // Aquí podrías validar la contraseña real si quisieras
    // Por ahora, asumimos que es correcta y guardamos la sesión

    const sessionData = {
        userName: userName,
        botName: botName,
        token: 'sesion-activa-token' // Simulación de token
    };

    // GUARDAR EN MEMORIA DEL NAVEGADOR
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessionData));

    // Cambiar pantalla
    iniciarInterfazChat(userName, botName);
}

// 3. Función para mostrar el Chat y ocultar Login
function iniciarInterfazChat(user, bot) {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('chat-screen').style.display = 'flex';
    
    // Actualizar nombre del bot en la interfaz
    document.getElementById('display-bot-name').textContent = bot;
    
    // Mensaje de bienvenida en consola o UI
    console.log(`Sesión iniciada para: ${user} con el asistente: ${bot}`);
}

// 4. Función de Logout (Botón "Cerrar Sesión")
function logout() {
    // Borrar memoria
    localStorage.removeItem(STORAGE_KEY);
    // Recargar página para volver al inicio
    location.reload();
}
