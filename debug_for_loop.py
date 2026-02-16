#!/usr/bin/env python3
"""Debug for loop parsing"""

from lexer import Lexer
from parser import Parser

# Simple for loop code
code = """
func main() {
    for (i := 0; i < 5; i = i + 1) {
        fmt.Println(i);
    }
}
"""

lexer = Lexer(code)
tokens = lexer.tokenize()

print("=" * 70)
print("TOKENS")
print("=" * 70)
for i, token in enumerate(tokens):
    print(f"{i:3d}: {token.type.name:15s} = {repr(token.value)}")

print("\n" + "=" * 70)
print("PARSING")
print("=" * 70)

try:
    parser = Parser(tokens)
    program = parser.parse()
    print("OK: Successfully parsed!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
