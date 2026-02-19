package main

import "fmt"

func main() {
	// Test 1: Array with indexed initialization
	fmt.Println("=== Test 1: Indexed Array ===")
	a := [...]int{100, 3: 400, 500}
	fmt.Println("Array:", a)
	fmt.Println("Length:", len(a))
	fmt.Println("a[0]:", a[0])
	fmt.Println("a[1]:", a[1])
	fmt.Println("a[2]:", a[2])
	fmt.Println("a[3]:", a[3])
	fmt.Println("a[4]:", a[4])

	// Test 2: Multiple indexed elements
	fmt.Println("\n=== Test 2: Multiple Indices ===")
	b := [...]int{0: 10, 2: 20, 4: 40, 6: 60}
	fmt.Println("Array:", b)
	fmt.Println("Length:", len(b))

	// Test 3: Mixed indexed and sequential
	fmt.Println("\n=== Test 3: Mixed ===")
	c := [...]int{1, 2, 5: 50, 60, 70}
	fmt.Println("Array:", c)
	fmt.Println("c[0]:", c[0])
	fmt.Println("c[1]:", c[1])
	fmt.Println("c[5]:", c[5])
	fmt.Println("c[6]:", c[6])
	fmt.Println("c[7]:", c[7])

	// Test 4: Array with explicit size and indices
	fmt.Println("\n=== Test 4: Explicit Size ===")
	d := [10]int{1: 11, 5: 55, 9: 99}
	fmt.Println("Array:", d)
	fmt.Println("Length:", len(d))

	// Test 5: Original gobyexample.com case
	fmt.Println("\n=== Test 5: Original Example ===")
	e := [...]int{100, 3: 400, 500}
	fmt.Println("idx:", e)

	fmt.Println("\n=== All tests completed ===")
}
