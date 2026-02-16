#!/usr/bin/env python3
"""Debug for loop parsing with detailed tracing"""

from lexer import Lexer, TokenType
from parser import Parser, ForStmt
from ast_nodes import *

# Simple for loop code
code = """func main() {
    for (i := 0; i < 5; i = i + 1) {
        fmt.Println(i);
    }
}
"""

lexer = Lexer(code)
tokens = lexer.tokenize()

# Create parser but don't call parse yet
parser = Parser(tokens)

# Skip to the for loop
parser.pos = 7  # Position of FOR token

print(f"Starting at position {parser.pos}: {tokens[parser.pos]}")

# Manually step through parse_for_stmt logic
print("\n1. parse_for_stmt called")
print(f"   Current token: {parser.current_token()}")

# Check if FOR already consumed - it should have been
parser.advance()  # Simulate FOR consumption
print("\n2. After consuming FOR, current token:", parser.current_token())

# Now we're at LPAREN
if parser.consume(TokenType.LPAREN):
    print("\n3. Consumed LPAREN, has_parens=True")
    print(f"   Current token: {parser.current_token()}")
    
    # Should be at 'i' 
    # Skip to post-semicolon parsing to debug
    parser.pos = 16  # SEMICOLON after condition
    print(f"\n4. Jumped to position {parser.pos}: {parser.current_token()}")
    
    if parser.consume(TokenType.SEMICOLON):
        print("\n5. Consumed SEMICOLON after condition")
        print(f"   Current token: {parser.current_token()}")
        
        # Should be at 'i' (start of post)
        if not parser.match(TokenType.RBRACE, TokenType.RPAREN, TokenType.LBRACE):
            print("\n6. Parsing post expression")
            print(f"   Current token: {parser.current_token()}")
            
            # Parse 'i'
            post_expr = Identifier(parser.current_token().value)
            parser.advance()
            print(f"   After parsing 'i': {parser.current_token()}")
            
            # Should be at '='
            if parser.match(TokenType.ASSIGN):
                print("\n7. Found ASSIGN operator")
                op = parser.current_token().value
                parser.advance()
                print(f"   After consuming '=': {parser.current_token()}")
                
                # Now manually parse right side: i + 1
                #  Should be at 'i'
                parser.advance()  # skip 'i'
                print(f"   After parsing target: {parser.current_token()}")
                
                parser.advance()  # skip '+'
                print(f"   After +: {parser.current_token()}")
                
                parser.advance()  # skip '1'
                print(f"   After parsing '1': {parser.current_token()}")
                
                # Now we should be at RPAREN
                print(f"\n8. About to expect RPAREN")
                print(f"   Current token: {parser.current_token()}")
                if parser.current_token().type == TokenType.RPAREN:
                    print("   SUCCESS: Found RPAREN!")
                else:
                    print(f"   ERROR: Expected RPAREN but got {parser.current_token().type}")
