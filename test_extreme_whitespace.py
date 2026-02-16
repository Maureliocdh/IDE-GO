#!/usr/bin/env python3
"""Extreme whitespace stress test"""

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

# Extreme formatting with excessive whitespace
extreme_test = """package     main


import     "fmt"




func     calculate  (  a    int  ,   b    int  )    int


{


    result    :=    a    +    b


    return    result


}




func     main  (  )


{


    if     x    :=    10   ;   x    >    5


    {


        for     i    :=    0   ;   i    <    3   ;   i++


        {


            fmt.Println  (  i  )


        }


    }


    value    :=    calculate  (  15  ,   25  )


    fmt.Println  (  "Result:"  ,   value  )


}
"""

print("=" * 70)
print("EXTREME WHITESPACE STRESS TEST")
print("=" * 70)
print("\nTesting code with excessive whitespace, newlines, and spacing...\n")

try:
    # Lexing
    print("1. Lexing...")
    lexer = Lexer(extreme_test)
    tokens = lexer.tokenize()
    print(f"   OK - Generated {len(tokens)} tokens")
    
    # Parsing
    print("\n2. Parsing...")
    parser = Parser(tokens)
    program = parser.parse()
    print(f"   OK - Parsed {len(program.declarations)} declarations")
    
    # Interpreting
    print("\n3. Executing...")
    print("-" * 70)
    interp = Interpreter(program)
    interp.run()
    print("-" * 70)
    print("\n   OK - Execution successful!")
    
    print("\n" + "=" * 70)
    print("✓ STRESS TEST PASSED")
    print("The compiler handles extreme whitespace variations flawlessly!")
    print("=" * 70)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
