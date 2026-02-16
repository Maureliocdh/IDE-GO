from typing import Dict, List, Optional, Union, Set
from ast_nodes import *
from dataclasses import dataclass
import re

# filepath: c:\Users\maure\Desktop\gi\compiler.py


@dataclass
class CompilationContext:
    """Stores compilation state"""
    indent_level: int = 0
    header_includes: Set[str] = None
    generated_structs: Set[str] = None
    generated_functions: Set[str] = None
    
    def __post_init__(self):
        if self.header_includes is None:
            self.header_includes = set()
        if self.generated_structs is None:
            self.generated_structs = set()
        if self.generated_functions is None:
            self.generated_functions = set()
    
    def indent(self):
        self.indent_level += 1
    
    def dedent(self):
        self.indent_level = max(0, self.indent_level - 1)
    
    def get_indent(self) -> str:
        return "    " * self.indent_level


class Compiler:
    """Compiles Go-like AST to C code"""
    
    def __init__(self, program: Program):
        self.program = program
        self.context = CompilationContext()
        self.c_code = []
        self.type_mappings = {
            'int': 'int',
            'int8': 'char',
            'int16': 'short',
            'int32': 'int',
            'int64': 'long',
            'uint': 'unsigned int',
            'uint8': 'unsigned char',
            'uint16': 'unsigned short',
            'uint32': 'unsigned int',
            'uint64': 'unsigned long',
            'float32': 'float',
            'float64': 'double',
            'bool': 'int',
            'string': 'char*',
            'rune': 'int',
            'byte': 'unsigned char',
        }
    
    def compile(self) -> str:
        """Main compilation entry point"""
        # Add C headers
        self.add_headers()
        
        # Add helper functions and macros
        self.add_helpers()
        
        # Compile type declarations
        for decl in self.program.declarations:
            if isinstance(decl, StructDecl):
                self.compile_struct_decl(decl)
        
        # Compile function declarations and definitions
        for decl in self.program.declarations:
            if isinstance(decl, FuncDecl):
                self.compile_func_decl(decl)
        
        # Compile global variables
        for decl in self.program.declarations:
            if isinstance(decl, VarDecl):
                self.compile_var_decl(decl, global_scope=True)
            elif isinstance(decl, ConstDecl):
                self.compile_const_decl(decl)
        
        return self.get_c_code()
    
    def add_headers(self):
        """Add required C headers"""
        headers = [
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <string.h>",
            "#include <math.h>",
            "#include <stdbool.h>",
            ""
        ]
        self.c_code.extend(headers)
    
    def add_helpers(self):
        """Add helper functions and macros"""
        helpers = [
            "// Helper macros and functions",
            "#define TRUE 1",
            "#define FALSE 0",
            "",
            "typedef struct {",
            "    void* ptr;",
            "    int cap;",
            "    int len;",
            "} Array;",
            "",
            "typedef struct {",
            "    void* data;",
            "} Map;",
            "",
            "// String functions",
            "char* go_string_concat(char* a, char* b) {",
            "    char* result = (char*)malloc(strlen(a) + strlen(b) + 1);",
            "    strcpy(result, a);",
            "    strcat(result, b);",
            "    return result;",
            "}",
            "",
            "int go_string_length(char* s) {",
            "    return strlen(s);",
            "}",
            "",
        ]
        self.c_code.extend(helpers)
    
    def compile_struct_decl(self, struct_decl: StructDecl):
        """Compile struct declaration"""
        if struct_decl.name in self.context.generated_structs:
            return
        
        self.context.generated_structs.add(struct_decl.name)
        self.c_code.append(f"typedef struct {{")
        
        for field in struct_decl.fields:
            c_type = self.get_c_type(field.type_)
            self.c_code.append(f"    {c_type} {field.name};")
        
        self.c_code.append(f"}} {struct_decl.name};")
        self.c_code.append("")
    
    def compile_func_decl(self, func_decl: FuncDecl):
        """Compile function declaration and definition"""
        if func_decl.name in self.context.generated_functions:
            return
        
        self.context.generated_functions.add(func_decl.name)
        
        # Get return type
        if func_decl.returns:
            return_type = self.get_c_type(func_decl.returns[0])
        else:
            return_type = "void"
        
        # Build parameter list
        params = []
        for param in func_decl.params:
            c_type = self.get_c_type(param.type_)
            params.append(f"{c_type} {param.name}")
        
        param_str = ", ".join(params) if params else "void"
        
        # Function signature
        self.c_code.append(f"{return_type} {func_decl.name}({param_str}) {{")
        self.context.indent()
        
        # Function body
        if func_decl.body:
            for stmt in func_decl.body.statements:
                self.compile_statement(stmt)
        else:
            self.c_code.append(f"{self.context.get_indent()}return;")
        
        self.context.dedent()
        self.c_code.append("}")
        self.c_code.append("")
    
    def compile_var_decl(self, var_decl: VarDecl, global_scope: bool = False):
        """Compile variable declaration"""
        if var_decl.type_:
            c_type = self.get_c_type(var_decl.type_)
        else:
            c_type = "int"  # Default type
        
        if var_decl.value:
            value_expr = self.compile_expression(var_decl.value)
            line = f"{c_type} {var_decl.name} = {value_expr};"
        else:
            line = f"{c_type} {var_decl.name};"
        
        if global_scope:
            self.c_code.append(line)
        else:
            self.c_code.append(f"{self.context.get_indent()}{line}")
    
    def compile_const_decl(self, const_decl: ConstDecl):
        """Compile constant declaration"""
        if const_decl.type_:
            c_type = self.get_c_type(const_decl.type_)
        else:
            c_type = "const int"
        
        value_expr = self.compile_expression(const_decl.value)
        line = f"#define {const_decl.name} {value_expr}"
        self.c_code.append(line)
    
    def compile_statement(self, stmt: Statement):
        """Compile a statement"""
        if isinstance(stmt, VarDecl):
            self.compile_var_decl(stmt, global_scope=False)
        
        elif isinstance(stmt, ConstDecl):
            self.compile_const_decl(stmt)
        
        elif isinstance(stmt, ExpressionStmt):
            expr = self.compile_expression(stmt.expr)
            self.c_code.append(f"{self.context.get_indent()}{expr};")
        
        elif isinstance(stmt, ReturnStmt):
            if stmt.values:
                if len(stmt.values) == 1:
                    expr = self.compile_expression(stmt.values[0])
                    self.c_code.append(f"{self.context.get_indent()}return {expr};")
                else:
                    # Multiple returns (Go feature) - simplified
                    expr = self.compile_expression(stmt.values[0])
                    self.c_code.append(f"{self.context.get_indent()}return {expr};")
            else:
                self.c_code.append(f"{self.context.get_indent()}return;")
        
        elif isinstance(stmt, IfStmt):
            self.compile_if_stmt(stmt)
        
        elif isinstance(stmt, ForStmt):
            self.compile_for_stmt(stmt)
        
        elif isinstance(stmt, ForRangeStmt):
            self.compile_for_range_stmt(stmt)
        
        elif isinstance(stmt, SwitchStmt):
            self.compile_switch_stmt(stmt)
        
        elif isinstance(stmt, Block):
            self.compile_block(stmt)
        
        elif isinstance(stmt, DeferStmt):
            # Deferred function calls - simplified
            expr = self.compile_expression(stmt.call)
            self.c_code.append(f"{self.context.get_indent()}{expr};")
        
        elif isinstance(stmt, BreakStmt):
            self.c_code.append(f"{self.context.get_indent()}break;")
        
        elif isinstance(stmt, ContinueStmt):
            self.c_code.append(f"{self.context.get_indent()}continue;")
        
        elif isinstance(stmt, AssignStmt):
            self.compile_assign_stmt(stmt)
        
        elif isinstance(stmt, IncDecStmt):
            expr = self.compile_expression(stmt.expr)
            self.c_code.append(f"{self.context.get_indent()}{expr}{stmt.operator};")
    
    def compile_block(self, block: Block):
        """Compile a block of statements"""
        for stmt in block.statements:
            self.compile_statement(stmt)
    
    def compile_if_stmt(self, if_stmt: IfStmt):
        """Compile if statement"""
        condition = self.compile_expression(if_stmt.condition)
        self.c_code.append(f"{self.context.get_indent()}if ({condition}) {{")
        self.context.indent()
        self.compile_block(if_stmt.then_block)
        self.context.dedent()
        
        if if_stmt.else_block:
            if isinstance(if_stmt.else_block, IfStmt):
                # else if
                self.c_code.append(f"{self.context.get_indent()}}} else if (")
                condition = self.compile_expression(if_stmt.else_block.condition)
                self.c_code[-1] += f"{condition}) {{"
                self.context.indent()
                self.compile_block(if_stmt.else_block.then_block)
                self.context.dedent()
            else:
                # else
                self.c_code.append(f"{self.context.get_indent()}}} else {{")
                self.context.indent()
                self.compile_block(if_stmt.else_block)
                self.context.dedent()
        
        self.c_code.append(f"{self.context.get_indent()}}}")
    
    def compile_for_stmt(self, for_stmt: ForStmt):
        """Compile traditional for loop"""
        self.c_code.append(f"{self.context.get_indent()}for (")
        
        # Init
        init_str = ""
        if for_stmt.init:
            if isinstance(for_stmt.init, ExpressionStmt):
                init_str = self.compile_expression(for_stmt.init.expr)
            elif isinstance(for_stmt.init, AssignStmt):
                # Handle assignment in init (e.g., i := 0)
                assign = for_stmt.init
                if assign.operator == ":=":
                    # Declaration and initialization
                    target = assign.targets[0]
                    value = assign.values[0]
                    target_name = target.name if isinstance(target, Identifier) else "var"
                    val_expr = self.compile_expression(value)
                    # Infer type from value
                    c_type = self._infer_c_type(value)
                    init_str = f"{c_type} {target_name} = {val_expr}"
                else:
                    # Regular assignment
                    target = self.compile_expression(assign.targets[0])
                    value = self.compile_expression(assign.values[0])
                    init_str = f"{target} = {value}"
        
        self.c_code[-1] += f"{init_str}; "
        
        # Condition
        if for_stmt.condition:
            condition = self.compile_expression(for_stmt.condition)
            self.c_code[-1] += f"{condition}; "
        else:
            self.c_code[-1] += "; "
        
        # Post
        if for_stmt.post:
            if isinstance(for_stmt.post, ExpressionStmt):
                post_expr = self.compile_expression(for_stmt.post.expr)
                self.c_code[-1] += f"{post_expr}"
            elif isinstance(for_stmt.post, IncDecStmt):
                post_expr = self.compile_expression(for_stmt.post.expr)
                self.c_code[-1] += f"{post_expr}{for_stmt.post.operator}"
        
        self.c_code[-1] += ") {"
        self.context.indent()
        self.compile_block(for_stmt.body)
        self.context.dedent()
        self.c_code.append(f"{self.context.get_indent()}}}")
    
    def compile_for_range_stmt(self, for_range: ForRangeStmt):
        """Compile for range loop"""
        iterable = self.compile_expression(for_range.iterable)
        
        # Simplified: treat as array iteration
        if for_range.value:
            self.c_code.append(f"{self.context.get_indent()}for (int {for_range.key or 'i'} = 0; {for_range.key or 'i'} < sizeof({iterable})/sizeof({iterable}[0]); {for_range.key or 'i'}++) {{")
            self.context.indent()
            if for_range.value:
                # Infer type from iterable - default to int for array elements
                value_type = self._infer_c_type(for_range.iterable)
                # Strip pointer notation if present to get element type
                if value_type.endswith('*'):
                    value_type = value_type[:-1]
                else:
                    value_type = "int"  # default fallback
                self.c_code.append(f"{self.context.get_indent()}{value_type} {for_range.value} = {iterable}[{for_range.key or 'i'}];")
            self.compile_block(for_range.body)
            self.context.dedent()
            self.c_code.append(f"{self.context.get_indent()}}}")
    
    def compile_switch_stmt(self, switch_stmt: SwitchStmt):
        """Compile switch statement"""
        if switch_stmt.expr:
            expr = self.compile_expression(switch_stmt.expr)
            self.c_code.append(f"{self.context.get_indent()}switch ({expr}) {{")
        else:
            self.c_code.append(f"{self.context.get_indent()}switch (1) {{")
        
        self.context.indent()
        
        for case in switch_stmt.cases:
            if case.values:
                # Regular case
                for value in case.values:
                    val_expr = self.compile_expression(value)
                    self.c_code.append(f"{self.context.get_indent()}case {val_expr}:")
            else:
                # Default case
                self.c_code.append(f"{self.context.get_indent()}default:")
            
            self.context.indent()
            for stmt in case.statements:
                self.compile_statement(stmt)
            self.c_code.append(f"{self.context.get_indent()}break;")
            self.context.dedent()
        
        self.context.dedent()
        self.c_code.append(f"{self.context.get_indent()}}}")
    
    def compile_assign_stmt(self, assign: AssignStmt):
        """Compile assignment statement"""
        if assign.operator == ":=":
            # Declaration and assignment - infer type from value
            for target, value in zip(assign.targets, assign.values):
                val_expr = self.compile_expression(value)
                target_name = target.name if isinstance(target, Identifier) else 'var'
                
                # Infer C type from the value expression
                c_type = self._infer_c_type(value)
                self.c_code.append(f"{self.context.get_indent()}{c_type} {target_name} = {val_expr};")
        else:
            # Regular assignment
            targets = [self.compile_expression(t) for t in assign.targets]
            values = [self.compile_expression(v) for v in assign.values]
            
            for target, value in zip(targets, values):
                op = assign.operator[:-1] if assign.operator.endswith('=') else '='
                self.c_code.append(f"{self.context.get_indent()}{target} {op}= {value};")
    
    def compile_expression(self, expr: Expression) -> str:
        """Compile an expression"""
        if isinstance(expr, Literal):
            return self.compile_literal(expr)
        
        elif isinstance(expr, Identifier):
            return expr.name
        
        elif isinstance(expr, BinaryOp):
            return self.compile_binary_op(expr)
        
        elif isinstance(expr, UnaryOp):
            return self.compile_unary_op(expr)
        
        elif isinstance(expr, CallExpr):
            return self.compile_call_expr(expr)
        
        elif isinstance(expr, IndexExpr):
            return self.compile_index_expr(expr)
        
        elif isinstance(expr, FieldExpr):
            return self.compile_field_expr(expr)
        
        elif isinstance(expr, ArrayLiteral):
            return self.compile_array_literal(expr)
        
        elif isinstance(expr, MapLiteral):
            return self.compile_map_literal(expr)
        
        elif isinstance(expr, TypeCast):
            return self.compile_type_cast(expr)
        
        elif isinstance(expr, TernaryOp):
            return self.compile_ternary_op(expr)
        
        elif isinstance(expr, SliceExpr):
            return self.compile_slice_expr(expr)
        
        elif isinstance(expr, MakeLiteral):
            return self.compile_make_literal(expr)
        
        elif isinstance(expr, NewLiteral):
            return self.compile_new_literal(expr)
        
        else:
            return "0"
    
    def compile_literal(self, lit: Literal) -> str:
        """Compile a literal value"""
        # Handle both string type names and TokenType enums
        type_str = lit.type_
        if hasattr(type_str, 'name'):  # TokenType enum
            type_str = type_str.name.lower()
        
        if type_str == "int":
            return lit.value
        elif type_str == "float":
            return lit.value
        elif type_str == "string":
            # Ensure string literal is properly quoted
            if lit.value.startswith('"') and lit.value.endswith('"'):
                return lit.value
            else:
                return f'"{lit.value}"'
        elif type_str == "rune":
            return f"'{lit.value}'"
        elif type_str == "bool":
            return "1" if lit.value == "true" else "0"
        else:
            return str(lit.value)
    
    def compile_binary_op(self, op: BinaryOp) -> str:
        """Compile binary operation"""
        left = self.compile_expression(op.left)
        right = self.compile_expression(op.right)
        
        # Map Go operators to C operators
        op_map = {
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
            '%': '%',
            '==': '==',
            '!=': '!=',
            '<': '<',
            '>': '>',
            '<=': '<=',
            '>=': '>=',
            '&&': '&&',
            '||': '||',
            '&': '&',
            '|': '|',
            '^': '^',
            '<<': '<<',
            '>>': '>>',
        }
        
        c_op = op_map.get(op.op, op.op)
        return f"({left} {c_op} {right})"
    
    def compile_unary_op(self, op: UnaryOp) -> str:
        """Compile unary operation"""
        operand = self.compile_expression(op.operand)
        
        op_map = {
            '+': '+',
            '-': '-',
            '!': '!',
            '^': '~',
            '*': '*',
            '&': '&',
        }
        
        c_op = op_map.get(op.op, op.op)
        
        if op.op in ['++', '--']:
            return f"{operand}{c_op}"
        else:
            return f"{c_op}{operand}"
    
    def compile_call_expr(self, call: CallExpr) -> str:
        """Compile function call"""
        # Handle fmt.Println and fmt.Print
        if isinstance(call.func, FieldExpr):
            if isinstance(call.func.expr, Identifier):
                package = call.func.expr.name
                method = call.func.field
                
                if package == "fmt":
                    if method == "Println":
                        return self._compile_fmt_println(call.args)
                    elif method == "Print":
                        return self._compile_fmt_print(call.args)
        
        # Regular function call
        if isinstance(call.func, Identifier):
            func_name = call.func.name
        else:
            func_name = self.compile_expression(call.func)
        
        args = [self.compile_expression(arg) for arg in call.args]
        args_str = ", ".join(args)
        
        return f"{func_name}({args_str})"
    
    def _compile_fmt_println(self, args: List[Expression]) -> str:
        """Compile fmt.Println with proper format specifiers"""
        if not args:
            return 'printf("\\n")'
        
        format_str = ""
        compiled_args = []
        
        for arg in args:
            arg_code = self.compile_expression(arg)
            inferred_type = self._infer_c_type(arg)
            
            if inferred_type == "char*":
                format_str += "%s "
            elif inferred_type == "double":
                format_str += "%f "
            else:  # int and others
                format_str += "%d "
            
            compiled_args.append(arg_code)
        
        # Remove trailing space and add newline
        format_str = format_str.rstrip() + "\\n"
        
        all_args = [f'"{format_str}"'] + compiled_args
        return f"printf({', '.join(all_args)})"
    
    def _compile_fmt_print(self, args: List[Expression]) -> str:
        """Compile fmt.Print with proper format specifiers"""
        if not args:
            return 'printf("")'
        
        format_str = ""
        compiled_args = []
        
        for arg in args:
            arg_code = self.compile_expression(arg)
            inferred_type = self._infer_c_type(arg)
            
            if inferred_type == "char*":
                format_str += "%s"
            elif inferred_type == "double":
                format_str += "%f"
            else:  # int and others
                format_str += "%d"
            
            compiled_args.append(arg_code)
        
        all_args = [f'"{format_str}"'] + compiled_args
        return f"printf({', '.join(all_args)})"
    
    def compile_index_expr(self, idx: IndexExpr) -> str:
        """Compile index access"""
        expr = self.compile_expression(idx.expr)
        index = self.compile_expression(idx.index)
        return f"{expr}[{index}]"
    
    def compile_field_expr(self, field: FieldExpr) -> str:
        """Compile field access"""
        expr = self.compile_expression(field.expr)
        return f"{expr}.{field.field}"
    
    def compile_array_literal(self, arr: ArrayLiteral) -> str:
        """Compile array literal"""
        elements = [self.compile_expression(elem) for elem in arr.elements]
        return "{" + ", ".join(elements) + "}"
    
    def compile_map_literal(self, map_lit: MapLiteral) -> str:
        """Compile map literal (simplified)"""
        return "{}"
    
    def compile_type_cast(self, cast: TypeCast) -> str:
        """Compile type cast"""
        c_type = self.get_c_type(cast.type_)
        expr = self.compile_expression(cast.expr)
        return f"(({c_type})({expr}))"
    
    def compile_ternary_op(self, ternary: TernaryOp) -> str:
        """Compile ternary operator"""
        condition = self.compile_expression(ternary.condition)
        true_expr = self.compile_expression(ternary.true_expr)
        false_expr = self.compile_expression(ternary.false_expr)
        return f"({condition} ? {true_expr} : {false_expr})"
    
    def compile_slice_expr(self, slice_expr: SliceExpr) -> str:
        """Compile slice expression (simplified)"""
        expr = self.compile_expression(slice_expr.expr)
        start = self.compile_expression(slice_expr.start) if slice_expr.start else "0"
        end = self.compile_expression(slice_expr.end) if slice_expr.end else "sizeof(expr)/sizeof(expr[0])"
        return f"{expr}"
    
    def compile_make_literal(self, make_lit: MakeLiteral) -> str:
        """Compile make expression"""
        return "(void*)malloc(sizeof(int) * 10)"
    
    def compile_new_literal(self, new_lit: NewLiteral) -> str:
        """Compile new expression"""
        c_type = self.get_c_type(new_lit.type_)
        return f"({c_type}*)malloc(sizeof({c_type}))"
    
    def get_c_type(self, type_: Type) -> str:
        """Convert Go type to C type"""
        if isinstance(type_, PrimitiveType):
            return self.type_mappings.get(type_.name, "int")
        
        elif isinstance(type_, NamedType):
            # Check type_mappings first (for built-in types like 'string')
            if type_.name in self.type_mappings:
                return self.type_mappings[type_.name]
            return type_.name
        
        elif isinstance(type_, PointerType):
            inner_type = self.get_c_type(type_.type_)
            return f"{inner_type}*"
        
        elif isinstance(type_, ArrayType):
            inner_type = self.get_c_type(type_.type_)
            if type_.size:
                return f"{inner_type}[]"
            else:
                return f"{inner_type}*"
        
        elif isinstance(type_, SliceType):
            inner_type = self.get_c_type(type_.type_)
            return f"{inner_type}*"
        
        elif isinstance(type_, MapType):
            return "void*"
        
        else:
            return "int"
    
    def _infer_c_type(self, expr: Expression) -> str:
        """Infer C type from an expression with improved heuristics"""
        if isinstance(expr, Literal):
            # Direct type inference from literal
            # Handle both string type_ and TokenType enum
            type_str = str(expr.type_).lower()
            
            # Extract the actual type name from TokenType enum if needed
            # e.g., "TokenType.STRING" -> "string"
            if "tokentype." in type_str:
                type_str = type_str.split(".")[1]
            elif "<tokentype." in type_str:
                # Handle format like "<TokenType.STRING: 3>"
                type_str = type_str.split(".")[1].split(":")[0].strip(">")
            
            # Map to C types
            type_map = {
                "int": "int",
                "float": "double",
                "string": "char*",
                "bool": "int",
                "rune": "int"
            }
            return type_map.get(type_str, "int")
        
        elif isinstance(expr, Identifier):
            # Try to infer from identifier name patterns
            name = expr.name.lower()
            if any(x in name for x in ['str', 'string', 'text', 'msg', 'message', 'name', 'label', 'title', 'description', 's']):
                return "char*"
            elif any(x in name for x in ['float', 'double', 'decimal']):
                return "double"
            elif any(x in name for x in ['count', 'idx', 'index', 'num', 'size', 'len', 'i', 'j', 'k']):
                return "int"
            else:
                return "int"  # Default for unknown identifiers
        
        elif isinstance(expr, BinaryOp):
            # Infer type based on operation
            if expr.op in ['+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>']:
                left_type = self._infer_c_type(expr.left)
                right_type = self._infer_c_type(expr.right)
                
                # String concatenation
                if expr.op == '+' and (left_type == "char*" or right_type == "char*"):
                    return "char*"
                
                # Float promotion
                if 'double' in [left_type, right_type] or 'float' in [left_type, right_type]:
                    return "double"
                
                return left_type  # Preserve left operand type
            
            elif expr.op in ['==', '!=', '<', '>', '<=', '>=', '&&', '||']:
                return "int"  # Boolean operations return int (0 or 1)
        
        elif isinstance(expr, UnaryOp):
            if expr.op == '&':
                # Address-of operator returns pointer
                inner_type = self._infer_c_type(expr.operand)
                return f"{inner_type}*"
            elif expr.op == '*':
                # Dereference operator removes pointer
                inner_type = self._infer_c_type(expr.operand)
                if inner_type.endswith('*'):
                    return inner_type[:-1]
                return "int"
            else:
                return self._infer_c_type(expr.operand)
        
        elif isinstance(expr, CallExpr):
            # Try to infer from function name
            if isinstance(expr.func, Identifier):
                func_name = expr.func.name.lower()
                if any(x in func_name for x in ['string', 'str', 'concat']):
                    return "char*"
                elif any(x in func_name for x in ['float', 'sqrt', 'pow']):
                    return "double"
            return "int"  # Default for function calls
        
        elif isinstance(expr, ArrayLiteral):
            # Infer element type from first element
            if expr.elements:
                elem_type = self._infer_c_type(expr.elements[0])
                return f"{elem_type}*"
            return "int*"
        
        elif isinstance(expr, MapLiteral):
            return "void*"  # Maps are complex structures
        
        elif isinstance(expr, IndexExpr):
            # Array/pointer indexing returns element type
            container_type = self._infer_c_type(expr.expr)
            if container_type.endswith('*'):
                return container_type[:-1]
            return "int"
        
        elif isinstance(expr, FieldExpr):
            # Field access - would need symbol table for accurate inference
            return "int"
        
        else:
            return "int"  # Safe default fallback
    
    def get_c_code(self) -> str:
        """Get generated C code"""
        return "\n".join(self.c_code)


def compile_program(program: Program) -> str:
    """Convenience function to compile a program"""
    compiler = Compiler(program)
    return compiler.compile()