"""
indentation_checker.py — Validador de indentacion para codigo Python.
Usa ast.parse / IndentationError para detectar problemas.
"""
import ast


class IndentationChecker:
    """Detecta errores de indentacion en codigo Python."""

    def __init__(self, source: str):
        self.source = source

    def check(self):
        """
        Retorna lista de (numero_linea, mensaje) para cada error encontrado.
        Si no hay errores, retorna lista vacia.
        """
        errors = []
        try:
            ast.parse(self.source)
        except IndentationError as e:
            errors.append((e.lineno or 1, f"Error de indentacion: {e.msg}"))
        except SyntaxError:
            pass  # Errores de sintaxis los maneja el parser
        return errors


def check_indentation(source: str):
    """Funcion de conveniencia que retorna lista de (linea, mensaje)."""
    return IndentationChecker(source).check()
