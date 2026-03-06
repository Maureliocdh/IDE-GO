"""
c_generator.py — Transpiler Python → C99.
Convierte un subconjunto de Python a codigo C equivalente usando el modulo ast.
"""
import ast
import sys
from typing import List, Optional, Set, Dict


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de tipos
# ──────────────────────────────────────────────────────────────────────────────

_INT_OPS   = (ast.Add, ast.Sub, ast.Mult, ast.Mod, ast.FloorDiv,
              ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)
_FLOAT_OPS = (ast.Div,)

_PY_BUILTIN_MAP = {
    "abs":   "abs",
    "len":   "strlen",
    "ord":   "(int)",
    "chr":   "(char)",
    "exit":  "exit",
}

_OP_MAP = {
    ast.Add:  "+",  ast.Sub:  "-",  ast.Mult: "*",  ast.Div:  "/",
    ast.Mod:  "%",  ast.Pow:  "",   ast.FloorDiv: "/",
    ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^",
    ast.LShift: "<<", ast.RShift: ">>",
}
_UNARY_OP_MAP = {
    ast.UAdd: "+", ast.USub: "-", ast.Not: "!", ast.Invert: "~",
}
_CMP_OP_MAP = {
    ast.Eq: "==", ast.NotEq: "!=",
    ast.Lt: "<",  ast.LtE:   "<=",
    ast.Gt: ">",  ast.GtE:   ">=",
}
_BOOL_OP_MAP = {
    ast.And: "&&", ast.Or: "||",
}


# ──────────────────────────────────────────────────────────────────────────────
class CTranspiler(ast.NodeVisitor):
    """Visita el AST de Python y produce codigo C99."""

    def __init__(self):
        self._lines:       List[str]       = []
        self._indent:      int             = 0
        self._headers:     Set[str]        = set()
        self._declared:    Set[str]        = set()  # local vars already declared
        self._global_decl: Set[str]        = set()  # global vars
        self._func_types:  Dict[str, str]  = {}     # func name → return type
        self._in_func:     bool            = False
        self._cur_func:    Optional[str]   = None

    # ── emit helpers ──────────────────────────────────────────────────────────

    def _emit(self, line: str = ""):
        self._lines.append("    " * self._indent + line)

    def _blank(self):
        self._lines.append("")

    # ── type inference ────────────────────────────────────────────────────────

    def _infer_type(self, node) -> str:
        """Best-effort C type inference from a Python expression node."""
        if node is None:
            return "int"
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):   return "int"
            if isinstance(node.value, int):    return "int"
            if isinstance(node.value, float):  return "double"
            if isinstance(node.value, str):    return "char*"
            return "int"
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, _FLOAT_OPS):
                return "double"
            lt = self._infer_type(node.left)
            rt = self._infer_type(node.right)
            if lt == "double" or rt == "double":
                return "double"
            return lt
        if isinstance(node, ast.UnaryOp):
            return self._infer_type(node.operand)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fn = node.func.id
                if fn in ("int", "abs", "ord", "len", "bool"):
                    return "int"
                if fn in ("float",):
                    return "double"
                if fn in ("str", "chr", "input"):
                    return "char*"
                if fn in self._func_types:
                    return self._func_types[fn]
        if isinstance(node, ast.Name):
            if node.id in ("True", "False"):
                return "int"
        if isinstance(node, ast.BoolOp):
            return "int"
        if isinstance(node, ast.Compare):
            return "int"
        return "int"

    # ── expression visitor ────────────────────────────────────────────────────

    def _expr(self, node) -> str:
        """Recursively convert a Python expression node to a C expression string."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "1" if node.value else "0"
            if isinstance(node.value, str):
                escaped = node.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
                return f'"{escaped}"'
            return str(node.value)

        if isinstance(node, ast.Name):
            name_map = {"True": "1", "False": "0", "None": "NULL"}
            return name_map.get(node.id, node.id)

        if isinstance(node, ast.BinOp):
            l = self._expr(node.left)
            r = self._expr(node.right)
            if isinstance(node.op, ast.Pow):
                self._headers.add("math.h")
                return f"pow({l}, {r})"
            if isinstance(node.op, ast.FloorDiv):
                # integer floor division
                return f"(int)({l}) / (int)({r})"
            op = _OP_MAP.get(type(node.op), "?")
            return f"({l} {op} {r})"

        if isinstance(node, ast.UnaryOp):
            op = _UNARY_OP_MAP.get(type(node.op), "?")
            return f"({op}{self._expr(node.operand)})"

        if isinstance(node, ast.BoolOp):
            op = _BOOL_OP_MAP.get(type(node.op), "&&")
            parts = [self._expr(v) for v in node.values]
            return f" {op} ".join(f"({p})" for p in parts)

        if isinstance(node, ast.Compare):
            result = self._expr(node.left)
            for op, comp in zip(node.ops, node.comparators):
                c_op = _CMP_OP_MAP.get(type(op), "==")
                if isinstance(op, ast.In):
                    return f"strstr({self._expr(comp)}, {result}) != NULL"
                if isinstance(op, ast.NotIn):
                    return f"strstr({self._expr(comp)}, {result}) == NULL"
                if isinstance(op, ast.Is):
                    c_op = "=="
                if isinstance(op, ast.IsNot):
                    c_op = "!="
                result = f"({result} {c_op} {self._expr(comp)})"
            return result

        if isinstance(node, ast.Call):
            return self._call_expr(node)

        if isinstance(node, ast.IfExp):
            # ternary: a if cond else b
            return f"({self._expr(node.test)} ? {self._expr(node.body)} : {self._expr(node.orelse)})"

        if isinstance(node, ast.Subscript):
            val  = self._expr(node.value)
            slc  = node.slice
            if isinstance(slc, ast.Constant):
                return f"{val}[{slc.value}]"
            return f"{val}[{self._expr(slc)}]"

        if isinstance(node, ast.Attribute):
            obj  = self._expr(node.value)
            attr = node.attr
            # common method mapping
            return f"{obj}.{attr}"

        # Fallback: unparse (Python 3.9+)
        try:
            return ast.unparse(node)
        except Exception:
            return "/* expr */"

    def _call_expr(self, node: ast.Call) -> str:
        """Convert a Python Call node to a C call expression."""
        # ── print() ───────────────────────────────────────────────────────────
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self._headers.add("stdio.h")
            return self._print_to_printf(node)

        # ── type casts ───────────────────────────────────────────────────────
        if isinstance(node.func, ast.Name):
            fn = node.func.id
            args = node.args

            if fn == "int" and args:
                inner = self._expr(args[0])
                t = self._infer_type(args[0])
                if t == "char*":
                    self._headers.add("stdlib.h")
                    return f"atoi({inner})"
                return f"(int)({inner})"

            if fn == "float" and args:
                inner = self._expr(args[0])
                t = self._infer_type(args[0])
                if t == "char*":
                    self._headers.add("stdlib.h")
                    return f"atof({inner})"
                return f"(double)({inner})"

            if fn == "str" and args:
                # sprintf to a temp buffer — complicated; emit comment
                inner = self._expr(args[0])
                return f"/* str({inner}) */"

            if fn == "len" and args:
                self._headers.add("string.h")
                return f"strlen({self._expr(args[0])})"

            if fn == "abs" and args:
                self._headers.add("stdlib.h")
                return f"abs({self._expr(args[0])})"

            if fn == "input":
                self._headers.add("stdio.h")
                self._headers.add("string.h")
                return "/* input() — use scanf/fgets in C */"

            if fn == "range":
                # range() is consumed by for-loop visitor
                return f"range({', '.join(self._expr(a) for a in node.args)})"

            if fn in ("list", "tuple", "set", "dict"):
                return f"/* {fn}() not directly supported in C */"

            # generic call
            args_str = ", ".join(self._expr(a) for a in node.args)
            return f"{fn}({args_str})"

        # method call: obj.method(...)
        if isinstance(node.func, ast.Attribute):
            obj  = self._expr(node.func.value)
            meth = node.func.attr
            args_str = ", ".join(self._expr(a) for a in node.args)

            if meth == "append":
                return f"/* {obj}.append({args_str}) — use array manually in C */"
            if meth in ("lower", "upper"):
                self._headers.add("ctype.h")
                return f"/* {obj}.{meth}() — use tolower/toupper loop in C */"
            if meth == "format":
                return f"/* {obj}.format({args_str}) — use sprintf in C */"
            if meth == "split":
                return f"/* {obj}.split({args_str}) — use strtok in C */"
            if meth == "strip":
                return f"/* {obj}.strip() — trim manually in C */"
            return f"{obj}.{meth}({args_str})"

        args_str = ", ".join(self._expr(a) for a in node.args)
        return f"{self._expr(node.func)}({args_str})"

    def _print_to_printf(self, node: ast.Call) -> str:
        """Convert print(...) to printf(...)."""
        self._headers.add("stdio.h")
        if not node.args:
            return 'printf("\\n")'

        fmt_parts = []
        arg_exprs = []
        for arg in node.args:
            t = self._infer_type(arg)
            if t == "double":
                fmt_parts.append("%g")
            elif t == "char*":
                fmt_parts.append("%s")
            else:
                fmt_parts.append("%d")
            arg_exprs.append(self._expr(arg))

        sep = self._get_keyword(node.keywords, "sep", " ")
        end = self._get_keyword(node.keywords, "end", "\\n")

        fmt_str = sep.join(fmt_parts) + end
        args_str = ", ".join(arg_exprs)
        return f'printf("{fmt_str}", {args_str})'

    def _get_keyword(self, keywords, name: str, default: str) -> str:
        for kw in keywords:
            if kw.arg == name:
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    v = kw.value.value.replace("\n", "\\n").replace("\t", "\\t")
                    return v
        return default

    # ── statement visitors ────────────────────────────────────────────────────

    def visit_Module(self, node: ast.Module) -> str:
        """Entry point: generates the complete C file."""
        # Collect function defs to emit forward declarations
        func_defs = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        main_stmts = [n for n in node.body
                      if not isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom))]

        # First pass: infer return types
        for fd in func_defs:
            self._func_types[fd.name] = self._infer_func_return_type(fd)

        # Headers (filled during generation) — we do two passes
        body_lines_start = 0  # index where headers will be inserted

        # Reserve space for headers
        header_placeholder = "__HEADERS__"
        self._emit(header_placeholder)
        self._blank()

        # Forward declarations
        for fd in func_defs:
            ret = self._func_types.get(fd.name, "int")
            params = self._params_to_c(fd)
            self._emit(f"{ret} {fd.name}({params});")
        if func_defs:
            self._blank()

        # Function definitions
        for fd in func_defs:
            self.visit(fd)
            self._blank()

        # main()
        if main_stmts:
            self._emit("int main(int argc, char* argv[]) {")
            self._indent += 1
            self._declared = set()
            self._in_func = True
            for stmt in main_stmts:
                self.visit(stmt)
            self._emit("return 0;")
            self._indent -= 1
            self._in_func = False
            self._emit("}")

        # Replace header placeholder
        headers_str = "\n".join(f"#include <{h}>" for h in sorted(self._headers))
        result = "\n".join(self._lines)
        result = result.replace(header_placeholder, headers_str, 1)
        return result

    def _infer_func_return_type(self, node: ast.FunctionDef) -> str:
        """Look for return statements to infer function return type."""
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                return self._infer_type(child.value)
        return "void"

    def _params_to_c(self, node: ast.FunctionDef) -> str:
        """Convert function parameters to C declaration string."""
        params = []
        for arg in node.args.args:
            # Try to get annotation type
            if arg.annotation:
                ann = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else ""
                type_map = {"int": "int", "float": "double", "str": "char*",
                            "bool": "int", "None": "void"}
                c_type = type_map.get(ann, "int")
            else:
                c_type = "int"
            params.append(f"{c_type} {arg.arg}")
        return ", ".join(params) if params else "void"

    def visit_FunctionDef(self, node: ast.FunctionDef):
        ret = self._func_types.get(node.name, "void")
        params = self._params_to_c(node)
        self._emit(f"{ret} {node.name}({params}) {{")
        self._indent += 1

        saved_declared = self._declared
        saved_in_func  = self._in_func
        saved_cur_func = self._cur_func
        self._declared = set()
        self._in_func  = True
        self._cur_func = node.name

        for stmt in node.body:
            self.visit(stmt)

        self._indent -= 1
        self._declared = saved_declared
        self._in_func  = saved_in_func
        self._cur_func = saved_cur_func
        self._emit("}")

    def visit_Return(self, node: ast.Return):
        if node.value is None:
            self._emit("return;")
        else:
            self._emit(f"return {self._expr(node.value)};")

    def visit_Assign(self, node: ast.Assign):
        """Handles simple assignments: a = expr, a = b = expr."""
        val = self._expr(node.value)
        for target in node.targets:
            tname = self._expr(target)
            if tname not in self._declared and tname not in self._global_decl:
                c_type = self._infer_type(node.value)
                self._emit(f"{c_type} {tname} = {val};")
                self._declared.add(tname)
            else:
                self._emit(f"{tname} = {val};")

    def visit_AugAssign(self, node: ast.AugAssign):
        """Handles a += b, a -= b, etc."""
        target = self._expr(node.target)
        val    = self._expr(node.value)
        if isinstance(node.op, ast.Pow):
            self._headers.add("math.h")
            self._emit(f"{target} = pow({target}, {val});")
            return
        op = _OP_MAP.get(type(node.op), "?")
        self._emit(f"{target} {op}= {val};")

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Handles annotated assignments: a: int = 5"""
        if node.target is None:
            return
        tname = self._expr(node.target)
        ann   = ast.unparse(node.annotation) if hasattr(ast, "unparse") else "int"
        type_map = {"int": "int", "float": "double", "str": "char*", "bool": "int"}
        c_type = type_map.get(ann, "int")

        if node.value:
            val = self._expr(node.value)
            if tname not in self._declared:
                self._emit(f"{c_type} {tname} = {val};")
                self._declared.add(tname)
            else:
                self._emit(f"{tname} = {val};")
        else:
            if tname not in self._declared:
                self._emit(f"{c_type} {tname};")
                self._declared.add(tname)

    def visit_Expr(self, node: ast.Expr):
        """Stand-alone expression statement (e.g., print(...))."""
        expr_str = self._expr(node.value)
        self._emit(f"{expr_str};")

    def visit_If(self, node: ast.If):
        self._emit(f"if ({self._expr(node.test)}) {{")
        self._indent += 1
        for stmt in node.body:
            self.visit(stmt)
        self._indent -= 1

        # handle elif chain
        orelse = node.orelse
        while orelse:
            if len(orelse) == 1 and isinstance(orelse[0], ast.If):
                inner = orelse[0]
                self._emit(f"}} else if ({self._expr(inner.test)}) {{")
                self._indent += 1
                for stmt in inner.body:
                    self.visit(stmt)
                self._indent -= 1
                orelse = inner.orelse
            else:
                self._emit("} else {")
                self._indent += 1
                for stmt in orelse:
                    self.visit(stmt)
                self._indent -= 1
                orelse = []
        self._emit("}")

    def visit_While(self, node: ast.While):
        self._emit(f"while ({self._expr(node.test)}) {{")
        self._indent += 1
        for stmt in node.body:
            self.visit(stmt)
        self._indent -= 1
        self._emit("}")

    def visit_For(self, node: ast.For):
        """Handles for i in range(...) and for item in iterable."""
        target = self._expr(node.target)

        # for i in range(...)
        if (isinstance(node.iter, ast.Call) and
                isinstance(node.iter.func, ast.Name) and
                node.iter.func.id == "range"):
            args = node.iter.args
            if len(args) == 1:
                start, stop, step = "0", self._expr(args[0]), "1"
            elif len(args) == 2:
                start, stop, step = self._expr(args[0]), self._expr(args[1]), "1"
            else:
                start = self._expr(args[0])
                stop  = self._expr(args[1])
                step_val = args[2]
                step  = self._expr(step_val)
                # detect negative step
                if isinstance(step_val, ast.UnaryOp) and isinstance(step_val.op, ast.USub):
                    op = ">"; inc = f"-= {self._expr(step_val.operand)}"
                    self._emit(f"for (int {target} = {start}; {target} {op} {stop}; {target} {inc}) {{")
                    self._indent += 1
                    for stmt in node.body:
                        self.visit(stmt)
                    self._indent -= 1
                    self._emit("}")
                    return
            self._emit(f"for (int {target} = {start}; {target} < {stop}; {target} += {step}) {{")
        else:
            # Generic iteration — emit comment and best-effort
            iter_expr = self._expr(node.iter)
            self._emit(f"/* for {target} in {iter_expr} — adapt to your array */")
            self._emit(f"for (int _i = 0; _i < /* size */; _i++) {{")
            self._emit(f"    /* {target} = {iter_expr}[_i]; */")

        self._indent += 1
        self._declared.add(target)
        for stmt in node.body:
            self.visit(stmt)
        self._indent -= 1
        self._emit("}")

    def visit_Break(self, node):
        self._emit("break;")

    def visit_Continue(self, node):
        self._emit("continue;")

    def visit_Pass(self, node):
        self._emit("/* pass */")

    def visit_Global(self, node):
        for name in node.names:
            self._global_decl.add(name)
        self._emit(f"/* global {', '.join(node.names)} */")

    def visit_Import(self, node):
        for alias in node.names:
            self._emit(f"/* import {alias.name} */")

    def visit_ImportFrom(self, node):
        names = [a.name for a in node.names]
        self._emit(f"/* from {node.module} import {', '.join(names)} */")

    def generic_visit(self, node):
        cls = type(node).__name__
        self._emit(f"/* unsupported: {cls} */")

    # ── entry ─────────────────────────────────────────────────────────────────

    def generate(self, source: str) -> str:
        """Parse Python source and return equivalent C code."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"// Error de sintaxis Python en linea {e.lineno}: {e.msg}\n"
        return self.visit_Module(tree)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

class CGenerator:
    """Wrapper de alto nivel — igual interfaz que Compiler / AssemblyGenerator."""

    def __init__(self, program=None, source: str = ""):
        self.program = program
        self.source  = source

    def set_source(self, source: str):
        self.source = source

    def generate(self) -> str:
        """Genera codigo C a partir de self.source y retorna el string."""
        if not self.source.strip():
            return "// No hay codigo fuente disponible\n"

        header = (
            "/*\n"
            " * Codigo C generado automaticamente desde Python\n"
            " * por Python IDE - c_generator.py\n"
            " */\n\n"
        )
        try:
            transpiler = CTranspiler()
            c_code = transpiler.generate(self.source)
            return header + c_code
        except Exception as e:
            return f"// Error al generar C: {e}\n"
