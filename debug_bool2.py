#!/usr/bin/env python3
"""Debug boolean operations with more detail"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from ast_nodes import *

code = """package main

func main() {
    fmt.Println(true && false)
}
"""

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

func_decl = program.declarations[0]
stmt = func_decl.body.statements[0]

print(f"Statement type: {type(stmt).__name__}")
if isinstance(stmt, ExpressionStmt):
    expr = stmt.expr
    print(f"Expression type: {type(expr).__name__}")
    if isinstance(expr, CallExpr):
        print(f"Call function: {type(expr.func).__name__}")
        if isinstance(expr.func, FieldExpr):
            print(f"  Field expr: {expr.func.expr.name if isinstance(expr.func.expr, Identifier) else '?'}")
            print(f"  Field: {expr.func.field}")
        print(f"  Args: {len(expr.args)}")
        for i, arg in enumerate(expr.args):
            print(f"    Arg {i}: {type(arg).__name__}")
            if isinstance(arg, BinaryOp):
                print(f"      Operator: {arg.op}")
                print(f"      Left: {type(arg.left).__name__} = {arg.left.value if hasattr(arg.left, 'value') else '?'}")
                print(f"      Right: {type(arg.right).__name__} = {arg.right.value if hasattr(arg.right, 'value') else '?'}")

print("\nRunning interpreter...")
interpreter = Interpreter(program)

# Monkey-patch print_output to see if it's being called
original_print = interpreter.print_output
def debug_print(msg):
    print(f"[PRINT OUTPUT]: '{msg}'")
    original_print(msg)

interpreter.print_output = debug_print
interpreter.run()

print("\nDone!")
