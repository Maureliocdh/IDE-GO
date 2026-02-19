package main

import "fmt"

// ═══════════════════════════════════════════════════════════════
// ARCHIVO DE PRUEBA - GO-APK-IDE FULL VERSION
// Este archivo demuestra todas las características del IDE
// ═══════════════════════════════════════════════════════════════

// ┌─────────────────────────────────────────────────────────────┐
// │ SNIPPETS - Prueba la expansión de snippets                 │
// │ Escribe "main" y presiona Tab → crea func main()          │
// │ Escribe "for" y presiona Tab → crea bucle for             │
// │ Escribe "if" y presiona Tab → crea estructura if          │
// │ Escribe "err" y presiona Tab → crea manejo de error       │
// └─────────────────────────────────────────────────────────────┘

// ┌─────────────────────────────────────────────────────────────┐
// │ AUTOCOMPLETADO - Prueba con Ctrl+Space                     │
// │ 1. Escribe "fmt." y presiona Ctrl+Space                    │
// │ 2. Verás sugerencias: Println, Printf, Sprintf             │
// │ 3. Usa ↑↓ para navegar, Enter/Tab para completar          │
// └─────────────────────────────────────────────────────────────┘

// ┌─────────────────────────────────────────────────────────────┐
// │ GO TO DEFINITION - Presiona F12 sobre un símbolo           │
// │ 1. Posiciona cursor sobre "saludar" en main()               │
// │ 2. Presiona F12 → salta a la definición de saludar()       │
// │ 3. Funciona con funciones, variables, constantes           │
// └─────────────────────────────────────────────────────────────┘

const VERSION = "1.0"
const NOMBRE_APP = "Go-APK-IDE"

var contador int = 0
var mensaje string = "Hola Mundo"

// Función de ejemplo para probar Go to Definition (F12)
func saludar(nombre string) {
	fmt.Println("Hola", nombre)
	fmt.Println("Bienvenido a", NOMBRE_APP, VERSION)
}

// Función para demostrar renombrado de símbolos
func calcularSuma(a int, b int) int {
	resultado := a + b
	return resultado
}

// ┌─────────────────────────────────────────────────────────────┐
// │ RENAME SYMBOL - Presiona F2 para renombrar                 │
// │ 1. Posiciona cursor sobre "calcularSuma"                    │
// │ 2. Presiona F2                                               │
// │ 3. Escribe nuevo nombre: "sumar"                            │
// │ 4. Todas las ocurrencias se renombran automáticamente       │
// └─────────────────────────────────────────────────────────────┘

func main() {
	// ── Variables para probar autocompletado ──
	var nombre string = "Usuario"
	var edad int = 25
	var activo bool = true
	var precio float64 = 99.99

	// ── Probar función saludar (Go to Definition con F12) ──
	saludar(nombre)

	// ── Bucle for tradicional ──
	for i := 0; i < 5; i++ {
		fmt.Println("Iteración:", i)
	}

	// ── Condicionales ──
	if edad >= 18 {
		fmt.Println("Mayor de edad")
	} else {
		fmt.Println("Menor de edad")
	}

	// ── Arrays y slices ──
	numeros := []int{10, 20, 30, 40, 50}
	for i := 0; i < len(numeros); i++ {
		fmt.Println("Número:", numeros[i])
	}

	// ── Switch ──
	switch nombre {
	case "Admin":
		fmt.Println("Usuario administrador")
	case "Usuario":
		fmt.Println("Usuario normal")
	default:
		fmt.Println("Usuario desconocido")
	}

	// ── Función matemática ──
	suma := calcularSuma(10, 20)
	fmt.Println("Suma:", suma)

	// ── Demostrar contador de variables ──
	contador = contador + 1
	fmt.Println("Contador:", contador)
	fmt.Println("Precio:", precio)
	fmt.Println("Activo:", activo)
}

// ┌─────────────────────────────────────────────────────────────┐
// │ CARACTERÍSTICAS ADICIONALES DEL IDE:                        │
// ├─────────────────────────────────────────────────────────────┤
// │ ✓ CTRL+G        → Ir a línea específica                    │
// │ ✓ CTRL+D        → Duplicar línea actual                     │
// │ ✓ CTRL+/        → Comentar/Descomentar línea               │
// │ ✓ CTRL+F        → Buscar y reemplazar                       │
// │ ✓ CTRL+S        → Guardar archivo                           │
// │ ✓ CTRL+W        → Cerrar pestaña                            │
// │ ✓ CTRL+Tab      → Siguiente pestaña                         │
// │ ✓ CTRL+Rueda    → Zoom in/out                               │
// │ ✓ CTRL+0        → Resetear zoom                             │
// │ ✓ F5            → Ejecutar código                           │
// │ ✓ F6            → Compilar a C                              │
// │ ✓ F7            → Generar ensamblador                       │
// │ ✓ F8            → Toggle terminal integrado                 │
// │ ✓ F12           → Ir a definición                           │
// │ ✓ F2            → Renombrar símbolo                         │
// │ ✓ Ctrl+Space    → Autocompletado manual                    │
// │ ✓ Escape        → Cerrar autocompletado                     │
// └─────────────────────────────────────────────────────────────┘

// ┌─────────────────────────────────────────────────────────────┐
// │ MENÚS DISPONIBLES:                                          │
// ├─────────────────────────────────────────────────────────────┤
// │ • Archivo      → Nuevo, Abrir, Guardar, Exportar a C       │
// │ • Edición      → Buscar, Ir a línea, Comentar, Autocompletar│
// │ • Navegación   → Ir a definición                            │
// │ • Refactoring  → Renombrar símbolo                          │
// │ • Vista        → Cambiar tema, Zoom, Terminal               │
// │ • Ejecutar     → Ejecutar, Compilar, Generar ASM            │
// │ • Herramientas → Estadísticas del código                    │
// │ • Ayuda        → Acerca de                                  │
// └─────────────────────────────────────────────────────────────┘

// ┌─────────────────────────────────────────────────────────────┐
// │ PANEL DE ERRORES:                                           │
// │ • El IDE detecta errores en tiempo real (750ms delay)       │
// │ • Los errores aparecen subrayados en rojo                   │
// │ • Panel inferior muestra lista de errores                   │
// │ • Click en error → navega a la línea                        │
// │ • Detecta errores de indentación, sintaxis y léxicos        │
// └─────────────────────────────────────────────────────────────┘

// ┌─────────────────────────────────────────────────────────────┐
// │ EXPLORADOR DE ARCHIVOS:                                     │
// │ • Click en 📂 para abrir carpeta de proyecto               │
// │ • Doble click en archivo para abrirlo                       │
// │ • Click derecho para crear/renombrar/eliminar               │
// │ • Iconos por tipo de archivo                                │
// └─────────────────────────────────────────────────────────────┘

// ┌─────────────────────────────────────────────────────────────┐
// │ TERMINAL INTEGRADO (F8):                                    │
// │ • Presiona F8 para mostrar/ocultar terminal                 │
// │ • Ejecuta comandos del sistema                              │
// │ • Salida con colores (verde stdout, rojo stderr)            │
// │ • Botones: Ejecutar, Limpiar                                │
// └─────────────────────────────────────────────────────────────┘

// ┌─────────────────────────────────────────────────────────────┐
// │ ESTADÍSTICAS:                                               │
// │ • Menú Herramientas → Estadísticas del Código               │
// │ • Muestra: líneas totales, código, comentarios, vacías      │
// │ • Cuenta: palabras, caracteres, funciones, variables        │
// └─────────────────────────────────────────────────────────────┘

// ═══════════════════════════════════════════════════════════════
// ¡EXPLORA TODAS LAS CARACTERÍSTICAS DEL IDE!
// Consulta CARACTERISTICAS_COMPLETAS.txt para más información
// ═══════════════════════════════════════════════════════════════
