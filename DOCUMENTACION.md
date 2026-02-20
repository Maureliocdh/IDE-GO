# Documentación del Proyecto — IDE Go en Python

> **Versión:** 1.0 — Febrero 2026  
> **Lenguaje:** Python 3.10+  
> **Interfaz gráfica:** Tkinter  
> **Propósito:** IDE completo para un subconjunto de Go, con intérprete, compilador a C y generador de ensamblador, todo implementado desde cero en Python.

---

## Tabla de Contenidos

1. [Descripción General](#1-descripción-general)
2. [Estructura de Archivos](#2-estructura-de-archivos)
3. [Pipeline de Ejecución](#3-pipeline-de-ejecución)
4. [Módulo: `lexer.py`](#4-módulo-lexerpy)
5. [Módulo: `ast_nodes.py`](#5-módulo-ast_nodespy)
6. [Módulo: `parser.py`](#6-módulo-parserpy)
7. [Módulo: `interpreter.py`](#7-módulo-interpreterpy)
8. [Módulo: `compiler.py`](#8-módulo-compilerpy)
9. [Módulo: `assembly_generator.py`](#9-módulo-assembly_generatorpy)
10. [Módulo: `indentation_checker.py`](#10-módulo-indentation_checkerpy)
11. [Módulo: `main.py` — La IDE](#11-módulo-mainpy--la-ide)
12. [Características del Lenguaje Soportadas](#12-características-del-lenguaje-soportadas)
13. [Atajos de Teclado](#13-atajos-de-teclado)
14. [Ejemplos de Uso](#14-ejemplos-de-uso)
15. [Notas Técnicas y Limitaciones](#15-notas-técnicas-y-limitaciones)

---

## 1. Descripción General

Este proyecto implementa un **entorno de desarrollo integrado (IDE)** para el lenguaje **Go** (un subconjunto representativo). A diferencia de un IDE que simplemente invoca un compilador externo, este proyecto implementa **toda la cadena de herramientas desde cero** en Python puro:

```
Código fuente Go
      │
      ▼
  [Lexer]        ← lexer.py         Tokenización
      │
      ▼
  [Parser]       ← parser.py        Análisis sintáctico → AST
      │
      ▼
  [AST Nodes]    ← ast_nodes.py     Representación del árbol
      │
    ┌─┴────────────────────┐
    ▼                      ▼
[Intérprete]         [Compilador]
interpreter.py        compiler.py  →  Código C
                           │
                      [Generador ASM]
                  assembly_generator.py  →  TAC + x86-64
```

La interfaz gráfica (`main.py`) integra todos estos componentes en una ventana Tkinter con pestañas, resaltado de sintaxis, panel de errores, explorador de archivos y terminal.

---

## 2. Estructura de Archivos

```
gi/
├── main.py                  # IDE principal (GUI Tkinter)
├── lexer.py                 # Analizador léxico (tokenizador)
├── parser.py                # Parser recursivo descendente
├── ast_nodes.py             # Definición de nodos AST (dataclasses)
├── interpreter.py           # Intérprete de árbol (tree-walker)
├── compiler.py              # Transpilador Go → C
├── assembly_generator.py    # Generador TAC + x86-64 simplificado
├── indentation_checker.py   # Validador de indentación
├── DOCUMENTACION.md         # Este archivo
│
├── notes.txt                # Programas Go de referencia con salidas esperadas
├── TODO.txt                 # Lista de tareas pendientes
│
└── tests/
    ├── bubbleSort_test.py
    ├── comprehensive_test.py
    ├── final_test.py
    ├── pipeline_test.py
    ├── test_advanced.py
    ├── test_features.go
    ├── test_quick.py
    ├── test_simple.py
    └── ...
```

---

## 3. Pipeline de Ejecución

Cuando el usuario presiona **F5 (Ejecutar)**, ocurre lo siguiente:

```
1. Se obtiene el texto del editor activo
2. Lexer(código).tokenize()        → Lista[Token]
3. Parser(tokens).parse()          → Program (AST raíz)
4. Interpreter(ast).run()          → Salida a la consola
```

Cuando el usuario presiona **F6 (Compilar a C)**:

```
1–3. Igual que arriba
4. Compiler(ast).compile()         → Cadena de código C
5. Se muestra en la pestaña "⚙️ Código C Generado"
```

Cuando el usuario presiona **F7 (Generar ASM)**:

```
1–3. Igual que arriba
4. AssemblyGenerator(ast).generate()
     → TAC (código de tres direcciones) + x86-64 simplificado
5. Se muestran en las pestañas correspondientes
```

---

## 4. Módulo: `lexer.py`

### Responsabilidad
Convierte el código fuente Go (texto plano) en una secuencia de **tokens**.

### Clase `TokenType` (Enum)
Define todos los tipos de token reconocidos:

| Categoría | Ejemplos |
|-----------|---------|
| Literales | `INT`, `FLOAT`, `STRING`, `RUNE`, `TRUE`, `FALSE`, `NIL` |
| Palabras clave | `PACKAGE`, `IMPORT`, `FUNC`, `IF`, `ELSE`, `FOR`, `RETURN`, `STRUCT`, `INTERFACE`, `TYPE`, `VAR`, `CONST`, `MAP`, `SWITCH`, `CASE`, `DEFER`, `GO`, `RANGE` |
| Operadores | `PLUS`, `MINUS`, `STAR`, `SLASH`, `EQ`, `NEQ`, `LT`, `GT`, `AND`, `OR`, `NOT`, `WALRUS` (`:=`), `ASSIGN` (`=`) |
| Delimitadores | `LPAREN`, `RPAREN`, `LBRACE`, `RBRACE`, `LBRACKET`, `RBRACKET`, `COMMA`, `DOT`, `COLON`, `SEMICOLON` |
| Especiales | `IDENTIFIER`, `NEWLINE`, `EOF`, `ELLIPSIS` (`...`) |

### Clase `Token`
```python
@dataclass
class Token:
    type: TokenType   # Tipo del token
    value: str        # Texto original
    line: int         # Número de línea (1-based)
    column: int       # Columna (1-based)
```

### Clase `Lexer`

**Constructor:** `Lexer(source: str)`

**Método principal:** `tokenize() → List[Token]`

#### Métodos internos relevantes

| Método | Descripción |
|--------|-------------|
| `read_string(quote_char)` | Lee strings y rune literals. Decodifica secuencias de escape: `\n`, `\t`, `\r`, `\\`, `\"`, `\'`, `\a`, `\b`, `\f`, `\v`, `\0`, `\uXXXX`, `\UXXXXXXXX` |
| `read_number()` | Lee enteros decimales, flotantes y hexadecimales (`0x...`) |
| `read_identifier()` | Lee identificadores y palabras clave |
| `skip_comment()` | Salta comentarios `//` y `/* */` |
| `skip_whitespace()` | Salta espacios/tabs (no newlines) |

#### Reglas especiales de tokenización
- Los **saltos de línea** (`\n`) se emiten como `NEWLINE` y el parser los usa como terminadores de sentencia.
- Los **puntos y coma** (`;`) se emiten como `SEMICOLON`.
- El operador `:=` (declaración corta) se tokeniza como `WALRUS`.
- Los literales hexadecimales (`0xFF`) se tokenizan como `INT`.

---

## 5. Módulo: `ast_nodes.py`

### Responsabilidad
Define todas las clases de nodos del **Árbol Sintáctico Abstracto (AST)** usando `dataclasses` de Python.

### Jerarquía de clases base

```
ASTNode
├── Type              # Nodos de tipo
│   ├── PrimitiveType     # int, string, bool, float64...
│   ├── PointerType       # *T
│   ├── ArrayType         # [N]T
│   ├── SliceType         # []T
│   ├── MapType           # map[K]V
│   ├── FuncType          # func(...)...
│   ├── ChannelType       # chan T
│   ├── NamedType         # MiTipo
│   └── InterfaceType     # interface{...}
│
├── Statement         # Nodos de sentencia
│   ├── AssignStmt        # x = 5  /  x, y := 1, 2
│   ├── IfStmt            # if cond { } else { }
│   ├── ForStmt           # for init; cond; post { }
│   ├── ForRangeStmt      # for k, v := range iter { }
│   ├── SwitchStmt        # switch expr { case ... }
│   ├── ReturnStmt        # return x, err
│   ├── DeferStmt         # defer f()
│   ├── BreakStmt         # break
│   ├── ContinueStmt      # continue
│   ├── FallthroughStmt   # fallthrough
│   ├── IncDecStmt        # x++  /  x--
│   └── ExpressionStmt    # expr usado como sentencia
│
└── Expression        # Nodos de expresión
    ├── Literal           # 42, "hola", true
    ├── Identifier        # nombre de variable/función
    ├── BinaryOp          # a + b, a && b
    ├── UnaryOp           # -x, !b, *ptr, &var
    ├── CallExpr          # f(arg1, arg2)
    ├── IndexExpr         # arr[i]
    ├── SliceExpr         # arr[start:end]
    ├── FieldExpr         # struct.campo / pkg.Nombre
    ├── StructLiteral     # MyStruct{campo: val}
    ├── ArrayLiteral      # []int{1, 2, 3}
    ├── MapLiteral        # map[string]int{"a": 1}
    ├── TypeCast          # int(x)
    ├── MakeLiteral       # make([]int, 10)
    ├── NewLiteral        # new(T)
    ├── LambdaExpr        # func(x int) int { return x }
    └── TypeCast/IsExpr   # x.(T) — type assertion
```

### Nodos de declaración de nivel superior

| Nodo | Representa |
|------|-----------|
| `Program` | Raíz del AST: `package` + imports + declaraciones |
| `PackageDecl` | `package main` |
| `ImportDecl` | `import "fmt"` |
| `FuncDecl` | `func nombre(params) returns { body }` — incluye receptor para métodos |
| `StructDecl` | `type X struct { fields }` |
| `InterfaceDecl` | `type X interface { methods }` |
| `VarDecl` | `var x int = 5` |
| `ConstDecl` | `const Pi = 3.14` |
| `TypeDecl` | `type MyInt int` |
| `Parameter` | Parámetro de función con nombre, tipo y flag `variadic` |
| `StructField` | Campo de struct: nombre, tipo, tag, flag `embedded` |

---

## 6. Módulo: `parser.py`

### Responsabilidad
Implementa un **parser recursivo descendente** que transforma la lista de tokens en un AST de tipo `Program`.

### Clase `Parser`

**Constructor:** `Parser(tokens: List[Token])`

**Método principal:** `parse() → Program`

### Métodos de utilidad

| Método | Descripción |
|--------|-------------|
| `current_token()` | Token en la posición actual |
| `peek_token(offset)` | Token a `offset` posiciones adelante |
| `advance()` | Avanza al siguiente token |
| `expect(type)` | Consume el token esperado, lanza `SyntaxError` si no coincide |
| `match(*types)` | Verdadero si el token actual es de alguno de los tipos dados |
| `consume(type)` | Si coincide, avanza y retorna `True` |
| `skip_newlines()` | Salta `NEWLINE` consecutivos |
| `skip_statement_terminators()` | Salta `NEWLINE` y `SEMICOLON` |

### Métodos de parseo principales

#### Nivel superior
| Método | Produce |
|--------|---------|
| `parse()` | `Program` |
| `parse_package()` | `PackageDecl` |
| `parse_imports()` | `List[ImportDecl]` — soporta `import "x"` e `import ( "x"; "y" )` |
| `parse_declarations()` | Lista de `FuncDecl`, `StructDecl`, `VarDecl`, etc. |
| `parse_func_decl()` | `FuncDecl` con soporte para receptor (métodos) |
| `parse_struct_decl()` | `StructDecl` |
| `parse_interface_decl()` | `InterfaceDecl` |
| `parse_type_decl()` | `TypeDecl` |

#### Sentencias
| Método | Produce |
|--------|---------|
| `parse_statement()` | Despacha al método correcto según el token actual |
| `parse_if_stmt()` | `IfStmt` — soporta `if init; cond` y `if x, ok := v.(T); ok` |
| `parse_for_stmt()` | `ForStmt` / `ForRangeStmt` — soporta `for`, `for cond`, `for init; cond; post`, `for range`, `for i, w := 0, 0; ...` |
| `parse_switch_stmt()` | `SwitchStmt` |
| `parse_return_stmt()` | `ReturnStmt` |
| `parse_assign_stmt()` | `AssignStmt` — detecta `=`, `:=`, `+=`, etc. |
| `parse_var_decl()` | `VarDecl` |
| `parse_const_decl()` | `ConstDecl` — soporta `iota` en bloques `const (...)` |

#### Expresiones (precedencia ascendente)
```
parse_expression
  └─ parse_ternary
       └─ parse_or  (||)
            └─ parse_and  (&&)
                 └─ parse_comparison  (==, !=, <, >, <=, >=)
                      └─ parse_bitwise_or  (|)
                           └─ parse_bitwise_xor  (^)
                                └─ parse_bitwise_and  (&)
                                     └─ parse_shift  (<<, >>)
                                          └─ parse_additive  (+, -)
                                               └─ parse_multiplicative  (*, /, %)
                                                    └─ parse_unary  (-, !, *, &, ^)
                                                         └─ parse_postfix  ([i], .campo, (args), .(T))
                                                              └─ parse_primary  (literal, ident, func, struct...)
```

### Casos especiales del parser
- **Composite literals** (`T{...}`): Se deshabilitan en ciertos contextos (e.g., condición de `if`) mediante el flag `_no_complit`.
- **Type assertions** (`x.(T)`): Producen nodo `TypeCast(type_=T, expr=x)`.
- **Literal de struct anónimo**: `struct { campo tipo }{ val }` dentro de expresiones.
- **Múltiples valores en `const (...)`** con iota incremental.

---

## 7. Módulo: `interpreter.py`

### Responsabilidad
Ejecuta el AST directamente usando **evaluación de árbol** (tree-walking interpreter). No genera código máquina: recorre el AST nodo a nodo, manteniendo un entorno de ejecución.

### Clase `Value`
```python
@dataclass
class Value:
    type_name: str   # "int", "float", "string", "bool", "pointer", "struct", etc.
    value: Any       # Valor Python nativo
```

Tipos de runtime soportados:

| `type_name` | `value` en Python |
|-------------|------------------|
| `"int"` | `int` |
| `"float"` | `float` |
| `"string"` | `str` |
| `"bool"` | `bool` |
| `"rune"` | `int` (codepoint Unicode) |
| `"nil"` | `None` |
| `"array"` / `"slice"` | `list` de `Value` |
| `"map"` | `dict` de `str` → `Value` |
| `"pointer"` | `{"heap": Value}` o `{"env": Environment, "name": str}` |
| tipo de struct | `dict` de campo → `Value` |
| `"error"` | `str` (mensaje) |
| `"func"` | `FuncDecl` |

### Clase `Environment`
Representa un ámbito léxico. Cada llamada a función crea un nuevo `Environment` hijo.

```python
class Environment:
    parent: Optional[Environment]
    variables: Dict[str, Value]
    functions: Dict[str, FuncDecl]
    constants: Dict[str, Value]
```

Métodos: `define(name, value)`, `define_const(name, value)`, `define_function(name, decl)`, `get(name)`, `set(name, value)`, `get_function(name)`.

### Clase `Interpreter`

**Constructor:** `Interpreter(program: Program, output_widget=None)`

**Método principal:** `run()` — carga declaraciones globales, registra métodos, ejecuta `main()`.

#### Métodos de evaluación

| Método | Descripción |
|--------|-------------|
| `eval_expression(expr)` | Despacha al evaluador correcto según el tipo de nodo |
| `eval_literal(lit)` | Convierte literales string/int/float/bool/nil a `Value` |
| `eval_binary_op(op)` | Aritmética, comparación, lógica, concatenación de strings |
| `eval_unary_op(op)` | `-`, `!`, `*` (deref), `&` (address-of) |
| `eval_call(call)` | Llamadas a función, métodos, funciones builtin |
| `eval_field(expr)` | Acceso a campo de struct y constantes de paquetes (`math.Pi`) |
| `eval_index(expr)` | Indexado de arrays, slices y maps |
| `eval_assign(stmt)` | Asignación simple y múltiple, type assertions en `:=` |
| `execute_statement(stmt)` | Ejecuta cualquier sentencia del AST |
| `execute_block(block, env)` | Ejecuta un bloque con su propio environment |

#### Funciones builtin soportadas

| Función | Comportamiento |
|---------|---------------|
| `fmt.Println(...)` | Imprime valores separados por espacio + `\n` |
| `fmt.Printf(fmt, ...)` | Formateo con `%v`, `%d`, `%f`, `%s`, `%x`, `%#U`, `%p`, etc. |
| `fmt.Sprintf(fmt, ...)` | Igual que Printf pero retorna string |
| `fmt.Errorf(fmt, ...)` | Retorna un `Value("error", msg)` |
| `len(x)` | Longitud de string (bytes), array, slice o map |
| `cap(x)` | Capacidad de slice |
| `append(slice, elems...)` | Agrega elementos a un slice |
| `make(type, len, cap?)` | Crea slices/maps |
| `new(T)` | Crea puntero a valor cero del tipo |
| `delete(map, key)` | Elimina clave de un map |
| `panic(msg)` | Lanza `RuntimeError` |
| `copy(dst, src)` | Copia elementos entre slices |
| `real(c)`, `imag(c)` | Partes de número complejo |
| `utf8.RuneCountInString(s)` | Cuenta runas (codepoints) en un string UTF-8 |
| `utf8.DecodeRuneInString(s)` | Retorna (runa, ancho en bytes) |
| `math.Pi`, `math.E`, ... | Constantes matemáticas |
| `math.Sin`, `math.Cos`, `math.Sqrt`, ... | Funciones matemáticas (una y dos argumentos) |
| `strings.Contains`, `strings.HasPrefix`, ... | Funciones de cadenas |

#### Punteros
- `&variable` → `Value("pointer", {"env": env, "name": "variable"})` — referencia al entorno
- `&StructLiteral{...}` → `Value("pointer", {"heap": Value})` — puntero a heap
- `*ptr` → desreferencía el puntero
- `ptr.campo` → acceso transparente a campo vía puntero

#### Excepciones de control de flujo
Implementadas como excepciones Python internas:

| Clase | Uso |
|-------|-----|
| `ReturnException(values)` | `return` |
| `BreakException` | `break` |
| `ContinueException` | `continue` |
| `FallthroughException` | `fallthrough` |

#### Soporte de interfaces
- Los métodos se registran en `self.methods: Dict[str_typename, Dict[str_methodname, (FuncDecl, receiver_param)]]`.
- Los type assertions `x.(T)` se evalúan en `_eval_single_or_comma_ok()`: compara `value.type_name == target_name`.
- La interfaz `Stringer` se detecta automáticamente: si un tipo tiene método `String()`, se usa en `to_string()`.

#### Estructuras embedded
- Al acceder a un campo no encontrado en el struct, se busca en campos embedded (anidados).
- Los métodos de un tipo embedded se promueven y son accesibles desde el tipo contenedor.

---

## 8. Módulo: `compiler.py`

### Responsabilidad
Transpila el AST a **código C** compatible con C99.

### Clase `CompilationContext`
```python
@dataclass
class CompilationContext:
    indent_level: int           # Nivel de indentación actual
    header_includes: Set[str]   # Headers C incluidos
    generated_structs: Set[str] # Structs ya generados
    generated_functions: Set[str] # Funciones ya generadas
```

### Clase `Compiler`

**Constructor:** `Compiler(program: Program)`

**Método principal:** `compile() → str` — retorna el código C completo.

#### Mapeo de tipos Go → C

| Go | C |
|----|---|
| `int` | `int` |
| `int8` | `char` |
| `int64` | `long` |
| `float32` | `float` |
| `float64` | `double` |
| `bool` | `int` |
| `string` | `char*` |
| `rune` | `int` |
| `byte` | `unsigned char` |

#### Helpers generados automáticamente
- Macros `TRUE`/`FALSE`
- Structs `Array` y `Map` genéricos
- Función `go_string_concat(a, b)` para concatenación de strings
- Función `go_print(...)` para fmt.Println

#### Flujo de compilación
1. `add_headers()` — `#include <stdio.h>`, `<stdlib.h>`, `<math.h>`, etc.
2. `add_helpers()` — macros y funciones auxiliares
3. Compila `StructDecl` → `typedef struct { ... } Name;`
4. Compila `FuncDecl` → funciones C
5. Compila `VarDecl`/`ConstDecl` globales → variables/constantes C

---

## 9. Módulo: `assembly_generator.py`

### Responsabilidad
Genera dos representaciones de bajo nivel a partir del AST:
1. **TAC** (Three-Address Code / Código de Tres Direcciones)
2. **Ensamblador x86-64** simplificado

### Clase `TACInstruction`
```python
@dataclass
class TACInstruction:
    op: str       # Operación: ASSIGN, +, -, CALL, RETURN, GOTO, IF_FALSE...
    arg1: str     # Primer argumento
    arg2: str     # Segundo argumento
    result: str   # Variable de resultado
    label: str    # Etiqueta (para saltos)
    comment: str  # Comentario opcional
```

### Clase `AssemblyGenerator`

**Constructor:** `AssemblyGenerator(program: Program)`

**Método principal:** `generate() → (tac_str, asm_str)`

#### Operaciones TAC generadas

| Operación | Significado |
|-----------|-------------|
| `ASSIGN` | `t1 = x` |
| `+`, `-`, `*`, `/` | Aritmética: `t2 = t1 + t3` |
| `FUNC_BEGIN / FUNC_END` | Delimitadores de función |
| `PARAM` | Pasar argumento a función |
| `CALL` | Llamada a función |
| `RETURN` | Retorno de función |
| `GOTO` | Salto incondicional |
| `IF_FALSE / IF_TRUE` | Salto condicional |
| `PRINT` | Instrucción de salida |

#### Variables temporales
Se generan automáticamente con nombres `t1`, `t2`, ... usando `new_temp()`.

#### Etiquetas
Se generan con prefijos: `L` (etiquetas genéricas), `if_true_`, `if_false_`, `for_start_`, `for_end_`.

---

## 10. Módulo: `indentation_checker.py`

### Responsabilidad
Valida la indentación del código Go, detectando inconsistencias antes de parsear.

### Clase `IndentationError`
```python
class IndentationError(Exception):
    line_num: int
    message: str
```

### Clase `IndentationChecker`

**Constructor:** `IndentationChecker(code: str)`

**Método principal:** `check() → List[Tuple[int, str]]`  
Retorna lista de `(número_línea, mensaje_error)`.

#### Errores detectados
- **Mezcla de tabs y espacios** en la misma línea
- **Indentación incorrecta** del cierre `}` (no coincide con el nivel del bloque abierto)
- **Indentación inconsistente**: el tipo de indentación cambia entre líneas (tabs vs espacios)

### Función `check_indentation(code: str) → List[Tuple[int, str]]`
Función de conveniencia que crea un `IndentationChecker` y llama a `check()`.

---

## 11. Módulo: `main.py` — La IDE

### Responsabilidad
Implementa la interfaz gráfica completa usando **Tkinter**. Integra todos los módulos anteriores.

### Clases de la interfaz

#### `CustomText(tk.Text)`
Widget de texto personalizado que intercepta todas las operaciones (`insert`, `delete`, `replace`, etc.) mediante un proxy Tcl y genera el evento `<<Change>>`. Esto permite que los números de línea y el resaltado de sintaxis se actualicen automáticamente.

#### `LineNumbers(tk.Canvas)`
Canvas que dibuja los números de línea alineados con el widget `CustomText` asociado.

| Método | Descripción |
|--------|-------------|
| `attach(text_widget)` | Vincula el canvas al widget de texto |
| `redraw()` | Redibuja todos los números visibles usando `dlineinfo()` |

#### `EditorTab`
Encapsula una **pestaña individual** del editor.

**Atributos:**
| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `ruta_actual` | `str\|None` | Ruta del archivo abierto |
| `archivo_modificado` | `bool` | Si hay cambios sin guardar |
| `font_size` | `int` | Tamaño de fuente actual |
| `errores` | `list` | Errores detectados en esta pestaña |
| `texto_codigo` | `CustomText` | El editor de texto principal |
| `linenumbers` | `LineNumbers` | Canvas de números de línea |
| `_tab_btn_frame` | `tk.Frame` | Frame del botón en la barra de pestañas |
| `_tab_label` | `tk.Button` | Botón con el nombre de la pestaña |
| `_tab_close` | `tk.Button` | Botón ✕ para cerrar la pestaña |

**Métodos:**
| Método | Descripción |
|--------|-------------|
| `get_nombre_para_tab()` | Retorna nombre para la pestaña (basename o "Sin título"), añade `*` si hay cambios |
| `get_contenido()` | Retorna el texto completo del editor |

#### `GoIDE` (clase principal)

**Constructor:** `GoIDE(root: tk.Tk)`  
Inicializa toda la interfaz: menús, barra de herramientas, explorador de archivos, editor con pestañas, panel de salida, panel de errores.

### Layout de la ventana

```
┌─────────────────────────────────────────────────────────┐
│  Barra de Menú: Archivo | Edición | Vista | Ejecutar... │
├─────────────────────────────────────────────────────────┤
│  Barra de Herramientas: [Abrir] [Guardar] [Compilar]... │
├───────────────┬─────────────────────────────────────────┤
│               │  [tab1] [tab2 ×] [tab3 ×]  ← tab_bar  │
│  Explorador   ├─────────────────────────────────────────┤
│  de archivos  │                                         │
│               │      Editor de código (CustomText)      │
│  (TreeView)   │                                         │
│               ├─────────────────────────────────────────┤
│               │  ⚠️ PROBLEMAS  [0 errores]              │
│               │  Lista de errores de sintaxis/indentación│
├───────────────┼─────────────────────────────────────────┤
│               │  📟Consola | ⚙️Código C | 🔍Léxico | ASM│
│               │                                         │
│               │         Panel de salida                 │
└───────────────┴─────────────────────────────────────────┘
```

### Barra de pestañas personalizada (`tab_bar`)

La barra de pestañas **reemplaza** las pestañas nativas de `ttk.Notebook` para poder añadir botones de cierre (✕).

- **Tab activa**: fondo `#1e1e1e`, texto blanco
- **Tab inactiva**: fondo `#2d2d2d`, texto gris
- **Hover sobre tab**: resalta el fondo
- **Clic en ✕**: cierra la pestaña (con diálogo de guardado si hay cambios)
- **Clic en el nombre**: selecciona la pestaña

### Gestión de pestañas

| Método | Descripción |
|--------|-------------|
| `crear_nueva_tab(ruta, contenido)` | Crea una nueva `EditorTab`, la añade al notebook y crea su botón en la barra |
| `get_tab_actual()` | Retorna la `EditorTab` activa |
| `cerrar_tab(tab)` | Cierra la pestaña indicada con diálogo de confirmación |
| `cerrar_tab_actual()` | Cierra la pestaña activa (Ctrl+W) |
| `siguiente_tab()` | Cambia a la siguiente pestaña (Ctrl+Tab) |
| `anterior_tab()` | Cambia a la anterior (Ctrl+Shift+Tab) |
| `actualizar_nombre_tab(tab)` | Actualiza el texto del botón y del notebook |
| `_crear_boton_tab(tab, nombre)` | Crea el miniframe con label + ✕ en la barra |
| `_seleccionar_tab(tab)` | Selecciona la pestaña y actualiza el visual |
| `_actualizar_tab_visual()` | Reaplica colores activo/inactivo a todos los botones |

### Acciones del editor

| Método | Descripción |
|--------|-------------|
| `nuevo_archivo()` | Crea una nueva pestaña vacía |
| `abrir_archivo(ruta?)` | Abre un archivo `.go` en una nueva pestaña |
| `guardar()` | Guarda el archivo actual (Ctrl+S) |
| `guardar_como()` | Guarda con nuevo nombre |
| `accion_ejecutar()` | F5: Lexer → Parser → Intérprete |
| `accion_compilar()` | F6: Lexer → Parser → Compilador C |
| `accion_generar_asm()` | F7: Lexer → Parser → Generador ASM |
| `limpiar()` | Limpia las pestañas de salida |

### Resaltado de sintaxis

El método `aplicar_highlight(tab)` usa expresiones regulares para colorear:

| Color | Qué resalta |
|-------|-------------|
| `#569cd6` (azul) | Palabras clave Go: `func`, `if`, `for`, `return`, ... |
| `#4ec9b0` (teal) | Tipos: `int`, `string`, `bool`, `float64`, ... |
| `#ce9178` (naranja) | Strings literales `"..."` |
| `#b5cea8` (verde claro) | Números |
| `#608b4e` (verde) | Comentarios `//` y `/* */` |
| `#dcdcaa` (amarillo) | Nombres de funciones (antes de `(`) |
| `#9cdcfe` (celeste) | Identificadores en declaraciones `func` |
| `#f44747` (rojo) | Errores subrayados |

### Panel de errores

Muestra errores en tiempo real mientras el usuario escribe (con debounce de 500ms):
- **Errores de sintaxis** del parser
- **Errores de indentación** del `IndentationChecker`
- Clic en un error → navega a la línea correspondiente

### Explorador de archivos
- Muestra el árbol de directorios del proyecto abierto (`ttk.Treeview`)
- Doble clic en archivo → lo abre en una nueva pestaña
- Botón "Abrir Carpeta..." → seleccionar raíz del proyecto

### Funcionalidades adicionales

| Feature | Atajo | Descripción |
|---------|-------|-------------|
| Buscar y reemplazar | Ctrl+F | Ventana flotante con regex opcional |
| Ir a línea | Ctrl+G | Input numérico, posiciona el cursor |
| Duplicar línea | Ctrl+D | Duplica la línea actual |
| Comentar/descomentar | Ctrl+/ | Toggle `//` en las líneas seleccionadas |
| Autocompletado | Ctrl+Space | Lista de palabras clave y símbolos definidos |
| Ir a definición | F12 | Salta a la declaración del símbolo bajo el cursor |
| Renombrar símbolo | F2 | Renombra todas las ocurrencias en el archivo |
| Zoom in/out | Ctrl+Rueda | Cambia el tamaño de fuente del editor |
| Reset zoom | Ctrl+0 | Restaura el tamaño de fuente por defecto |
| Toggle terminal | F8 | Muestra/oculta el panel de terminal integrado |
| Cambiar tema | — | Alterna entre tema oscuro y claro |
| Estadísticas | — | Líneas, palabras, caracteres, funciones, etc. |

---

## 12. Características del Lenguaje Soportadas

### ✅ Completamente soportadas
| Característica | Ejemplo |
|----------------|---------|
| Declaración de paquete | `package main` |
| Imports simples y agrupados | `import "fmt"` / `import ("fmt"; "math")` |
| Variables con `:=` y `var` | `x := 5` / `var s string = "hola"` |
| Constantes e iota | `const (A = iota; B; C)` |
| Tipos primitivos | `int`, `float64`, `string`, `bool`, `rune`, `byte` |
| Punteros | `&x`, `*ptr`, paso por referencia |
| Structs | Definición, literales posicionales/nombrados, campos zero-value |
| Métodos | Receptores valor y puntero `func (r *Rect) Area() int` |
| Interfaces | Definición, implementación implícita, type assertions `x.(T)` |
| Embedding | Campos y métodos promovidos `type C struct { Base; ... }` |
| Arrays y slices | `[3]int{1,2,3}`, `[]string{"a","b"}`, `append`, `len`, `cap` |
| Maps | `map[string]int{"a": 1}`, `delete`, literales |
| For clásico | `for i := 0; i < n; i++` |
| For while | `for cond { }` |
| For range | `for i, v := range slice` / `for k, v := range mapas` |
| For multi-var | `for i, w := 0, 0; i < len(s); i += w` |
| If con init | `if err := f(); err != nil` / `if c, ok := x.(T); ok` |
| Switch | Con expresión, `case` múltiple, `default`, `fallthrough` |
| Defer | `defer f()` — LIFO al retornar |
| Funciones variádicas | `func f(args ...int)` |
| Retornos múltiples | `func div(a, b int) (int, int)` |
| Closures / lambdas | `f := func(x int) int { return x * 2 }` |
| Strings UTF-8 | Iteración por bytes y runas, `\uXXXX`, `\UXXXXXXXX` |
| Literales hex | `0xFF`, `0x0E2A` |
| Paquete `math` | `math.Pi`, `math.Sin`, `math.Sqrt`, ... |
| Paquete `unicode/utf8` | `RuneCountInString`, `DecodeRuneInString` |
| Paquete `fmt` | `Println`, `Printf`, `Sprintf`, `Errorf`, verbos `%v %d %f %s %x %#U %p` |
| Type declarations locales | `type X int` dentro de funciones |

### ⚠️ Parcialmente soportadas
| Característica | Estado |
|----------------|--------|
| Goroutines (`go f()`) | Se ejecutan síncronamente (sin paralelismo real) |
| Channels | Estructura parseada, semántica limitada |
| Select | Parseado, implementación básica |
| panic/recover | `panic` lanza error, `recover` no implementado |
| Interfaces vacías `interface{}` | Acepta cualquier valor |
| Generics | No soportado |

---

## 13. Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| **F5** | Ejecutar código (intérprete) |
| **F6** | Compilar a C |
| **F7** | Generar ensamblador |
| **F8** | Mostrar/ocultar terminal |
| **F12** | Ir a definición |
| **F2** | Renombrar símbolo |
| **Ctrl+S** | Guardar |
| **Ctrl+N** | Nueva pestaña |
| **Ctrl+O** | Abrir archivo |
| **Ctrl+W** | Cerrar pestaña actual |
| **Ctrl+Tab** | Siguiente pestaña |
| **Ctrl+Shift+Tab** | Pestaña anterior |
| **Ctrl+F** | Buscar y reemplazar |
| **Ctrl+G** | Ir a línea |
| **Ctrl+D** | Duplicar línea |
| **Ctrl+/** | Comentar/descomentar |
| **Ctrl+Space** | Autocompletado manual |
| **Ctrl+0** | Resetear zoom |
| **Ctrl+Rueda** | Zoom in/out |

---

## 14. Ejemplos de Uso

### Punteros
```go
package main
import "fmt"

func zeroval(ival int) { ival = 0 }
func zeroptr(iptr *int) { *iptr = 0 }

func main() {
    i := 1
    fmt.Println("initial:", i)  // initial: 1
    zeroval(i)
    fmt.Println("zeroval:", i)  // zeroval: 1
    zeroptr(&i)
    fmt.Println("zeroptr:", i)  // zeroptr: 0
}
```

### Structs
```go
package main
import "fmt"

type person struct {
    name string
    age  int
}

func newPerson(name string) *person {
    p := person{name: name}
    p.age = 42
    return &p
}

func main() {
    fmt.Println(person{"Bob", 20})          // {Bob 20}
    fmt.Println(person{name: "Alice", age: 30}) // {Alice 30}
    fmt.Println(newPerson("Jon"))               // &{Jon 42}
}
```

### Interfaces
```go
package main
import ("fmt"; "math")

type geometry interface {
    area() float64
    perim() float64
}
type circle struct { radius float64 }

func (c circle) area() float64  { return math.Pi * c.radius * c.radius }
func (c circle) perim() float64 { return 2 * math.Pi * c.radius }

func measure(g geometry) {
    fmt.Println(g.area())
}

func main() {
    measure(circle{radius: 5})  // 78.53981633974483
}
```

### Enumeraciones con iota
```go
package main
import "fmt"

type Estado int
const (
    Inactivo Estado = iota
    Conectado
    Error
)

func main() {
    fmt.Println(Conectado) // 1
}
```

---

## 15. Notas Técnicas y Limitaciones

### Modelo de valores
El intérprete usa un modelo **boxed**: cada valor en el programa Go se representa como un objeto `Value(type_name, value)` en Python. Esto simplifica la implementación pero tiene un costo de rendimiento para programas con mucha aritmética.

### Punteros
Los punteros a variables locales se implementan como referencias al `Environment` (`{"env": env, "name": "x"}`). Los punteros a struct heap-allocated usan `{"heap": Value}`. Al mostrarlos con `fmt.Println`, el intérprete desreferencia automáticamente para mostrar `&{campo valor}`.

### Strings y runas
Los strings Go son **secuencias de bytes UTF-8**. El intérprete representa strings como `str` de Python (Unicode). `len(s)` retorna el número de bytes (codificación UTF-8), no el número de caracteres. Las runas se representan como `int` (codepoint Unicode).

### Scope y closures
Las funciones capturan su entorno de definición. Las closures funcionan correctamente para lectura; la escritura a variables capturadas del scope externo requiere que estén en el mismo environment accesible por referencia.

### Type assertions
`x.(T)` en contexto de dos valores (`c, ok := x.(T)`) usa comparación estricta de `type_name`. Solo retorna `(valor, true)` si el `type_name` del valor coincide exactamente con el tipo solicitado.

### Iota
El contador `iota` se reinicia a 0 en cada bloque `const (...)` y se incrementa por cada especificación de constante. Se soportan expresiones con iota como `1 << iota`.

### Formato de salida
`fmt.Println` de un struct imprime `{val1 val2 ...}` (valores separados por espacio, sin nombres de campo), igual que Go real. Un puntero a struct imprime `&{val1 val2 ...}`.

---

*Documentación generada el 19 de febrero de 2026.*
