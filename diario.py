import datetime

def escribir_entrada():
    """Permite al usuario agregar una nueva entrada al diario."""
    print("\n--- Escribiendo en tu libreta ---")
    print("Escribe lo que quieras. Presiona Enter cuando termines.")
    texto = input("> ")
    
    # Obtenemos la fecha y hora actual automáticamente
    fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Guardamos en el archivo (la 'a' significa 'append' o agregar al final)
    with open("mi_diario.txt", "a", encoding="utf-8") as archivo:
        archivo.write(f"[{fecha_hora}]\n")
        archivo.write(f"{texto}\n")
        archivo.write("-" * 30 + "\n") # Una línea separadora
    
    print("Guardado. Tu memoria está segura.")

def leer_entradas():
    """Muestra el contenido del diario."""
    print("\n--- Abriendo el pasado ---")
    try:
        # Abrimos el archivo en modo lectura ('r')
        with open("mi_diario.txt", "r", encoding="utf-8") as archivo:
            contenido = archivo.read()
            if contenido:
                print(contenido)
            else:
                print("La libreta está vacía por ahora.")
    except FileNotFoundError:
        print("Aún no has escrito nada en tu diario.")

def main():
    """Función principal que controla el menú."""
    while True:
        print("\n=== TU DIARIO PERSONAL ===")
        print("1. Escribir (Plasmar el día)")
        print("2. Consultar (Recordar el pasado)")
        print("3. Cerrar libreta")
        
        opcion = input("\nElige una opción (1-3): ")

        if opcion == '1':
            escribir_entrada()
        elif opcion == '2':
            leer_entradas()
        elif opcion == '3':
            print("Cerrando. Hasta la próxima.")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")

# Este bloque asegura que el programa arranque
if __name__ == "__main__":
    main()
