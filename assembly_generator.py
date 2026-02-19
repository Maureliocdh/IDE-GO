"""
Generador de Código Ensamblador (Código Intermedio)
Genera código de tres direcciones y ensamblador x86-64 simplificado
"""

from typing import Dict, List, Optional, Tuple
from ast_nodes import *
from dataclasses import dataclass


@dataclass
class TACInstruction:
    """Instrucción de Código de Tres Direcciones (TAC)"""
    op: str           # Operación
    arg1: str = ""    # Primer argumento
    arg2: str = ""    # Segundo argumento
    result: str = ""  # Resultado
    label: str = ""   # Etiqueta (opcional)
    comment: str = "" # Comentario (opcional)
    
    def __str__(self):
        if self.label:
            return f"{self.label}:"
        if self.op == "PARAM":
            return f"    PARAM {self.arg1}"
        if self.op == "CALL":
            return f"    {self.result} = CALL {self.arg1}, {self.arg2}"
        if self.op == "RETURN":
            return f"    RETURN {self.arg1}" if self.arg1 else "    RETURN"
        if self.op == "GOTO":
            return f"    GOTO {self.arg1}"
        if self.op == "IF_FALSE":
            return f"    IF_FALSE {self.arg1} GOTO {self.arg2}"
        if self.op == "IF_TRUE":
            return f"    IF_TRUE {self.arg1} GOTO {self.arg2}"
        if self.op == "ASSIGN":
            return f"    {self.result} = {self.arg1}"
        if self.op == "PRINT":
            return f"    PRINT {self.arg1}"
        if self.op == "FUNC_BEGIN":
            return f"\nFUNC_BEGIN {self.arg1}:"
        if self.op == "FUNC_END":
            return f"FUNC_END {self.arg1}"
        if self.op == "COMMENT":
            return f"    ; {self.comment}"
        if self.arg2:
            return f"    {self.result} = {self.arg1} {self.op} {self.arg2}"
        return f"    {self.op} {self.arg1} {self.arg2} {self.result}".strip()


class AssemblyGenerator:
    """Genera código intermedio (TAC) y ensamblador x86-64"""
    
    def __init__(self, program: Program):
        self.program = program
        self.tac_instructions: List[TACInstruction] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.string_literals: Dict[str, str] = {}
        self.string_counter = 0
        self.current_function = ""
        self.variables: Dict[str, str] = {}  # var_name -> register/location
        
    def new_temp(self) -> str:
        """Genera un nuevo nombre de variable temporal"""
        self.temp_counter += 1
        return f"t{self.temp_counter}"
    
    def new_label(self, prefix: str = "L") -> str:
        """Genera una nueva etiqueta"""
        self.label_counter += 1
        return f"{prefix}{self.label_counter}"
    
    def new_string_label(self) -> str:
        """Genera una nueva etiqueta para string"""
        self.string_counter += 1
        return f"str{self.string_counter}"
    
    def emit(self, op: str, arg1: str = "", arg2: str = "", result: str = "", 
             label: str = "", comment: str = ""):
        """Emite una instrucción TAC"""
        instr = TACInstruction(op, arg1, arg2, result, label, comment)
        self.tac_instructions.append(instr)
    
    def emit_label(self, label: str):
        """Emite una etiqueta"""
        self.tac_instructions.append(TACInstruction("", label=label))
    
    def generate(self) -> Tuple[str, str]:
        """Genera código intermedio y ensamblador"""
        # Generar TAC
        self.generate_tac()
        
        # Convertir TAC a string
        tac_code = self.tac_to_string()
        
        # Generar ensamblador x86-64
        asm_code = self.generate_x86_64()
        
        return tac_code, asm_code
    
    def generate_tac(self):
        """Genera código de tres direcciones desde el AST"""
        self.emit("COMMENT", comment="=== Código Intermedio (TAC) ===")
        self.emit("COMMENT", comment="Generado desde código Go-like")
        self.emit("COMMENT", comment="")
        
        # Procesar declaraciones globales
        for decl in self.program.declarations:
            if isinstance(decl, VarDecl):
                self.gen_var_decl(decl)
            elif isinstance(decl, ConstDecl):
                self.gen_const_decl(decl)
        
        # Procesar funciones
        for decl in self.program.declarations:
            if isinstance(decl, FuncDecl):
                self.gen_func_decl(decl)
    
    def gen_var_decl(self, decl: VarDecl):
        """Genera TAC para declaración de variable"""
        if decl.value:
            result = self.gen_expression(decl.value)
            self.emit("ASSIGN", result, result=decl.name)
        else:
            self.emit("ASSIGN", "0", result=decl.name)
    
    def gen_const_decl(self, decl: ConstDecl):
        """Genera TAC para declaración de constante"""
        result = self.gen_expression(decl.value)
        self.emit("ASSIGN", result, result=decl.name)
    
    def gen_func_decl(self, decl: FuncDecl):
        """Genera TAC para declaración de función"""
        self.current_function = decl.name
        self.emit("FUNC_BEGIN", decl.name)
        
        # Parámetros
        for param in decl.params:
            self.emit("COMMENT", comment=f"param {param.name}")
        
        # Cuerpo
        if decl.body:
            self.gen_block(decl.body)
        
        self.emit("FUNC_END", decl.name)
        self.current_function = ""
    
    def gen_block(self, block: Block):
        """Genera TAC para un bloque"""
        for stmt in block.statements:
            self.gen_statement(stmt)
    
    def gen_statement(self, stmt):
        """Genera TAC para una sentencia"""
        if isinstance(stmt, VarDecl):
            self.gen_var_decl(stmt)
        elif isinstance(stmt, AssignStmt):
            self.gen_assignment(stmt)
        elif isinstance(stmt, IfStmt):
            self.gen_if_stmt(stmt)
        elif isinstance(stmt, ForStmt):
            self.gen_for_stmt(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.gen_return_stmt(stmt)
        elif isinstance(stmt, ExpressionStmt):
            self.gen_expression(stmt.expr)
        elif isinstance(stmt, IncDecStmt):
            self.gen_inc_dec(stmt)
        elif isinstance(stmt, Block):
            self.gen_block(stmt)
        elif isinstance(stmt, SwitchStmt):
            self.gen_switch_stmt(stmt)
    
    def gen_assignment(self, stmt: AssignStmt):
        """Genera TAC para asignación (incluyendo :=)"""
        # Procesar múltiples asignaciones
        for i, target in enumerate(stmt.targets):
            if i < len(stmt.values):
                value = self.gen_expression(stmt.values[i])
                
                if isinstance(target, Identifier):
                    target_name = target.name
                elif isinstance(target, IndexExpr):
                    arr = self.gen_expression(target.expr)
                    idx = self.gen_expression(target.index)
                    target_name = f"{arr}[{idx}]"
                else:
                    target_name = self.new_temp()
                
                self.emit("ASSIGN", value, result=target_name)
    
    def gen_if_stmt(self, stmt: IfStmt):
        """Genera TAC para if"""
        cond = self.gen_expression(stmt.condition)
        else_label = self.new_label("else")
        end_label = self.new_label("endif")
        
        self.emit("IF_FALSE", cond, else_label)
        
        # Then branch
        self.gen_block(stmt.then_block)
        self.emit("GOTO", end_label)
        
        # Else branch
        self.emit_label(else_label)
        if stmt.else_block:
            if isinstance(stmt.else_block, Block):
                self.gen_block(stmt.else_block)
            else:
                self.gen_statement(stmt.else_block)
        
        self.emit_label(end_label)
    
    def gen_for_stmt(self, stmt: ForStmt):
        """Genera TAC para for"""
        start_label = self.new_label("for_start")
        end_label = self.new_label("for_end")
        
        # Init
        if stmt.init:
            self.gen_statement(stmt.init)
        
        self.emit_label(start_label)
        
        # Condition
        if stmt.condition:
            cond = self.gen_expression(stmt.condition)
            self.emit("IF_FALSE", cond, end_label)
        
        # Body
        if stmt.body:
            self.gen_block(stmt.body)
        
        # Post
        if stmt.post:
            self.gen_statement(stmt.post)
        
        self.emit("GOTO", start_label)
        self.emit_label(end_label)
    
    def gen_return_stmt(self, stmt: ReturnStmt):
        """Genera TAC para return"""
        if stmt.values:
            for val in stmt.values:
                result = self.gen_expression(val)
                self.emit("RETURN", result)
        else:
            self.emit("RETURN")
    
    def gen_inc_dec(self, stmt: IncDecStmt):
        """Genera TAC para incremento/decremento"""
        var = self.gen_expression(stmt.expr)
        op = "+" if stmt.op == "++" else "-"
        temp = self.new_temp()
        self.emit(op, var, "1", temp)
        self.emit("ASSIGN", temp, result=var)
    
    def gen_switch_stmt(self, stmt: SwitchStmt):
        """Genera TAC para switch"""
        cond = self.gen_expression(stmt.expr) if stmt.expr else None
        end_label = self.new_label("switch_end")
        
        for case in stmt.cases:
            if case.values:  # case
                case_label = self.new_label("case")
                next_case = self.new_label("next_case")
                
                for val in case.values:
                    case_val = self.gen_expression(val)
                    temp = self.new_temp()
                    self.emit("==", cond, case_val, temp)
                    self.emit("IF_TRUE", temp, case_label)
                
                self.emit("GOTO", next_case)
                self.emit_label(case_label)
                
                for s in case.statements:
                    self.gen_statement(s)
                
                self.emit("GOTO", end_label)
                self.emit_label(next_case)
            else:  # default
                for s in case.statements:
                    self.gen_statement(s)
        
        self.emit_label(end_label)
    
    def gen_expression(self, expr) -> str:
        """Genera TAC para una expresión y retorna el resultado"""
        if isinstance(expr, Literal):
            if hasattr(expr.type_, 'name'):
                type_name = expr.type_.name.lower()
            else:
                type_name = str(expr.type_).lower()
            
            if type_name == "string":
                label = self.new_string_label()
                self.string_literals[label] = expr.value
                return f'"{expr.value}"'
            return str(expr.value)
        
        elif isinstance(expr, Identifier):
            return expr.name
        
        elif isinstance(expr, BinaryOp):
            left = self.gen_expression(expr.left)
            right = self.gen_expression(expr.right)
            temp = self.new_temp()
            self.emit(expr.op, left, right, temp)
            return temp
        
        elif isinstance(expr, UnaryOp):
            operand = self.gen_expression(expr.operand)
            temp = self.new_temp()
            self.emit(f"UNARY_{expr.op}", operand, result=temp)
            return temp
        
        elif isinstance(expr, CallExpr):
            return self.gen_call_expr(expr)
        
        elif isinstance(expr, IndexExpr):
            arr = self.gen_expression(expr.expr)
            idx = self.gen_expression(expr.index)
            temp = self.new_temp()
            self.emit("INDEX", arr, idx, temp)
            return temp
        
        elif isinstance(expr, FieldExpr):
            obj = self.gen_expression(expr.expr)
            return f"{obj}.{expr.field}"
        
        elif isinstance(expr, ArrayLiteral):
            temp = self.new_temp()
            self.emit("ARRAY_NEW", str(len(expr.elements)), result=temp)
            for i, elem in enumerate(expr.elements):
                val = self.gen_expression(elem)
                self.emit("ARRAY_SET", temp, str(i), val)
            return temp
        
        elif isinstance(expr, LambdaExpr):
            label = self.new_label("lambda")
            return f"&{label}"
        
        return str(expr)
    
    def gen_call_expr(self, call: CallExpr) -> str:
        """Genera TAC para llamada a función"""
        # Evaluar argumentos primero
        args = []
        for arg in call.args:
            val = self.gen_expression(arg)
            args.append(val)
        
        # Emitir PARAMs
        for arg in args:
            self.emit("PARAM", arg)
        
        # Determinar nombre de función
        if isinstance(call.func, Identifier):
            func_name = call.func.name
        elif isinstance(call.func, FieldExpr):
            if isinstance(call.func.expr, Identifier):
                pkg = call.func.expr.name
                method = call.func.field
                func_name = f"{pkg}.{method}"
                
                # Caso especial para fmt.Println, fmt.Print, etc.
                if pkg == "fmt" and method in ["Println", "Print", "Printf"]:
                    for arg in args:
                        self.emit("PRINT", arg)
                    return ""
            else:
                func_name = f"{call.func.expr}.{call.func.field}"
        else:
            func_name = str(call.func)
        
        temp = self.new_temp()
        self.emit("CALL", func_name, str(len(args)), temp)
        return temp
    
    def tac_to_string(self) -> str:
        """Convierte las instrucciones TAC a string"""
        lines = []
        lines.append("; ========================================")
        lines.append("; CÓDIGO INTERMEDIO DE TRES DIRECCIONES")
        lines.append("; ========================================")
        lines.append("")
        
        # Sección de datos (strings)
        if self.string_literals:
            lines.append(".data:")
            for label, value in self.string_literals.items():
                lines.append(f"    {label}: \"{value}\"")
            lines.append("")
        
        lines.append(".code:")
        for instr in self.tac_instructions:
            lines.append(str(instr))
        
        return "\n".join(lines)
    
    def generate_x86_64(self) -> str:
        """Genera código ensamblador x86-64"""
        asm = []
        asm.append("; ========================================")
        asm.append("; CÓDIGO ENSAMBLADOR x86-64 (Simplificado)")
        asm.append("; Generado desde código Go-like")
        asm.append("; ========================================")
        asm.append("")
        
        # Sección de datos
        asm.append("section .data")
        asm.append("    fmt_int:     db \"%d\", 10, 0")
        asm.append("    fmt_str:     db \"%s\", 10, 0")
        asm.append("    fmt_newline: db 10, 0")
        
        for label, value in self.string_literals.items():
            escaped = value.replace('"', '\\"')
            asm.append(f"    {label}: db \"{escaped}\", 0")
        
        asm.append("")
        
        # Sección BSS (variables sin inicializar)
        asm.append("section .bss")
        asm.append("    ; Variables temporales")
        for i in range(1, self.temp_counter + 1):
            asm.append(f"    t{i}: resq 1")
        asm.append("")
        
        # Sección de código
        asm.append("section .text")
        asm.append("    global main")
        asm.append("    extern printf")
        asm.append("    extern scanf")
        asm.append("    extern malloc")
        asm.append("    extern free")
        asm.append("")
        
        # Convertir TAC a ensamblador
        current_func = ""
        for instr in self.tac_instructions:
            if instr.op == "FUNC_BEGIN":
                current_func = instr.arg1
                asm.append(f"{instr.arg1}:")
                asm.append("    push rbp")
                asm.append("    mov rbp, rsp")
                asm.append("    sub rsp, 64        ; Reservar espacio para locales")
                asm.append("")
            
            elif instr.op == "FUNC_END":
                asm.append("")
                asm.append(f".{instr.arg1}_end:")
                asm.append("    mov rsp, rbp")
                asm.append("    pop rbp")
                asm.append("    ret")
                asm.append("")
            
            elif instr.op == "ASSIGN":
                asm.append(f"    ; {instr.result} = {instr.arg1}")
                if instr.arg1.isdigit() or (instr.arg1.startswith('-') and instr.arg1[1:].isdigit()):
                    asm.append(f"    mov rax, {instr.arg1}")
                else:
                    asm.append(f"    mov rax, [{instr.arg1}]")
                asm.append(f"    mov [{instr.result}], rax")
            
            elif instr.op == "RETURN":
                if instr.arg1:
                    if instr.arg1.isdigit():
                        asm.append(f"    mov rax, {instr.arg1}")
                    else:
                        asm.append(f"    mov rax, [{instr.arg1}]")
                asm.append(f"    jmp .{current_func}_end")
            
            elif instr.op in ["+", "-", "*", "/"]:
                asm.append(f"    ; {instr.result} = {instr.arg1} {instr.op} {instr.arg2}")
                
                # Cargar primer operando
                if instr.arg1.isdigit():
                    asm.append(f"    mov rax, {instr.arg1}")
                else:
                    asm.append(f"    mov rax, [{instr.arg1}]")
                
                # Cargar segundo operando
                if instr.arg2.isdigit():
                    asm.append(f"    mov rbx, {instr.arg2}")
                else:
                    asm.append(f"    mov rbx, [{instr.arg2}]")
                
                # Operación
                if instr.op == "+":
                    asm.append("    add rax, rbx")
                elif instr.op == "-":
                    asm.append("    sub rax, rbx")
                elif instr.op == "*":
                    asm.append("    imul rax, rbx")
                elif instr.op == "/":
                    asm.append("    xor rdx, rdx")
                    asm.append("    idiv rbx")
                
                asm.append(f"    mov [{instr.result}], rax")
            
            elif instr.op in ["==", "!=", "<", ">", "<=", ">="]:
                asm.append(f"    ; {instr.result} = {instr.arg1} {instr.op} {instr.arg2}")
                
                if instr.arg1.isdigit():
                    asm.append(f"    mov rax, {instr.arg1}")
                else:
                    asm.append(f"    mov rax, [{instr.arg1}]")
                
                if instr.arg2.isdigit():
                    asm.append(f"    cmp rax, {instr.arg2}")
                else:
                    asm.append(f"    cmp rax, [{instr.arg2}]")
                
                cmp_map = {
                    "==": "sete", "!=": "setne",
                    "<": "setl", ">": "setg",
                    "<=": "setle", ">=": "setge"
                }
                asm.append(f"    {cmp_map[instr.op]} al")
                asm.append("    movzx rax, al")
                asm.append(f"    mov [{instr.result}], rax")
            
            elif instr.op == "GOTO":
                asm.append(f"    jmp {instr.arg1}")
            
            elif instr.op == "IF_FALSE":
                asm.append(f"    ; if not {instr.arg1} goto {instr.arg2}")
                if instr.arg1.isdigit():
                    asm.append(f"    mov rax, {instr.arg1}")
                else:
                    asm.append(f"    mov rax, [{instr.arg1}]")
                asm.append("    test rax, rax")
                asm.append(f"    jz {instr.arg2}")
            
            elif instr.op == "IF_TRUE":
                asm.append(f"    ; if {instr.arg1} goto {instr.arg2}")
                if instr.arg1.isdigit():
                    asm.append(f"    mov rax, {instr.arg1}")
                else:
                    asm.append(f"    mov rax, [{instr.arg1}]")
                asm.append("    test rax, rax")
                asm.append(f"    jnz {instr.arg2}")
            
            elif instr.op == "CALL":
                asm.append(f"    ; {instr.result} = call {instr.arg1}")
                asm.append(f"    call {instr.arg1}")
                if instr.result:
                    asm.append(f"    mov [{instr.result}], rax")
            
            elif instr.op == "PARAM":
                asm.append(f"    ; push param {instr.arg1}")
                if instr.arg1.isdigit():
                    asm.append(f"    push {instr.arg1}")
                elif instr.arg1.startswith('"'):
                    # Es un string literal
                    pass
                else:
                    asm.append(f"    push qword [{instr.arg1}]")
            
            elif instr.op == "PRINT":
                asm.append(f"    ; print {instr.arg1}")
                if instr.arg1.startswith('"'):
                    # Imprimir string literal
                    asm.append("    lea rdi, [fmt_str]")
                    # Encontrar la etiqueta del string
                    for label, val in self.string_literals.items():
                        if f'"{val}"' == instr.arg1:
                            asm.append(f"    lea rsi, [{label}]")
                            break
                    else:
                        # String en línea
                        asm.append(f"    lea rsi, [{instr.arg1}]")
                elif instr.arg1.isdigit():
                    asm.append("    lea rdi, [fmt_int]")
                    asm.append(f"    mov rsi, {instr.arg1}")
                else:
                    asm.append("    lea rdi, [fmt_int]")
                    asm.append(f"    mov rsi, [{instr.arg1}]")
                asm.append("    xor rax, rax")
                asm.append("    call printf")
            
            elif instr.label:
                asm.append(f"{instr.label}:")
            
            elif instr.op == "COMMENT":
                if instr.comment:
                    asm.append(f"    ; {instr.comment}")
        
        return "\n".join(asm)


def generate_assembly(program: Program) -> Tuple[str, str]:
    """Función helper para generar código ensamblador"""
    generator = AssemblyGenerator(program)
    return generator.generate()
