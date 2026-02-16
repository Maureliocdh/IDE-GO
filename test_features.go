package main

import "fmt"

func main() {
	fmt.Println("--- Testing Basic Features ---")

	// Test 1: Variables
	fmt.Println("\n> Variables:")
	var a = "initial"
	fmt.Println(a)

	var b, c int = 1, 2
	fmt.Println(b, c)

	f := "apple"
	fmt.Println(f)

	// Test 2: Constants
	const n = 500000000
	fmt.Println("\n> Constants:")
	fmt.Println(n)

	// Test 3: For loops
	fmt.Println("\n> For loops:")
	for i := range 3 {
		fmt.Println("range", i)
	}

	// Test 4: Arrays and len
	fmt.Println("\n> Arrays:")
	nums := []int{2, 3, 4}
	sum := 0
	for _, num := range nums {
		sum += num
	}
	fmt.Println("sum:", sum)
	fmt.Println("len:", len(nums))

	// Test 5: Maps
	fmt.Println("\n> Maps:")
	m := make(map[string]int)
	m["k1"] = 7
	m["k2"] = 13
	fmt.Println("map:", m)

	// Test 6: Multiple returns with blank identifier
	fmt.Println("\n> Multiple returns:")
	_, c2 := vals()
	fmt.Println(c2)

	fmt.Println("\n--- Tests Complete ---")
}

func vals() (int, int) {
	return 3, 7
}
