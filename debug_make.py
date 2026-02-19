from parser import parse_source
from interpreter import Interpreter

code = open(r'c:\Users\maure\Desktop\gi\test_slices.go', encoding='utf-8').read()
ast = parse_source(code)
interp = Interpreter(ast)

# Monkey-patch make to debug
orig_eval_make = interp.eval_make
def debug_eval_make(make_lit):
    result = orig_eval_make(make_lit)
    if result.type_name == "array" and result.value:
        print(f"DEBUG make result: {[(v.type_name, v.value) for v in result.value]}")
    return result
interp.eval_make = debug_eval_make

interp.run()
