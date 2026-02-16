#!/usr/bin/env python3
"""Debug boolean operations"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = """package main

func main() {
    fmt.Println(true && false)
    fmt.Println(true || false)
    fmt.Println(!true)
}
"""

print("=" * 70)
print("BOOLEAN OPERATIONS TEST")
print("=" * 70)

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

print(f"Parsed {len(program.declarations)} declarations")
for decl in program.declarations:
    print(f"  - {type(decl).__name__}: {decl.name if hasattr(decl, 'name') else '?'}")
    if hasattr(decl, 'body') and decl.body:
        print(f"    Body has {len(decl.body.statements)} statements")
        for i, stmt in enumerate(decl.body.statements):
            print(f"      Statement {i}: {type(stmt).__name__}")

print("\nRunning interpreter...")
interpreter = Interpreter(program)
interpreter.run()

print("\nDone!")
