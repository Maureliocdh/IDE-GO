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

# Trace execute_block
original_execute_block = interpreter.execute_block
def traced_execute_block(block):
    print(f"execute_block: {len(block.statements)} statements")
    for i, stmt in enumerate(block.statements):
        print(f"  Processing statement {i}: {type(stmt).__name__}")
    return original_execute_block(block)

interpreter.execute_block = traced_execute_block

# Trace call_function
original_call_function = interpreter.call_function
def traced_call_function(func_decl, args):
    print(f"call_function: {func_decl.name}")
    result = original_call_function(func_decl, args)
    print(f"call_function completed: {func_decl.name}")
    return result

interpreter.call_function = traced_call_function

# Trace execute_statement
original_execute_statement = interpreter.execute_statement
def traced_execute_statement(stmt):
    print(f"    -> execute_statement: {type(stmt).__name__}")
    return original_execute_statement(stmt)

interpreter.execute_statement = traced_execute_statement

print("Running interpreter...")
interpreter.run()
