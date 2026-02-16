#!/usr/bin/env python3
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = """package main
import "fmt"
func main() {
	fmt.Println("Testing")
	nums := []int{2, 3}
	fmt.Println("array:", nums)
}
"""

try:
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    interp = Interpreter(program)
    interp.run()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
