#!/usr/bin/env python3
"""Debug eval_call to see why print_output isn't called"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from ast_nodes import *

code = """package main

func main() {
    fmt.Println(true && false)
}
"""

lexer = Lexer(code)
tokens = lexer.tokenize()

parser = Parser(tokens)
program = parser.parse()

interpreter = Interpreter(program)

# Monkey-patch eval_call to see what's happening
original_eval_call = interpreter.eval_call

def debug_eval_call(call):
    print(f"[EVAL_CALL] Called")
    print(f"  func type: {type(call.func).__name__}")
    
    if isinstance(call.func, FieldExpr):
        print(f"  FieldExpr detected")
        print(f"    expr type: {type(call.func.expr).__name__}")
        if isinstance(call.func.expr, Identifier):
            package = call.func.expr.name
            method = call.func.field
            print(f"    package: {package}")
            print(f"    method: {method}")
            
            if package == "fmt":
                print(f"    fmt detected!")
                if method == "Println":
                    print(f"    Println detected!")
                    print(f"    Args: {len(call.args)}")
                    for i, arg in enumerate(call.args):
                        print(f"      Evaluating arg {i}...")
                        val = interpreter.eval_expression(arg)
                        print(f"        Result: type={val.type}, value={val.value}")
                        str_val = interpreter.to_string(val)
                        print(f"        String: '{str_val}'")
                        print(f"        Calling print_output...")
                        interpreter.print_output(str_val)
                    return Value("nil", None)
    
    return original_eval_call(call)

interpreter.eval_call = debug_eval_call

print("Running interpreter...")
interpreter.run()
print("\nDone!")
