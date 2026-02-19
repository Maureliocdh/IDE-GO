package main

import "fmt"

// ═══════════════════════════════════════════════════════════════
// PRUEBAS DE INDENTACIÓN - Basado en gobyexample.com
// ═══════════════════════════════════════════════════════════════

// 1. FUNCIÓN BÁSICA
func main() {
	fmt.Println("Hola Mundo")
}

// 2. IF/ELSE
func checkNumber(n int) {
	if n < 0 {
		fmt.Println("negativo")
	} else if n == 0 {
		fmt.Println("cero")
	} else {
		fmt.Println("positivo")
	}
}

// 3. FOR LOOPS
func loops() {
	// For básico
	for i := 0; i < 5; i++ {
		fmt.Println(i)
	}

	// While style
	j := 0
	for j < 5 {
		fmt.Println(j)
		j = j + 1
	}

	// Infinite loop
	for {
		fmt.Println("loop")
		break
	}
}

// 4. SWITCH
func switchExample(i int) {
	switch i {
	case 1:
		fmt.Println("uno")
	case 2:
		fmt.Println("dos")
	case 3:
		fmt.Println("tres")
	default:
		fmt.Println("otro")
	}
}

// 5. ARRAYS Y SLICES
func arraysExample() {
	var a []int
	a = []int{1, 2, 3, 4, 5}

	for i := 0; i < len(a); i++ {
		fmt.Println(a[i])
	}

	// Range
	for index, value := range a {
		fmt.Println(index, value)
	}
}

// 6. MAPS
func mapsExample() {
	m := map[string]int{
		"uno":  1,
		"dos":  2,
		"tres": 3,
	}

	for key, value := range m {
		fmt.Println(key, value)
	}
}

// 7. FUNCIONES CON MÚLTIPLES RETURNS
func swap(x int, y int) (int, int) {
	return y, x
}

// 8. STRUCTS
func structsExample() {
	type Person struct {
		name string
		age  int
	}

	p := Person{
		name: "Juan",
		age:  30,
	}

	fmt.Println(p.name)
	fmt.Println(p.age)
}

// 9. INTERFACES
func interfacesExample() {
	type Geometry interface {
		area() float64
		perim() float64
	}

	type Rectangle struct {
		width  float64
		height float64
	}

	var g Geometry
	g = Rectangle{width: 10, height: 5}
}

// 10. ERROR HANDLING
func divide(a int, b int) (int, error) {
	if b == 0 {
		return 0, fmt.Errorf("no se puede dividir por cero")
	}
	return a / b, nil
}

func errorExample() {
	result, err := divide(10, 0)
	if err != nil {
		fmt.Println("Error:", err)
	} else {
		fmt.Println("Resultado:", result)
	}
}

// 11. DEFER
func deferExample() {
	defer fmt.Println("mundo")
	fmt.Println("hola")
}

// 12. NESTED STRUCTURES
func nestedExample() {
	for i := 0; i < 3; i++ {
		for j := 0; j < 3; j++ {
			if i == j {
				fmt.Println("diagonal")
			} else {
				fmt.Println("no diagonal")
			}
		}
	}
}

// 13. CLOSURES
func closureExample() int {
	sum := 0
	for i := 0; i < 10; i++ {
		sum = sum + i
	}
	return sum
}

// 14. VARIADIC FUNCTIONS
func sum(nums []int) int {
	total := 0
	for _, num := range nums {
		total = total + num
	}
	return total
}

// ═══════════════════════════════════════════════════════════════
// INSTRUCCIONES PARA PROBAR:
// ═══════════════════════════════════════════════════════════════
//
// 1. Posiciona el cursor al final de una línea con {
//    y presiona Enter → debe indentar automáticamente
//
// 2. Escribe } → debe des-indentar automáticamente
//    al nivel correcto
//
// 3. Prueba escribir estructuras completas:
//    - Escribe "if true {" + Enter
//    - Escribe código indentado
//    - Escribe "}" → debe alinearse con el if
//
// 4. Prueba con estructuras anidadas:
//    - for dentro de for
//    - if dentro de for
//    - switch dentro de función
//
// 5. Verifica que use TABS no espacios (estándar Go)
//
// ═══════════════════════════════════════════════════════════════
