class Ordenador:
    def __init__(self, datos):
        # El constructor recibe la lista y la guarda en un atributo
        self.datos = datos

    def burbuja(self, ascendente=True):
        """Implementación del algoritmo de burbuja."""
        n = len(self.datos)
        # Hacemos una copia para no modificar la lista original si no queremos
        lista = self.datos[:] 
        
        for i in range(n):
            for j in range(0, n - i - 1):
                # Lógica para decidir si ordenamos de menor a mayor o viceversa
                if ascendente:
                    condicion = lista[j] > lista[j + 1]
                else:
                    condicion = lista[j] < lista[j + 1]
                
                if condicion:
                    lista[j], lista[j + 1] = lista[j + 1], lista[j]
        
        return lista

    def mostrar_datos(self):
        print(f"Estado actual de los datos: {self.datos}")

# --- Ejemplo de uso ---

# 1. Instanciamos la clase con un array (lista)
mi_ordenador = Ordenador([50, 10, 40, 20, 30])

# 2. Mostramos los datos originales
mi_ordenador.mostrar_datos()

# 3. Ordenamos de forma ascendente
resultado = mi_ordenador.burbuja(ascendente=True)
print(f"Lista ordenada: {resultado}")

# 4. Ordenamos de forma descendente
resultado_desc = mi_ordenador.burbuja(ascendente=False)
print(f"Lista descendente: {resultado_desc}")
