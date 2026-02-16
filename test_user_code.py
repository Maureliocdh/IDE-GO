#!/usr/bin/env python3
"""Test the specific failing code"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = """package main

import (
	"fmt"
	"maps"
	"math"
	"slices"
	"time"
)

func main() {
	fmt.Println("--- EJECUTANDO TODOS LOS EJEMPLOS ---")

	ejemploHolaMundo()
	ejemploValores()
	ejemploVariables()
	ejemploConstantes()
	ejemploFor()
	ejemploIfElse()
	ejemploSwitch()
	ejemploArrays()
	ejemploSlices()
	ejemploMaps()
	ejemploFunciones()
	ejemploRetornoMultiple()
	ejemploClousures()
	ejemploRecursividad()
	ejemploRange()

	fmt.Println("\n--- FIN DE LOS EJEMPLOS ---")
}

// 1. Hola Mundo
func ejemploHolaMundo() {
	fmt.Println("\n> Hola Mundo:")
	fmt.Println("hello world")
}

// 2. Valores y Operadores
func ejemploValores() {
	fmt.Println("\n> Valores:")
	fmt.Println("go" + "lang")
	fmt.Println("1+1 =", 1+1)
	fmt.Println("7.0/3.0 =", 7.0/3.0)
	fmt.Println(true && false)
	fmt.Println(true || false)
	fmt.Println(!true)
}

// 3. Variables
func ejemploVariables() {
	fmt.Println("\n> Variables:")
	var a = "initial"
	fmt.Println(a)

	var b, c int = 1, 2
	fmt.Println(b, c)

	var d = true
	fmt.Println(d)

	var e int
	fmt.Println(e)

	f := "apple"
	fmt.Println(f)
}

// 4. Constantes
const s string = "constant"

func ejemploConstantes() {
	fmt.Println("\n> Constantes:")
	fmt.Println(s)
	const n = 500000000
	const d = 3e20 / n
	fmt.Println(d)
	fmt.Println(int64(d))
	fmt.Println(math.Sin(n))
}

// 5. For Loops
func ejemploFor() {
	fmt.Println("\n> For:")
	i := 1
	for i <= 3 {
		fmt.Println(i)
		i = i + 1
	}

	for j := 0; j < 3; j++ {
		fmt.Println(j)
	}

	for i := range 3 {
		fmt.Println("range", i)
	}

	for {
		fmt.Println("loop una vez")
		break
	}

	for n := range 6 {
		if n%2 == 0 {
			continue
		}
		fmt.Println(n)
	}
}

// 6. If/Else
func ejemploIfElse() {
	fmt.Println("\n> If/Else:")
	if 7%2 == 0 {
		fmt.Println("7 is even")
	} else {
		fmt.Println("7 is odd")
	}

	if 8%4 == 0 {
		fmt.Println("8 is divisible by 4")
	}

	if 8%2 == 0 || 7%2 == 0 {
		fmt.Println("either 8 or 7 are even")
	}

	if num := 9; num < 0 {
		fmt.Println(num, "is negative")
	} else if num < 10 {
		fmt.Println(num, "has 1 digit")
	} else {
		fmt.Println(num, "has multiple digits")
	}
}

// 7. Switch
func ejemploSwitch() {
	fmt.Println("\n> Switch:")
	i := 2
	fmt.Print("Write ", i, " as ")
	switch i {
	case 1:
		fmt.Println("one")
	case 2:
		fmt.Println("two")
	case 3:
		fmt.Println("three")
	}

	switch time.Now().Weekday() {
	case time.Saturday, time.Sunday:
		fmt.Println("It's the weekend")
	default:
		fmt.Println("It's a weekday")
	}

	t := time.Now()
	switch {
	case t.Hour() < 12:
		fmt.Println("It's before noon")
	default:
		fmt.Println("It's after noon")
	}

	whatAmI := func(i interface{}) {
		switch t := i.(type) {
		case bool:
			fmt.Println("I'm a bool")
		case int:
			fmt.Println("I'm an int")
		default:
			fmt.Printf("Don't know type %T\n", t)
		}
	}
	whatAmI(true)
	whatAmI(1)
	whatAmI("hey")
}

// 8. Arrays
func ejemploArrays() {
	fmt.Println("\n> Arrays:")
	var a [5]int
	fmt.Println("emp:", a)

	a[4] = 100
	fmt.Println("set:", a)
	fmt.Println("get:", a[4])
	fmt.Println("len:", len(a))

	b := [5]int{1, 2, 3, 4, 5}
	fmt.Println("dcl:", b)

	var twoD [2][3]int
	for i := range 2 {
		for j := range 3 {
			twoD[i][j] = i + j
		}
	}
	fmt.Println("2d: ", twoD)
}

// 9. Slices
func ejemploSlices() {
	fmt.Println("\n> Slices:")
	var s []string
	s = make([]string, 3)
	s[0] = "a"
	s[1] = "b"
	s[2] = "c"
	fmt.Println("set:", s)

	s = append(s, "d")
	s = append(s, "e", "f")
	fmt.Println("apd:", s)

	l := s[2:5]
	fmt.Println("sl1:", l)

	t := []string{"g", "h", "i"}
	t2 := []string{"g", "h", "i"}
	if slices.Equal(t, t2) {
		fmt.Println("t == t2")
	}
}

// 10. Maps
func ejemploMaps() {
	fmt.Println("\n> Maps:")
	m := make(map[string]int)
	m["k1"] = 7
	m["k2"] = 13
	fmt.Println("map:", m)

	delete(m, "k2")
	fmt.Println("map:", m)

	n := map[string]int{"foo": 1, "bar": 2}
	n2 := map[string]int{"foo": 1, "bar": 2}
	if maps.Equal(n, n2) {
		fmt.Println("n == n2")
	}
}

// 11. Funciones
func plus(a int, b int) int {
	return a + b
}
func plusPlus(a, b, c int) int {
	return a + b + c
}
func ejemploFunciones() {
	fmt.Println("\n> Funciones:")
	res := plus(1, 2)
	fmt.Println("1+2 =", res)
	res = plusPlus(1, 2, 3)
	fmt.Println("1+2+3 =", res)
}

// 12. Retorno Múltiple
func vals() (int, int) {
	return 3, 7
}
func ejemploRetornoMultiple() {
	fmt.Println("\n> Retorno Múltiple:")
	a, b := vals()
	fmt.Println(a)
	fmt.Println(b)
	_, c := vals()
	fmt.Println(c)
}

// 13. Closures
func intSeq() func() int {
	i := 0
	return func() int {
		i++
		return i
	}
}
func ejemploClousures() {
	fmt.Println("\n> Closures:")
	nextInt := intSeq()
	fmt.Println(nextInt())
	fmt.Println(nextInt())
	newInts := intSeq()
	fmt.Println(newInts())
}

// 14. Recursividad
func fact(n int) int {
	if n == 0 {
		return 1
	}
	return n * fact(n - 1)
}
func ejemploRecursividad() {
	fmt.Println("\n> Recursividad:")
	fmt.Println("Fact(7):", fact(7))

	var fib func(n int) int
	fib = func(n int) int {
		if n < 2 {
			return n
		}
		return fib(n-1) + fib(n-2)
	}
	fmt.Println("Fib(7):", fib(7))
}

// 15. Range
func ejemploRange() {
	fmt.Println("\n> Range:")
	nums := []int{2, 3, 4}
	sum := 0
	for _, num := range nums {
		sum += num
	}
	fmt.Println("sum:", sum)

	kvs := map[string]string{"a": "apple", "b": "banana"}
	for k, v := range kvs {
		fmt.Printf("%s -> %s\n", k, v)
	}
}
"""

print("="*70)
print("TESTING USER'S CODE")
print("="*70)

try:
    print("\n1. Lexing...")
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    print(f"   OK - Lexed {len(tokens)} tokens")
    
    print("\n2. Parsing...")
    parser = Parser(tokens)
    program = parser.parse()
    print(f"   OK - Parsed {len(program.declarations)} declarations")
    
    print("\n3. Interpreting...")
    print("-"*70)
    interp = Interpreter(program)
    interp.run()
    print("-"*70)
    print("\n   OK - Success!")
    
except Exception as e:
    print(f"\n   ERROR: {e}")
    import traceback
    traceback.print_exc()
