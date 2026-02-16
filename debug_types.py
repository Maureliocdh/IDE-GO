from lexer import Lexer
from parser import Parser
from ast_nodes import FuncDecl

code = open('test_string.go').read()

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

# Find the main function
for decl in program.declarations:
    if isinstance(decl, FuncDecl) and decl.name == 'main':
        for stmt in decl.body.statements:
            if hasattr(stmt, 'type_'):
                print(f'VarDecl: name={stmt.name}, type_={stmt.type_}, type(type_)={type(stmt.type_).__name__}')
                if hasattr(stmt.type_, 'name'):
                    print(f'  type_.name={stmt.type_.name}')
                # Also check the value
                if hasattr(stmt, 'value'):
                    print(f'  value={stmt.value}, type(value)={type(stmt.value).__name__}')
                    if hasattr(stmt.value, 'type_'):
                        print(f'  value.type_={stmt.value.type_}')

