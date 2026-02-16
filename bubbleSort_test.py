#!/usr/bin/env python3
"""Test bubble sort compilation and execution"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from compiler import Compiler

# Bubble sort code
code = """package main

func bubbleSort(arr []int) {
    n := len(arr);
    for (i := 0; i < n-1; i = i + 1) {
        for (j := 0; j < n-i-1; j = j + 1) {
            if (arr[j] > arr[j+1]) {
                // Intercambio de valores usando una variable temporal
                temp := arr[j];
                arr[j] = arr[j+1];
                arr[j+1] = temp;
            }
        }
    }
}

func main() {
    // Inicialización del arreglo con el nuevo formato soportado
    var datos []int;
    datos = [64, 34, 25, 12, 22, 11, 90];
    
    fmt.Println("Lista Original:", datos);
    
    // Llamada a la función pasándole el arreglo por referencia
    bubbleSort(datos);
    
    fmt.Println("Lista Ordenada:", datos);
}
"""

print("=" * 70)
print("BUBBLE SORT TEST - LEXER")
print("=" * 70)

try:
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    print(f"OK Successfully lexed {len(tokens)} tokens")
    
    print("\n" + "=" * 70)
    print("BUBBLE SORT TEST - PARSER")
    print("=" * 70)
    
    parser = Parser(tokens)
    program = parser.parse()
    print(f"OK Successfully parsed program")
    print(f"  - Package: {program.package.name if program.package else 'None'}")
    print(f"  - Functions: {len([d for d in program.declarations if hasattr(d, '__class__') and d.__class__.__name__ == 'FuncDecl'])}")
    
    print("\n" + "=" * 70)
    print("BUBBLE SORT TEST - INTERPRETER")
    print("=" * 70)
    
    interpreter = Interpreter(program)
    interpreter.run()
    
    print("\n" + "=" * 70)
    print("BUBBLE SORT TEST - COMPILER")
    print("=" * 70)
    
    compiler = Compiler(program)
    c_code = compiler.compile()
    print(f"OK Successfully compiled to C")
    print(f"  - Generated {len(c_code)} characters of C code")
    print("\nGenerated C code:")
    print("-" * 70)
    print(c_code)
    print("-" * 70)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
