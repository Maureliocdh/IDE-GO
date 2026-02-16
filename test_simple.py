#!/usr/bin/env python3
"""Test basic Go features"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = """package main

import "fmt"

func main() {
	nums := []int{2, 3, 4}
	fmt.Println("nums:", nums)
	fmt.Println("len:", len(nums))
	
	sum := 0
	for _, num := range nums {
		sum += num
	}
	fmt.Println("sum:", sum)
}
"""

print("=" * 70)
print("Testing array literals and range")
print("=" * 70)

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

print("\nRunning interpreter...")
interpreter = Interpreter(program)
try:
    interpreter.run()
    print("\n✓ Success!")
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
