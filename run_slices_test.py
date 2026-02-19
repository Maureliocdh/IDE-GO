from parser import parse_source
from interpreter import Interpreter
import traceback

code = open(r'c:\Users\maure\Desktop\gi\test_slices.go', encoding='utf-8').read()
try:
    ast = parse_source(code)
    interp = Interpreter(ast)
    interp.run()
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
