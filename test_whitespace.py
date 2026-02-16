#!/usr/bin/env python3
"""Test whitespace and indentation handling"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

# Test 1: Multiple spaces and tabs between tokens
test1 = """package main

import    "fmt"

func    main()    {
    x    :=    10
    y    :=    20
    fmt.Println(x    +    y)
}
"""

# Test 2: Braces on different lines with various spacing
test2 = """package main

import "fmt"

func calculate(a int, b int) int
{
    result := a + b
    return result
}

func main()
{
    value := calculate(5, 10)
    fmt.Println("Result:", value)
}
"""

# Test 3: Multiple empty lines between statements
test3 = """package main

import "fmt"


func main() {


    x := 10


    y := 20


    fmt.Println(x + y)


}
"""

# Test 4: Mixed indentation styles (tabs and spaces)
test4 = """package main

import "fmt"

func main() {
\tx := 10
    y := 20
\t\tfor i := 0; i < 3; i++ {
    \t\tfmt.Println(i)
\t\t}
    fmt.Println(x + y)
}
"""

# Test 5: Newlines before and after braces in control structures
test5 = """package main

import "fmt"

func main() 
{
    if x := 10; x > 5
    {
        fmt.Println("x is greater than 5")
    }
    
    for i := 0; i < 3; i++
    {
        fmt.Println(i)
    }
}
"""

tests = [
    ("Multiple spaces/tabs", test1),
    ("Braces on new lines", test2),
    ("Multiple empty lines", test3),
    ("Mixed indentation", test4),
    ("Newlines around braces", test5)
]

print("=" * 70)
print("WHITESPACE HANDLING TESTS")
print("=" * 70)

for test_name, code in tests:
    print(f"\n[Test: {test_name}]")
    try:
        # Lexing
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        print(f"  Lexing: OK ({len(tokens)} tokens)")
        
        # Parsing
        parser = Parser(tokens)
        program = parser.parse()
        print(f"  Parsing: OK ({len(program.declarations)} declarations)")
        
        # Interpreting
        interp = Interpreter(program)
        interp.run()
        print(f"  Execution: OK")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print("ALL WHITESPACE TESTS COMPLETED")
print("=" * 70)
