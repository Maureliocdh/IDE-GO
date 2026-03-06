"""
assembly_generator.py — Genera TAC (AST dump) y bytecode Python.
TAC  → ast.dump  (Codigo Intermedio)
ASM  → dis.dis   (Bytecode / pseudo-ensamblador)
"""
import ast
import dis
import io


class AssemblyGenerator:

    def __init__(self, program, source: str = ""):
        self.program = program
        self.source = source

    def set_source(self, source: str):
        self.source = source

    def generate(self):
        """Retorna tupla (tac_code: str, asm_code: str)."""
        tac_code = ""
        asm_code = ""

        if not self.source:
            return "# Sin codigo fuente", "# Sin codigo fuente"

        # ── TAC: Arbol Sintactico Abstracto (AST dump) ──────────────────────
        try:
            tree = ast.parse(self.source)
            tac_code = "=== ARBOL SINTACTICO ABSTRACTO (AST) ===\n\n"
            tac_code += ast.dump(tree, indent=2)
        except SyntaxError as e:
            tac_code = f"Error de sintaxis en linea {e.lineno}: {e.msg}"
        except Exception as e:
            tac_code = f"Error generando AST: {e}"

        # ── ASM: Bytecode Python (dis) ───────────────────────────────────────
        try:
            code_obj = compile(self.source, "<script.py>", "exec")
            buf = io.StringIO()
            dis.dis(code_obj, file=buf)
            asm_code = "=== BYTECODE PYTHON (dis) ===\n\n"
            asm_code += buf.getvalue()
        except SyntaxError as e:
            asm_code = f"Error de sintaxis en linea {e.lineno}: {e.msg}"
        except Exception as e:
            asm_code = f"Error generando bytecode: {e}"

        return tac_code, asm_code
