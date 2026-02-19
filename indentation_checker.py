"""
Validador de indentación para código Go-like
Detecta errores de indentación inconsistente, mezcla de tabs/espacios, etc.
"""

import re
from typing import List, Tuple, Optional


class IndentationError(Exception):
    """Excepción para errores de indentación"""
    def __init__(self, line_num: int, message: str):
        self.line_num = line_num
        self.message = message
        super().__init__(f"Línea {line_num}: {message}")


class IndentationChecker:
    """Valida la indentación del código fuente"""
    
    def __init__(self, code: str):
        self.code = code
        self.lines = code.split('\n')
        self.errors: List[Tuple[int, str]] = []
        self.use_tabs = None  # None, True (tabs), o False (spaces)
        self.indent_size = 4  # Tamaño de indentación si se usan espacios
        
    def check(self) -> List[Tuple[int, str]]:
        """
        Valida la indentación del código completo
        Retorna lista de errores: [(line_num, message), ...]
        """
        self.errors = []
        expected_indent = 0
        last_line_opened_block = False
        
        for i, line in enumerate(self.lines, start=1):
            # Ignorar líneas vacías
            if not line.strip():
                continue
            
            # Ignorar comentarios completos
            if line.strip().startswith('//'):
                continue
            
            # Detectar tipo de indentación (tabs vs spaces)
            self._detect_indent_type(line, i)
            
            # Obtener nivel de indentación actual
            current_indent = self._get_indent_level(line)
            
            # Verificar mezcla de tabs y espacios
            if self._has_mixed_indentation(line):
                self.errors.append((i, "Mezcla de tabulaciones y espacios en la indentación"))
            
            # Verificar que cierre de bloque } tenga la indentación correcta
            stripped = line.strip()
            if stripped.startswith('}'):
                # El } debe estar al nivel del bloque que abrió
                if current_indent != expected_indent - 1:
                    self.errors.append((
                        i, 
                        f"Indentación incorrecta: esperado {expected_indent - 1} nivel(es), encontrado {current_indent}"
                    ))
                expected_indent -= 1
                # Handle "} else {" and "} else if ... {" — the closing } and opening { on same line
                if stripped.endswith('{'):
                    expected_indent += 1
                    last_line_opened_block = True
                else:
                    last_line_opened_block = False
                continue
            
            # Si la línea anterior abrió un bloque {, este debe estar más indentado
            if last_line_opened_block:
                if current_indent != expected_indent:
                    self.errors.append((
                        i,
                        f"Indentación incorrecta después de '{{': esperado {expected_indent} nivel(es), encontrado {current_indent}"
                    ))
            else:
                # Verificar que la indentación sea la esperada
                if current_indent != expected_indent:
                    self.errors.append((
                        i,
                        f"Indentación inconsistente: esperado {expected_indent} nivel(es), encontrado {current_indent}"
                    ))
            
            # Detectar si esta línea abre un bloque
            if stripped.endswith('{'):
                expected_indent += 1
                last_line_opened_block = True
            else:
                last_line_opened_block = False
        
        return self.errors
    
    def _detect_indent_type(self, line: str, line_num: int):
        """Detecta si se usan tabs o espacios y verifica consistencia"""
        if not line or line[0] not in (' ', '\t'):
            return
        
        # Detectar primer caracter de indentación
        first_char = line[0]
        
        if self.use_tabs is None:
            # Primera línea con indentación - establecer estándar
            self.use_tabs = (first_char == '\t')
        else:
            # Verificar consistencia con el estándar establecido
            if self.use_tabs and first_char == ' ':
                self.errors.append((
                    line_num,
                    "Se detectaron espacios cuando el archivo usa tabulaciones"
                ))
            elif not self.use_tabs and first_char == '\t':
                self.errors.append((
                    line_num,
                    "Se detectaron tabulaciones cuando el archivo usa espacios"
                ))
    
    def _has_mixed_indentation(self, line: str) -> bool:
        """Verifica si una línea mezcla tabs y espacios en su indentación"""
        if not line:
            return False
        
        # Contar caracteres de indentación al inicio
        indent_chars = []
        for char in line:
            if char in (' ', '\t'):
                indent_chars.append(char)
            else:
                break
        
        # Si hay tanto tabs como espacios, es mezcla
        has_tabs = '\t' in indent_chars
        has_spaces = ' ' in indent_chars
        
        return has_tabs and has_spaces
    
    def _get_indent_level(self, line: str) -> int:
        """
        Calcula el nivel de indentación de una línea
        Retorna: número de niveles de indentación
        """
        if not line:
            return 0
        
        tabs = 0
        spaces = 0
        
        for char in line:
            if char == '\t':
                tabs += 1
            elif char == ' ':
                spaces += 1
            else:
                break
        
        # Si usa tabs, retornar número de tabs
        if tabs > 0:
            return tabs
        
        # Si usa espacios, dividir por indent_size
        if spaces > 0:
            return spaces // self.indent_size
        
        return 0
    
    def validate_and_raise(self):
        """
        Valida el código y lanza excepción si hay errores
        """
        errors = self.check()
        if errors:
            # Reportar el primer error encontrado
            line_num, message = errors[0]
            raise IndentationError(line_num, message)
    
    def get_formatted_errors(self) -> str:
        """Retorna los errores formateados como string"""
        if not self.errors:
            return ""
        
        result = "⚠️ ERRORES DE INDENTACIÓN DETECTADOS:\n\n"
        for line_num, message in self.errors:
            result += f"  Línea {line_num}: {message}\n"
        
        return result


def check_indentation(code: str) -> Optional[str]:
    """
    Función helper para validar indentación
    Retorna None si no hay errores, o un mensaje de error si los hay
    """
    checker = IndentationChecker(code)
    errors = checker.check()
    
    if errors:
        return checker.get_formatted_errors()
    
    return None


def validate_indentation(code: str):
    """
    Valida indentación y lanza excepción si hay errores
    """
    checker = IndentationChecker(code)
    checker.validate_and_raise()
