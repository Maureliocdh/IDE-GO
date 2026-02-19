package main

import "fmt"

// Este archivo contiene errores intencionales para probar el sistema de detección

func main() {
    // Error 1: Sintaxis - falta llave de apertura
    if x > 5
        fmt.Println("mayor")
    }
    
    // Error 2: Indentación inconsistente
x := 10
    y := 20
    
    // Error 3: Sintaxis - paréntesis sin cerrar
    result := calcular(5, 10
    
    // Error 4: Token inválido
    valor := @42
    
    // Código correcto
    for i := 0; i < 5; i++ {
        fmt.Println(i)
    }
}

func calcular(a int, b int) int {
    return a + b
}
