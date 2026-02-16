from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from ast_nodes import FuncDecl, VarDecl

code = '''package main
func main() {
    msg string = "Hello"
    fmt.Println(msg)
}'''

lexer = Lexer(code)
tokens = lexer.tokenize()
parser = Parser(tokens)
program = parser.parse()

print("Parsed AST:")
for decl in program.declarations:
    if isinstance(decl, FuncDecl) and decl.name == 'main':
        for i, stmt in enumerate(decl.body.statements):
            print(f"  Statement {i}: {type(stmt).__name__}")
            if isinstance(stmt, VarDecl):
                print(f"    name={stmt.name}, type_={stmt.type_}, value={stmt.value}")

print("\nRunning interpreter:")
interpreter = Interpreter(program)
interpreter.run()
