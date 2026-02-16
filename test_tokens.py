from lexer import Lexer

code = '''msg string = "Hello"'''

lexer = Lexer(code)
tokens = lexer.tokenize()

print("Tokens:")
for i, tok in enumerate(tokens):
    print(f"  {i}: {tok}")
