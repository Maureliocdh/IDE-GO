package main

import "fmt"

func main() {
	var s []string
	fmt.Println("uninit:", s, len(s) == 0)
}
