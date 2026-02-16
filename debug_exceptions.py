from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
import traceback

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

# Trace execute_block with exception handling
original_execute_block = interpreter.execute_block
def traced_execute_block(block):
    print(f"execute_block: {len(block.statements)} statements")
    for i, stmt in enumerate(block.statements):
        try:
            print(f"  Executing statement {i}: {type(stmt).__name__}")
            interpreter.execute_statement(stmt)
            print(f"    -> Completed")
        except Exception as e:
            print(f"    -> EXCEPTION: {e}")
            traceback.print_exc()
            raise

interpreter.execute_block = traced_execute_block

print("Running interpreter...")
try:
    interpreter.run()
except Exception as e:
    print(f"FATAL ERROR: {e}")
    traceback.print_exc()
