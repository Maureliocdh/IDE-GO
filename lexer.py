"""
lexer.py — Analizador lexico para Python.
Usa el modulo tokenize de la biblioteca estandar.
"""
import tokenize
import io
import keyword
from enum import Enum, auto
from dataclasses import dataclass
from typing import List


class TokenType(Enum):
    KEYWORD    = auto()
    NAME       = auto()
    NUMBER     = auto()
    STRING     = auto()
    COMMENT    = auto()
    OP         = auto()
    NEWLINE    = auto()
    INDENT     = auto()
    DEDENT     = auto()
    ERRORTOKEN = auto()
    OTHER      = auto()


@dataclass
class Token:
    type:  TokenType
    value: str
    line:  int


class Lexer:
    """Tokeniza codigo Python usando el modulo tokenize de la stdlib."""

    def __init__(self, source: str):
        self.source = source

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        try:
            source_io = io.StringIO(self.source)
            for tok in tokenize.generate_tokens(source_io.readline):
                if tok.type == tokenize.ENDMARKER:
                    break
                if tok.type in (tokenize.NL, tokenize.ENCODING):
                    continue

                if tok.type == tokenize.COMMENT:
                    tokens.append(Token(TokenType.COMMENT, tok.string, tok.start[0]))
                    continue

                if tok.type == tokenize.NAME and keyword.iskeyword(tok.string):
                    ttype = TokenType.KEYWORD
                elif tok.type == tokenize.NAME:
                    ttype = TokenType.NAME
                elif tok.type == tokenize.NUMBER:
                    ttype = TokenType.NUMBER
                elif tok.type == tokenize.STRING:
                    ttype = TokenType.STRING
                elif tok.type == tokenize.OP:
                    ttype = TokenType.OP
                elif tok.type == tokenize.NEWLINE:
                    ttype = TokenType.NEWLINE
                elif tok.type == tokenize.INDENT:
                    ttype = TokenType.INDENT
                elif tok.type == tokenize.DEDENT:
                    ttype = TokenType.DEDENT
                elif tok.type == tokenize.ERRORTOKEN:
                    ttype = TokenType.ERRORTOKEN
                else:
                    ttype = TokenType.OTHER

                tokens.append(Token(type=ttype, value=tok.string, line=tok.start[0]))

        except tokenize.TokenizeError as e:
            lineno = e.args[1][0] if len(e.args) > 1 else 0
            raise Exception(f"Error lexico en linea {lineno}: {e.args[0]}")

        return tokens
