from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from ast_nodes import FuncDecl

code = '''package main

func main() {
    var x int = 5
    fmt.Println(x)
}'''

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

# Check declarations
print("Program declarations:")
for decl in program.declarations:
    print(f"  {type(decl).__name__}: {decl.name if hasattr(decl, 'name') else '?'}")

print("\nExecuting interpreter...")
interpreter = Interpreter(program)

# Track environment operations
original_print_output = interpreter.print_output
call_count = [0]
def traced_print_output(msg):
    call_count[0] += 1
    print(f"[TRACE] print_output called: '{msg}'")
    return original_print_output(msg)

interpreter.print_output = traced_print_output

print("Calling interpreter.run()...")
interpreter.run()
print(f"\nTotal print_output calls: {call_count[0]}")
