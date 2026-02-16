#!/usr/bin/env python3
"""Test more advanced features from prubas.go"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

# Test: For loop with <=
test1 = """package main

func main() {
    i := 1
    for i <= 3 {
        fmt.Println(i)
        i = i + 1
    }
}
"""

# Test: If/else
test2 = """package main

func main() {
    if 7%2 == 0 {
        fmt.Println("7 is even")
    } else {
        fmt.Println("7 is odd")
    }
}
"""

# Test: Boolean operations
test3 = """package main

func main() {
    fmt.Println(true && false)
    fmt.Println(true || false)
    fmt.Println(!true)
}
"""

# Test: Multiple return values (this likely won't work yet)
test4 = """package main

func vals() (int, int) {
    return 3, 7
}

func main() {
    a, b := vals()
    fmt.Println(a)
    fmt.Println(b)
}
"""

# Test: Function with parameters
test5 = """package main

func plus(a int, b int) int {
    return a + b
}

func main() {
    res := plus(1, 2)
    fmt.Println("1+2 =", res)
}
"""

tests = [
    ("For with condition", test1),
    ("If/Else", test2),
    ("Boolean ops", test3),
    ("Multiple return (expected to fail)", test4),
    ("Function with params", test5),
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
        
        print("✓ Parsing successful")
        
        interpreter = Interpreter(program)
        interpreter.run()
        
        print("✓ Interpretation successful")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
