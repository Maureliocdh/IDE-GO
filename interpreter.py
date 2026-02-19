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
        self.setup_builtins()
    
    def setup_builtins(self):
        """Setup built-in functions and constants"""
        # Built-in functions will be handled in call_function
        pass
    
    def print_output(self, message: str):
        """Print to console or output widget"""
        if self.output_widget:
            self.output_widget.insert("end", message + "\n")
            self.output_widget.see("end")
        else:
            print(message)
    
    def type_of(self, value: Value) -> str:
        """Get the type name of a value"""
        return value.type_name
    
    def to_string(self, value: Value) -> str:
        """Convert value to string representation"""
        if value.type_name == "string":
            return value.value
        elif value.type_name == "int":
            return str(value.value)
        elif value.type_name == "float":
            return str(value.value)
        elif value.type_name == "bool":
            return "true" if value.value else "false"
        elif value.type_name == "array":
            elements = [self.to_string(v) for v in value.value]
            return "[" + ", ".join(elements) + "]"
        elif value.type_name == "map":
            pairs = [f"{k}: {self.to_string(v)}" for k, v in value.value.items()]
            return "{" + ", ".join(pairs) + "}"
        else:
            return str(value.value)
    
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
                self.call_function(main_func, [])
            except RuntimeError:
                # No main function, that's okay
                pass
        
        except Exception as e:
            self.print_output(f"Error: {str(e)}")
    
    def execute_declaration(self, decl: Union[FuncDecl, VarDecl, ConstDecl, TypeDecl, StructDecl, InterfaceDecl]):
        """Execute a top-level declaration"""
        if isinstance(decl, FuncDecl):
            self.global_env.define_function(decl.name, decl)
        elif isinstance(decl, VarDecl):
            value = None
            if decl.value:
                value = self.eval_expression(decl.value)
            else:
                value = Value("nil", None)
            self.global_env.define(decl.name, value)
        elif isinstance(decl, ConstDecl):
            value = self.eval_expression(decl.value)
            self.global_env.define_const(decl.name, value)
        elif isinstance(decl, TypeDecl):
            # Type declarations are just metadata in our interpreter
            pass
        elif isinstance(decl, StructDecl):
            # Struct declarations are stored for later use
            pass
        elif isinstance(decl, InterfaceDecl):
            # Interface declarations are stored for later use
            pass
    
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
            return Value("int", int(lit.value))
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
            return Value("bool", left.value == right.value)
        elif op.op == "!=":
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
            # Address-of operator (returns pointer)
            return Value("pointer", operand)
        elif op.op == "*":
            # Dereference operator
            if operand.type_name == "pointer":
                return operand.value
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
                        self.print_output("".join(output))
                        return Value("nil", None)
                    elif method == "Printf":
                        if len(call.args) > 0:
                            format_val = self.eval_expression(call.args[0])
                            format_str = str(format_val.value)
                            args = [self.eval_expression(arg) for arg in call.args[1:]]
                            
                            # Simple printf implementation
                            result = format_str
                            for arg in args:
                                # Replace various format specifiers
                                if '%s' in result:
                                    result = result.replace('%s', self.to_string(arg), 1)
                                elif '%d' in result:
                                    result = result.replace('%d', str(int(arg.value)), 1)
                                elif '%f' in result:
                                    result = result.replace('%f', str(float(arg.value)), 1)
                                elif '%v' in result:
                                    result = result.replace('%v', self.to_string(arg), 1)
                                elif '%T' in result:
                                    result = result.replace('%T', arg.type_name, 1)
                            
                            # Handle \n escape sequences
                            result = result.replace('\\n', '\n')
                            self.print_output(result)
                        return Value("nil", None)
                
                # Handle math package
                if package == "math":
                    if method == "Sin":
                        if len(call.args) != 1:
                            raise RuntimeError("math.Sin() takes exactly 1 argument")
                        arg = self.eval_expression(call.args[0])
                        import math
                        return Value("float", math.sin(float(arg.value)))
                
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
            
            # Handle method calls on objects (like t.Hour())
            obj = self.eval_expression(call.func.expr)
            method = call.func.field
            
            if obj.type_name == "time":
                if method == "Hour":
                    return Value("int", obj.value.get("hour", 12))
                elif method == "Weekday":
                    return Value("int", obj.value.get("weekday", 1))
        
        if isinstance(call.func, Identifier):
            func_name = call.func.name
            
            # Built-in functions
            if func_name == "len":
                if len(call.args) != 1:
                    raise RuntimeError("len() takes exactly 1 argument")
                arg = self.eval_expression(call.args[0])
                if arg.type_name == "string":
                    return Value("int", len(arg.value))
                elif arg.type_name == "array":
                    return Value("int", len(arg.value))
                elif arg.type_name == "map":
                    return Value("int", len(arg.value))
                else:
                    raise RuntimeError(f"len() not supported for type {arg.type_name}")
            
            elif func_name == "make":
                # make(type, size) or make(map[K]V)
                if len(call.args) < 1:
                    raise RuntimeError("make() requires at least 1 argument")
                # For now, handle make([]Type, size) and make(map[K]V)
                # This is simplified - just return empty array or map
                if len(call.args) >= 2:
                    size_val = self.eval_expression(call.args[1])
                    size = int(size_val.value)
                    return Value("array", [Value("nil", None) for _ in range(size)])
                else:
                    return Value("map", {})
            
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
            if func_name == "print":
                for arg in call.args:
                    val = self.eval_expression(arg)
                    self.print_output(self.to_string(val))
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
                        return Value("int", len(val.value))
                    else:
                        raise RuntimeError(f"Cannot get len of {val.type_name}")
            
            elif func_name == "cap":
                if call.args:
                    val = self.eval_expression(call.args[0])
                    if val.type_name in ["array"]:
                        return Value("int", len(val.value))
                    else:
                        raise RuntimeError(f"Cannot get cap of {val.type_name}")
            
            elif func_name == "append":
                if len(call.args) >= 2:
                    arr = self.eval_expression(call.args[0])
                    if arr.type_name == "array":
                        new_arr = arr.value.copy()
                        for arg in call.args[1:]:
                            new_arr.append(self.eval_expression(arg))
                        return Value("array", new_arr)
            
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
                    args = [self.eval_expression(arg) for arg in call.args]
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
        
        # Bind parameters
        for i, param in enumerate(func_decl.params):
            if i < len(args):
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
        
        if expr.type_name == "array":
            i = int(index.value)
            if 0 <= i < len(expr.value):
                return expr.value[i]
            else:
                raise RuntimeError(f"Array index out of bounds: {i}")
        elif expr.type_name == "map":
            key = self.to_string(index)
            if key in expr.value:
                return expr.value[key]
            else:
                return Value("nil", None)
        elif expr.type_name == "string":
            i = int(index.value)
            if 0 <= i < len(expr.value):
                return Value("rune", ord(expr.value[i]))
            else:
                raise RuntimeError(f"String index out of bounds: {i}")
        else:
            raise RuntimeError(f"Cannot index {expr.type_name}")
    
    def eval_field(self, field: FieldExpr) -> Value:
        """Evaluate field access"""
        obj = self.eval_expression(field.expr)
        
        if isinstance(obj.value, dict) and field.field in obj.value:
            return obj.value[field.field]
        
        raise RuntimeError(f"Field {field.field} not found")
    
    def eval_array_literal(self, arr: ArrayLiteral) -> Value:
        """Evaluate array literal"""
        elements = [self.eval_expression(elem) for elem in arr.elements]
        return Value("array", elements)
    
    def eval_map_literal(self, map_lit: MapLiteral) -> Value:
        """Evaluate map literal"""
        map_dict = {}
        for key, value in map_lit.pairs:
            k = self.to_string(self.eval_expression(key))
            v = self.eval_expression(value)
            map_dict[k] = v
        return Value("map", map_dict)
    
    def eval_struct_literal(self, struct_lit: StructLiteral) -> Value:
        """Evaluate struct literal"""
        struct_dict = {}
        for field_name, field_value in struct_lit.fields:
            struct_dict[field_name] = self.eval_expression(field_value)
        return Value(struct_lit.type_, struct_dict)
    
    def eval_type_cast(self, cast: TypeCast) -> Value:
        """Evaluate type cast"""
        expr = self.eval_expression(cast.expr)
        
        if isinstance(cast.type_, PrimitiveType):
            if cast.type_.name == "int":
                return Value("int", int(float(expr.value)))
            elif cast.type_.name == "float64":
                return Value("float", float(expr.value))
            elif cast.type_.name == "string":
                return Value("string", self.to_string(expr))
            elif cast.type_.name == "bool":
                return Value("bool", self.is_truthy(expr))
        
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
        
        start = 0
        end = len(expr.value)
        
        if slice_expr.start:
            start = int(self.eval_expression(slice_expr.start).value)
        if slice_expr.end:
            end = int(self.eval_expression(slice_expr.end).value)
        
        if expr.type_name in ["array", "string"]:
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
            return Value("array", [Value("nil", None) for _ in range(length)])
        
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
                value = Value("nil", None)
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
            for i, char in enumerate(iterable.value):
                if for_range.key and for_range.key != "_":
                    self.current_env.define(for_range.key, Value("int", i))
                if for_range.value and for_range.value != "_":
                    self.current_env.define(for_range.value, Value("rune", ord(char)))
                
                try:
                    self.execute_block(for_range.body)
                except BreakException:
                    break
                except ContinueException:
                    continue
    
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
        if assign.operator == ":=":
            # Short variable declaration
            # Special handling for multi-value assignment from single expression
            if len(assign.values) == 1 and len(assign.targets) > 1:
                value = self.eval_expression(assign.values[0])
                # If the value is a tuple (multiple returns), unpack it
                if value.type_name == "tuple" and isinstance(value.value, list):
                    for i, target in enumerate(assign.targets):
                        if isinstance(target, Identifier):
                            # Skip blank identifier
                            if target.name == "_":
                                continue
                            v = value.value[i] if i < len(value.value) else Value("nil", None)
                            self.current_env.define(target.name, v)
                else:
                    # Not a tuple, assign same value to first target, nil to rest
                    for i, target in enumerate(assign.targets):
                        if isinstance(target, Identifier):
                            # Skip blank identifier
                            if target.name == "_":
                                continue
                            v = value if i == 0 else Value("nil", None)
                            self.current_env.define(target.name, v)
            else:
                # Regular parallel assignment
                # Evaluate ALL right-hand side values BEFORE assigning
                values = []
                for i in range(len(assign.targets)):
                    if i < len(assign.values):
                        values.append(self.eval_expression(assign.values[i]))
                    else:
                        values.append(Value("nil", None))
                
                # Now assign the evaluated values
                for i, target in enumerate(assign.targets):
                    if isinstance(target, Identifier):
                        # Skip blank identifier
                        if target.name == "_":
                            continue
                        self.current_env.define(target.name, values[i])
        else:
            # Regular assignment
            # Special handling for multi-value assignment from single expression
            if len(assign.values) == 1 and len(assign.targets) > 1:
                value = self.eval_expression(assign.values[0])
                # If the value is a tuple (multiple returns), unpack it
                if value.type_name == "tuple" and isinstance(value.value, list):
                    for i, target in enumerate(assign.targets):
                        if isinstance(target, Identifier):
                            v = value.value[i] if i < len(value.value) else Value("nil", None)
                            self.current_env.set(target.name, v)
                        elif isinstance(target, IndexExpr):
                            v = value.value[i] if i < len(value.value) else Value("nil", None)
                            expr = self.eval_expression(target.expr)
                            index = self.eval_expression(target.index)
                            if expr.type_name == "array":
                                expr.value[int(index.value)] = v
                            elif expr.type_name == "map":
                                expr.value[self.to_string(index)] = v
                else:
                    # Not a tuple, assign same value to first target, nil to rest
                    for i, target in enumerate(assign.targets):
                        if isinstance(target, Identifier):
                            v = value if i == 0 else Value("nil", None)
                            self.current_env.set(target.name, v)
                        elif isinstance(target, IndexExpr):
                            v = value if i == 0 else Value("nil", None)
                            expr = self.eval_expression(target.expr)
                            index = self.eval_expression(target.index)
                            if expr.type_name == "array":
                                expr.value[int(index.value)] = v
                            elif expr.type_name == "map":
                                expr.value[self.to_string(index)] = v
            else:
                # Regular parallel assignment
                # CRITICAL: Evaluate ALL right-hand side values BEFORE assigning
                # This is necessary for swap operations like arr[j], arr[j+1] = arr[j+1], arr[j]
                values = []
                for i in range(len(assign.targets)):
                    if i < len(assign.values):
                        values.append(self.eval_expression(assign.values[i]))
                    else:
                        values.append(Value("nil", None))
                
                # Now assign the evaluated values
                for i, target in enumerate(assign.targets):
                    value = values[i]
                    if isinstance(target, Identifier):
                        self.current_env.set(target.name, value)
                    elif isinstance(target, IndexExpr):
                        # Handle index assignment
                        expr = self.eval_expression(target.expr)
                        index = self.eval_expression(target.index)
                        if expr.type_name == "array":
                            expr.value[int(index.value)] = value
                        elif expr.type_name == "map":
                            expr.value[self.to_string(index)] = value
    
    def execute_inc_dec(self, stmt: IncDecStmt):
        """Execute increment/decrement statement"""
        if isinstance(stmt.expr, Identifier):
            val = self.current_env.get(stmt.expr.name)
            if stmt.operator == "++":
                self.current_env.set(stmt.expr.name, Value(val.type_name, val.value + 1))
            elif stmt.operator == "--":
                self.current_env.set(stmt.expr.name, Value(val.type_name, val.value - 1))