#!/usr/bin/env python3
"""Debug multiple variable declaration"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from ast_nodes import *

code = """package main

func main() {
    var b, c int = 1, 2
    fmt.Println(b, c)
}
"""

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

# Get the main function
main_func = None
for decl in program.declarations:
    if isinstance(decl, FuncDecl) and decl.name == "main":
        main_func = decl
        break

if main_func:
    print(f"Main function has {len(main_func.body.statements)} statements")
    for i, stmt in enumerate(main_func.body.statements):
        print(f"\n  Statement {i}: {type(stmt).__name__}")
        if isinstance(stmt, VarDecl):
            print(f"    Name: {stmt.name}")
            print(f"    Type: {stmt.type_}")
            print(f"    Value: {type(stmt.value).__name__ if stmt.value else None}")

print("\n\nRunning interpreter...")
interpreter = Interpreter(program)
interpreter.run()
print("\nDone!")
