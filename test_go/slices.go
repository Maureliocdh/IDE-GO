package main

import "fmt"

func main() {
	flavors := []string{"chocolate", "vanilla", "strawberry", "banana"}

	for _, flav := range flavors {
		switch flav {
		case "strawberry":
			fmt.Println(flav, "is my favorite!")
			fallthrough
		case "vanilla", "chocolate":
			fmt.Println(flav, "is great!")
		default:
			fmt.Println("I've never tried", flav, "before")
		}
	}
}
