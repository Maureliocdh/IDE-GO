import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    RUNE = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    SLICE = auto()
    # Keywords
    PACKAGE = auto()
    IMPORT = auto()
    FUNC = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    BREAK = auto()
    CONTINUE = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    VAR = auto()
    CONST = auto()
    TYPE = auto()
    STRUCT = auto()
    INTERFACE = auto()
    MAP = auto()
    DEFER = auto()
    GO = auto()
    CHAN = auto()
    SELECT = auto()
    FALLTHROUGH = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    AMPERSAND = auto()
    PIPE = auto()
    CARET = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    AMPNOT = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    STAREQ = auto()
    SLASHEQ = auto()
    PERCENTEQ = auto()
    ANDEQ = auto()
    PIPEEQ = auto()
    CARETEQ = auto()
    LSHIFTEQ = auto()
    RSHIFTEQ = auto()
    ANDNOTEQ = auto()
    NOT = auto()
    AND = auto()
    OR = auto()
    ARROW = auto()
    INC = auto()
    DEC = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    ASSIGN = auto()
    WALRUS = auto()
    ELLIPSIS = auto()
    
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    SEMICOLON = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    QUESTION = auto()
    
    # Special
    IDENTIFIER = auto()
    EOF = auto()
    NEWLINE = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class Lexer:
    KEYWORDS = {
        'package': TokenType.PACKAGE,
        'import': TokenType.IMPORT,
        'func': TokenType.FUNC,
        'return': TokenType.RETURN,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'for': TokenType.FOR,
        'break': TokenType.BREAK,
        'continue': TokenType.CONTINUE,
        'switch': TokenType.SWITCH,
        'case': TokenType.CASE,
        'default': TokenType.DEFAULT,
        'var': TokenType.VAR,
        'const': TokenType.CONST,
        'type': TokenType.TYPE,
        'struct': TokenType.STRUCT,
        'interface': TokenType.INTERFACE,
        'map': TokenType.MAP,
        'defer': TokenType.DEFER,
        'go': TokenType.GO,
        'chan': TokenType.CHAN,
        'select': TokenType.SELECT,
        'fallthrough': TokenType.FALLTHROUGH,
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        'nil': TokenType.NIL,
        'slice': TokenType.SLICE,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def current_char(self) -> Optional[str]:
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]
    
    def peek_char(self, offset=1) -> Optional[str]:
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self):
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
    
    def skip_whitespace(self):
        """Skip spaces, tabs, and carriage returns (but not newlines)"""
        while self.current_char() and self.current_char() in ' \t\r':
            self.advance()
    
    def skip_comment(self):
        if self.current_char() == '/' and self.peek_char() == '/':
            while self.current_char() and self.current_char() != '\n':
                self.advance()
        elif self.current_char() == '/' and self.peek_char() == '*':
            self.advance()
            self.advance()
            while self.current_char():
                if self.current_char() == '*' and self.peek_char() == '/':
                    self.advance()
                    self.advance()
                    break
                self.advance()
    
    def read_string(self, quote_char):
        value = ''
        self.advance()
        while self.current_char() and self.current_char() != quote_char:
            if self.current_char() == '\\':
                self.advance()
                if self.current_char():
                    value += self.current_char()
                    self.advance()
            else:
                value += self.current_char()
                self.advance()
        if self.current_char() == quote_char:
            self.advance()
        return value
    
    def read_number(self):
        value = ''
        has_dot = False
        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            if self.current_char() == '.':
                if has_dot or not self.peek_char() or not self.peek_char().isdigit():
                    break
                has_dot = True
            value += self.current_char()
            self.advance()
        return value, TokenType.FLOAT if has_dot else TokenType.INT
    
    def read_identifier(self):
        value = ''
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            value += self.current_char()
            self.advance()
        return value
    
    def add_token(self, token_type: TokenType, value: str):
        self.tokens.append(Token(token_type, value, self.line, self.column))
    
    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()
            
            if not self.current_char():
                break
            
            if self.current_char() == '/' and (self.peek_char() == '/' or self.peek_char() == '*'):
                self.skip_comment()
                continue
            
            if self.current_char() == '\n':
                self.add_token(TokenType.NEWLINE, '\n')
                self.advance()
            elif self.current_char() == '"':
                value = self.read_string('"')
                self.add_token(TokenType.STRING, value)
            elif self.current_char() == "'":
                value = self.read_string("'")
                self.add_token(TokenType.RUNE, value)
            elif self.current_char().isdigit():
                value, token_type = self.read_number()
                self.add_token(token_type, value)
            elif self.current_char().isalpha() or self.current_char() == '_':
                value = self.read_identifier()
                token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
                self.add_token(token_type, value)
            elif self.current_char() == '+':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.PLUSEQ, '+=')
                    self.advance()
                elif self.current_char() == '+':
                    self.add_token(TokenType.INC, '++')
                    self.advance()
                else:
                    self.add_token(TokenType.PLUS, '+')
            elif self.current_char() == '-':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.MINUSEQ, '-=')
                    self.advance()
                elif self.current_char() == '-':
                    self.add_token(TokenType.DEC, '--')
                    self.advance()
                else:
                    self.add_token(TokenType.MINUS, '-')
            elif self.current_char() == '*':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.STAREQ, '*=')
                    self.advance()
                else:
                    self.add_token(TokenType.STAR, '*')
            elif self.current_char() == '/':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.SLASHEQ, '/=')
                    self.advance()
                else:
                    self.add_token(TokenType.SLASH, '/')
            elif self.current_char() == '%':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.PERCENTEQ, '%=')
                    self.advance()
                else:
                    self.add_token(TokenType.PERCENT, '%')
            elif self.current_char() == '=':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.EQ, '==')
                    self.advance()
                else:
                    self.add_token(TokenType.ASSIGN, '=')
            elif self.current_char() == '!':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.NEQ, '!=')
                    self.advance()
                else:
                    self.add_token(TokenType.NOT, '!')
            elif self.current_char() == '<':
                self.advance()
                if self.current_char() == '<':
                    self.advance()
                    if self.current_char() == '=':
                        self.add_token(TokenType.LSHIFTEQ, '<<=')
                        self.advance()
                    else:
                        self.add_token(TokenType.LSHIFT, '<<')
                elif self.current_char() == '=':
                    self.add_token(TokenType.LTE, '<=')
                    self.advance()
                elif self.current_char() == '-':
                    self.advance()
                    self.add_token(TokenType.ARROW, '<-')
                else:
                    self.add_token(TokenType.LT, '<')
            elif self.current_char() == '>':
                self.advance()
                if self.current_char() == '>':
                    self.advance()
                    if self.current_char() == '=':
                        self.add_token(TokenType.RSHIFTEQ, '>>=')
                        self.advance()
                    else:
                        self.add_token(TokenType.RSHIFT, '>>')
                elif self.current_char() == '=':
                    self.add_token(TokenType.GTE, '>=')
                    self.advance()
                else:
                    self.add_token(TokenType.GT, '>')
            elif self.current_char() == '&':
                self.advance()
                if self.current_char() == '&':
                    self.add_token(TokenType.AND, '&&')
                    self.advance()
                elif self.current_char() == '=':
                    self.add_token(TokenType.ANDEQ, '&=')
                    self.advance()
                elif self.current_char() == '^':
                    self.advance()
                    if self.current_char() == '=':
                        self.add_token(TokenType.ANDNOTEQ, '&^=')
                        self.advance()
                    else:
                        self.add_token(TokenType.AMPNOT, '&^')
                else:
                    self.add_token(TokenType.AMPERSAND, '&')
            elif self.current_char() == '|':
                self.advance()
                if self.current_char() == '|':
                    self.add_token(TokenType.OR, '||')
                    self.advance()
                elif self.current_char() == '=':
                    self.add_token(TokenType.PIPEEQ, '|=')
                    self.advance()
                else:
                    self.add_token(TokenType.PIPE, '|')
            elif self.current_char() == '^':
                self.advance()
                if self.current_char() == '=':
                    self.add_token(TokenType.CARETEQ, '^=')
                    self.advance()
                else:
                    self.add_token(TokenType.CARET, '^')
            elif self.current_char() == '(':
                self.add_token(TokenType.LPAREN, '(')
                self.advance()
            elif self.current_char() == ')':
                self.add_token(TokenType.RPAREN, ')')
                self.advance()
            elif self.current_char() == '{':
                self.add_token(TokenType.LBRACE, '{')
                self.advance()
            elif self.current_char() == '}':
                self.add_token(TokenType.RBRACE, '}')
                self.advance()
            elif self.current_char() == '[':
                self.add_token(TokenType.LBRACKET, '[')
                self.advance()
            elif self.current_char() == ']':
                self.add_token(TokenType.RBRACKET, ']')
                self.advance()
            elif self.current_char() == ';':
                self.add_token(TokenType.SEMICOLON, ';')
                self.advance()
            elif self.current_char() == ',':
                self.add_token(TokenType.COMMA, ',')
                self.advance()
            elif self.current_char() == '.':
                self.advance()
                if self.current_char() == '.' and self.peek_char() == '.':
                    self.add_token(TokenType.ELLIPSIS, '...')
                    self.advance()
                    self.advance()
                else:
                    self.add_token(TokenType.DOT, '.')
            elif self.current_char() == ':':
                self.advance()  # Consume the ':' character
                if self.current_char() == '=':
                    # WALRUS token := found
                    self.add_token(TokenType.WALRUS, ':=')
                    self.advance()  # Consume the '=' character
                else:
                    # Just COLON token ':'
                    self.add_token(TokenType.COLON, ':')
                # NOTE: No extra advance() here - the main loop will handle whitespace
            elif self.current_char() == '?':
                self.add_token(TokenType.QUESTION, '?')
                self.advance()
            else:
                self.advance()
        
        self.add_token(TokenType.EOF, '')
        return self.tokens