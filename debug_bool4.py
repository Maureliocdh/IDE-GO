#!/usr/bin/env python3
"""Debug eval_expression for boolean operations"""

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

interpreter = Interpreter(program)

# Get the BinaryOp argument from the parsed AST
func_decl = program.declarations[0]
stmt = func_decl.body.statements[0]
call_expr = stmt.expr
arg = call_expr.args[0]

print(f"Argument type: {type(arg).__name__}")
print(f"Binary operator: {arg.op}")
print(f"Left: {type(arg.left).__name__} = {arg.left.value}")
print(f"Right: {type(arg.right).__name__} = {arg.right.value}")

print("\nEvaluating boolean operation...")
try:
    result = interpreter.eval_expression(arg)
    print(f"Result: type_name={result.type_name}, value={result.value}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")
