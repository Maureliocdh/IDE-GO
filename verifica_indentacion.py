"""
PRUEBA RÁPIDA DEL VALIDADOR DE INDENTACIÓN
===========================================

Ejecuta este script para probar el validador antes de abrir la interfaz gráfica.
"""

from indentation_checker import IndentationChecker

# Tu código con indentación incorrecta
codigo = '''package main
import "fmt"

func bubbleSort(arr []int) {
    n := len(arr)
    		for i := 0; i < n-1; i++ {
        for j := 0; j < n-i-1; j++ {
            if arr[j] > arr[j+1] {
                arr[j], arr[j+1] = arr[j+1], arr[j]
            }
        }
    }
}

func main() {
    datos := []int{64, 34, 25, 12, 22, 11, 90}
    fmt.Println("Original:", datos)
    bubbleSort(datos)
    fmt.Println("Ordenado:", datos)
}
'''

print("\n" + "=" * 70)
print("VALIDANDO INDENTACIÓN DE TU CÓDIGO")
print("=" * 70 + "\n")

checker = IndentationChecker(codigo)
errors = checker.check()

if errors:
    print("❌ SE DETECTARON ERRORES DE INDENTACIÓN:\n")
    for line_num, message in errors:
        # Mostrar la línea problemática
        linea = codigo.split('\n')[line_num - 1]
        print(f"📍 Línea {line_num}:")
        print(f"   {repr(linea)}")
        print(f"   ⚠️  {message}\n")
    
    print("\n💡 SOLUCIÓN:")
    print("   Corrige la indentación de las líneas marcadas.")
    print("   Las líneas dentro de bloques {{}} deben estar")
    print("   indentadas con el mismo tipo de espaciado (4 espacios o 1 tab).")
else:
    print("✅ La indentación es correcta!")

print("\n" + "=" * 70)
