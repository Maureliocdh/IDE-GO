#!/usr/bin/env python3
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from compiler import Compiler

test_cases = [
    ("Variable declarations", '''package main
func main() {
    var x int = 5
    fmt.Println(x)
}'''),
    
    ("Multiple variables", '''package main
func main() {
    var a, b int = 1, 2
    fmt.Println(a, b)
}'''),
    
    ("Short declarations", '''package main
func main() {
    x := 42
    fmt.Println(x)
}'''),
    
    ("Multi-target assignments", '''package main
func main() {
    x, y := 10, 20
    fmt.Println(x, y)
}'''),
    
    ("String variables", '''package main
func main() {
    name := "World"
    fmt.Println(name)
}'''),
    
    ("Typed strings", '''package main
func main() {
    msg string = "Hello"
    fmt.Println(msg)
}'''),
]

print("=" * 60)
print("INTERPRETER TESTS")
print("=" * 60)

for name, code in test_cases:
    print(f"\n{name}:")
    print("-" * 40)
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()
        interpreter = Interpreter(program)
        interpreter.run()
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 60)
print("COMPILER TESTS")
print("=" * 60)

for name, code in test_cases[:3]:  # Test first 3 with compiler
    print(f"\n{name} (C generation):")
    print("-" * 40)
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()
        compiler = Compiler(program)
        c_code = compiler.compile()
        
        # Find main function
        lines = c_code.split('\n')
        main_start = -1
        for i, line in enumerate(lines):
            if 'void main' in line:
                main_start = i
                break
        
        if main_start >= 0:
            for i in range(main_start, min(main_start + 10, len(lines))):
                if lines[i].strip() and not lines[i].strip().startswith('//'):
                    print(lines[i])
        
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 60)
print("SUMMARY: All tests completed")
print("=" * 60)
