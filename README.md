# Sistema de Registro Personal (Web)

Una interfaz web minimalista para el registro de datos personales y gestión de buffer volátil.

## Requisitos Previos

Necesitas tener Python instalado en tu sistema.

## Instalación

1.  Descarga los archivos `app_web.py` y `requirements.txt` en una carpeta.
2.  Abre tu terminal o línea de comandos en esa carpeta.
3.  Instala las dependencias necesarias ejecutando:

    ```bash
    pip install -r requirements.txt
    ```

## Ejecución del Sistema

1.  En la terminal, ejecuta el siguiente comando:

    ```bash
    python app_web.py
    ```

2.  Verás un mensaje que dice `Running on http://127.0.0.1:5000`.
3.  Abre tu navegador web (Chrome, Edge, Safari) y escribe esa dirección: `http://127.0.0.1:5000`.

## Uso

* **[ GUARDAR REGISTRO ]**: Almacena el texto ingresado en `bitacora_web.txt` con fecha y hora. Útil para documentación permanente.
* **[ MODO VOLÁTIL / BORRAR ]**: Envía el texto al sistema para su procesamiento inmediato y eliminación. No deja rastros en el disco duro. Útil para pruebas de teclado o limpieza mental rápida.
