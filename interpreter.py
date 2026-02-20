from typing import Any, Dict, List, Optional, Union
from ast_nodes import *
from dataclasses import dataclass
import sys

# filepath: c:\Users\maure\Desktop\gi\interpreter.py

@dataclass
class Value:
    """Represents a value during interpretation"""
    type_name: str
    value: Any
    
    def __repr__(self):
        return f"{self.value}"

class Environment:
    """Represents a scope for variables and functions"""
    def __init__(self, parent: Optional['Environment'] = None):
        self.parent = parent
        self.variables: Dict[str, Value] = {}
        self.functions: Dict[str, FuncDecl] = {}
        self.constants: Dict[str, Value] = {}
    
    def define(self, name: str, value: Value):
        self.variables[name] = value
    
    def define_const(self, name: str, value: Value):
        self.constants[name] = value
    
    def define_function(self, name: str, func_decl: FuncDecl):
        self.functions[name] = func_decl
    
    def get(self, name: str) -> Value:
        if name in self.variables:
            return self.variables[name]
        if name in self.constants:
            return self.constants[name]
        if self.parent:
            return self.parent.get(name)
        raise RuntimeError(f"Undefined variable: {name}")
    
    def get_function(self, name: str) -> FuncDecl:
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_function(name)
        raise RuntimeError(f"Undefined function: {name}")
    
    def set(self, name: str, value: Value):
        if name in self.variables:
            self.variables[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        raise RuntimeError(f"Undefined variable: {name}")

class ControlFlowException(Exception):
    """Base class for control flow exceptions"""
    pass

class ReturnException(ControlFlowException):
    def __init__(self, values: List[Value]):
        self.values = values

class BreakException(ControlFlowException):
    pass

class ContinueException(ControlFlowException):
    pass

class FallthroughException(ControlFlowException):
    pass

class Interpreter:
    def __init__(self, program: Program, output_widget=None):
        self.program = program
        self.output_widget = output_widget
        self.global_env = Environment()
        self.current_env = self.global_env
        self.methods = {}       # type_name -> {method_name -> (FuncDecl, receiver_param)}
        self.type_registry = {} # type_name -> StructDecl | TypeDecl
        self._string_method_stack = set()  # guard against recursive String() calls
        self.setup_builtins()
    
    def setup_builtins(self):
        """Setup built-in functions and constants"""
        # Built-in functions will be handled in call_function
        pass
    
    def print_output(self, message: str):
        """Print to console or output widget, with trailing newline"""
        if self.output_widget:
            self.output_widget.insert("end", message + "\n")
            self.output_widget.see("end")
        else:
            print(message)

    def print_output_inline(self, message: str):
        """Print to console or output widget, WITHOUT trailing newline"""
        if self.output_widget:
            self.output_widget.insert("end", message)
            self.output_widget.see("end")
        else:
            print(message, end='')
    
    def type_of(self, value: Value) -> str:
        """Get the type name of a value"""
        return value.type_name
    
    def to_map_key(self, value: Value) -> str:
        """Convert a value to a map key string (never calls custom String() methods)."""
        if value.type_name == "string":
            return value.value
        elif value.type_name == "nil":
            return "nil"
        elif value.type_name == "bool":
            return "true" if value.value else "false"
        elif isinstance(value.value, (int, float)):
            return str(value.value)
        else:
            return str(value.value)

    def to_string(self, value: Value) -> str:
        """Convert value to string representation - format like Go's fmt"""
        type_name = value.type_name
        # Check for custom String() method (guard against recursion)
        if (type_name in self.methods and
                "String" in self.methods[type_name] and
                type_name not in self._string_method_stack):
            self._string_method_stack.add(type_name)
            try:
                method_decl, recv_param = self.methods[type_name]["String"]
                result = self.call_method(method_decl, value, [])
                return result.value if result.type_name == "string" else str(result.value)
            finally:
                self._string_method_stack.discard(type_name)
        if type_name == "string":
            return value.value
        elif type_name in ("int", "rune"):
            return str(value.value)
        elif type_name == "float":
            return str(value.value)
        elif type_name == "bool":
            return "true" if value.value else "false"
        elif type_name == "nil":
            return "<nil>"
        elif type_name == "error":
            return str(value.value)
        elif type_name == "array":
            if value.value is None:
                return "[]"
            elements = [self.to_string(v) for v in value.value]
            return "[" + " ".join(elements) + "]"
        elif type_name == "map":
            pairs = [f"{k}:{self.to_string(v)}" for k, v in sorted(value.value.items())]
            return "map[" + " ".join(pairs) + "]" if pairs else "map[]"
        elif type_name == "pointer":
            # Auto-deref for display
            if isinstance(value.value, dict):
                # Check if it's a heap or env pointer
                if "heap" in value.value:
                    inner = value.value["heap"]
                    return "&" + self.to_string(inner)
                elif "env" in value.value:
                    # Dereference env pointer to show actual value
                    env = value.value["env"]
                    name = value.value.get("name")
                    if name:
                        try:
                            inner = env.get(name)
                            return "&" + self.to_string(inner)
                        except Exception:
                            pass
                    # Fallback: print as simulated memory address
                    return "0x" + format(id(value.value["env"]) & 0xFFFFFFFF, '08x')
            return "0x" + format(id(value.value) & 0xFFFFFFFF, '08x')
        elif isinstance(value.value, dict):
            # Struct value - print as {field1 field2 ...}
            parts = [self.to_string(v) for v in value.value.values()]
            return "{" + " ".join(parts) + "}"
        else:
            return str(value.value)

    def _deref_pointer(self, ptr: Value) -> Value:
        """Dereference a pointer Value."""
        if ptr.type_name != "pointer":
            return ptr
        if isinstance(ptr.value, Value):
            return ptr.value  # simple value pointer
        if isinstance(ptr.value, dict):
            if "heap" in ptr.value:
                return ptr.value["heap"]
            elif "env" in ptr.value:
                return ptr.value["env"].get(ptr.value["name"])
        return Value("nil", None)

    def _assign_through_pointer(self, ptr: Value, new_val: Value):
        """Write through a pointer."""
        if isinstance(ptr.value, dict):
            if "heap" in ptr.value:
                heap_obj = ptr.value["heap"]
                heap_obj.type_name = new_val.type_name
                heap_obj.value = new_val.value
            elif "env" in ptr.value:
                ptr.value["env"].set(ptr.value["name"], new_val)
        elif isinstance(ptr.value, Value):
            ptr.value.type_name = new_val.type_name
            ptr.value.value = new_val.value

    def call_method(self, func_decl: FuncDecl, receiver: Value, args: list) -> Value:
        """Call a method with a receiver."""
        func_env = Environment(self.global_env)
        if func_decl.receiver:
            func_env.define(func_decl.receiver.name, receiver)
        for i, param in enumerate(func_decl.params):
            func_env.define(param.name, args[i] if i < len(args) else Value("nil", None))
        prev_env = self.current_env
        self.current_env = func_env
        try:
            if func_decl.body:
                self.execute_block(func_decl.body)
            return Value("nil", None)
        except ReturnException as ret:
            if len(ret.values) > 1:
                return Value("tuple", ret.values)
            return ret.values[0] if ret.values else Value("nil", None)
        finally:
            self.current_env = prev_env

    def _format_string(self, fmt_str: str, args: list) -> str:
        """Process format string with % verbs."""
        import re
        result = fmt_str
        idx = 0
        def replace_verb(m):
            nonlocal idx
            if idx >= len(args):
                return m.group(0)
            arg = args[idx]; idx += 1
            verb = m.group(1)
            if verb == 'v':
                return self.to_string(arg)
            elif verb == 's':
                return self.to_string(arg)
            elif verb == 'd':
                return str(int(arg.value))
            elif verb == 'f':
                return str(float(arg.value))
            elif verb == 'x':
                return format(int(arg.value), 'x')
            elif verb == 'X':
                return format(int(arg.value), 'X')
            elif verb == 'o':
                return format(int(arg.value), 'o')
            elif verb == 'b':
                return format(int(arg.value), 'b')
            elif verb == 'e':
                return format(float(arg.value), 'e')
            elif verb == 'g':
                return str(float(arg.value))
            elif verb == 't':
                return 'true' if arg.value else 'false'
            elif verb == 'T':
                return arg.type_name
            elif verb == 'p':
                return '0x' + format(id(arg.value) & 0xFFFFFFFFFF, '010x')
            elif verb == '#U':
                # Unicode: U+0E2A '\u0e2a'
                cp = int(arg.value)
                ch = chr(cp)
                return f"U+{cp:04X} '{ch}'"
            elif verb == 'c':
                return chr(int(arg.value))
            elif verb == 'q':
                return repr(self.to_string(arg))
            return m.group(0)
        result = re.sub(r'%([#]?[vsdfoObxXetTpUcq])', replace_verb, result)
        result = result.replace('\\n', '\n').replace('\\t', '\t')
        return result
    
    def is_truthy(self, value: Value) -> bool:
        """Check if a value is truthy"""
        if value.type_name == "bool":
            return value.value
        elif value.type_name == "int":
            return value.value != 0
        elif value.type_name == "float":
            return value.value != 0.0
        elif value.type_name == "string":
            return len(value.value) > 0
        elif value.type_name == "nil":
            return False
        else:
            return True
    
    def get_zero_value(self, type_: Optional[Type]) -> Value:
        """Get zero value for a given type"""
        if type_ is None:
            return Value("nil", None)
        
        if isinstance(type_, NamedType):
            # Handle basic types
            if type_.name == "int":
                return Value("int", 0)
            elif type_.name == "float64" or type_.name == "float32" or type_.name == "float":
                return Value("float", 0.0)
            elif type_.name == "string":
                return Value("string", "")
            elif type_.name == "bool":
                return Value("bool", False)
            else:
                return Value("nil", None)
        
        elif isinstance(type_, ArrayType):
            # For arrays, create array with zero values
            if type_.size:
                # Fixed-size array: [5]int
                size_val = self.eval_expression(type_.size)
                size = int(size_val.value)
                # Create independent zero values for each element
                elements = [self.get_zero_value(type_.type_) for _ in range(size)]
                return Value("array", elements)
            else:
                # Slice: []int - uninitialized starts as nil
                return Value("array", None)
        
        elif isinstance(type_, SliceType):
            # Uninitialized slices are nil
            return Value("array", None)
        
        elif isinstance(type_, MapType):
            # Maps start empty
            return Value("map", {})
        
        elif isinstance(type_, PointerType):
            # Pointers start as nil
            return Value("pointer", None)
        
        else:
            return Value("nil", None)

    def _infer_map_zero(self, map_val: 'Value') -> 'Value':
        """Infer zero value for a map based on its existing values"""
        if map_val.value:
            sample = next(iter(map_val.value.values()))
            type_name = sample.type_name
            if type_name == "int":
                return Value("int", 0)
            elif type_name == "float":
                return Value("float", 0.0)
            elif type_name == "string":
                return Value("string", "")
            elif type_name == "bool":
                return Value("bool", False)
        return Value("int", 0)  # default for empty/unknown maps

    def run(self):
        """Execute the program"""
        try:
            if self.program.package:
                # Package declaration is just metadata
                pass
            
            for decl in self.program.declarations:
                self.execute_declaration(decl)
            
            # Look for main function and execute it
            try:
                main_func = self.global_env.get_function("main")
            except (RuntimeError, KeyError, NameError):
                main_func = None  # No main function, that's okay
            if main_func is not None:
                self.call_function(main_func, [])
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.print_output(f"Error: {str(e)}")
    
    def execute_declaration(self, decl: Union[FuncDecl, VarDecl, ConstDecl, TypeDecl, StructDecl, InterfaceDecl]):
        """Execute a top-level declaration"""
        if isinstance(decl, FuncDecl):
            if decl.receiver:
                # Method with receiver: store in methods dict
                recv_type = decl.receiver.type_
                if isinstance(recv_type, PointerType):
                    type_name = recv_type.type_.name if isinstance(recv_type.type_, NamedType) else str(recv_type.type_)
                else:
                    type_name = recv_type.name if isinstance(recv_type, NamedType) else str(recv_type)
                if type_name not in self.methods:
                    self.methods[type_name] = {}
                self.methods[type_name][decl.name] = (decl, decl.receiver)
            else:
                self.global_env.define_function(decl.name, decl)
        elif isinstance(decl, VarDecl):
            value = None
            if decl.value:
                value = self.eval_expression(decl.value)
            else:
                value = self.get_zero_value(decl.type_)
            self.global_env.define(decl.name, value)
        elif isinstance(decl, ConstDecl):
            value = self.eval_expression(decl.value)
            # Preserve named type (e.g. StateIdle ServerState = iota)
            if decl.type_ and isinstance(decl.type_, NamedType):
                value = Value(decl.type_.name, value.value)
            self.global_env.define_const(decl.name, value)
        elif isinstance(decl, TypeDecl):
            self.type_registry[decl.name] = decl
        elif isinstance(decl, StructDecl):
            self.type_registry[decl.name] = decl
        elif isinstance(decl, InterfaceDecl):
            self.type_registry[decl.name] = decl
    
    def eval_expression(self, expr: Expression) -> Value:
        """Evaluate an expression"""
        if isinstance(expr, Literal):
            return self.eval_literal(expr)
        elif isinstance(expr, Identifier):
            return self.current_env.get(expr.name)
        elif isinstance(expr, BinaryOp):
            return self.eval_binary_op(expr)
        elif isinstance(expr, UnaryOp):
            return self.eval_unary_op(expr)
        elif isinstance(expr, CallExpr):
            return self.eval_call(expr)
        elif isinstance(expr, IndexExpr):
            return self.eval_index(expr)
        elif isinstance(expr, FieldExpr):
            return self.eval_field(expr)
        elif isinstance(expr, ArrayLiteral):
            return self.eval_array_literal(expr)
        elif isinstance(expr, MapLiteral):
            return self.eval_map_literal(expr)
        elif isinstance(expr, StructLiteral):
            return self.eval_struct_literal(expr)
        elif isinstance(expr, TypeCast):
            return self.eval_type_cast(expr)
        elif isinstance(expr, TernaryOp):
            return self.eval_ternary(expr)
        elif isinstance(expr, SliceExpr):
            return self.eval_slice(expr)
        elif isinstance(expr, MakeLiteral):
            return self.eval_make(expr)
        elif isinstance(expr, NewLiteral):
            return self.eval_new(expr)
        elif isinstance(expr, LambdaExpr):
            # Store both the lambda and the environment for closures
            return Value("function", {"lambda": expr, "env": self.current_env})
        else:
            raise RuntimeError(f"Unknown expression type: {type(expr)}")
    
    def eval_literal(self, lit: Literal) -> Value:
        """Evaluate a literal"""
        # Handle both string type names and TokenType enums
        type_str = lit.type_
        if hasattr(type_str, 'name'):  # TokenType enum
            type_str = type_str.name.lower()
        
        if type_str == "int":
            return Value("int", int(lit.value, 0) if isinstance(lit.value, str) and lit.value.startswith('0x') else int(lit.value))
        elif type_str == "float":
            return Value("float", float(lit.value))
        elif type_str == "string":
            return Value("string", lit.value)
        elif type_str == "rune":
            return Value("rune", ord(lit.value[0]) if lit.value else 0)
        elif type_str == "bool":
            return Value("bool", lit.value == "true")
        elif type_str == "true":
            return Value("bool", True)
        elif type_str == "false":
            return Value("bool", False)
        elif type_str == "nil":
            return Value("nil", None)
        else:
            raise RuntimeError(f"Unknown literal type: {lit.type_}")
    
    def eval_binary_op(self, op: BinaryOp) -> Value:
        """Evaluate a binary operation"""
        left = self.eval_expression(op.left)
        right = self.eval_expression(op.right)
        
        if op.op == "+":
            if left.type_name == "string" or right.type_name == "string":
                return Value("string", self.to_string(left) + self.to_string(right))
            elif left.type_name == "int" and right.type_name == "int":
                return Value("int", left.value + right.value)
            elif left.type_name in ["int", "float"] and right.type_name in ["int", "float"]:
                return Value("float", float(left.value) + float(right.value))
        elif op.op == "-":
            if left.type_name == "int" and right.type_name == "int":
                return Value("int", left.value - right.value)
            else:
                return Value("float", float(left.value) - float(right.value))
        elif op.op == "*":
            if left.type_name == "int" and right.type_name == "int":
                return Value("int", left.value * right.value)
            else:
                return Value("float", float(left.value) * float(right.value))
        elif op.op == "/":
            if right.value == 0:
                raise RuntimeError("Division by zero")
            if left.type_name == "int" and right.type_name == "int":
                return Value("int", left.value // right.value)
            else:
                return Value("float", float(left.value) / float(right.value))
        elif op.op == "%":
            return Value("int", int(left.value) % int(right.value))
        elif op.op == "==":
            # Handle nil comparison specially
            if left.type_name == "nil" or right.type_name == "nil":
                # In Go, only uninitialized slice is equal to nil
                if left.type_name == "nil" and right.type_name == "nil":
                    return Value("bool", True)
                elif left.type_name == "array" and right.type_name == "nil":
                    # Empty slice [] is not nil, check if it's really uninitialized
                    return Value("bool", left.value is None)
                elif left.type_name == "nil" and right.type_name == "array":
                    return Value("bool", right.value is None)
                else:
                    return Value("bool", left.value is None and right.value is None)
            return Value("bool", left.value == right.value)
        elif op.op == "!=":
            # Handle nil comparison specially
            if left.type_name == "nil" or right.type_name == "nil":
                if left.type_name == "nil" and right.type_name == "nil":
                    return Value("bool", False)
                elif left.type_name == "array" and right.type_name == "nil":
                    return Value("bool", left.value is not None)
                elif left.type_name == "nil" and right.type_name == "array":
                    return Value("bool", right.value is not None)
                else:
                    return Value("bool", not (left.value is None and right.value is None))
            return Value("bool", left.value != right.value)
        elif op.op == "<":
            return Value("bool", left.value < right.value)
        elif op.op == ">":
            return Value("bool", left.value > right.value)
        elif op.op == "<=":
            return Value("bool", left.value <= right.value)
        elif op.op == ">=":
            return Value("bool", left.value >= right.value)
        elif op.op == "&&":
            return Value("bool", self.is_truthy(left) and self.is_truthy(right))
        elif op.op == "||":
            return Value("bool", self.is_truthy(left) or self.is_truthy(right))
        elif op.op == "&":
            return Value("int", int(left.value) & int(right.value))
        elif op.op == "|":
            return Value("int", int(left.value) | int(right.value))
        elif op.op == "^":
            return Value("int", int(left.value) ^ int(right.value))
        elif op.op == "<<":
            return Value("int", int(left.value) << int(right.value))
        elif op.op == ">>":
            return Value("int", int(left.value) >> int(right.value))
        else:
            raise RuntimeError(f"Unknown operator: {op.op}")
    
    def eval_unary_op(self, op: UnaryOp) -> Value:
        """Evaluate a unary operation"""
        operand = self.eval_expression(op.operand)
        
        if op.op == "+":
            return operand
        elif op.op == "-":
            if operand.type_name == "int":
                return Value("int", -operand.value)
            else:
                return Value("float", -float(operand.value))
        elif op.op == "!":
            return Value("bool", not self.is_truthy(operand))
        elif op.op == "^":
            return Value("int", ~int(operand.value))
        elif op.op == "&":
            # Address-of: create a reference pointer to the actual variable
            operand_expr = op.operand
            if isinstance(operand_expr, Identifier):
                # Point to the environment variable by reference
                return Value("pointer", {"env": self.current_env, "name": operand_expr.name})
            elif isinstance(operand_expr, StructLiteral) or isinstance(operand_expr, CallExpr):
                # Heap-allocated pointer (e.g. &person{...} or &SomeFunc(...))
                heap_val = self.eval_expression(operand_expr)
                return Value("pointer", {"heap": heap_val})
            else:
                # Fallback: evaluate and wrap
                inner = self.eval_expression(operand_expr)
                return Value("pointer", {"heap": inner})
        elif op.op == "*":
            # Dereference operator
            if operand.type_name == "pointer":
                return self._deref_pointer(operand)
            else:
                raise RuntimeError(f"Cannot dereference non-pointer type: {operand.type_name}")
        elif op.op == "++":
            if isinstance(op.operand, Identifier):
                new_val = Value(operand.type_name, operand.value + 1)
                self.current_env.set(op.operand.name, new_val)
                return operand
        elif op.op == "--":
            if isinstance(op.operand, Identifier):
                new_val = Value(operand.type_name, operand.value - 1)
                self.current_env.set(op.operand.name, new_val)
                return operand
        else:
            raise RuntimeError(f"Unknown unary operator: {op.op}")
    
    def eval_call(self, call: CallExpr) -> Value:
        """Evaluate a function call"""
        # Handle fmt.Println, fmt.Print, and fmt.Printf
        if isinstance(call.func, FieldExpr):
            if isinstance(call.func.expr, Identifier):
                package = call.func.expr.name
                method = call.func.field
                
                # First check if it's a package.function call
                if package == "fmt":
                    output = []
                    if method == "Println":
                        for arg in call.args:
                            val = self.eval_expression(arg)
                            output.append(self.to_string(val))
                        self.print_output(" ".join(output))
                        return Value("nil", None)
                    elif method == "Print":
                        for arg in call.args:
                            val = self.eval_expression(arg)
                            output.append(self.to_string(val))
                        self.print_output_inline("".join(output))
                        return Value("nil", None)
                    elif method == "Printf":
                        if len(call.args) > 0:
                            format_val = self.eval_expression(call.args[0])
                            fmt_args = [self.eval_expression(arg) for arg in call.args[1:]]
                            result = self._format_string(str(format_val.value), fmt_args)
                            self.print_output_inline(result)
                        return Value("nil", None)
                    elif method == "Sprintf":
                        if len(call.args) > 0:
                            format_val = self.eval_expression(call.args[0])
                            fmt_args = [self.eval_expression(arg) for arg in call.args[1:]]
                            result = self._format_string(str(format_val.value), fmt_args)
                            return Value("string", result)
                        return Value("string", "")
                    elif method == "Errorf":
                        if len(call.args) > 0:
                            format_val = self.eval_expression(call.args[0])
                            fmt_args = [self.eval_expression(arg) for arg in call.args[1:]]
                            result = self._format_string(str(format_val.value), fmt_args)
                            return Value("error", result)
                        return Value("error", "")
                
                # Handle unicode/utf8 package
                if package == "utf8":
                    import unicodedata
                    if method == "RuneCountInString":
                        s = self.eval_expression(call.args[0]).value
                        return Value("int", len(s))
                    elif method == "DecodeRuneInString":
                        s = self.eval_expression(call.args[0]).value
                        if not s:
                            return Value("tuple", [Value("rune", 0xFFFD), Value("int", 0)])
                        ch = s[0]
                        cp = ord(ch)
                        width = len(ch.encode('utf-8'))
                        return Value("tuple", [Value("rune", cp), Value("int", width)])
                    elif method == "RuneLen":
                        r = self.eval_expression(call.args[0]).value
                        ch = chr(int(r))
                        return Value("int", len(ch.encode('utf-8')))
                    elif method == "ValidString":
                        return Value("bool", True)

                # Handle math package
                if package == "math":
                    import math as _m
                    _math_funcs1 = {
                        "Sin": _m.sin, "Cos": _m.cos, "Tan": _m.tan,
                        "Asin": _m.asin, "Acos": _m.acos, "Atan": _m.atan,
                        "Sqrt": _m.sqrt, "Cbrt": _m.pow,
                        "Exp": _m.exp, "Exp2": lambda x: 2**x,
                        "Log": _m.log, "Log2": _m.log2, "Log10": _m.log10,
                        "Abs": _m.fabs, "Ceil": _m.ceil, "Floor": _m.floor,
                        "Round": round, "Trunc": _m.trunc,
                        "Sinh": _m.sinh, "Cosh": _m.cosh, "Tanh": _m.tanh,
                        "IsNaN": _m.isnan, "IsInf": lambda x: _m.isinf(x),
                    }
                    _math_funcs2 = {
                        "Atan2": _m.atan2, "Pow": _m.pow, "Hypot": _m.hypot,
                        "Remainder": _m.remainder, "Mod": _m.fmod,
                        "Dim": lambda a, b: max(a - b, 0.0),
                        "Max": max, "Min": min,
                    }
                    if method == "Inf":
                        sign_arg = self.eval_expression(call.args[0]) if call.args else Value("int", 1)
                        sign = float(sign_arg.value)
                        return Value("float64", float('inf') if sign >= 0 else float('-inf'))
                    if method in _math_funcs1:
                        arg = self.eval_expression(call.args[0])
                        return Value("float64", float(_math_funcs1[method](float(arg.value))))
                    if method in _math_funcs2:
                        a = self.eval_expression(call.args[0])
                        b = self.eval_expression(call.args[1])
                        return Value("float64", float(_math_funcs2[method](float(a.value), float(b.value))))
                
                # Handle slices package
                if package == "slices":
                    if method == "Equal":
                        if len(call.args) != 2:
                            raise RuntimeError("slices.Equal() takes exactly 2 arguments")
                        a = self.eval_expression(call.args[0])
                        b = self.eval_expression(call.args[1])
                        if a.type_name == "array" and b.type_name == "array":
                            if len(a.value) != len(b.value):
                                return Value("bool", False)
                            for i in range(len(a.value)):
                                if a.value[i].value != b.value[i].value:
                                    return Value("bool", False)
                            return Value("bool", True)
                        return Value("bool", False)
                
                # Handle maps package
                if package == "maps":
                    if method == "Equal":
                        if len(call.args) != 2:
                            raise RuntimeError("maps.Equal() takes exactly 2 arguments")
                        a = self.eval_expression(call.args[0])
                        b = self.eval_expression(call.args[1])
                        if a.type_name == "map" and b.type_name == "map":
                            if len(a.value) != len(b.value):
                                return Value("bool", False)
                            for key in a.value:
                                if key not in b.value or a.value[key].value != b.value[key].value:
                                    return Value("bool", False)
                            return Value("bool", True)
                        return Value("bool", False)
                
                # Handle time package (simplified mocks)
                if package == "time":
                    if method == "Now":
                        # Return a mock time object
                        return Value("time", {"hour": 14, "weekday": 1})
                    if method == "Saturday":
                        return Value("int", 6)
                    if method == "Sunday":
                        return Value("int", 0)
            
            # Handle method calls on objects (like t.Hour(), user struct methods)
            obj = self.eval_expression(call.func.expr)
            method_name = call.func.field

            # Auto-deref pointer for method dispatch
            actual = obj
            if obj.type_name == "pointer":
                actual = self._deref_pointer(obj)

            type_name = actual.type_name

            # Built-in type methods
            if type_name == "time":
                if method_name == "Hour":
                    return Value("int", actual.value.get("hour", 12))
                elif method_name == "Weekday":
                    return Value("int", actual.value.get("weekday", 1))

            # User-defined methods
            if type_name in self.methods and method_name in self.methods[type_name]:
                method_decl, recv_param = self.methods[type_name][method_name]
                args = [self.eval_expression(a) for a in call.args]
                # If receiver is pointer-type, pass the pointer so mutations work
                if isinstance(recv_param.type_, PointerType):
                    return self.call_method(method_decl, obj, args)
                return self.call_method(method_decl, actual, args)

            # Check embedded struct types for method
            if isinstance(actual.value, dict):
                for emb_key, emb_val in actual.value.items():
                    if isinstance(emb_val, Value):
                        emb_type = emb_val.type_name
                        if emb_type in self.methods and method_name in self.methods[emb_type]:
                            method_decl, recv_param = self.methods[emb_type][method_name]
                            args = [self.eval_expression(a) for a in call.args]
                            return self.call_method(method_decl, emb_val, args)

            raise RuntimeError(f"Method '{method_name}' not found on type '{type_name}'")
        
        if isinstance(call.func, Identifier):
            func_name = call.func.name
            
            # Built-in functions
            if func_name == "len":
                if len(call.args) != 1:
                    raise RuntimeError("len() takes exactly 1 argument")
                arg = self.eval_expression(call.args[0])
                if arg.type_name == "string":
                    # Go's len() counts bytes, not characters
                    return Value("int", len(arg.value.encode('utf-8')))
                elif arg.type_name == "array":
                    if arg.value is None:  # nil slice
                        return Value("int", 0)
                    return Value("int", len(arg.value))
                elif arg.type_name == "map":
                    return Value("int", len(arg.value))
                else:
                    raise RuntimeError(f"len() not supported for type {arg.type_name}")
            
            elif func_name == "make":
                # make([]Type, size), make([][]Type, size), make(map[K]V)
                if len(call.args) < 1:
                    raise RuntimeError("make() requires at least 1 argument")
                
                # Determine the element type from the first argument
                type_arg = call.args[0]
                size = 0
                if len(call.args) >= 2:
                    size = int(self.eval_expression(call.args[1]).value)
                
                # Check if the type argument is a slice: []Type or [][]Type
                if isinstance(type_arg, ArrayLiteral) and type_arg.elements == []:
                    # This shouldn't happen, but fallback
                    return Value("array", [Value("nil", None) for _ in range(size)])
                
                # We need to determine element type from the AST
                # The parser would have stored the type info in the Identifier or elsewhere
                # Look for type info via the token position / identifier name
                # For now, handle based on the parsed arg structure
                
                # Build zero values based on known patterns
                if isinstance(type_arg, Identifier):
                    type_name_str = type_arg.name
                    if type_name_str == "map" or isinstance(type_arg, MapLiteral):
                        return Value("map", {})
                    return Value("array", [Value("nil", None) for _ in range(size)])
                
                return Value("array", [Value("nil", None) for _ in range(size)])
            
            elif func_name == "append":
                if len(call.args) < 2:
                    raise RuntimeError("append() requires at least 2 arguments")
                slice_val = self.eval_expression(call.args[0])
                if slice_val.type_name != "array":
                    raise RuntimeError("append() requires slice as first argument")
                new_slice = slice_val.value.copy()
                for i in range(1, len(call.args)):
                    new_slice.append(self.eval_expression(call.args[i]))
                return Value("array", new_slice)
            
            elif func_name == "delete":
                if len(call.args) != 2:
                    raise RuntimeError("delete() requires exactly 2 arguments")
                map_val = self.eval_expression(call.args[0])
                key_val = self.eval_expression(call.args[1])
                if map_val.type_name != "map":
                    raise RuntimeError("delete() requires map as first argument")
                key_str = self.to_string(key_val)
                if key_str in map_val.value:
                    del map_val.value[key_str]
                return Value("nil", None)

            elif func_name == "clear":
                if len(call.args) != 1:
                    raise RuntimeError("clear() requires exactly 1 argument")
                container = self.eval_expression(call.args[0])
                if container.type_name == "map":
                    container.value.clear()
                elif container.type_name == "array" and container.value is not None:
                    container.value.clear()
                return Value("nil", None)

            if func_name == "print":
                for arg in call.args:
                    val = self.eval_expression(arg)
                    self.print_output(self.to_string(val))
                return Value("nil", None)

            elif func_name == "panic":
                msg = self.eval_expression(call.args[0]) if call.args else Value("string", "panic")
                raise RuntimeError(f"panic: {self.to_string(msg)}")
                return Value("nil", None)
            
            elif func_name == "println":
                for arg in call.args:
                    val = self.eval_expression(arg)
                    self.print_output(self.to_string(val))
                return Value("nil", None)
            
            elif func_name == "len":
                if call.args:
                    val = self.eval_expression(call.args[0])
                    if val.type_name in ["string", "array", "map"]:
                        if val.value is None:  # nil slice
                            return Value("int", 0)
                        return Value("int", len(val.value))
                    else:
                        raise RuntimeError(f"Cannot get len of {val.type_name}")
            
            elif func_name == "cap":
                if call.args:
                    val = self.eval_expression(call.args[0])
                    if val.type_name in ["array"]:
                        if val.value is None:  # nil slice
                            return Value("int", 0)
                        return Value("int", len(val.value))
                    else:
                        raise RuntimeError(f"Cannot get cap of {val.type_name}")
            
            elif func_name == "append":
                if len(call.args) >= 2:
                    arr = self.eval_expression(call.args[0])
                    if arr.type_name == "array":
                        # Handle nil slice
                        if arr.value is None:
                            new_arr = []
                        else:
                            new_arr = arr.value.copy()
                        for arg in call.args[1:]:
                            new_arr.append(self.eval_expression(arg))
                        return Value("array", new_arr)
            
            elif func_name == "copy":
                if len(call.args) != 2:
                    raise RuntimeError("copy() requires exactly 2 arguments")
                dst = self.eval_expression(call.args[0])
                src = self.eval_expression(call.args[1])
                if dst.type_name != "array" or src.type_name != "array":
                    raise RuntimeError("copy() requires slices as arguments")
                if dst.value is None or src.value is None:
                    return Value("int", 0)
                # Copy elements from src to dst
                count = min(len(dst.value), len(src.value))
                for i in range(count):
                    dst.value[i] = src.value[i]
                return Value("int", count)
            
            elif func_name == "make":
                return self.eval_make_builtin(call.args)
            
            elif func_name == "int":
                if call.args:
                    val = self.eval_expression(call.args[0])
                    return Value("int", int(float(val.value)))
            
            elif func_name == "int64":
                if call.args:
                    val = self.eval_expression(call.args[0])
                    return Value("int", int(float(val.value)))
            
            elif func_name == "string":
                if call.args:
                    val = self.eval_expression(call.args[0])
                    return Value("string", self.to_string(val))
            
            elif func_name == "float64":
                if call.args:
                    val = self.eval_expression(call.args[0])
                    return Value("float", float(val.value))
            
            else:
                # User-defined function
                try:
                    func_decl = self.current_env.get_function(func_name)
                    # Handle nums... spread: if last arg is EllipsisExpr, unpack the slice
                    raw_args = call.args
                    if raw_args and isinstance(raw_args[-1], EllipsisExpr):
                        spread_val = self.eval_expression(raw_args[-1].expr)
                        args = [self.eval_expression(a) for a in raw_args[:-1]]
                        if spread_val.type_name == "array" and spread_val.value:
                            args.extend(spread_val.value)
                    else:
                        args = [self.eval_expression(arg) for arg in raw_args]
                    return self.call_function(func_decl, args)
                except RuntimeError:
                    # Check if it's a variable holding a function (closure)
                    try:
                        var_value = self.current_env.get(func_name)
                        if var_value.type_name == "function":
                            args = [self.eval_expression(arg) for arg in call.args]
                            return self.call_lambda(var_value.value, args)
                    except RuntimeError:
                        pass
                    raise RuntimeError(f"Undefined function: {func_name}")
        
        raise RuntimeError("Invalid function call")
    
    def call_function(self, func_decl: FuncDecl, args: List[Value]) -> Value:
        """Call a user-defined function"""
        # Create new environment for function
        func_env = Environment(self.global_env)
        
        # Bind parameters — handle variadic last param
        for i, param in enumerate(func_decl.params):
            if param.variadic:
                # Pack all remaining args into a slice
                func_env.define(param.name, Value("array", list(args[i:])))
            elif i < len(args):
                func_env.define(param.name, args[i])
            else:
                func_env.define(param.name, Value("nil", None))
        
        # Execute function body
        prev_env = self.current_env
        self.current_env = func_env
        
        try:
            if func_decl.body:
                self.execute_block(func_decl.body)
            return Value("nil", None)
        except ReturnException as ret:
            # If multiple return values, return them as a tuple Value
            if len(ret.values) > 1:
                return Value("tuple", ret.values)
            else:
                return ret.values[0] if ret.values else Value("nil", None)
        finally:
            self.current_env = prev_env
    
    def call_lambda(self, closure: dict, args: List[Value]) -> Value:
        """Call a lambda/closure function"""
        lambda_expr = closure["lambda"]
        captured_env = closure["env"]
        
        # Create new environment with captured environment as parent (for closure)
        func_env = Environment(captured_env)
        
        # Bind parameters
        for i, param in enumerate(lambda_expr.params):
            if i < len(args):
                func_env.define(param.name, args[i])
            else:
                func_env.define(param.name, Value("nil", None))
        
        # Execute function body
        prev_env = self.current_env
        self.current_env = func_env
        
        try:
            if lambda_expr.body:
                self.execute_block(lambda_expr.body)
            return Value("nil", None)
        except ReturnException as ret:
            if len(ret.values) > 1:
                return Value("tuple", ret.values)
            else:
                return ret.values[0] if ret.values else Value("nil", None)
        finally:
            self.current_env = prev_env
    
    def eval_index(self, idx: IndexExpr) -> Value:
        """Evaluate array/map indexing"""
        expr = self.eval_expression(idx.expr)
        index = self.eval_expression(idx.index)

        # Auto-deref pointer
        if expr.type_name == "pointer":
            expr = self._deref_pointer(expr)

        if expr.type_name == "array":
            i = int(index.value)
            if expr.value is None:
                raise RuntimeError("index on nil slice")
            if 0 <= i < len(expr.value):
                return expr.value[i]
            else:
                raise RuntimeError(f"Array index out of bounds: {i}")
        elif expr.type_name == "map":
            key = self.to_map_key(index)
            if key in expr.value:
                return expr.value[key]
            else:
                return self._infer_map_zero(expr)
        elif expr.type_name == "string":
            i = int(index.value)
            s = expr.value
            if 0 <= i < len(s.encode('utf-8')):
                # Return byte at that position
                return Value("int", s.encode('utf-8')[i])
            else:
                raise RuntimeError(f"String index out of bounds: {i}")
        else:
            raise RuntimeError(f"Cannot index {expr.type_name}")
    
    def eval_field(self, field: FieldExpr) -> Value:
        """Evaluate field access (struct.field, auto-deref pointers, methods)"""
        # Handle math package constants before evaluating the object expression
        if isinstance(field.expr, Identifier) and field.expr.name == "math":
            import math as _math
            _math_consts = {
                "Pi": _math.pi, "E": _math.e, "Phi": 1.618033988749895,
                "Sqrt2": _math.sqrt(2), "SqrtE": _math.sqrt(_math.e),
                "SqrtPi": _math.sqrt(_math.pi), "SqrtPhi": _math.sqrt(1.618033988749895),
                "Ln2": _math.log(2), "Log2E": _math.log2(_math.e),
                "Ln10": _math.log(10), "Log10E": _math.log10(_math.e),
                "MaxFloat64": 1.7976931348623157e+308, "SmallestNonzeroFloat64": 5e-324,
                "MaxInt": 9223372036854775807, "MinInt": -9223372036854775808,
                "Inf": float('inf'), "NaN": float('nan'),
            }
            fname = field.field
            if fname in _math_consts:
                return Value("float64", _math_consts[fname])
        obj = self.eval_expression(field.expr)

        # Auto-dereference pointer
        actual = obj
        if obj.type_name == "pointer":
            actual = self._deref_pointer(obj)

        field_name = field.field

        # Direct struct field access
        if isinstance(actual.value, dict):
            if field_name in actual.value:
                return actual.value[field_name]
            # Check embedded fields
            for k, v in actual.value.items():
                if isinstance(v, Value) and isinstance(v.value, dict) and field_name in v.value:
                    return v.value[field_name]

        # Package-level or function variable access (fallback)
        raise RuntimeError(f"Field '{field_name}' not found on {actual.type_name}")
    
    def eval_array_literal(self, arr: ArrayLiteral) -> Value:
        """Evaluate array literal"""
        elements = [self.eval_expression(elem) for elem in arr.elements]
        return Value("array", elements)
    
    def eval_map_literal(self, map_lit: MapLiteral) -> Value:
        """Evaluate map literal"""
        map_dict = {}
        for key, value in map_lit.pairs:
            self.skip_newlines_hook()
            k = self.to_map_key(self.eval_expression(key))
            v = self.eval_expression(value)
            map_dict[k] = v
        return Value("map", map_dict)

    def skip_newlines_hook(self):
        """No-op hook for map literal evaluation (placeholder)."""
        pass
    
    def eval_struct_literal(self, struct_lit: StructLiteral) -> Value:
        """Evaluate struct literal"""
        # Look up type definition for field ordering / zero values
        type_name = struct_lit.type_
        type_def = self.type_registry.get(type_name)
        struct_dict = {}

        # Pre-fill with zero values if type is known
        if type_def and isinstance(type_def, StructDecl):
            for f in type_def.fields:
                struct_dict[f.name] = self.get_zero_value(f.type_)

        if struct_lit.fields and struct_lit.fields[0][0] == "":
            # Positional fields
            if type_def and isinstance(type_def, StructDecl):
                for i, (_, val_expr) in enumerate(struct_lit.fields):
                    if i < len(type_def.fields):
                        struct_dict[type_def.fields[i].name] = self.eval_expression(val_expr)
            else:
                for i, (_, val_expr) in enumerate(struct_lit.fields):
                    struct_dict[f"_f{i}"] = self.eval_expression(val_expr)
        else:
            # Named fields (may be mixed with keys from embedded structs)
            for field_name, val_expr in struct_lit.fields:
                if field_name == "":
                    continue
                val = self.eval_expression(val_expr)
                # Check if this field is actually an embedded struct field name
                if (type_def and isinstance(type_def, StructDecl) and
                        any(f.name == field_name and f.embedded for f in type_def.fields)):
                    struct_dict[field_name] = val
                else:
                    struct_dict[field_name] = val
        return Value(type_name, struct_dict)
    
    def eval_type_cast(self, cast: TypeCast) -> Value:
        """Evaluate type cast or type assertion"""
        expr = self.eval_expression(cast.expr)

        if isinstance(cast.type_, PrimitiveType):
            if cast.type_.name == "int":
                return Value("int", int(float(expr.value)))
            elif cast.type_.name in ("float64", "float32", "float"):
                return Value("float", float(expr.value))
            elif cast.type_.name == "string":
                # int->string: interpret as rune
                if expr.type_name in ("int", "rune"):
                    return Value("string", chr(int(expr.value)))
                return Value("string", self.to_string(expr))
            elif cast.type_.name == "bool":
                return Value("bool", self.is_truthy(expr))
            elif cast.type_.name in ("byte", "uint8", "int8", "int16", "int32", "int64",
                                     "uint", "uint16", "uint32", "uint64", "uintptr"):
                return Value("int", int(float(expr.value)))
            elif cast.type_.name == "rune":
                return Value("rune", int(expr.value))
        elif isinstance(cast.type_, NamedType):
            target_name = cast.type_.name
            # Auto-deref pointer for type assertions
            actual = expr
            if expr.type_name == "pointer":
                actual = self._deref_pointer(expr)
            # Same underlying type or struct match
            if actual.type_name == target_name:
                return actual
            if isinstance(actual.value, dict):
                # Struct value cast to named type (interface assertion)
                return Value(target_name, actual.value)
            # Numeric cast to named type
            if isinstance(actual.value, (int, float)):
                return Value(target_name, actual.value)
            return Value(target_name, actual.value)

        return expr
    
    def eval_ternary(self, ternary: TernaryOp) -> Value:
        """Evaluate ternary operator"""
        condition = self.eval_expression(ternary.condition)
        if self.is_truthy(condition):
            return self.eval_expression(ternary.true_expr)
        else:
            return self.eval_expression(ternary.false_expr)
    
    def eval_slice(self, slice_expr: SliceExpr) -> Value:
        """Evaluate slice expression"""
        expr = self.eval_expression(slice_expr.expr)
        
        # Handle nil slices
        if expr.value is None:
            return Value("array", None)
        
        start = 0
        end = len(expr.value)
        
        if slice_expr.start:
            start = int(self.eval_expression(slice_expr.start).value)
        if slice_expr.end:
            end = int(self.eval_expression(slice_expr.end).value)
        
        if expr.type_name == "string":
            # Go string slicing uses byte offsets
            encoded = expr.value.encode('utf-8')
            if slice_expr.end:
                sliced_bytes = encoded[start:end]
            else:
                sliced_bytes = encoded[start:]
            return Value("string", sliced_bytes.decode('utf-8'))
        elif expr.type_name in ["array"]:
            sliced = expr.value[start:end]
            return Value(expr.type_name, sliced)
        else:
            raise RuntimeError(f"Cannot slice {expr.type_name}")
    
    def eval_make(self, make_lit: MakeLiteral) -> Value:
        """Evaluate make expression"""
        if isinstance(make_lit.type_, SliceType):
            length = 0
            if make_lit.len_:
                length = int(self.eval_expression(make_lit.len_).value)
            # Create slice with zero values of the element type
            elements = [self.get_zero_value(make_lit.type_.type_) for _ in range(length)]
            return Value("array", elements)
        
        elif isinstance(make_lit.type_, MapType):
            return Value("map", {})
        
        elif isinstance(make_lit.type_, ChannelType):
            return Value("channel", [])
        
        else:
            raise RuntimeError(f"Cannot make {type(make_lit.type_)}")
    
    def eval_make_builtin(self, args: List[Expression]) -> Value:
        """Evaluate make builtin function"""
        if not args:
            raise RuntimeError("make requires at least 1 argument")
        
        type_arg = self.eval_expression(args[0])
        
        if isinstance(args[0], Identifier):
            type_name = args[0].name
            if type_name == "map":
                return Value("map", {})
            elif type_name.startswith("[]"):
                length = 0
                if len(args) > 1:
                    length = int(self.eval_expression(args[1]).value)
                return Value("array", [Value("nil", None) for _ in range(length)])
        
        return Value("nil", None)
    
    def eval_new(self, new_lit: NewLiteral) -> Value:
        """Evaluate new expression"""
        return Value("pointer", Value("nil", None))
    
    def execute_block(self, block: Block):
        """Execute a block of statements"""
        for stmt in block.statements:
            self.execute_statement(stmt)
    
    def execute_statement(self, stmt: Statement):
        """Execute a statement"""
        if isinstance(stmt, ExpressionStmt):
            self.eval_expression(stmt.expr)
        
        elif isinstance(stmt, VarDecl):
            # Handle local variable declaration
            value = None
            if stmt.value:
                value = self.eval_expression(stmt.value)
            else:
                # Initialize with zero value for the type
                value = self.get_zero_value(stmt.type_)
            self.current_env.define(stmt.name, value)
        
        elif isinstance(stmt, ConstDecl):
            # Handle local constant declaration
            value = self.eval_expression(stmt.value)
            self.current_env.define_const(stmt.name, value)
        
        elif isinstance(stmt, ReturnStmt):
            values = [self.eval_expression(v) for v in stmt.values]
            raise ReturnException(values)
        
        elif isinstance(stmt, IfStmt):
            self.execute_if(stmt)
        
        elif isinstance(stmt, ForStmt):
            self.execute_for(stmt)
        
        elif isinstance(stmt, ForRangeStmt):
            self.execute_for_range(stmt)
        
        elif isinstance(stmt, SwitchStmt):
            self.execute_switch(stmt)
        
        elif isinstance(stmt, Block):
            self.execute_block(stmt)
        
        elif isinstance(stmt, DeferStmt):
            # Defer execution (simplified - execute immediately for now)
            self.eval_expression(stmt.call)
        
        elif isinstance(stmt, GoStmt):
            # Goroutine (simplified - execute immediately for now)
            self.eval_expression(stmt.call)
        
        elif isinstance(stmt, BreakStmt):
            raise BreakException()
        
        elif isinstance(stmt, ContinueStmt):
            raise ContinueException()
        
        elif isinstance(stmt, FallthroughStmt):
            raise FallthroughException()
        
        elif isinstance(stmt, AssignStmt):
            self.execute_assign(stmt)
        
        elif isinstance(stmt, IncDecStmt):
            self.execute_inc_dec(stmt)
        
        elif isinstance(stmt, (StructDecl, InterfaceDecl, TypeDecl)):
            # Local type declaration inside a function — register it
            self.execute_declaration(stmt)
    
    def execute_if(self, if_stmt: IfStmt):
        """Execute if statement"""
        # Execute init statement if present
        if if_stmt.init:
            self.execute_statement(if_stmt.init)
        
        condition = self.eval_expression(if_stmt.condition)
        
        if self.is_truthy(condition):
            self.execute_block(if_stmt.then_block)
        elif if_stmt.else_block:
            if isinstance(if_stmt.else_block, IfStmt):
                self.execute_if(if_stmt.else_block)
            else:
                self.execute_block(if_stmt.else_block)
    
    def execute_for(self, for_stmt: ForStmt):
        """Execute for loop"""
        if for_stmt.init:
            self.execute_statement(for_stmt.init)
        
        while True:
            if for_stmt.condition:
                condition = self.eval_expression(for_stmt.condition)
                if not self.is_truthy(condition):
                    break
            
            try:
                self.execute_block(for_stmt.body)
            except BreakException:
                break
            except ContinueException:
                pass
            
            if for_stmt.post:
                self.execute_statement(for_stmt.post)
    
    def execute_for_range(self, for_range: ForRangeStmt):
        """Execute for range loop"""
        iterable = self.eval_expression(for_range.iterable)
        
        # Handle range over integers: for i := range 3 (0, 1, 2)
        if iterable.type_name == "int":
            for i in range(int(iterable.value)):
                if for_range.key and for_range.key != "_":
                    self.current_env.define(for_range.key, Value("int", i))
                if for_range.value and for_range.value != "_":
                    self.current_env.define(for_range.value, Value("int", i))
                
                try:
                    self.execute_block(for_range.body)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif iterable.type_name == "array":
            for i, elem in enumerate(iterable.value):
                if for_range.key and for_range.key != "_":
                    self.current_env.define(for_range.key, Value("int", i))
                if for_range.value and for_range.value != "_":
                    self.current_env.define(for_range.value, elem)
                
                try:
                    self.execute_block(for_range.body)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif iterable.type_name == "map":
            for key, value in iterable.value.items():
                if for_range.key and for_range.key != "_":
                    self.current_env.define(for_range.key, Value("string", key))
                if for_range.value and for_range.value != "_":
                    self.current_env.define(for_range.value, value)
                
                try:
                    self.execute_block(for_range.body)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif iterable.type_name == "string":
            byte_pos = 0
            for rune_char in iterable.value:
                if for_range.key and for_range.key != "_":
                    self.current_env.define(for_range.key, Value("int", byte_pos))
                if for_range.value and for_range.value != "_":
                    self.current_env.define(for_range.value, Value("rune", ord(rune_char)))
                try:
                    self.execute_block(for_range.body)
                except BreakException:
                    break
                except ContinueException:
                    pass
                byte_pos += len(rune_char.encode('utf-8'))
    
    def execute_switch(self, switch_stmt: SwitchStmt):
        """Execute switch statement"""
        switch_val = None
        if switch_stmt.expr:
            switch_val = self.eval_expression(switch_stmt.expr)
        
        matched = False
        for case in switch_stmt.cases:
            if matched:
                # Execute remaining cases after match (fallthrough behavior)
                try:
                    for stmt in case.statements:
                        self.execute_statement(stmt)
                except FallthroughException:
                    continue
                except BreakException:
                    break
            else:
                # Check if case matches
                if not case.values:  # Default case
                    matched = True
                    try:
                        for stmt in case.statements:
                            self.execute_statement(stmt)
                    except FallthroughException:
                        continue
                    except BreakException:
                        break
                else:
                    for val_expr in case.values:
                        case_val = self.eval_expression(val_expr)
                        if switch_val is None or case_val.value == switch_val.value:
                            matched = True
                            try:
                                for stmt in case.statements:
                                    self.execute_statement(stmt)
                            except FallthroughException:
                                break
                            except BreakException:
                                return
                            break
    
    def execute_assign(self, assign: AssignStmt):
        """Execute assignment statement"""
        def _eval_single_or_comma_ok(val_expr):
            """Evaluate expression; return (val, bool) tuple for comma-ok patterns."""
            if isinstance(val_expr, IndexExpr):
                container = self.eval_expression(val_expr.expr)
                if container.type_name == "map":
                    key = self.to_map_key(self.eval_expression(val_expr.index))
                    exists = key in container.value
                    map_val = container.value[key] if exists else self._infer_map_zero(container)
                    return Value("tuple", [map_val, Value("bool", exists)])
            elif isinstance(val_expr, TypeCast):
                # Type assertion comma-ok: c, ok := x.(T)
                obj = self.eval_expression(val_expr.expr)
                if obj.type_name == "pointer":
                    obj = self._deref_pointer(obj)
                target_type = val_expr.type_
                target_name = target_type.name if isinstance(target_type, NamedType) else None
                if target_name and obj.type_name == target_name:
                    return Value("tuple", [obj, Value("bool", True)])
                # Type assertion fails
                return Value("tuple", [Value("nil", None), Value("bool", False)])
            return self.eval_expression(val_expr)

        def _assign_target(target, value, op, is_define):
            """Assign value to a single target."""
            if isinstance(target, Identifier):
                if target.name == "_":
                    return
                if op in ("+=", "-=", "*=", "/=", "%=", "&=", "|=", "^="):
                    current = self.current_env.get(target.name)
                    value = self._apply_compound_op(op[:-1], current, value)
                if is_define:
                    self.current_env.define(target.name, value)
                else:
                    self.current_env.set(target.name, value)
            elif isinstance(target, FieldExpr):
                # obj.field = value (auto-deref if pointer)
                obj = self.eval_expression(target.expr)
                if obj.type_name == "pointer":
                    obj = self._deref_pointer(obj)
                if isinstance(obj.value, dict):
                    fname = target.field
                    if fname in obj.value:
                        if op in ("+=", "-=", "*=", "/=", "%="):
                            value = self._apply_compound_op(op[:-1], obj.value[fname], value)
                        obj.value[fname] = value
                    else:
                        # Check embedded fields
                        for emb_val in obj.value.values():
                            if isinstance(emb_val, Value) and isinstance(emb_val.value, dict) and fname in emb_val.value:
                                obj.value[fname] = value
                                return
                        obj.value[fname] = value  # create new field
            elif isinstance(target, UnaryOp) and target.op == "*":
                # *ptr = value
                ptr = self.eval_expression(target.operand)
                if ptr.type_name == "pointer":
                    self._assign_through_pointer(ptr, value)
            elif isinstance(target, IndexExpr):
                expr_val = self.eval_expression(target.expr)
                if expr_val.type_name == "pointer":
                    expr_val = self._deref_pointer(expr_val)
                index_val = self.eval_expression(target.index)
                if op in ("+=", "-=", "*=", "/=", "%="):
                    op_base = op[:-1]
                    if expr_val.type_name == "array":
                        current = expr_val.value[int(index_val.value)]
                        value = self._apply_compound_op(op_base, current, value)
                        expr_val.value[int(index_val.value)] = value
                    elif expr_val.type_name == "map":
                        key = self.to_map_key(index_val)
                        current = expr_val.value.get(key, Value("int", 0))
                        value = self._apply_compound_op(op_base, current, value)
                        expr_val.value[key] = value
                else:
                    if expr_val.type_name == "array":
                        expr_val.value[int(index_val.value)] = value
                    elif expr_val.type_name == "map":
                        expr_val.value[self.to_map_key(index_val)] = value

        op = assign.operator
        is_define = (op == ":=")

        # Multi-target from single expression (tuple unpack / comma-ok)
        if len(assign.values) == 1 and len(assign.targets) > 1:
            value = _eval_single_or_comma_ok(assign.values[0])
            if value.type_name == "tuple" and isinstance(value.value, list):
                for i, target in enumerate(assign.targets):
                    v = value.value[i] if i < len(value.value) else Value("nil", None)
                    _assign_target(target, v, "=", is_define)
            else:
                _assign_target(assign.targets[0], value, "=", is_define)
                for target in assign.targets[1:]:
                    _assign_target(target, Value("nil", None), "=", is_define)
        else:
            # Evaluate all RHS first (handles swap: a, b = b, a)
            values = []
            for i in range(len(assign.targets)):
                if i < len(assign.values):
                    values.append(self.eval_expression(assign.values[i]))
                else:
                    values.append(Value("nil", None))
            for i, target in enumerate(assign.targets):
                _assign_target(target, values[i], op, is_define)


    def _apply_compound_op(self, op: str, left: 'Value', right: 'Value') -> 'Value':
        """Apply a binary operator for compound assignment (+=, -=, etc.)"""
        lv = left.value
        rv = right.value
        if op == "+":
            if left.type_name == "string":
                return Value("string", str(lv) + str(rv))
            return Value(left.type_name, lv + rv)
        elif op == "-":
            return Value(left.type_name, lv - rv)
        elif op == "*":
            return Value(left.type_name, lv * rv)
        elif op == "/":
            if left.type_name in ("float", "float64", "float32"):
                return Value(left.type_name, lv / rv)
            return Value(left.type_name, int(lv // rv))
        elif op == "%":
            return Value(left.type_name, lv % rv)
        elif op == "&":
            return Value(left.type_name, int(lv) & int(rv))
        elif op == "|":
            return Value(left.type_name, int(lv) | int(rv))
        elif op == "^":
            return Value(left.type_name, int(lv) ^ int(rv))
        return right

    def execute_inc_dec(self, stmt: IncDecStmt):
        """Execute increment/decrement statement"""
        if isinstance(stmt.expr, Identifier):
            val = self.current_env.get(stmt.expr.name)
            if stmt.operator == "++":
                self.current_env.set(stmt.expr.name, Value(val.type_name, val.value + 1))
            elif stmt.operator == "--":
                self.current_env.set(stmt.expr.name, Value(val.type_name, val.value - 1))