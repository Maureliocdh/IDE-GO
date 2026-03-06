def ordenamiento_burbuja(lista):
    n = len(lista)
    
    # Recorremos toda la lista
    for i in range(n):
        # El último elemento ya está en su lugar, así que no necesitamos tocarlo
        for j in range(0, n - i - 1):
            
            # Si el elemento actual es mayor al que sigue...
            if lista[j] > lista[j + 1]:
                # ¡Intercambio!
                lista[j], lista[j + 1] = lista[j + 1], lista[j]
    
    return lista

# Ejemplo de uso:
mi_lista = [64, 34, 25, 12, 22, 11, 90]
lista_ordenada = ordenamiento_burbuja(mi_lista)

print(f"Lista ordenada: {lista_ordenada}")

