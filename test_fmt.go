package main

import "fmt"

func main() {
	// Test fmt.Println
	x := 42
	y := 3.14
	msg := "hello"

	fmt.Println(x)
	fmt.Println(msg)
	fmt.Println(x, y, msg)
	fmt.Print("Direct print: ")
	fmt.Println("done")

	// Test var inside function
	var a int = 10
	var b, c int = 20, 30
	fmt.Println(a, b, c)
}
