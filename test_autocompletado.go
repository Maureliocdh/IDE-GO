package main

import "fmt"

// Archivo de prueba para el sistema de autocompletado
// Instrucciones:
// 1. Escribe "fu" → Debería sugerir "func"
// 2. Escribe "fmt.P" → Debería sugerir "fmt.Println", "fmt.Printf"
// 3. Presiona Ctrl+Space en cualquier lugar → Ver todas las sugerencias
// 4. Define funciones y variables abajo, luego intenta autocompletarlas

func calcularSuma(a int, b int) int {
	return a + b
}

func procesarDatos(datos []int) {
	for _, valor := range datos {
		fmt.Println(valor)
	}
}

func main() {
	// Prueba 1: Escribe "cal" aquí abajo → Debería sugerir "calcularSuma"

	// Prueba 2: Escribe "proc" aquí abajo → Debería sugerir "procesarDatos"

	// Prueba 3: Declara una variable y luego intenta autocompletarla
	precioUnitario := 100
	cantidadProductos := 5

	// Escribe "prec" → Debería sugerir "precioUnitario"

	// Escribe "cant" → Debería sugerir "cantidadProductos"

	// Prueba 4: Palabras clave
	// Escribe "fo" → Debería sugerir "for"

	// Escribe "sw" → Debería sugerir "switch"

	// Prueba 5: Tipos de datos
	// Escribe "in" → Debería sugerir "int", "int8", "int16", "int32", "int64", "interface"

	// Prueba 6: Funciones estándar
	// Escribe "le" → Debería sugerir "len"
	// Escribe "ap" → Debería sugerir "append"
	// Escribe "ma" → Debería sugerir "make", "map"

	// Prueba 7: Navegación con teclado
	// Escribe "f", presiona ↓ varias veces para navegar
	// Presiona Enter para completar la seleccionada

	// Prueba 8: Ctrl+Space sin escribir nada
	// Posiciona el cursor aquí y presiona Ctrl+Space

}
