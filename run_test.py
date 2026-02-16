#!/usr/bin/env python3
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = open('test_simplified.go').read()

try:
    print("Lexing...")
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    print(f"✓ Lexed {len(tokens)} tokens")
    
    print("\nParsing...")
    parser = Parser(tokens)
    program = parser.parse()
    print(f"✓ Parsed {len(program.declarations)} declarations")
    
    print("\nRunning interpreter...")
    print("="*70)
    interp = Interpreter(program)
    interp.run()
    print("="*70)
    print("\n✓ Success!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
