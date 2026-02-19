package main

import "fmt"

func main() {
	// Test 1: Array declaration with size
	var a [5]int
	fmt.Println("emp:", a)

	// Test 2: Array assignment
	a[4] = 100
	fmt.Println("set:", a)
	fmt.Println("get:", a[4])

	// Test 3: Array length
	fmt.Println("len:", len(a))

	// Test 4: Array literal with explicit size
	b := [5]int{1, 2, 3, 4, 5}
	fmt.Println("dcl:", b)

	// Test 5: Array literal with inferred size (...)
	c := [...]int{1, 2, 3, 4, 5}
	fmt.Println("inferred:", c)

	// Test 6: Array literal with another inferred size
	d := [...]int{10, 20, 30}
	fmt.Println("inferred2:", d)

	// Test 7: Simple 2D array
	var twoD [2][3]int
	for i := range 2 {
		for j := range 3 {
			twoD[i][j] = i + j
		}
	}
	fmt.Println("2d: ", twoD)

	// Test 8: 2D array initialization
	twoD2 := [2][3]int{
		{1, 2, 3},
		{4, 5, 6},
	}
	fmt.Println("2d init: ", twoD2)
}
