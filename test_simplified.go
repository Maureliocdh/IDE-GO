package main

import (
	"fmt"
	"maps"
	"math"
	"slices"
)

func main() {
	fmt.Println("--- Testing Supported Features ---")

	// Test variables
	fmt.Println("\n> Variables:")
	var a = "initial"
	fmt.Println(a)

	var b, c int = 1, 2
	fmt.Println(b, c)

	f := "apple"
	fmt.Println(f)

	// Test constants
	const n = 500000000
	const d = 3e20 / n
	fmt.Println("\n> Constants:")
	fmt.Println(d)
	fmt.Println(int64(d))
	fmt.Println(math.Sin(n))

	// Test for loops
	fmt.Println("\n> For loops:")
	for i := range 3 {
		fmt.Println("range", i)
	}

	// Test arrays
	fmt.Println("\n> Arrays:")
	nums := []int{2, 3, 4}
	sum := 0
	for _, num := range nums {
		sum += num
	}
	fmt.Println("sum:", sum)
	fmt.Println("len:", len(nums))

	// Test slices Equal
	fmt.Println("\n> Slices:")
	t := []string{"g", "h", "i"}
	t2 := []string{"g", "h", "i"}
	if slices.Equal(t, t2) {
		fmt.Println("t == t2")
	}

	// Test maps
	fmt.Println("\n> Maps:")
	m := make(map[string]int)
	m["k1"] = 7
	m["k2"] = 13
	fmt.Println("map:", m)

	n2 := map[string]int{"foo": 1, "bar": 2}
	n3 := map[string]int{"foo": 1, "bar": 2}
	if maps.Equal(n2, n3) {
		fmt.Println("n2 == n3")
	}

	// Test functions
	fmt.Println("\n> Functions:")
	res := plus(1, 2)
	fmt.Println("1+2 =", res)

	// Test multiple return
	fmt.Println("\n> Multiple returns:")
	a1, b1 := vals()
	fmt.Println(a1)
	fmt.Println(b1)

	_, c1 := vals()
	fmt.Println(c1)

	fmt.Println("\n--- Tests Complete ---")
}

func plus(a int, b int) int {
	return a + b
}

func vals() (int, int) {
	return 3, 7
}
