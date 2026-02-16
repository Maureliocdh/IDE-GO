from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from ast_nodes import AssignStmt, ExpressionStmt

code = '''package main
func main() {
    x := 5
    fmt.Println(x)
}'''

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

from ast_nodes import FuncDecl
for decl in program.declarations:
    if isinstance(decl, FuncDecl) and decl.name == 'main':
        print(f"Main function statements:")
        for i, stmt in enumerate(decl.body.statements):
            print(f"  {i}: {type(stmt).__name__}")
            if isinstance(stmt, AssignStmt):
                print(f"     targets: {stmt.targets}")
                print(f"     values: {stmt.values}")
                print(f"     operator: {stmt.operator}")
            elif isinstance(stmt, ExpressionStmt):
                print(f"     expr type: {type(stmt.expr).__name__}")

print("\nRunning interpreter...")
interpreter = Interpreter(program)

# Detailed tracing
original_eval_call = interpreter.eval_call
def traced_eval_call(call):
    print(f"eval_call: {call.func}")
    result = original_eval_call(call)
    print(f"eval_call returned: {result}")
    return result

interpreter.eval_call = traced_eval_call

# Trace execute_assign
original_execute_assign = interpreter.execute_assign
def traced_execute_assign(assign):
    print(f"execute_assign: targets={assign.targets}, values={assign.values}, op={assign.operator}")
    result = original_execute_assign(assign)
    print(f"execute_assign completed")
    return result

interpreter.execute_assign = traced_execute_assign

interpreter.run()
