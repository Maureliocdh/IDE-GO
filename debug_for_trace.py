#!/usr/bin/env python3
"""Debug which branch is broken"""

from lexer import Lexer, TokenType
from parser import Parser

code = """func main() {
    for (i := 0; i < 5; i = i + 1) {
        fmt.Println(i);
    }
}
"""

lexer = Lexer(code)
tokens = lexer.tokenize()

# Monkey-patch the parser to add debug output
original_parse_for = Parser.parse_for_stmt

def debug_parse_for(self):
    print(f"DEBUG: Entering parse_for_stmt at pos {self.pos}: {self.current_token()}")
   
    # Start of method
    has_parens = self.consume(TokenType.LPAREN)
    print(f"DEBUG: has_parens={has_parens}, now at pos {self.pos}: {self.current_token()}")
    
    if not has_parens and self.match(TokenType.LBRACE):
        print("DEBUG: Matched LBRACE, returning simple ForStmt")
        return ForStmt(None, None, None, self.parse_block())
    
    init = None
    condition = None
    post = None
    
    print(f"DEBUG: Checking first part - match SEMICOLON? {self.match(TokenType.SEMICOLON)}")
    
    if not self.match(TokenType.SEMICOLON):
        print(f"DEBUG: Parsing init expression")
        expr = self.parse_expression()
        print(f"DEBUG: Parsed expr, now at pos {self.pos}: {self.current_token()}")
        
        if self.match(TokenType.WALRUS, TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ, 
                     TokenType.STAREQ, TokenType.SLASHEQ):
            print(f"DEBUG: Found assignment operator {self.current_token().value}")
            op = self.current_token().value
            self.advance()
            value = self.parse_expression()
            print(f"DEBUG: Parsed value, now at pos {self.pos}: {self.current_token()}")
            
            from ast_nodes import AssignStmt
            init = AssignStmt([expr], [value], op)
            
            print(f"DEBUG: After creating init, checking for semicolon. has_parens={has_parens}, match SEMICOLON? {self.match(TokenType.SEMICOLON)}")
            
            if has_parens or self.match(TokenType.SEMICOLON):
                print(f"DEBUG: Expecting SEMICOLON")
                self.expect(TokenType.SEMICOLON)
                print(f"DEBUG: After expecting SEMICOLON, pos {self.pos}: {self.current_token()}")
    
    print(f"DEBUG: After init parsing, init={init}, pos {self.pos}: {self.current_token()}")
    print(f"DEBUG: Checking C-style loop branch: init={init is not None}, match SEMICOLON? {self.match(TokenType.SEMICOLON)}")
    
    # Parse condition if we're in C-style loop
    if init or self.match(TokenType.SEMICOLON):
        print(f"DEBUG: Entered C-style loop branch")
        if self.consume(TokenType.SEMICOLON):
            print(f"DEBUG: Consumed SEMICOLON (should not happen if already consumed!), pos {self.pos}: {self.current_token()}")
        else:
            print(f"DEBUG: Did NOT consume SEMICOLON, pos {self.pos}: {self.current_token()}")
    
    print(f"DEBUG: About to expect RPAREN at pos {self.pos}: {self.current_token()}")
    
    if has_parens:
        self.expect(TokenType.RPAREN)
    
    return None  # Would return the full ForStmt

Parser.parse_for_stmt = debug_parse_for

parser = Parser(tokens)
try:
    program = parser.parse()
    print("SUCCESS!")
except Exception as e:
    print(f"ERROR: {e}")
