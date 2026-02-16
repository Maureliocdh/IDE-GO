#!/usr/bin/env python3
"""
Comprehensive test suite for the Go-to-C compiler/interpreter
Testing all 7 fix categories from the final session
"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from compiler import Compiler

def test_case(name, code, show_output=True):
    """Run a single test case"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    try:
        # Parse
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()
        print("✓ Parsing successful")
        
        # Interpret
        interpreter = Interpreter(program)
        print("Running interpreter:")
        interpreter.run()
        
        # Compile
        compiler = Compiler(program)
        c_code = compiler.compile()
        print("✓ Compilation successful")
        
        if show_output:
            # Show main() from C
            lines = c_code.split('\n')
            in_main = False
            for line in lines:
                if 'void main' in line:
                    in_main = True
                if in_main:
                    print(line)
                    if line.strip() == '}':
                        break
        
        return True
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test Suite
tests_passed = 0
tests_total = 0

# Fix #1: Lexer colon fix (WALRUS token handling)
tests_total += 1
if test_case(
    "Fix #1: WALRUS token (:=) handling",
    '''package main
func main() {
    x := 10
    fmt.Println(x)
}'''):
    tests_passed += 1

# Fix #2: Local VAR/CONST declarations
tests_total += 1
if test_case(
    "Fix #2: Local variable declarations",
    '''package main
func main() {
    var x int = 5
    var y float32 = 3.14
    fmt.Println(x)
}'''):
    tests_passed += 1

# Fix #3: Multiple assignments
tests_total += 1
if test_case(
    "Fix #3: Multiple variable declarations",
    '''package main
func main() {
    var a, b, c int = 1, 2, 3
    fmt.Println(a, b, c)
}''', show_output=False):
    tests_passed += 1

# Fix #4: Short variable declarations with WALRUS
tests_total += 1
if test_case(
    "Fix #4: Short variable declarations (WALRUS)",
    '''package main
func main() {
    x, y := 42, 99
    fmt.Println(x, y)
}'''):
    tests_passed += 1

# Fix #5: Package method calls (fmt.Println)
tests_total += 1
if test_case(
    "Fix #5: Package method support (fmt.Println)",
    '''package main
func main() {
    msg := "World"
    fmt.Println("Hello,", msg)
}'''):
    tests_passed += 1

# Fix #6: Type inference for strings
tests_total += 1
if test_case(
    "Fix #6: String type inference",
    '''package main
func main() {
    name string = "Alice"
    text := "Bob"
    fmt.Println(name, text)
}'''):
    tests_passed += 1

# Fix #7: Proper token consumption
tests_total += 1
if test_case(
    "Fix #7: Token consumption (parse_assign_stmt)",
    '''package main
func main() {
    x := 1
    x = x + 1
    x += 5
    fmt.Println(x)
}'''):
    tests_passed += 1

# Summary
print(f"\n{'='*60}")
print(f"TEST SUMMARY")
print(f"{'='*60}")
print(f"Passed: {tests_passed}/{tests_total}")
if tests_passed == tests_total:
    print("✓ ALL TESTS PASSED!")
else:
    print(f"✗ {tests_total - tests_passed} tests failed")
print(f"{'='*60}\n")
