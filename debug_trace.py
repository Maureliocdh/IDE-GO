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

interpreter = Interpreter(program)

# Trace eval_expression
original_eval_call = interpreter.eval_call
def traced_eval_call(call):
    print(f"[TRACE] eval_call called with: {call}")
    result = original_eval_call(call)
    print(f"[TRACE] eval_call returned: {result}")
    return result

interpreter.eval_call = traced_eval_call

# Trace eval_expression
original_eval_expression = interpreter.eval_expression
call_stack = []
def traced_eval_expression(expr):
    indent = "  " * len(call_stack)
    print(f"{indent}[TRACE] eval_expression: {type(expr).__name__}")
    call_stack.append(True)
    try:
        result = original_eval_expression(expr)
        print(f"{indent}[TRACE] -> {result}")
        return result
    finally:
        call_stack.pop()

interpreter.eval_expression = traced_eval_expression

# Trace execute_statement
original_execute_statement = interpreter.execute_statement
def traced_execute_statement(stmt):
    print(f"[TRACE] execute_statement: {type(stmt).__name__}")
    return original_execute_statement(stmt)

interpreter.execute_statement = traced_execute_statement

print("Running interpreter...")
interpreter.run()
