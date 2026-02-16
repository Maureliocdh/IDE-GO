#!/usr/bin/env python3
"""Debug multi-assignment parsing"""

from lexer import Lexer
from parser import Parser
from ast_nodes import *

code = """package main

func vals() (int, int) {
    return 3, 7
}

func main() {
    a, b := vals()
    fmt.Println(a)
    fmt.Println(b)
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
        if isinstance(stmt, AssignStmt):
            print(f"    Targets: {len(stmt.targets)}")
            for j, target in enumerate(stmt.targets):
                print(f"      Target {j}: {type(target).__name__}", end="")
                if isinstance(target, Identifier):
                    print(f" - {target.name}")
                else:
                    print()
            print(f"    Values: {len(stmt.values)}")
            for j, value in enumerate(stmt.values):
                print(f"      Value {j}: {type(value).__name__}")
            print(f"    Operator: {stmt.operator}")
