from parser import parse_source
from interpreter import Interpreter

code = open(r'c:\Users\maure\Desktop\gi\test_slices.go', encoding='utf-8').read()
prog = parse_source(code)

main_decl = prog.declarations[0]
# find s = make([]string, 3) - should be stmt index 2
for i, stmt in enumerate(main_decl.body.statements[:7]):
    print(f"STMT {i}: {type(stmt).__name__}")
    if hasattr(stmt, 'values') and stmt.values:
        for v in stmt.values:
            print(f"  value type: {type(v).__name__}")
            if hasattr(v, 'type_'):
                print(f"  v.type_: {type(v.type_).__name__} = {v.type_}")
            if hasattr(v, 'func'):
                print(f"  func: {v.func}")
