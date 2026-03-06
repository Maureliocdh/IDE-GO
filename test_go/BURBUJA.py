def ordenamiento_burbuja(lista):
    n = len(lista)
    # Hacemos una copia para no destruir la original
    lista_copia = lista[:] 
    
    for i in range(n):
        for j in range(0, n - i - 1):
            if lista_copia[j] > lista_copia[j + 1]:
                lista_copia[j], lista_copia[j + 1] = lista_copia[j + 1], lista_copia[j]
    
    return lista_copia

# Ejemplo de uso:
mi_lista = [64, 34, 25, 12, 22, 11, 90]

# Ahora sí, imprimimos correctamente usando una coma o f-string
print("Lista original:", mi_lista)

lista_ordenada = ordenamiento_burbuja(mi_lista)

print(f"Lista ordenada: {lista_ordenada}")

