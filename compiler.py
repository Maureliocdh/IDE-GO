"""
compiler.py — Analisis y bytecode de codigo Python usando ast y dis.
"""
import ast
import dis
import io


class Compiler:
    """
    Para codigo Python, 'compilar' significa:
    - Analizar la estructura con ast
    - Mostrar el bytecode con dis
    """

    def __init__(self, program, source: str = ""):
        self.program = program
        self.source = source

    def set_source(self, source: str):
        self.source = source

    def compile(self) -> str:
        if not self.source:
            return "# No hay codigo fuente disponible"

        output_lines = []
        output_lines.append("# === ANALISIS DE CODIGO PYTHON ===")
        output_lines.append("")

        # --- Seccion 1: Estructura (AST) ---
        try:
            tree = ast.parse(self.source)
            output_lines.append("# --- Estructura detectada ---")
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = [a.arg for a in node.args.args]
                    output_lines.append(
                        f"#   Funcion:  {node.name}({', '.join(args)})  "
                        f"[linea {node.lineno}]"
                    )
                elif isinstance(node, ast.AsyncFunctionDef):
                    args = [a.arg for a in node.args.args]
                    output_lines.append(
                        f"#   Funcion async: {node.name}({', '.join(args)})  "
                        f"[linea {node.lineno}]"
                    )
                elif isinstance(node, ast.ClassDef):
                    bases = [getattr(b, 'id', '?') for b in node.bases]
                    output_lines.append(
                        f"#   Clase:    {node.name}"
                        + (f"({', '.join(bases)})" if bases else "")
                        + f"  [linea {node.lineno}]"
                    )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        output_lines.append(f"#   import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    names = [a.name for a in node.names]
                    output_lines.append(
                        f"#   from {node.module} import {', '.join(names)}"
                    )
        except SyntaxError as e:
            output_lines.append(f"# Error de sintaxis en linea {e.lineno}: {e.msg}")
            return "\n".join(output_lines)

        output_lines.append("")
        output_lines.append("# --- Bytecode compilado (dis) ---")

        # --- Seccion 2: Bytecode ---
        try:
            code_obj = compile(self.source, "<script.py>", "exec")
            buf = io.StringIO()
            dis.dis(code_obj, file=buf)
            output_lines.append(buf.getvalue())
        except Exception as e:
            output_lines.append(f"# Error generando bytecode: {e}")

        return "\n".join(output_lines)
