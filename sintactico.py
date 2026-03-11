"""
Analizador Sintáctico - Modo Terminal
Ingresa código Python y obtén el árbol sintáctico (AST) en consola.
"""
import sys
import ast
import enum as _enum
from lexer import Lexer
from parser import Parser

# Forzar salida UTF-8 (necesario en Windows para caracteres de árbol y ANSI)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def _valor_inline(nodo) -> str:
    """Devuelve una representación compacta si el nodo es 'hoja', o '' si no."""
    if nodo is None:
        return "∅"
    if isinstance(nodo, bool):
        return str(nodo)
    if isinstance(nodo, (int, float)):
        return str(nodo)
    if isinstance(nodo, str):
        return repr(nodo)
    if isinstance(nodo, _enum.Enum):
        return nodo.name
    return ""


def imprimir_nodo(nodo, pad="", ultimo=True, etiqueta=""):
    """Imprime el AST con formato de árbol usando caracteres visuales."""
    RAMA   = "├── "
    ULTIMO = "└── "
    BARRA  = "│   "
    VACIO  = "    "

    conector = ULTIMO if ultimo else RAMA
    pad_hijo = pad + (VACIO if ultimo else BARRA)

    # ── None ──────────────────────────────────────────────────────────────────
    if nodo is None:
        print(f"{pad}{conector}{etiqueta}∅")
        return

    # ── Tipos simples ─────────────────────────────────────────────────────────
    inline = _valor_inline(nodo)
    if inline:
        print(f"{pad}{conector}{etiqueta}{inline}")
        return

    # ── Listas ────────────────────────────────────────────────────────────────
    if isinstance(nodo, list):
        if not nodo:
            print(f"{pad}{conector}{etiqueta}[ ]")
            return
        print(f"{pad}{conector}{etiqueta}[ {len(nodo)} elemento(s) ]")
        for i, item in enumerate(nodo):
            imprimir_nodo(item, pad=pad_hijo, ultimo=(i == len(nodo) - 1),
                          etiqueta=f"[{i}] ")
        return

    # ── Nodos del AST de Python (ast.AST) ─────────────────────────────────────
    if isinstance(nodo, ast.AST):
        nombre = type(nodo).__name__
        # ast.iter_fields devuelve solo los campos definidos en _fields (sin ruido)
        campos = [(f, v) for f, v in ast.iter_fields(nodo)
                  if v is not None and v != [] and v != {}]

        # Nodo "hoja" compacto: 1 campo primitivo → una sola línea
        if len(campos) == 1:
            clave, valor = campos[0]
            val_str = _valor_inline(valor)
            if val_str:
                print(f"{pad}{conector}{etiqueta}\033[1;36m{nombre}\033[0m({clave}={val_str})")
                return

        print(f"{pad}{conector}{etiqueta}\033[1;33m{nombre}\033[0m")
        for i, (campo, valor) in enumerate(campos):
            imprimir_nodo(valor, pad=pad_hijo, ultimo=(i == len(campos) - 1),
                          etiqueta=f"\033[90m{campo}\033[0m: ")
        return

    # ── Fallback ──────────────────────────────────────────────────────────────
    print(f"{pad}{conector}{etiqueta}{repr(nodo)}")


def analizar(codigo: str):
    print("\n" + "=" * 60)
    print("  ANÁLISIS LÉXICO")
    print("=" * 60)

    lexer = Lexer(codigo)
    try:
        tokens = lexer.tokenize()
    except Exception as e:
        print(f"[ERROR LÉXICO] {e}")
        return

    for t in tokens:
        print(f"  <{t.type.name:10} | {repr(t.value):30} | línea {t.line}>")

    print("\n" + "=" * 60)
    print("  ANÁLISIS SINTÁCTICO (AST)")
    print("=" * 60)

    # El parser necesita el source original para ast.parse()
    parser = Parser(tokens, source=codigo)
    try:
        programa = parser.parse()
    except SyntaxError as e:
        print(f"[ERROR SINTÁCTICO] {e}")
        return
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    if programa is None:
        print("  (sin árbol — código vacío)")
        return

    # Raíz sin conector
    nombre_raiz = type(programa).__name__
    print(f"\033[1;33m{nombre_raiz}\033[0m")
    campos_raiz = [(f, v) for f, v in ast.iter_fields(programa)
                   if v is not None and v != [] and v != {}]
    for i, (campo, valor) in enumerate(campos_raiz):
        imprimir_nodo(valor, pad="", ultimo=(i == len(campos_raiz) - 1),
                      etiqueta=f"\033[90m{campo}\033[0m: ")
    print("\n✅ Análisis completado sin errores.\n")


def leer_multilinea():
    """Lee código hasta que el usuario envíe la señal de fin."""
    print("Ingresa el código Python y presiona Enter para analizar:")
    print("  · Pega el código y escribe  ---  en una línea sola + Enter")
    print("  · O presiona Ctrl+Z (Windows) / Ctrl+D (Linux/Mac) + Enter")
    print("-" * 60)
    lineas = []
    while True:
        try:
            linea = input()
        except EOFError:
            break
        if linea.strip() == "---":
            break
        lineas.append(linea)
    return "\n".join(lineas)


def main():
    # Si se pasa un archivo como argumento: python sintactico.py archivo.py
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                codigo = f.read()
            print(f"Archivo: {ruta}")
            analizar(codigo)
        except FileNotFoundError:
            print(f"[ERROR] No se encontró el archivo: {ruta}")
        return

    # Modo interactivo: pedir código por terminal
    while True:
        codigo = leer_multilinea()
        if not codigo.strip():
            print("No se ingresó código. Saliendo.")
            break
        analizar(codigo)
        print("\n¿Analizar otro código? (s/n): ", end="", flush=True)
        try:
            respuesta = input().strip().lower()
        except EOFError:
            break
        if respuesta != "s":
            break


if __name__ == "__main__":
    main()
