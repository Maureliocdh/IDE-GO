#!/usr/bin/env python3
import sys
# Force reimport
if 'lexer' in sys.modules:
    del sys.modules['lexer']
if 'parser' in sys.modules:
    del sys.modules['parser']
if 'interpreter' in sys.modules:
    del sys.modules['interpreter']

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = """package main
import "fmt"

func main() {
    msg := "hello" + " world"
    fmt.Println(msg)

    var b, c int = 10, 20
    fmt.Println("Sum:", b + c)

    for i := 0; i < 3; i++ {
        fmt.Println("Iteration:", i)
    }

    if n := 10; n % 2 == 0 {
        fmt.Println(n, "is even")
    }
}
"""

print("="*70)
print("TESTING USER CODE")
print("="*70)

try:
    print("\n1. Lexing...")
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    print(f"   ✓ {len(tokens)} tokens")
    
    print("\n2. Parsing...")
    parser = Parser(tokens)
    program = parser.parse()
    print(f"   ✓ {len(program.declarations)} declarations")
    
    print("\n3. Executing...")
    print("-"*70)
    interp = Interpreter(program)
    interp.run()
    print("-"*70)
    print("\n✓ ALL TESTS PASSED!")
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
