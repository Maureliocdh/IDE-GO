"""
parser.py — Parser para Python usando el modulo ast de la stdlib.
"""
import ast
from typing import List


class Parser:
    """Parsea codigo Python y devuelve un arbol AST."""

    def __init__(self, tokens, source: str = ""):
        # tokens se mantiene para compatibilidad con la interfaz anterior
        self.tokens = tokens
        self._source = source

    def set_source(self, source: str):
        self._source = source

    def parse(self):
        """Devuelve un ast.Module o lanza SyntaxError/Exception."""
        if not self._source:
            return None
        try:
            tree = ast.parse(self._source)
            return tree
        except IndentationError as e:
            raise SyntaxError(f"Error de indentacion en linea {e.lineno}: {e.msg}")
        except SyntaxError as e:
            raise SyntaxError(f"Error de sintaxis en linea {e.lineno}: {e.msg}")
        except Exception as e:
            raise Exception(f"Error al parsear: {e}")
