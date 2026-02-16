from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = '''package main
func main() {
    x := 5
    fmt.Println(x)
}'''

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

interpreter = Interpreter(program)

# Trace execute_statement
original_execute_statement = interpreter.execute_statement
calls = []
def traced_execute_statement(stmt):
    calls.append(type(stmt).__name__)
    print(f"execute_statement: {type(stmt).__name__}")
    return original_execute_statement(stmt)

interpreter.execute_statement = traced_execute_statement

# Trace eval_expression
original_eval_expression = interpreter.eval_expression
def traced_eval_expression(expr):
    print(f"  eval_expression: {type(expr).__name__}")
    return original_eval_expression(expr)

interpreter.eval_expression = traced_eval_expression

print("Running interpreter...")
interpreter.run()
print(f"\nStatements executed: {calls}")
