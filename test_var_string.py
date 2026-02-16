from lexer import Lexer
from parser import Parser
from ast_nodes import FuncDecl, VarDecl

code = '''package main
func main() {
    var msg string = "Hello"
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
                print(f"    name={stmt.name}")
                print(f"    type_={stmt.type_}")
                print(f"    value={stmt.value}")
