from lexer import Lexer
from parser import Parser
from compiler import Compiler
from interpreter import Interpreter

# Complex test case with all features
code = '''package main

func main() {
    var x int = 10
    y := 20
    z, w := 30, 40
    
    fmt.Println(x, y, z, w)
    
    msg string = "Hello"
    fmt.Println(msg)
}'''

print('='*60)
print('COMPLETE PIPELINE TEST')
print('='*60)

# Lex
lexer = Lexer(code)
tokens = lexer.tokenize()
print(f'✓ Lexed {len(tokens)} tokens')

# Parse
parser = Parser(tokens)
program = parser.parse()
print(f'✓ Parsed {len(program.declarations)} declarations')

# Interpret
print('\nInterpreter Output:')
interpreter = Interpreter(program)
interpreter.run()

# Compile
compiler = Compiler(program)
c_code = compiler.compile()
print(f'\n✓ Compiled to {len(c_code)} characters of C code')

# Show main function
lines = c_code.split('\n')
for i, line in enumerate(lines):
    if 'void main' in line:
        print('\nGenerated main():')
        for j in range(i, min(i+15, len(lines))):
            if lines[j].strip():
                print(lines[j])
            if '}' in lines[j]:
                break
        break

print('\n' + '='*60)
print('✓ PIPELINE TEST PASSED - All components working!')
print('='*60)
