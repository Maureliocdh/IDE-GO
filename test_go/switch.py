import time # Para que podamos ver qué pasa paso a paso

def ordenamiento_burbuja(lista):
    n = len(lista)
    for i in range(n):
        for j in range(0, n - i - 1):
            if lista[j] > lista[j + 1]:
                lista[j], lista[j + 1] = lista[j + 1], lista[j]
    return lista

# --- CONFIGURACIÓN AUTOMÁTICA ---
datos = [40, 10, 30, 20]
paso = 1

print(" Iniciando proceso automático...")

while paso <= 3:
    match paso:
        case 1:
            print(f"\n[PASO 1] Mostrando lista inicial: {datos}")
        
        case 2:
            print("[PASO 2] Ordenando lista con Burbuja...")
            datos = ordenamiento_burbuja(datos)
            time.sleep(1) # Pausa de 1 segundo para simular "pensamiento"
        
        case 3:
            print(f"[PASO 3] Resultado final: {datos}")
            print("\n Proceso terminado con éxito.")

    paso += 1 # Avanza al siguiente paso automáticamente
