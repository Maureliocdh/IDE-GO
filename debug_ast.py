from lexer import Lexer
from parser import Parser
from ast_nodes import FuncDecl, CallExpr, FieldExpr, ExpressionStmt

code = '''package main

func main() {
    var x int = 5
    fmt.Println(x)
}'''

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

for decl in program.declarations:
    if isinstance(decl, FuncDecl) and decl.name == 'main':
        print(f"Main function found with {len(decl.body.statements)} statements")
        for i, stmt in enumerate(decl.body.statements):
            print(f"  Statement {i}: {type(stmt).__name__}")
            if isinstance(stmt, ExpressionStmt):
                print(f"    ExpressionStmt.expr type: {type(stmt.expr).__name__}")
                if isinstance(stmt.expr, CallExpr):
                    print(f"      CallExpr.func type: {type(stmt.expr.func).__name__}")
                    if isinstance(stmt.expr.func, FieldExpr):
                        print(f"        FieldExpr.expr: {stmt.expr.func.expr}")
                        print(f"        FieldExpr.field: {stmt.expr.func.field}")
