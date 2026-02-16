#!/usr/bin/env python3
"""Test individual code snippets from prubas.go"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from compiler import Compiler

# Test 1: Basic hello world
test1 = """package main

func main() {
    fmt.Println("hello world")
}
"""

# Test 2: String concatenation
test2 = """package main

func main() {
    fmt.Println("go" + "lang")
}
"""

# Test 3: Arithmetic
test3 = """package main

func main() {
    fmt.Println("1+1 =", 1+1)
    fmt.Println("7.0/3.0 =", 7.0/3.0)
}
"""

# Test 4: Multiple var declaration
test4 = """package main

func main() {
    var b, c int = 1, 2
    fmt.Println(b, c)
}
"""

# Test 5: For loop with increment
test5 = """package main

func main() {
    for j := 0; j < 3; j++ {
        fmt.Println(j)
    }
}
"""

tests = [
    ("Hello World", test1),
    ("String Concatenation", test2),
    ("Arithmetic", test3),
    ("Multiple Var Declaration", test4),
    ("For Loop with ++", test5),
]

for name, code in tests:
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        program = parser.parse()
        
        print("✓ Lexing and parsing successful")
        
        interpreter = Interpreter(program)
        interpreter.run()
        
        print("✓ Interpretation successful")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
