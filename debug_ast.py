from parser import parse_source
from interpreter import Interpreter
import ast as pyast

code = open(r'c:\Users\maure\Desktop\gi\test_slices.go', encoding='utf-8').read()
try:
    prog = parse_source(code)
    # Find the make([]string, 3) call
    for decl in prog.declarations:
        print(type(decl).__name__, getattr(decl, 'name', ''))
        if hasattr(decl, 'body') and decl.body:
            for stmt in decl.body.statements[:10]:
                print("  STMT:", type(stmt).__name__, end="")
                if hasattr(stmt, 'value') and stmt.value:
                    print(" VAL:", type(stmt.value).__name__, end="")
                    if hasattr(stmt.value, 'type_'):
                        print(" TYPE:", type(stmt.value.type_).__name__, stmt.value.type_)
                print()
except Exception as e:
    import traceback; traceback.print_exc()
