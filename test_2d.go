package main

import "fmt"

func main() {
	var twoD [2][3]int
	fmt.Println("before:", twoD)

	twoD[0][0] = 99
	fmt.Println("after:", twoD)

	for i := range 2 {
		for j := range 3 {
			twoD[i][j] = i + j
		}
	}
	fmt.Println("final:", twoD)
}
