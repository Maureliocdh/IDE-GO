
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog
import os
import re
import shutil

# IMPORTAMOS TUS ARCHIVOS

from interpreter import Interpreter
import lexer
from parser import Parser
from compiler import Compiler
from lexer import Lexer
from assembly_generator import AssemblyGenerator
from indentation_checker import IndentationChecker, check_indentation

# --- CLASE TEXTO PERSONALIZADO (PROXY) ---
# Esta clase arregla el bug de que no se actualicen los números
class CustomText(tk.Text):
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)
        # Creamos un proxy para interceptar cambios
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        # Ejecuta la acción original (escribir, borrar, etc.)
        cmd = (self._orig,) + args
        try:
            result = self.tk.call(cmd)
        except Exception:
            return None

        # Si hubo un cambio (insertar, borrar, scroll), generamos el evento <<Change>>
        if (args[0] in ("insert", "replace", "delete") or 
            args[0:3] == ("mark", "set", "insert") or
            args[0:2] == ("xview", "moveto") or
            args[0:2] == ("xview", "scroll") or
            args[0:2] == ("yview", "moveto") or
            args[0:2] == ("yview", "scroll")):
            self.event_generate("<<Change>>", when="tail")

        return result

# --- CLASE PARA NÚMEROS DE LÍNEA ---
class LineNumbers(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.text_widget = None

    def attach(self, text_widget):
        self.text_widget = text_widget

    def redraw(self, *args):
        '''Redibuja los números de línea'''
        self.delete("all")
        
        # Obtener el primer índice visible
        i = self.text_widget.index("@0,0")
        
        while True :
            dline = self.text_widget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=linenum, fill="#45475a", font=("Consolas", 11))
            i = self.text_widget.index("%s+1line" % i)

# --- TOOLTIP ---
class Tooltip:
    """Muestra un tooltip flotante al pasar el cursor sobre un widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._tip_win = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, event):
        self._after_id = self.widget.after(500, self._show)

    def _show(self):
        if self._tip_win:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip_win = tk.Toplevel(self.widget)
        self._tip_win.wm_overrideredirect(True)
        self._tip_win.wm_geometry(f"+{x}+{y}")
        self._tip_win.attributes("-topmost", True)
        lbl = tk.Label(self._tip_win, text=self.text,
                       bg="#313244", fg="#cdd6f4",
                       font=("Segoe UI", 9),
                       relief="flat", padx=8, pady=4,
                       borderwidth=0)
        lbl.pack()

    def _hide(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self._tip_win:
            self._tip_win.destroy()
            self._tip_win = None


# --- BOTÓN CIRCULAR CON ICONO ---
class CircleButton(tk.Canvas):
    """Botón circular con icono emoji y efecto hover."""
    def __init__(self, parent, icon, color, command, size=36, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bd=0, highlightthickness=0,
                         cursor="hand2", **kwargs)
        self._color = color
        self._hover = self._lighten(color, 0.25)
        self._size = size
        pad = 3
        self._oval = self.create_oval(pad, pad, size - pad, size - pad,
                                       fill=color, outline="", tags="btn")
        self._icon = self.create_text(size // 2, size // 2, text=icon,
                                       font=("Segoe UI Emoji", 14),
                                       fill="white", tags="btn")
        self.tag_bind("btn", "<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self.itemconfig(self._oval, fill=self._hover))
        self.bind("<Leave>", lambda e: self.itemconfig(self._oval, fill=self._color))
        self.tag_bind("btn", "<Enter>", lambda e: self.itemconfig(self._oval, fill=self._hover))
        self.tag_bind("btn", "<Leave>", lambda e: self.itemconfig(self._oval, fill=self._color))

    @staticmethod
    def _lighten(hex_color, factor=0.25):
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"


# --- CLASE PARA CADA PESTAÑA DEL EDITOR ---
class EditorTab:
    """Clase que encapsula una pestaña individual del editor"""
    def __init__(self, parent, ide_instance, font_size=13):
        self.ide = ide_instance
        self.ruta_actual = None
        self.archivo_modificado = False
        self.font_size = font_size
        self.errores = []  # Lista de errores encontrados en esta tab
        
        # Frame principal de la pestaña
        self.frame = tk.Frame(parent, bg=ide_instance.bg_color)
        
        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")
        
        # Editor de texto
        self.texto_codigo = CustomText(self.frame, undo=True, width=60, height=30,
                                       font=("Consolas", font_size), 
                                       bg=ide_instance.bg_color, 
                                       fg=ide_instance.fg_color,
                                       insertbackground="#94e2d5", 
                                       selectbackground="#313244",
                                       yscrollcommand=self.scrollbar.set, 
                                       borderwidth=0)
        
        # Números de línea
        self.linenumbers = LineNumbers(self.frame, width=40, bg="#13131d", highlightthickness=0)
        self.linenumbers.attach(self.texto_codigo)
        self.linenumbers.pack(side="left", fill="y")
        
        self.texto_codigo.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.texto_codigo.yview)
        
        # Eventos
        self.texto_codigo.bind("<<Change>>", self._on_change)
        self.texto_codigo.bind("<Configure>", self._on_change)
        self.texto_codigo.bind("<KeyRelease>", self.on_keyrelease)
        self.texto_codigo.bind("<ButtonRelease-1>", self.on_click)
        self.texto_codigo.bind("<Return>", self.auto_indentacion)
        self.texto_codigo.bind('<Control-MouseWheel>', self.zoom_editor)
        self.texto_codigo.bind('<Tab>', lambda e: ide_instance.detectar_snippet(e))
        
        # Configurar tags de sintaxis
        self.configurar_tags()
    
    def _on_change(self, event):
        """Actualiza números de línea"""
        self.linenumbers.redraw()
    
    def on_keyrelease(self, event):
        """Maneja eventos de teclado"""
        self.ide.resaltar_sintaxis_tab(self, event)
        self.ide.actualizar_barra_estado_tab(self, event)
        self.ide.validar_codigo_en_tiempo_real()  # Validación en tiempo real
        self.ide.manejar_autocompletado(event)    # Autocompletado
    
    def on_click(self, event):
        """Maneja clicks del mouse"""
        self.ide.actualizar_barra_estado_tab(self, event)
    
    def auto_indentacion(self, event):
        """Auto-indentación al presionar Enter"""
        return self.ide.auto_indentacion_tab(self)
    
    def zoom_editor(self, event):
        """Zoom con Ctrl+Rueda"""
        return self.ide.zoom_editor_tab(self, event)
    
    def configurar_tags(self):
        """Configura los tags de resaltado de sintaxis"""
        self.texto_codigo.tag_config("keyword",   foreground="#cba6f7")   # mauve
        self.texto_codigo.tag_config("type",      foreground="#89b4fa")   # blue
        self.texto_codigo.tag_config("string",    foreground="#fab387")   # peach
        self.texto_codigo.tag_config("numeros",   foreground="#a6e3a1")   # green
        self.texto_codigo.tag_config("comment",   foreground="#585b70")   # overlay1
        self.texto_codigo.tag_config("caracteres",foreground="#f9e2af")   # yellow
        # Tag para errores
        self.texto_codigo.tag_config("error", underline=True, foreground="#f38ba8")
        self.texto_codigo.tag_config("error_line", background="#2d1e2e")  # dark rose bg
        self.texto_codigo.tag_raise("error")  # Prioridad alta
    
    def get_nombre_para_tab(self):
        """Retorna el nombre para mostrar en la pestaña"""
        if self.ruta_actual:
            nombre = os.path.basename(self.ruta_actual)
        else:
            nombre = "Sin título"
        
        modificado = " •" if self.archivo_modificado else ""
        return nombre + modificado

# --- CLASE PRINCIPAL ---
class SimuladorPython:
    def __init__(self, root):
        self.root = root
        self.root.title("Python IDE")
        self.root.geometry("1350x800")
        
        self.font_size = 13  # Tamaño de fuente por defecto para nuevas tabs

        # Temas disponibles
        self.tema_actual = "oscuro"
        self.temas = {
            "oscuro": {
                "bg":         "#1e1e2e",   # Catppuccin Mocha base
                "fg":         "#cdd6f4",   # text
                "bg_editor":  "#1e1e2e",
                "fg_editor":  "#cdd6f4",
                "bg_toolbar": "#181825",   # mantle
                "bg_lineas":  "#161b22",   # sidebar
                "select_bg":  "#313244",   # surface0
            },
            "claro": {
                "bg":         "#eff1f5",   # Catppuccin Latte base
                "fg":         "#4c4f69",   # text
                "bg_editor":  "#eff1f5",
                "fg_editor":  "#4c4f69",
                "bg_toolbar": "#dce0e8",   # crust
                "bg_lineas":  "#e6e9ef",   # mantle
                "select_bg":  "#acb0be",   # overlay2
            }
        }

        self.bg_color = self.temas[self.tema_actual]["bg"]
        self.fg_color = self.temas[self.tema_actual]["fg"]
        self.root.configure(bg=self.bg_color)

        style = ttk.Style()
        style.theme_use('clam')

        # Notebook editor (pestañas de archivo)
        style.configure("TNotebook", background="#181825", borderwidth=0, tabmargins=[0,0,0,0])
        style.configure("TNotebook.Tab", background="#252530", foreground="#6c7086",
                        padding=[16, 7], font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", "#1e1e2e")],
                  foreground=[("selected", "#cba6f7")])

        # Notebook de salida (Output panel)
        style.configure("Output.TNotebook", background="#181825", borderwidth=0, tabmargins=[0,0,0,0])
        style.configure("Output.TNotebook.Tab", background="#1a1b26", foreground="#6c7086",
                        padding=[14, 6], font=("Segoe UI", 9))
        style.map("Output.TNotebook.Tab",
                  background=[("selected", "#1e1e2e")],
                  foreground=[("selected", "#89b4fa")])

        # BARRA DE MENÚ SUPERIOR
        menubar = tk.Menu(self.root, bg="#1e1e2e", fg="#cdd6f4",
                          activebackground="#313244", activeforeground="#cba6f7",
                          borderwidth=0, relief="flat")
        self.root.config(menu=menubar)

        _mo = dict(tearoff=0, bg="#1e1e2e", fg="#cdd6f4",
                   activebackground="#313244", activeforeground="#cba6f7",
                   borderwidth=0, selectcolor="#cba6f7")

        # -> Menú Archivo
        archivo_menu = tk.Menu(menubar, **_mo)
        archivo_menu.add_command(label="Nuevo", command=self.nuevo_archivo, accelerator="Ctrl+N")
        archivo_menu.add_command(label="Abrir", command=self.abrir_archivo, accelerator="Ctrl+O")
        archivo_menu.add_command(label="Abrir Carpeta...", command=self.abrir_carpeta_proyecto)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Guardar", command=self.guardar, accelerator="Ctrl+S")
        archivo_menu.add_command(label="Guardar Como", command=self.guardar_como)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Ver Bytecode...", command=self.exportar_codigo_c)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Cerrar Pestaña", command=self.cerrar_tab_actual, accelerator="Ctrl+W")
        archivo_menu.add_command(label="Salir", command=self.cerrar)
        menubar.add_cascade(label="Archivo", menu=archivo_menu)

        # -> Menú Edición
        edicion_menu = tk.Menu(menubar, **_mo)
        edicion_menu.add_command(label="Buscar y Reemplazar", command=self.abrir_buscador, accelerator="Ctrl+F")
        edicion_menu.add_command(label="Ir a Línea", command=self.ir_a_linea, accelerator="Ctrl+G")
        edicion_menu.add_separator()
        edicion_menu.add_command(label="Duplicar Línea", command=self.duplicar_linea, accelerator="Ctrl+D")
        edicion_menu.add_command(label="Comentar/Descomentar", command=self.comentar_descomentar, accelerator="Ctrl+/")
        edicion_menu.add_separator()
        edicion_menu.add_command(label="Autocompletar", command=self.activar_autocompletado_manual, accelerator="Ctrl+Space")
        menubar.add_cascade(label="Edición", menu=edicion_menu)

        # -> Menú Navegación
        navegacion_menu = tk.Menu(menubar, **_mo)
        navegacion_menu.add_command(label="Ir a Definición", command=self.ir_a_definicion, accelerator="F12")
        menubar.add_cascade(label="Navegación", menu=navegacion_menu)

        # -> Menú Refactoring
        refactor_menu = tk.Menu(menubar, **_mo)
        refactor_menu.add_command(label="Renombrar Símbolo", command=self.renombrar_simbolo, accelerator="F2")
        menubar.add_cascade(label="Refactoring", menu=refactor_menu)

        # -> Menú Vista
        vista_menu = tk.Menu(menubar, **_mo)
        vista_menu.add_command(label="Cambiar Tema (Claro/Oscuro)", command=self.cambiar_tema)
        vista_menu.add_separator()
        vista_menu.add_command(label="Aumentar Zoom", accelerator="Ctrl+Rueda")
        vista_menu.add_command(label="Resetear Zoom", command=self.resetear_zoom, accelerator="Ctrl+0")
        vista_menu.add_separator()
        vista_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal, accelerator="F8")
        menubar.add_cascade(label="Vista", menu=vista_menu)

        # -> Menú Ejecutar
        terminal_menu = tk.Menu(menubar, **_mo)
        terminal_menu.add_command(label="Ejecutar Código", command=self.accion_ejecutar, accelerator="F5")
        terminal_menu.add_command(label="Ver Bytecode", command=self.accion_compilar, accelerator="F6")
        terminal_menu.add_command(label="Generar Ensamblador", command=self.accion_generar_asm, accelerator="F7")
        terminal_menu.add_separator()
        terminal_menu.add_command(label="Guardar Ensamblador (.asm)", command=self.guardar_asm)
        menubar.add_cascade(label="Ejecutar", menu=terminal_menu)

        # -> Menú Herramientas
        herramientas_menu = tk.Menu(menubar, **_mo)
        herramientas_menu.add_command(label="Estadísticas del Código", command=self.mostrar_estadisticas)
        menubar.add_cascade(label="Herramientas", menu=herramientas_menu)

        # -> Menú Ayuda
        ayuda_menu = tk.Menu(menubar, **_mo)
        ayuda_menu.add_command(label="Acerca de", command=self.mostrar_acerca_de)
        menubar.add_cascade(label="Ayuda", menu=ayuda_menu)

        # --- 1. BARRA DE HERRAMIENTAS ---
        toolbar = tk.Frame(self.root, bg="#181825", padx=8, pady=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.crear_boton(toolbar, "📂", "Abrir archivo", self.abrir_archivo, "#313244")
        self.crear_boton(toolbar, "💾", "Guardar  Ctrl+S", self.guardar, "#313244")
        self.crear_boton(toolbar, "📋", "Guardar Como...", self.guardar_como, "#313244")

        # Separador visual
        tk.Frame(toolbar, width=1, bg="#45475a").pack(side=tk.LEFT, fill="y", padx=10, pady=4)

        self.crear_boton(toolbar, "🔢", "Ver Bytecode  F6", self.accion_compilar, "#007acc")
        self.crear_boton(toolbar, "📝", "Generar ASM  F7", self.accion_generar_asm, "#7c3aed")
        self.crear_boton(toolbar, "▶", "Ejecutar  F5", self.accion_ejecutar, "#16a34a")

        self.crear_boton(toolbar, "✕", "Salir", self.cerrar, "#b91c1c", side=tk.RIGHT)
        self.crear_boton(toolbar, "🧹", "Limpiar salida", self.limpiar, "#c2410c", side=tk.RIGHT)

        # --- 2. CONTENEDOR PRINCIPAL VERTICAL (estilo VS Code) ---
        # Divide la ventana en: zona superior (sidebar+editor) y panel inferior (output)
        self.main_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL,
                                         bg="#313244", sashwidth=5, sashrelief="flat")
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # --- 2a. ZONA SUPERIOR: sidebar + editor (horizontal) ---
        self.paned_window = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL,
                                           bg="#313244", sashwidth=5, sashrelief="flat")
        self.main_paned.add(self.paned_window, minsize=350)

        # --- 2.1. EXPLORADOR DE ARCHIVOS (SIDEBAR IZQUIERDO) ---
        self.panel_explorador = tk.Frame(self.paned_window, bg="#1e1e2e", width=250)
        self.paned_window.add(self.panel_explorador, minsize=180)
        self.crear_explorador_archivos()

        # Variable para carpeta del proyecto
        self.carpeta_proyecto = None

        # --- 3. EDITOR DE CÓDIGO CON PESTAÑAS Y PANEL DE ERRORES ---
        self.editor_frame = tk.Frame(self.paned_window, bg=self.bg_color)
        self.paned_window.add(self.editor_frame, minsize=400)

        # PanedWindow vertical para dividir editor y panel de errores
        self.editor_paned = tk.PanedWindow(self.editor_frame, orient=tk.VERTICAL,
                                           bg="#313244", sashwidth=4, sashrelief="flat")
        self.editor_paned.pack(fill=tk.BOTH, expand=True)

        # Frame superior para el editor con tabs
        frame_editor_tabs = tk.Frame(self.editor_paned, bg=self.bg_color)
        self.editor_paned.add(frame_editor_tabs, minsize=200)

        # Barra de pestañas personalizada
        self.tab_bar = tk.Frame(frame_editor_tabs, bg="#181825", height=36)
        self.tab_bar.pack(side=tk.TOP, fill=tk.X)
        self.tab_bar.pack_propagate(False)

        # Notebook sin cabeceras nativas (las sustituimos por tab_bar)
        style.layout('TabEditor.TNotebook', [('Notebook.client', {'sticky': 'nswe'})])
        style.configure('TabEditor.TNotebook', background=self.bg_color, borderwidth=0)
        self.editor_notebook = ttk.Notebook(frame_editor_tabs, style='TabEditor.TNotebook')
        self.editor_notebook.pack(fill=tk.BOTH, expand=True)

        # Lista de pestañas editoras
        self.tabs_editoras = []
        
        # Variables para control de validación
        self.validation_timer = None
        self.errores_actuales = []  # Lista de errores encontrados
        
        # Variables para autocompletado
        self.autocomplete_window = None  # Ventana flotante de sugerencias
        self.autocomplete_listbox = None  # Listbox con sugerencias
        self.autocomplete_activo = False  # Estado del autocompletado
        self.palabra_actual = ""  # Palabra que se está escribiendo
        self.sugerencias_actuales = []  # Lista de sugerencias filtradas
        
        # Palabras clave de Python
        self.palabras_clave = [
            # Keywords
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
            'except', 'finally', 'for', 'from', 'global', 'if', 'import',
            'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
            'return', 'try', 'while', 'with', 'yield',
            # Tipos integrados
            'int', 'float', 'str', 'bool', 'list', 'dict', 'tuple', 'set',
            'bytes', 'bytearray', 'complex', 'frozenset', 'range', 'object',
            # Funciones integradas comunes
            'print', 'input', 'len', 'type', 'isinstance', 'hasattr',
            'getattr', 'setattr', 'delattr', 'enumerate', 'zip', 'map',
            'filter', 'sorted', 'reversed', 'sum', 'min', 'max', 'abs',
            'round', 'open', 'super', 'property', 'staticmethod',
            'classmethod', 'vars', 'dir', 'help', 'id', 'hash', 'repr',
            'format', 'chr', 'ord', 'hex', 'oct', 'bin', 'pow', 'divmod',
            'any', 'all', 'next', 'iter', 'callable', 'compile', 'eval',
            'exec', 'globals', 'locals',
            # Atributos especiales comunes
            'self', 'cls', '__init__', '__str__', '__repr__', '__len__',
            '__getitem__', '__setitem__', '__name__', '__main__',
        ]
        
        # Variables para Go to Definition y navegación
        self.historial_navegacion = []  # Pila de posiciones visitadas
        self.indice_historial = -1  # Índice actual en el historial
        
        # Variables para renombrado de símbolos
        self.renombrando = False
        self.simbolo_a_renombrar = None
        
        # Snippets de Python
        self.snippets = {
            'def':    'def nombre():\n    pass',
            'defs':   'def nombre(self):\n    pass',
            'class':  'class Nombre:\n    def __init__(self):\n        pass',
            'classh': 'class Nombre(object):\n    def __init__(self):\n        pass',
            'if':     'if condicion:\n    pass',
            'ife':    'if condicion:\n    pass\nelse:\n    pass',
            'elif':   'elif condicion:\n    pass',
            'for':    'for i in range(10):\n    pass',
            'forin':  'for item in coleccion:\n    pass',
            'fore':   'for i, item in enumerate(coleccion):\n    pass',
            'while':  'while condicion:\n    pass',
            'try':    'try:\n    pass\nexcept Exception as e:\n    print(e)',
            'tryf':   'try:\n    pass\nexcept Exception as e:\n    print(e)\nfinally:\n    pass',
            'with':   'with open("archivo") as f:\n    pass',
            'main':   'if __name__ == "__main__":\n    main()',
            'pr':     'print()',
            'inp':    'input("Ingrese: ")',
            'imp':    'import ',
            'from':   'from  import ',
            'ret':    'return ',
            'lam':    'lambda x: x',
            'list':   '[] = []',
            'dict':   '{} = {}',
            'prop':   '@property\ndef nombre(self):\n    return self._nombre',
        }
        
        # Variables para terminal integrado
        self.terminal_visible = False
        self.terminal_frame = None
        self.terminal_text = None
        
        # Sistema de archivos recientes
        self.archivos_recientes = []
        self.max_recientes = 10
        
        # Crear la primera pestaña
        self.crear_nueva_tab()
        
        # Evento al cambiar de pestaña
        self.editor_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Bindings globales de teclado
        self.root.bind('<Control-s>', self.guardar)      
        self.root.bind('<Control-S>', self.guardar)      
        self.root.bind('<F5>', self.accion_ejecutar)  
        self.root.bind('<F6>', self.accion_compilar)
        self.root.bind('<F7>', self.accion_generar_asm)
        self.root.bind('<Control-f>', lambda e: self.abrir_buscador())
        self.root.bind('<Control-F>', lambda e: self.abrir_buscador())
        self.root.bind('<Control-g>', lambda e: self.ir_a_linea())
        self.root.bind('<Control-G>', lambda e: self.ir_a_linea())
        self.root.bind('<Control-d>', lambda e: self.duplicar_linea())
        self.root.bind('<Control-D>', lambda e: self.duplicar_linea())
        self.root.bind('<Control-slash>', lambda e: self.comentar_descomentar())
        self.root.bind('<Control-question>', lambda e: self.comentar_descomentar())
        self.root.bind('<Control-Tab>', lambda e: self.siguiente_tab())
        self.root.bind('<Control-Shift-Tab>', lambda e: self.anterior_tab())
        self.root.bind('<Control-w>', lambda e: self.cerrar_tab_actual())
        self.root.bind('<Control-W>', lambda e: self.cerrar_tab_actual())
        self.root.bind('<Control-0>', lambda e: self.resetear_zoom())
        self.root.bind('<Control-Key-0>', lambda e: self.resetear_zoom())
        self.root.bind('<F8>', lambda e: self.toggle_terminal())
        self.root.bind('<F12>', lambda e: self.ir_a_definicion())
        self.root.bind('<F2>', lambda e: self.renombrar_simbolo())
        self.root.bind('<Control-space>', lambda e: self.activar_autocompletado_manual())
        self.root.bind('<Escape>', lambda e: self.ocultar_autocompletado())
        self.root.bind('<Control-MouseWheel>', lambda e: self.zoom_editor_tab(self.get_tab_actual(), e))
        self.root.bind('<Control-Shift-MouseWheel>', lambda e: self.zoom_editor_tab(self.get_tab_actual(), e, inverso=True))
        #nueva pestañas control+n
        self.root.bind('<Control-n>', lambda e: self.crear_nueva_tab())
        self.root.bind('<Control-N>', lambda e: self.crear_nueva_tab())

        # Binding para autocompletado
        self.root.bind('<Control-space>', lambda e: self.activar_autocompletado_manual())
        self.root.bind('<Escape>', lambda e: self.ocultar_autocompletado())
        
        # Bindings para Go to Definition y Refactoring
        self.root.bind('<F12>', lambda e: self.ir_a_definicion())
        self.root.bind('<F2>', lambda e: self.renombrar_simbolo())
        
        # Bindings para utilidades adicionales
        self.root.bind('<Control-Key-0>', lambda e: self.resetear_zoom())
        self.root.bind('<F8>', lambda e: self.toggle_terminal())
        
        # NUEVOS: Bindings para pestañas
        self.root.bind('<Control-w>', lambda e: self.cerrar_tab_actual())
        self.root.bind('<Control-W>', lambda e: self.cerrar_tab_actual())
        self.root.bind('<Control-Tab>', lambda e: self.siguiente_tab())
        self.root.bind('<Control-Shift-Tab>', lambda e: self.anterior_tab())

        # --- 4. PANEL DE SALIDA INFERIOR (estilo VS Code) ---
        self._frame_output = tk.Frame(self.main_paned, bg="#181825")
        self.main_paned.add(self._frame_output, minsize=28)

        # Barra de títulos del panel (siempre visible, aunque el contenido esté oculto)
        panel_header = tk.Frame(self._frame_output, bg="#181825", height=28)
        panel_header.pack(side=tk.TOP, fill=tk.X)
        panel_header.pack_propagate(False)
        tk.Frame(self._frame_output, bg="#313244", height=1).pack(side=tk.TOP, fill=tk.X)

        # Notebook de salida
        self.notebook = ttk.Notebook(self._frame_output, style="Output.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_consola = tk.Frame(self.notebook, bg="#181825")
        self.consola = scrolledtext.ScrolledText(self.tab_consola, bg="#13131d", fg="#cdd6f4",
                                                  font=("Consolas", 11), insertbackground="#94e2d5",
                                                  selectbackground="#313244", borderwidth=0)
        self.consola.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_consola, text="  📟  Consola  ")

        self.tab_c = tk.Frame(self.notebook, bg="#181825")
        self.output_c = scrolledtext.ScrolledText(self.tab_c, bg="#13131d", fg="#89b4fa",
                                                   font=("Consolas", 11), borderwidth=0)
        self.output_c.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_c, text="  🔢  Bytecode  ")

        self.tab_tokens = tk.Frame(self.notebook, bg="#181825")
        self.texto_tokens = scrolledtext.ScrolledText(self.tab_tokens, bg="#13131d", fg="#a6e3a1",
                                                       font=("Consolas", 10), borderwidth=0)
        self.texto_tokens.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_tokens, text="  🔍  Léxico  ")

        self.tab_asm = tk.Frame(self.notebook, bg="#181825")
        self.output_asm = scrolledtext.ScrolledText(self.tab_asm, bg="#13131d", fg="#cba6f7",
                                                     font=("Consolas", 11), borderwidth=0)
        self.output_asm.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_asm, text="  📝  ASM  ")

        self.tab_tac = tk.Frame(self.notebook, bg="#181825")
        self.output_tac = scrolledtext.ScrolledText(self.tab_tac, bg="#13131d", fg="#74c7ec",
                                                     font=("Consolas", 11), borderwidth=0)
        self.output_tac.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_tac, text="  🔧  Intermedio  ")

        # Pestaña de Problemas (errores)
        self.tab_problemas = tk.Frame(self.notebook, bg="#181825")
        self.notebook.add(self.tab_problemas, text="  ⚠  Problemas  ")
        self.crear_panel_errores()

        # --- 5. BARRA DE ESTADO ---
        self.barra_estado = tk.Frame(self.root, bg="#181825", height=24)
        self.barra_estado.pack(side=tk.BOTTOM, fill=tk.X)

        # Segmento de lenguaje (acento púrpura)
        _seg_lang = tk.Frame(self.barra_estado, bg="#cba6f7")
        _seg_lang.pack(side=tk.LEFT, fill=tk.Y)
        self.label_tipo_archivo = tk.Label(_seg_lang, text=" ⬡  Python ", bg="#cba6f7", fg="#1e1e2e",
                                            font=("Segoe UI", 9, "bold"))
        self.label_tipo_archivo.pack(side=tk.LEFT, padx=2)

        self.label_linea_col = tk.Label(self.barra_estado, text="  Ln 1, Col 0", bg="#181825", fg="#a6adc8",
                                         font=("Segoe UI", 9), padx=4)
        self.label_linea_col.pack(side=tk.LEFT)

        self.label_total_lineas = tk.Label(self.barra_estado, text="| 1 línea", bg="#181825", fg="#585b70",
                                            font=("Segoe UI", 9), padx=2)
        self.label_total_lineas.pack(side=tk.LEFT)

        self.label_encoding = tk.Label(self.barra_estado, text="UTF-8", bg="#181825", fg="#6c7086",
                                        font=("Segoe UI", 9), padx=12)
        self.label_encoding.pack(side=tk.RIGHT)

        self.label_zoom = tk.Label(self.barra_estado, text="100%", bg="#181825", fg="#a6adc8",
                                    font=("Segoe UI", 9), padx=10)
        self.label_zoom.pack(side=tk.RIGHT)

        # Botón toggle del panel inferior (siempre visible en la barra de estado)
        self._panel_output_visible = True
        self._btn_toggle_panel = tk.Label(
            self.barra_estado, text="▽  Panel",
            bg="#181825", fg="#6c7086",
            font=("Segoe UI", 8), padx=10, cursor="hand2")
        self._btn_toggle_panel.pack(side=tk.RIGHT)
        self._btn_toggle_panel.bind("<Button-1>", lambda e: self.toggle_output_panel())
        self._btn_toggle_panel.bind("<Enter>", lambda e: self._btn_toggle_panel.config(fg="#a6adc8"))
        self._btn_toggle_panel.bind("<Leave>", lambda e: self._btn_toggle_panel.config(fg="#6c7086"))
        Tooltip(self._btn_toggle_panel, "Mostrar/ocultar panel inferior  Ctrl+J")
        self.root.bind('<Control-j>', lambda e: self.toggle_output_panel())
        self.root.bind('<Control-J>', lambda e: self.toggle_output_panel())


        # Actualizar titulo inicial
        self.actualizar_titulo()
        # Posición inicial del sash: editor 68% / panel 32%
        self.root.after(150, lambda: self.main_paned.sash_place(
            0, 0, int(self.root.winfo_height() * 0.68)))

    # --- MÉTODOS PARA GESTIÓN DE PESTAÑAS ---
    
    def get_tab_actual(self):
        """Retorna la pestaña del editor actualmente activa"""
        try:
            idx = self.editor_notebook.index(self.editor_notebook.select())
            if 0 <= idx < len(self.tabs_editoras):
                return self.tabs_editoras[idx]
        except:
            pass
        return None if not self.tabs_editoras else self.tabs_editoras[0]
    
    def crear_nueva_tab(self, ruta=None, contenido=""):
        """Crea una nueva pestaña del editor"""
        nueva_tab = EditorTab(self.editor_notebook, self, self.font_size)
        self.tabs_editoras.append(nueva_tab)
        
        # Determinar nombre de la pestaña
        if ruta:
            nueva_tab.ruta_actual = ruta
            nombre_tab = os.path.basename(ruta)
        else:
            nombre_tab = f"Sin título {len(self.tabs_editoras)}" if len(self.tabs_editoras) > 1 else "Sin título"
        
        # Agregar pestaña al notebook
        self.editor_notebook.add(nueva_tab.frame, text=nombre_tab)

        # Crear botón de pestaña en la barra personalizada
        self._crear_boton_tab(nueva_tab, nombre_tab)

        # Insertar contenido si existe
        if contenido:
            nueva_tab.texto_codigo.insert("1.0", contenido)
        
        # Seleccionar la nueva pestaña
        self.editor_notebook.select(nueva_tab.frame)
        
        # Actualizar visual
        self._actualizar_tab_visual()
        self.actualizar_titulo()
        self.actualizar_barra_estado_tab(nueva_tab)
        
        return nueva_tab
    
    def cerrar_tab_actual(self):
        """Cierra la pestaña actual (Ctrl+W)"""
        self.cerrar_tab(self.get_tab_actual())

    def cerrar_tab(self, tab):
        """Cierra la pestaña indicada (llamado por botón × o Ctrl+W)"""
        if not tab:
            return

        # Si solo queda una pestaña: limpiar en lugar de cerrar
        if len(self.tabs_editoras) == 1:
            if tab.archivo_modificado:
                respuesta = messagebox.askyesnocancel("¿Guardar cambios?",
                                                      "¿Desea guardar los cambios antes de cerrar?")
                if respuesta is None:
                    return
                elif respuesta:
                    self.guardar()
            tab.texto_codigo.delete("1.0", tk.END)
            tab.ruta_actual = None
            tab.archivo_modificado = False
            self.actualizar_nombre_tab(tab)
            self.actualizar_titulo()
            return

        # Hay múltiples pestañas — cerrar esta
        if tab.archivo_modificado:
            respuesta = messagebox.askyesnocancel("¿Guardar cambios?",
                                                  f"¿Desea guardar los cambios en {tab.get_nombre_para_tab()}?")
            if respuesta is None:
                return
            elif respuesta:
                self.guardar()

        try:
            idx = self.tabs_editoras.index(tab)
            self.editor_notebook.forget(idx)
            self.tabs_editoras.remove(tab)
            # Destruir el botón de la barra de pestañas
            if hasattr(tab, '_tab_btn_frame'):
                tab._tab_btn_frame.destroy()
            self.actualizar_titulo()
            nueva_tab = self.get_tab_actual()
            if nueva_tab:
                self._actualizar_tab_visual()
                self.actualizar_barra_estado_tab(nueva_tab)
        except:
            pass
    
    def siguiente_tab(self):
        """Cambia a la siguiente pestaña (Ctrl+Tab)"""
        if len(self.tabs_editoras) <= 1:
            return
        
        try:
            idx_actual = self.editor_notebook.index(self.editor_notebook.select())
            idx_siguiente = (idx_actual + 1) % len(self.tabs_editoras)
            self.editor_notebook.select(idx_siguiente)
        except:
            pass
    
    def anterior_tab(self):
        """Cambia a la pestaña anterior (Ctrl+Shift+Tab)"""
        if len(self.tabs_editoras) <= 1:
            return
        
        try:
            idx_actual = self.editor_notebook.index(self.editor_notebook.select())
            idx_anterior = (idx_actual - 1) % len(self.tabs_editoras)
            self.editor_notebook.select(idx_anterior)
        except:
            pass
    
    def on_tab_changed(self, event):
        """Evento cuando cambia la pestaña activa"""
        tab_actual = self.get_tab_actual()
        if tab_actual:
            self._actualizar_tab_visual()
            self.actualizar_titulo()
            self.actualizar_barra_estado_tab(tab_actual)
            self.actualizar_panel_errores()  # Actualizar panel de errores al cambiar de tab
    
    def actualizar_nombre_tab(self, tab):
        """Actualiza el nombre mostrado en la pestaña"""
        try:
            idx = self.tabs_editoras.index(tab)
            nombre = tab.get_nombre_para_tab()
            self.editor_notebook.tab(idx, text=nombre)
            # Actualizar también el botón de la barra personalizada
            if hasattr(tab, '_tab_label'):
                tab._tab_label.config(text=nombre)
        except:
            pass

    # --- MÉTODOS DE BARRA DE PESTAÑAS PERSONALIZADA ---

    def _crear_boton_tab(self, tab, nombre):
        """Crea el botón visual de la pestaña en la barra personalizada"""
        btn_frame = tk.Frame(self.tab_bar, bg="#181825", padx=0, pady=0)
        btn_frame.pack(side=tk.LEFT, padx=(0, 1), pady=(0, 0))

        lbl = tk.Button(btn_frame, text=nombre, bg="#181825", fg="#585b70",
                        border=0, padx=12, pady=7,
                        activebackground="#252530", activeforeground="#cba6f7",
                        font=("Segoe UI", 9), cursor="hand2",
                        command=lambda t=tab: self._seleccionar_tab(t))
        lbl.pack(side=tk.LEFT)

        close = tk.Button(btn_frame, text="×", bg="#181825", fg="#45475a",
                          border=0, padx=5, pady=7,
                          activebackground="#c42b1c", activeforeground="white",
                          font=("Segoe UI", 10), cursor="hand2",
                          command=lambda t=tab: self.cerrar_tab(t))
        close.pack(side=tk.LEFT)

        # Hover
        def on_enter(e, f=btn_frame, l=lbl, c=close):
            tab_actual = self.get_tab_actual()
            bg = "#1e1e2e" if tab is tab_actual else "#25253a"
            f.config(bg=bg); l.config(bg=bg); c.config(bg=bg, fg="#a6adc8")
        def on_leave(e, t=tab):
            self._actualizar_tab_visual()

        for w in (btn_frame, lbl, close):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

        tab._tab_btn_frame = btn_frame
        tab._tab_label = lbl
        tab._tab_close = close

    def _seleccionar_tab(self, tab):
        """Selecciona la pestaña indicada y actualiza el visual"""
        self.editor_notebook.select(tab.frame)
        self._actualizar_tab_visual()
        tab.texto_codigo.focus_set()

    def _actualizar_tab_visual(self):
        """Actualiza el aspecto activo/inactivo de todos los botones de pestaña"""
        tab_actual = self.get_tab_actual()
        for t in self.tabs_editoras:
            if not hasattr(t, '_tab_btn_frame'):
                continue
            if t is tab_actual:
                t._tab_btn_frame.config(bg="#1e1e2e",
                                        highlightbackground="#cba6f7", highlightthickness=1)
                t._tab_label.config(bg="#1e1e2e", fg="#cba6f7",
                                    font=("Segoe UI", 9, "bold"))
                t._tab_close.config(bg="#1e1e2e", fg="#6c7086")
            else:
                t._tab_btn_frame.config(bg="#181825", highlightthickness=0)
                t._tab_label.config(bg="#181825", fg="#585b70",
                                    font=("Segoe UI", 9))
                t._tab_close.config(bg="#181825", fg="#313244")

    # --- MÉTODOS PARA PANEL DE ERRORES Y VALIDACIÓN EN TIEMPO REAL ---
    
    def crear_panel_errores(self):
        """Crea el panel de problemas dentro de la pestaña del notebook inferior."""
        # Lista con scroll directamente (sin header separado, el tab ya tiene título)
        scrollbar_errores = tk.Scrollbar(self.tab_problemas, orient="vertical")
        scrollbar_errores.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas_errores = tk.Canvas(self.tab_problemas, bg="#13131d", highlightthickness=0,
                                        yscrollcommand=scrollbar_errores.set)
        self.canvas_errores.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_errores.config(command=self.canvas_errores.yview)

        self.frame_lista_errores = tk.Frame(self.canvas_errores, bg="#13131d")
        self.canvas_errores.create_window((0, 0), window=self.frame_lista_errores, anchor="nw")
        self.frame_lista_errores.bind(
            "<Configure>",
            lambda e: self.canvas_errores.configure(scrollregion=self.canvas_errores.bbox("all")))
    
    def validar_codigo_en_tiempo_real(self):
        """Valida el código después de un delay (750ms)"""
        # Cancelar validación pendiente
        if self.validation_timer:
            self.root.after_cancel(self.validation_timer)
        
        # Programar nueva validación
        self.validation_timer = self.root.after(750, self.ejecutar_validacion)
    
    def ejecutar_validacion(self):
        """Ejecuta la validación del código actual"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        codigo = tab_actual.texto_codigo.get("1.0", tk.END).strip()
        if not codigo:
            tab_actual.errores = []
            self.limpiar_errores_visuales(tab_actual)
            self.actualizar_panel_errores()
            return
        
        errores = []
        
        # Validar con ast.parse (captura indentación Y sintaxis)
        try:
            import ast as _ast
            _ast.parse(codigo)
        except IndentationError as e:
            errores.append({
                'linea': e.lineno or 1,
                'tipo': 'Indentación',
                'mensaje': e.msg
            })
        except SyntaxError as e:
            errores.append({
                'linea': e.lineno or 1,
                'tipo': 'Sintaxis',
                'mensaje': e.msg
            })
        except Exception as e:
            errores.append({
                'linea': 1,
                'tipo': 'Error',
                'mensaje': str(e)
            })
        
        # Guardar errores en la tab
        tab_actual.errores = errores
        
        # Actualizar visualización
        self.marcar_errores_en_editor(tab_actual)
        self.actualizar_panel_errores()
    
    def extraer_numero_linea(self, mensaje_error):
        """Intenta extraer número de línea de un mensaje de error"""
        import re
        match = re.search(r'l[ií]nea\s+(\d+)|line\s+(\d+)|fila\s+(\d+)', mensaje_error, re.IGNORECASE)
        if match:
            for group in match.groups():
                if group:
                    return int(group)
        return None
    
    def limpiar_errores_visuales(self, tab):
        """Limpia los marcadores visuales de errores en el editor"""
        tab.texto_codigo.tag_remove("error_line", "1.0", tk.END)
        tab.texto_codigo.tag_remove("error", "1.0", tk.END)
    
    def marcar_errores_en_editor(self, tab):
        """Marca visualmente los errores en el editor"""
        # Limpiar marcas previas
        self.limpiar_errores_visuales(tab)
        
        # Marcar cada error
        for error in tab.errores:
            linea = error['linea']
            try:
                # Marcar toda la línea con fondo
                tab.texto_codigo.tag_add("error_line", f"{linea}.0", f"{linea}.end")
                
                # Subrayar el contenido de la línea
                tab.texto_codigo.tag_add("error", f"{linea}.0", f"{linea}.end")
            except:
                pass  # Línea no existe
    
    def actualizar_panel_errores(self):
        """Actualiza la pestaña Problemas con los errores del archivo activo."""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return

        # Limpiar lista
        for widget in self.frame_lista_errores.winfo_children():
            widget.destroy()

        errores = tab_actual.errores
        num_errores = len(errores)

        # Actualizar título del tab con badge de conteo
        if num_errores == 0:
            self.notebook.tab(self.tab_problemas, text="  ⚠  Problemas  ")
        elif num_errores == 1:
            self.notebook.tab(self.tab_problemas, text="  ⚠  Problemas · 1  ")
        else:
            self.notebook.tab(self.tab_problemas, text=f"  ⚠  Problemas · {num_errores}  ")

        # Mostrar cada error
        for i, error in enumerate(errores):
            self.crear_item_error(i, error, tab_actual)

        # Auto-cambiar al tab si hay errores nuevos
        if num_errores > 0:
            try:
                self.notebook.select(self.tab_problemas)
            except Exception:
                pass
    
    def crear_item_error(self, index, error, tab):
        """Crea un ítem de error en una sola línea horizontal (estilo VS Code)."""
        tipo_color = {
            'Sintaxis':    '#f38ba8',
            'Léxico':      '#fab387',
            'Indentación': '#f9e2af',
            'Parser':      '#f38ba8'
        }
        color = tipo_color.get(error['tipo'], '#f38ba8')

        # Fondo alternado par/impar
        bg_row = "#181825" if index % 2 == 0 else "#13131d"

        row = tk.Frame(self.frame_lista_errores, bg=bg_row, cursor="hand2")
        row.pack(fill=tk.X, pady=0)

        # Nro de orden
        num_lbl = tk.Label(row, text=f" {index + 1} ", bg=bg_row, fg="#45475a",
                           font=("Consolas", 9), width=3, anchor="e")
        num_lbl.pack(side=tk.LEFT)

        # Icono de error
        ic_lbl = tk.Label(row, text="●", bg=bg_row, fg=color,
                          font=("Segoe UI", 9), padx=4)
        ic_lbl.pack(side=tk.LEFT)

        # Tipo
        tipo_lbl = tk.Label(row, text=error['tipo'], bg=bg_row, fg=color,
                            font=("Segoe UI", 9, "bold"), padx=2)
        tipo_lbl.pack(side=tk.LEFT)

        # Número de línea clickeable
        linea = error['linea']
        linea_lbl = tk.Label(row, text=f"L.{linea}", bg=bg_row, fg="#6c7086",
                             font=("Consolas", 9), padx=6, cursor="hand2")
        linea_lbl.pack(side=tk.LEFT)

        # Separador
        tk.Label(row, text="│", bg=bg_row, fg="#313244",
                 font=("Consolas", 9)).pack(side=tk.LEFT)

        # Mensaje (rellena el resto)
        msg_lbl = tk.Label(row, text=error['mensaje'], bg=bg_row, fg="#a6adc8",
                           font=("Consolas", 9), anchor="w", padx=6)
        msg_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Hover + click en todos los widgets
        all_widgets = [row, num_lbl, ic_lbl, tipo_lbl, linea_lbl, msg_lbl]
        bg_hover = "#252530"
        for w in all_widgets:
            w.bind("<Button-1>", lambda e, l=linea: self.ir_a_linea_error(l))
            w.bind("<Enter>", lambda e, r=row, ws=all_widgets, bh=bg_hover:
                   [x.config(bg=bh) for x in ws])
            w.bind("<Leave>", lambda e, r=row, ws=all_widgets, bn=bg_row:
                   [x.config(bg=bn) for x in ws])
    
    def ir_a_linea_error(self, linea):
        """Navega a la línea del error en el editor"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            # Mover cursor a la línea
            tab_actual.texto_codigo.mark_set(tk.INSERT, f"{linea}.0")
            tab_actual.texto_codigo.see(f"{linea}.0")
            
            # Dar foco al editor
            tab_actual.texto_codigo.focus_set()
            
            # Resaltar temporalmente la línea
            tab_actual.texto_codigo.tag_remove("highlight", "1.0", tk.END)
            tab_actual.texto_codigo.tag_add("highlight", f"{linea}.0", f"{linea}.end")
            tab_actual.texto_codigo.tag_config("highlight", background="#4a4a00")
            
            # Quitar resaltado después de 1.5 segundos
            self.root.after(1500, lambda: tab_actual.texto_codigo.tag_remove("highlight", "1.0", tk.END))
        except:
            pass

    # --- MÉTODOS PARA EXPLORADOR DE ARCHIVOS ---
    
    def crear_explorador_archivos(self):
        """Crea el panel del explorador de archivos (sidebar)"""
        # Header
        header_explorador = tk.Frame(self.panel_explorador, bg="#181825", height=36)
        header_explorador.pack(side=tk.TOP, fill=tk.X)
        header_explorador.pack_propagate(False)

        tk.Label(header_explorador, text="  EXPLORADOR", bg="#181825", fg="#6c7086",
                 font=("Segoe UI", 9, "bold"), padx=6, anchor="w").pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Botón para abrir carpeta
        btn_abrir_carpeta = tk.Button(header_explorador, text="📂", command=self.abrir_carpeta_proyecto,
                                       bg="#181825", fg="#a6adc8", relief="flat", font=("Segoe UI", 11),
                                       cursor="hand2", borderwidth=0,
                                       activebackground="#313244", activeforeground="#cba6f7")
        btn_abrir_carpeta.pack(side=tk.RIGHT, padx=5)

        # Botón para refrescar
        btn_refrescar = tk.Button(header_explorador, text="🔄", command=self.refrescar_explorador,
                                   bg="#181825", fg="#a6adc8", relief="flat", font=("Segoe UI", 11),
                                   cursor="hand2", borderwidth=0,
                                   activebackground="#313244", activeforeground="#cba6f7")
        btn_refrescar.pack(side=tk.RIGHT, padx=2)

        # Frame para el árbol de archivos
        tree_frame = tk.Frame(self.panel_explorador, bg="#1e1e2e")
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Scrollbars
        scrollbar_y = tk.Scrollbar(tree_frame, orient="vertical")
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = tk.Scrollbar(tree_frame, orient="horizontal")
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview para estructura de archivos
        style = ttk.Style()
        style.configure("Treeview", background="#1e1e2e", foreground="#cdd6f4",
                       fieldbackground="#1e1e2e", borderwidth=0, rowheight=22)
        style.configure("Treeview.Heading", background="#181825", foreground="#6c7086",
                       relief="flat", font=("Segoe UI", 9))
        style.map("Treeview", background=[("selected", "#313244")],
                  foreground=[("selected", "#cba6f7")])
        
        self.tree_archivos = ttk.Treeview(tree_frame, yscrollcommand=scrollbar_y.set,
                                          xscrollcommand=scrollbar_x.set, selectmode="browse")
        self.tree_archivos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.tree_archivos.yview)
        scrollbar_x.config(command=self.tree_archivos.xview)
        
        # Ocultar columna #0 header
        self.tree_archivos.heading("#0", text="Archivos", anchor="w")
        
        # Bindings
        self.tree_archivos.bind("<Double-Button-1>", self.on_tree_double_click)
        self.tree_archivos.bind("<Button-3>", self.on_tree_right_click)
        
        # Mensaje inicial
        self.tree_archivos.insert("", "end", text="Abrir carpeta para comenzar...", 
                                  values=(), tags=("info",))
        self.tree_archivos.tag_configure("info", foreground="#666666")
    
    def abrir_carpeta_proyecto(self):
        """Abre diálogo para seleccionar carpeta del proyecto"""
        from tkinter import filedialog
        
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta del proyecto")
        if carpeta:
            self.carpeta_proyecto = carpeta
            self.cargar_estructura_carpeta()
    
    def cargar_estructura_carpeta(self):
        """Carga la estructura de archivos de la carpeta del proyecto"""
        if not self.carpeta_proyecto:
            return
        
        # Limpiar árbol actual
        for item in self.tree_archivos.get_children():
            self.tree_archivos.delete(item)
        
        # Obtener nombre de la carpeta
        nombre_carpeta = os.path.basename(self.carpeta_proyecto)
        
        # Insertar nodo raíz
        root_node = self.tree_archivos.insert("", "end", text=f"📁 {nombre_carpeta}",
                                               values=(self.carpeta_proyecto,), open=True)
        
        # Cargar contenido recursivamente
        try:
            self.agregar_nodos_recursivo(root_node, self.carpeta_proyecto)
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar carpeta: {e}")
    
    def agregar_nodos_recursivo(self, parent_node, ruta):
        """Agrega nodos al árbol recursivamente"""
        try:
            items = os.listdir(ruta)
            
            # Separar carpetas y archivos
            carpetas = []
            archivos = []
            
            for item in items:
                item_path = os.path.join(ruta, item)
                if os.path.isdir(item_path):
                    # Ignorar carpetas ocultas y comunes
                    if not item.startswith('.') and item not in ['__pycache__', 'node_modules', '.git']:
                        carpetas.append(item)
                else:
                    archivos.append(item)
            
            # Ordenar alfabéticamente
            carpetas.sort()
            archivos.sort()
            
            # Agregar carpetas primero
            for carpeta in carpetas:
                carpeta_path = os.path.join(ruta, carpeta)
                node = self.tree_archivos.insert(parent_node, "end", text=f"📁 {carpeta}",
                                                 values=(carpeta_path,))
                # Recursivamente agregar contenido de subcarpetas
                self.agregar_nodos_recursivo(node, carpeta_path)
            
            # Agregar archivos
            for archivo in archivos:
                archivo_path = os.path.join(ruta, archivo)
                icono = self.obtener_icono_archivo(archivo)
                self.tree_archivos.insert(parent_node, "end", text=f"{icono} {archivo}",
                                         values=(archivo_path,))
        except PermissionError:
            pass  # Ignorar carpetas sin permisos
    
    def obtener_icono_archivo(self, nombre_archivo):
        """Retorna un icono según la extensión del archivo"""
        ext = os.path.splitext(nombre_archivo)[1].lower()
        iconos = {
            '.go': '🟦',
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.html': '🌐',
            '.css': '🎨',
            '.json': '📋',
            '.md': '📝',
            '.txt': '📄',
            '.c': '⚙️',
            '.cpp': '⚙️',
            '.h': '📌',
            '.asm': '🔧',
        }
        return iconos.get(ext, '📄')
    
    def on_tree_double_click(self, event):
        """Maneja doble click en el árbol de archivos"""
        selection = self.tree_archivos.selection()
        if not selection:
            return
        
        item = selection[0]
        valores = self.tree_archivos.item(item, "values")
        
        if not valores:
            return
        
        ruta = valores[0]
        
        # Si es un archivo, abrirlo
        if os.path.isfile(ruta):
            self.abrir_archivo_desde_explorador(ruta)
    
    def abrir_archivo_desde_explorador(self, ruta):
        """Abre un archivo desde el explorador en una nueva tab"""
        # Verificar si ya está abierto
        for tab in self.tabs_editoras:
            if tab.ruta_actual == ruta:
                # Ya está abierto, seleccionar esa tab
                idx = self.tabs_editoras.index(tab)
                self.editor_notebook.select(idx)
                return
        
        # Abrir archivo
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Crear nueva tab o usar la actual si está vacía
            tab_actual = self.get_tab_actual()
            if tab_actual and not tab_actual.ruta_actual and not tab_actual.archivo_modificado:
                # Usar tab actual vacía
                tab_actual.texto_codigo.delete("1.0", tk.END)
                tab_actual.texto_codigo.insert("1.0", contenido)
                tab_actual.ruta_actual = ruta
                tab_actual.archivo_modificado = False
            else:
                # Crear nueva tab
                nueva_tab = self.crear_nueva_tab()
                nueva_tab.texto_codigo.delete("1.0", tk.END)
                nueva_tab.texto_codigo.insert("1.0", contenido)
                nueva_tab.ruta_actual = ruta
                nueva_tab.archivo_modificado = False
            
            self.actualizar_nombre_tab(tab_actual if tab_actual and tab_actual.ruta_actual == ruta else self.get_tab_actual())
            self.actualizar_titulo()
            self.resaltar_sintaxis()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")
    
    def on_tree_right_click(self, event):
        """Muestra menú contextual al hacer click derecho"""
        # Seleccionar item bajo el cursor
        item = self.tree_archivos.identify_row(event.y)
        if item:
            self.tree_archivos.selection_set(item)
            
            # Crear menú contextual
            menu = tk.Menu(self.root, tearoff=0, bg="#2d2d2d", fg="white")
            
            valores = self.tree_archivos.item(item, "values")
            es_archivo = False
            
            if valores:
                ruta = valores[0]
                es_archivo = os.path.isfile(ruta)
            
            # Opciones del menú
            menu.add_command(label="📄 Nuevo Archivo", command=self.crear_archivo)
            menu.add_command(label="📁 Nueva Carpeta", command=self.crear_carpeta)
            menu.add_separator()
            
            if valores:
                menu.add_command(label="✏️ Renombrar", command=self.renombrar_item)
                menu.add_command(label="🗑️ Eliminar", command=self.eliminar_item)
                menu.add_separator()
            
            menu.add_command(label="🔄 Refrescar", command=self.refrescar_explorador)
            
            # Mostrar menú
            menu.post(event.x_root, event.y_root)
    
    def crear_archivo(self):
        """Crea un nuevo archivo en la carpeta seleccionada"""
        selection = self.tree_archivos.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Selecciona una carpeta primero")
            return
        
        item = selection[0]
        valores = self.tree_archivos.item(item, "values")
        
        if not valores:
            return
        
        ruta = valores[0]
        
        # Si es un archivo, usar su carpeta padre
        if os.path.isfile(ruta):
            ruta = os.path.dirname(ruta)
        
        # Pedir nombre del archivo
        from tkinter import simpledialog
        nombre = simpledialog.askstring("Nuevo Archivo", "Nombre del archivo:")
        
        if nombre:
            archivo_path = os.path.join(ruta, nombre)
            try:
                with open(archivo_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.refrescar_explorador()
                messagebox.showinfo("Éxito", f"Archivo creado: {nombre}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear el archivo:\n{e}")
    
    def crear_carpeta(self):
        """Crea una nueva carpeta en la carpeta seleccionada"""
        selection = self.tree_archivos.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Selecciona una carpeta primero")
            return
        
        item = selection[0]
        valores = self.tree_archivos.item(item, "values")
        
        if not valores:
            return
        
        ruta = valores[0]
        
        # Si es un archivo, usar su carpeta padre
        if os.path.isfile(ruta):
            ruta = os.path.dirname(ruta)
        
        # Pedir nombre de la carpeta
        from tkinter import simpledialog
        nombre = simpledialog.askstring("Nueva Carpeta", "Nombre de la carpeta:")
        
        if nombre:
            carpeta_path = os.path.join(ruta, nombre)
            try:
                os.makedirs(carpeta_path, exist_ok=True)
                self.refrescar_explorador()
                messagebox.showinfo("Éxito", f"Carpeta creada: {nombre}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta:\n{e}")
    
    def eliminar_item(self):
        """Elimina el archivo o carpeta seleccionada"""
        selection = self.tree_archivos.selection()
        if not selection:
            return
        
        item = selection[0]
        valores = self.tree_archivos.item(item, "values")
        
        if not valores:
            return
        
        ruta = valores[0]
        nombre = os.path.basename(ruta)
        
        # Confirmar eliminación
        if os.path.isfile(ruta):
            respuesta = messagebox.askyesno("Confirmar", f"¿Eliminar el archivo '{nombre}'?")
        else:
            respuesta = messagebox.askyesno("Confirmar", f"¿Eliminar la carpeta '{nombre}' y todo su contenido?")
        
        if respuesta:
            try:
                if os.path.isfile(ruta):
                    os.remove(ruta)
                else:
                    import shutil
                    shutil.rmtree(ruta)
                
                self.refrescar_explorador()
                messagebox.showinfo("Éxito", f"Eliminado: {nombre}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")
    
    def renombrar_item(self):
        """Renombra el archivo o carpeta seleccionada"""
        selection = self.tree_archivos.selection()
        if not selection:
            return
        
        item = selection[0]
        valores = self.tree_archivos.item(item, "values")
        
        if not valores:
            return
        
        ruta = valores[0]
        nombre_actual = os.path.basename(ruta)
        
        # Pedir nuevo nombre
        from tkinter import simpledialog
        nuevo_nombre = simpledialog.askstring("Renombrar", "Nuevo nombre:", initialvalue=nombre_actual)
        
        if nuevo_nombre and nuevo_nombre != nombre_actual:
            nueva_ruta = os.path.join(os.path.dirname(ruta), nuevo_nombre)
            try:
                os.rename(ruta, nueva_ruta)
                self.refrescar_explorador()
                messagebox.showinfo("Éxito", f"Renombrado a: {nuevo_nombre}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo renombrar:\n{e}")
    
    def refrescar_explorador(self):
        """Refresca el árbol de archivos"""
        if self.carpeta_proyecto:
            self.cargar_estructura_carpeta()

    # --- MÉTODOS PARA AUTOCOMPLETADO (IntelliSense) ---
    
    def manejar_autocompletado(self, event):
        """Maneja el autocompletado mientras se escribe"""
        # Ignorar teclas especiales que no insertan texto
        teclas_ignorar = ['Shift_L', 'Shift_R', 'Control_L', 'Control_R', 
                          'Alt_L', 'Alt_R', 'Caps_Lock', 'Tab', 'Escape',
                          'Up', 'Down', 'Left', 'Right', 'Home', 'End',
                          'Prior', 'Next', 'F1', 'F2', 'F3', 'F4', 'F5',
                          'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']
        
        if event.keysym in teclas_ignorar:
            return
        
        # Si se presionó Escape, ocultar autocompletado
        if event.keysym == 'Escape':
            self.ocultar_autocompletado()
            return
        
        # Si hay autocompletado activo y se presionan flechas o Enter
        if self.autocomplete_activo:
            if event.keysym == 'Down':
                self.navegar_autocompletado(1)
                return "break"
            elif event.keysym == 'Up':
                self.navegar_autocompletado(-1)
                return "break"
            elif event.keysym in ['Return', 'Tab']:
                self.completar_palabra()
                return "break"
        
        # Obtener palabra actual bajo el cursor
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            pos = tab_actual.texto_codigo.index(tk.INSERT)
            linea_num, col_num = map(int, pos.split('.'))
            linea_texto = tab_actual.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")
            
            # Encontrar la palabra que se está escribiendo
            inicio = col_num
            while inicio > 0 and (linea_texto[inicio-1].isalnum() or linea_texto[inicio-1] in ['_', '.']):
                inicio -= 1
            
            self.palabra_actual = linea_texto[inicio:col_num]
            
            # Si la palabra tiene al menos 2 caracteres, mostrar sugerencias
            if len(self.palabra_actual) >= 2:
                self.mostrar_autocompletado()
            else:
                self.ocultar_autocompletado()
        except:
            self.ocultar_autocompletado()
    
    def mostrar_autocompletado(self):
        """Muestra la ventana de autocompletado con sugerencias"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        # Obtener todas las sugerencias posibles
        sugerencias = self.obtener_sugerencias()
        
        # Filtrar sugerencias que coincidan con la palabra actual
        palabra_lower = self.palabra_actual.lower()
        sugerencias_filtradas = [s for s in sugerencias if s.lower().startswith(palabra_lower)]
        
        # Si no hay sugerencias, ocultar
        if not sugerencias_filtradas:
            self.ocultar_autocompletado()
            return
        
        self.sugerencias_actuales = sugerencias_filtradas
        
        # Crear ventana si no existe
        if not self.autocomplete_window:
            self.crear_ventana_autocompletado()
        
        # Actualizar contenido del listbox
        self.autocomplete_listbox.delete(0, tk.END)
        for sugerencia in sugerencias_filtradas[:15]:  # Máximo 15 sugerencias
            self.autocomplete_listbox.insert(tk.END, sugerencia)
        
        # Seleccionar la primera
        if self.autocomplete_listbox.size() > 0:
            self.autocomplete_listbox.selection_set(0)
            self.autocomplete_listbox.activate(0)
        
        # Posicionar ventana bajo el cursor
        try:
            # Obtener posición del cursor en la pantalla
            bbox = tab_actual.texto_codigo.bbox(tk.INSERT)
            if bbox:
                x = tab_actual.texto_codigo.winfo_rootx() + bbox[0]
                y = tab_actual.texto_codigo.winfo_rooty() + bbox[1] + bbox[3]
                
                self.autocomplete_window.geometry(f"+{x}+{y}")
                self.autocomplete_window.deiconify()
                self.autocomplete_activo = True
        except:
            pass
    
    def crear_ventana_autocompletado(self):
        """Crea la ventana flotante de autocompletado"""
        self.autocomplete_window = tk.Toplevel(self.root)
        self.autocomplete_window.withdraw()  # Ocultar inicialmente
        self.autocomplete_window.overrideredirect(True)  # Sin bordes
        self.autocomplete_window.attributes('-topmost', True)
        
        # Frame principal
        frame = tk.Frame(self.autocomplete_window, bg="#2d2d2d", relief="solid", bd=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(frame, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox con sugerencias
        self.autocomplete_listbox = tk.Listbox(frame, height=10, width=30,
                                                bg="#2d2d2d", fg="#cccccc",
                                                selectbackground="#094771",
                                                selectforeground="#ffffff",
                                                font=("Consolas", 10),
                                                borderwidth=0,
                                                yscrollcommand=scrollbar.set,
                                                activestyle="none")
        self.autocomplete_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.autocomplete_listbox.yview)
        
        # Binding para doble click
        self.autocomplete_listbox.bind("<Double-Button-1>", lambda e: self.completar_palabra())
    
    def ocultar_autocompletado(self):
        """Oculta la ventana de autocompletado"""
        if self.autocomplete_window:
            self.autocomplete_window.withdraw()
        self.autocomplete_activo = False
        self.sugerencias_actuales = []
    
    def navegar_autocompletado(self, direccion):
        """Navega por las sugerencias con flechas arriba/abajo"""
        if not self.autocomplete_listbox or self.autocomplete_listbox.size() == 0:
            return
        
        seleccion_actual = self.autocomplete_listbox.curselection()
        if not seleccion_actual:
            nuevo_indice = 0
        else:
            nuevo_indice = seleccion_actual[0] + direccion
        
        # Mantener dentro de límites
        if nuevo_indice < 0:
            nuevo_indice = self.autocomplete_listbox.size() - 1
        elif nuevo_indice >= self.autocomplete_listbox.size():
            nuevo_indice = 0
        
        self.autocomplete_listbox.selection_clear(0, tk.END)
        self.autocomplete_listbox.selection_set(nuevo_indice)
        self.autocomplete_listbox.activate(nuevo_indice)
        self.autocomplete_listbox.see(nuevo_indice)
    
    def completar_palabra(self):
        """Completa la palabra con la sugerencia seleccionada"""
        if not self.autocomplete_listbox or self.autocomplete_listbox.size() == 0:
            return
        
        seleccion = self.autocomplete_listbox.curselection()
        if not seleccion:
            return
        
        sugerencia = self.autocomplete_listbox.get(seleccion[0])
        
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            # Obtener posición actual
            pos = tab_actual.texto_codigo.index(tk.INSERT)
            linea_num, col_num = map(int, pos.split('.'))
            
            # Encontrar inicio de la palabra
            linea_texto = tab_actual.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")
            inicio = col_num
            while inicio > 0 and (linea_texto[inicio-1].isalnum() or linea_texto[inicio-1] in ['_', '.']):
                inicio -= 1
            
            # Eliminar la palabra parcial
            tab_actual.texto_codigo.delete(f"{linea_num}.{inicio}", f"{linea_num}.{col_num}")
            
            # Insertar la sugerencia completa
            tab_actual.texto_codigo.insert(f"{linea_num}.{inicio}", sugerencia)
            
            # Ocultar autocompletado
            self.ocultar_autocompletado()
        except:
            pass
    
    def obtener_sugerencias(self):
        """Obtiene lista completa de sugerencias posibles (Python)"""
        sugerencias = list(self.palabras_clave)
        
        tab_actual = self.get_tab_actual()
        if tab_actual:
            codigo = tab_actual.texto_codigo.get("1.0", tk.END)
            import re
            
            # def nombre(
            funciones = re.findall(r'\bdef\s+(\w+)\s*\(', codigo)
            sugerencias.extend(funciones)
            
            # class Nombre
            clases = re.findall(r'\bclass\s+(\w+)', codigo)
            sugerencias.extend(clases)
            
            # nombre = valor (asignaciones de nivel superior o local)
            variables = re.findall(r'^(\w+)\s*=', codigo, re.MULTILINE)
            sugerencias.extend([v for v in variables if v not in ('True', 'False', 'None')])
            
            # Parámetros de funciones
            params_raw = re.findall(r'\bdef\s+\w+\s*\(([^)]*)\)', codigo)
            for params in params_raw:
                for param in params.split(','):
                    p = param.strip().split('=')[0].strip().split(':')[0].strip()
                    if p and p not in ('self', 'cls', ''):
                        sugerencias.append(p)
        
        sugerencias = list(set(sugerencias))
        sugerencias.sort()
        return sugerencias
    
    def activar_autocompletado_manual(self):
        """Activa el autocompletado manualmente con Ctrl+Space"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            # Obtener palabra actual bajo el cursor
            pos = tab_actual.texto_codigo.index(tk.INSERT)
            linea_num, col_num = map(int, pos.split('.'))
            linea_texto = tab_actual.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")
            
            # Encontrar la palabra que se está escribiendo
            inicio = col_num
            while inicio > 0 and (linea_texto[inicio-1].isalnum() or linea_texto[inicio-1] in ['_', '.']):
                inicio -= 1
            
            self.palabra_actual = linea_texto[inicio:col_num]
            
            # Mostrar sugerencias sin requisito mínimo de caracteres
            if len(self.palabra_actual) >= 1:
                self.mostrar_autocompletado()
            else:
                # Si no hay palabra, mostrar todas las sugerencias
                self.palabra_actual = ""
                self.mostrar_autocompletado()
        except:
            pass
    
    # --- GO TO DEFINITION Y NAVEGACIÓN ---
    
    def ir_a_definicion(self):
        """Navega a la definición de un símbolo (F12)"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            # Guardar posición actual en historial
            pos_actual = tab_actual.texto_codigo.index(tk.INSERT)
            self.guardar_posicion_historial(pos_actual)
            
            # Obtener palabra bajo el cursor
            pos = tab_actual.texto_codigo.index(tk.INSERT)
            linea_num, col_num = map(int, pos.split('.'))
            linea_texto = tab_actual.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")
            
            # Encontrar límites de la palabra
            inicio = col_num
            while inicio > 0 and (linea_texto[inicio-1].isalnum() or linea_texto[inicio-1] == '_'):
                inicio -= 1
            
            fin = col_num
            while fin < len(linea_texto) and (linea_texto[fin].isalnum() or linea_texto[fin] == '_'):
                fin += 1
            
            simbolo = linea_texto[inicio:fin]
            
            if not simbolo:
                return
            
            # Buscar definición en el código (Python: def y class)
            codigo = tab_actual.texto_codigo.get("1.0", tk.END)
            lineas = codigo.split('\n')
            
            import re
            
            # Patrones Python
            patron_def   = rf'\bdef\s+{re.escape(simbolo)}\s*\('
            patron_class = rf'\bclass\s+{re.escape(simbolo)}\b'
            patron_var   = rf'^{re.escape(simbolo)}\s*='
            patron_param = rf'def\s+\w+\s*\([^)]*\b{re.escape(simbolo)}\b'
            
            for i, linea in enumerate(lineas):
                if (re.search(patron_def, linea) or
                    re.search(patron_class, linea) or
                    re.search(patron_var, linea) or
                    re.search(patron_param, linea)):
                    
                    if i + 1 == linea_num:
                        continue
                    
                    tab_actual.texto_codigo.mark_set(tk.INSERT, f"{i+1}.0")
                    tab_actual.texto_codigo.see(f"{i+1}.0")
                    
                    tab_actual.texto_codigo.tag_remove("definicion_highlight", "1.0", tk.END)
                    tab_actual.texto_codigo.tag_add("definicion_highlight", f"{i+1}.0", f"{i+1}.end")
                    tab_actual.texto_codigo.tag_config("definicion_highlight", background="#FFD700", foreground="#000")
                    
                    self.root.after(1000, lambda: tab_actual.texto_codigo.tag_remove("definicion_highlight", "1.0", tk.END))
                    self.actualizar_status_bar()
                    break
            else:
                messagebox.showinfo("Go to Definition", f"No se encontró la definición de '{simbolo}'")
        except Exception as e:
            print(f"Error en ir_a_definicion: {e}")
    
    def guardar_posicion_historial(self, posicion):
        """Guarda una posición en el historial de navegación"""
        # Si estamos en medio del historial, eliminar posiciones futuras
        if self.indice_historial < len(self.historial_navegacion) - 1:
            self.historial_navegacion = self.historial_navegacion[:self.indice_historial + 1]
        
        # Agregar nueva posición
        self.historial_navegacion.append(posicion)
        self.indice_historial = len(self.historial_navegacion) - 1
        
        # Limitar tamaño del historial
        if len(self.historial_navegacion) > 50:
            self.historial_navegacion.pop(0)
            self.indice_historial -= 1
    
    # --- REFACTORING: RENOMBRAR SÍMBOLO ---
    
    def renombrar_simbolo(self):
        """Renombra un símbolo en todo el archivo (F2)"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            # Obtener palabra bajo el cursor
            pos = tab_actual.texto_codigo.index(tk.INSERT)
            linea_num, col_num = map(int, pos.split('.'))
            linea_texto = tab_actual.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")
            
            # Encontrar límites de la palabra
            inicio = col_num
            while inicio > 0 and (linea_texto[inicio-1].isalnum() or linea_texto[inicio-1] == '_'):
                inicio -= 1
            
            fin = col_num
            while fin < len(linea_texto) and (linea_texto[fin].isalnum() or linea_texto[fin] == '_'):
                fin += 1
            
            simbolo_viejo = linea_texto[inicio:fin]
            
            if not simbolo_viejo:
                messagebox.showwarning("Renombrar", "No hay ningún símbolo bajo el cursor")
                return
            
            # Verificar que no sea una palabra clave
            if simbolo_viejo in self.palabras_clave:
                messagebox.showwarning("Renombrar", f"'{simbolo_viejo}' es una palabra clave y no puede ser renombrada")
                return
            
            # Preguntar nuevo nombre
            simbolo_nuevo = simpledialog.askstring("Renombrar Símbolo", 
                                                    f"Renombrar '{simbolo_viejo}' a:",
                                                    initialvalue=simbolo_viejo)
            
            if not simbolo_nuevo or simbolo_nuevo == simbolo_viejo:
                return
            
            # Validar nuevo nombre
            import re
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', simbolo_nuevo):
                messagebox.showerror("Error", "El nuevo nombre no es válido. Debe comenzar con letra o _ y contener solo letras, números y _")
                return
            
            # Obtener todo el código
            codigo = tab_actual.texto_codigo.get("1.0", tk.END)
            
            # Contar ocurrencias
            patron = rf'\b{re.escape(simbolo_viejo)}\b'
            ocurrencias = len(re.findall(patron, codigo))
            
            if ocurrencias == 0:
                messagebox.showinfo("Renombrar", f"No se encontraron referencias a '{simbolo_viejo}'")
                return
            
            # Confirmar
            respuesta = messagebox.askyesno("Renombrar Símbolo", 
                                           f"Se renombrará '{simbolo_viejo}' a '{simbolo_nuevo}'\n" +
                                           f"Se encontraron {ocurrencias} ocurrencia(s).\n\n" +
                                           f"¿Continuar?")
            
            if not respuesta:
                return
            
            # Realizar reemplazo
            nuevo_codigo = re.sub(patron, simbolo_nuevo, codigo)
            
            # Actualizar texto
            tab_actual.texto_codigo.delete("1.0", tk.END)
            tab_actual.texto_codigo.insert("1.0", nuevo_codigo)
            
            # Marcar como modificado
            tab_actual.archivo_modificado = True
            self.actualizar_titulo_tab()
            
            # Resaltar sintaxis
            self.resaltar_sintaxis_tab(tab_actual)
            
            messagebox.showinfo("Renombrar", f"Se renombraron {ocurrencias} ocurrencia(s)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al renombrar símbolo: {str(e)}")
    
    # --- SNIPPETS ---
    
    def detectar_snippet(self, event):
        """Detecta si se escribió un snippet y lo expande con Tab"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        # Solo procesar si se presionó Tab
        if event.keysym != 'Tab':
            return
        
        try:
            # Obtener palabra antes del cursor
            pos = tab_actual.texto_codigo.index(tk.INSERT)
            linea_num, col_num = map(int, pos.split('.'))
            linea_texto = tab_actual.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.{col_num}")
            
            # Encontrar la última palabra
            palabras = linea_texto.split()
            if not palabras:
                return
            
            palabra = palabras[-1]
            
            # Verificar si es un snippet
            if palabra in self.snippets:
                # Cancelar el Tab normal
                # Eliminar la palabra del snippet
                inicio_palabra = col_num - len(palabra)
                tab_actual.texto_codigo.delete(f"{linea_num}.{inicio_palabra}", f"{linea_num}.{col_num}")
                
                # Insertar el snippet
                snippet_texto = self.snippets[palabra]
                tab_actual.texto_codigo.insert(f"{linea_num}.{inicio_palabra}", snippet_texto)
                
                # Posicionar cursor después de la primera línea o en el primer \t
                if '\t' in snippet_texto:
                    # Encontrar posición del primer \t
                    partes = snippet_texto.split('\t', 1)
                    offset = len(partes[0])
                    nueva_pos = f"{linea_num}.{inicio_palabra + offset}"
                    tab_actual.texto_codigo.mark_set(tk.INSERT, nueva_pos)
                
                # Resaltar sintaxis
                self.resaltar_sintaxis_tab(tab_actual)
                
                # Marcar como modificado
                tab_actual.archivo_modificado = True
                self.actualizar_titulo_tab()
                
                return "break"  # Prevenir el Tab normal
        except Exception as e:
            print(f"Error en detectar_snippet: {e}")
    
    # --- UTILIDADES ADICIONALES ---
    
    def resetear_zoom(self):
        """Resetea el zoom a 11pt (Ctrl+0)"""
        tab_actual = self.get_tab_actual()
        if tab_actual:
            tab_actual.font_size = 11
            tab_actual.texto_codigo.config(font=("Consolas", 11))
            self.actualizar_status_bar()
    
    def toggle_output_panel(self):
        """Muestra u oculta el panel inferior (Ctrl+J).
        El frame permanece en main_paned para que el sash siempre sea arrastrable."""
        if self._panel_output_visible:
            # Guardar altura actual antes de colapsar
            try:
                self._sash_pos = self.main_paned.sash_coord(0)[1]
            except Exception:
                self._sash_pos = int(self.root.winfo_height() * 0.65)
            # Ocultar el notebook (queda solo la tira del header)
            self.notebook.pack_forget()
            # Empujar sash al fondo para que el editor ocupe todo
            total = self.main_paned.winfo_height()
            self.main_paned.sash_place(0, 0, total - 30)
            self._panel_output_visible = False
            self._btn_toggle_panel.config(text="△  Panel")
        else:
            # Restaurar notebook
            self.notebook.pack(in_=self._frame_output, fill=tk.BOTH, expand=True)
            # Restaurar posición del sash guardada (o 65% por defecto)
            pos = getattr(self, "_sash_pos", int(self.root.winfo_height() * 0.65))
            self.root.after(10, lambda: self.main_paned.sash_place(0, 0, pos))
            self._panel_output_visible = True
            self._btn_toggle_panel.config(text="▽  Panel")

    def toggle_terminal(self):
        """Muestra/oculta el terminal integrado (F8)"""
        if not self.terminal_frame:
            # Crear terminal por primera vez
            self.crear_terminal()
            self.terminal_visible = True
        else:
            # Toggle visibilidad
            if self.terminal_visible:
                self.terminal_frame.pack_forget()
                self.terminal_visible = False
            else:
                self.terminal_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False)
                self.terminal_visible = True
    
    def crear_terminal(self):
        """Crea el widget de terminal integrado"""
        # Frame para terminal
        self.terminal_frame = tk.Frame(self.editor_frame, bg="#181825", height=200)
        self.terminal_frame.pack(side=tk.BOTTOM, fill=tk.BOTH)

        # Label de título
        titulo_term = tk.Label(self.terminal_frame, text="  TERMINAL",
                              bg="#313244", fg="#a6adc8",
                              font=("Segoe UI", 9, "bold"),
                              anchor="w", padx=10)
        titulo_term.pack(fill=tk.X)

        # Frame para entrada y botones
        frame_controles = tk.Frame(self.terminal_frame, bg="#181825")
        frame_controles.pack(fill=tk.X, pady=2)

        # Entry para comandos
        self.terminal_input = tk.Entry(frame_controles, bg="#252530", fg="#cdd6f4",
                                       font=("Consolas", 10), insertbackground="#94e2d5",
                                       relief="flat", bd=4)
        self.terminal_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.terminal_input.bind('<Return>', lambda e: self.ejecutar_comando_terminal())

        # Botón ejecutar
        btn_ejecutar = tk.Button(frame_controles, text="▶  Ejecutar",
                                command=self.ejecutar_comando_terminal,
                                bg="#16a34a", fg="white",
                                font=("Segoe UI", 9), relief="flat", cursor="hand2")
        btn_ejecutar.pack(side=tk.LEFT, padx=5)

        # Botón limpiar
        btn_limpiar = tk.Button(frame_controles, text="🗑  Limpiar",
                               command=self.limpiar_terminal,
                               bg="#b91c1c", fg="white",
                               font=("Segoe UI", 9), relief="flat", cursor="hand2")
        btn_limpiar.pack(side=tk.LEFT, padx=5)

        # Área de salida
        scroll_term = tk.Scrollbar(self.terminal_frame)
        scroll_term.pack(side=tk.RIGHT, fill=tk.Y)

        self.terminal_text = tk.Text(self.terminal_frame,
                                     bg="#13131d", fg="#cdd6f4",
                                     font=("Consolas", 10),
                                     yscrollcommand=scroll_term.set,
                                     wrap=tk.WORD, height=10,
                                     insertbackground="#94e2d5")
        self.terminal_text.pack(fill=tk.BOTH, expand=True)
        scroll_term.config(command=self.terminal_text.yview)

        # Mensaje de bienvenida
        self.terminal_text.insert("1.0", "Terminal integrado — Escribe comandos y presiona Enter\n")
        self.terminal_text.insert("end", "─" * 70 + "\n")
        self.terminal_text.config(state=tk.DISABLED)
    
    def ejecutar_comando_terminal(self):
        """Ejecuta un comando en el terminal integrado"""
        comando = self.terminal_input.get().strip()
        if not comando:
            return
        
        self.terminal_text.config(state=tk.NORMAL)
        self.terminal_text.insert("end", f"\n$ {comando}\n", "comando")
        self.terminal_text.tag_config("comando", foreground="#569cd6")
        
        try:
            import subprocess
            # Ejecutar comando
            resultado = subprocess.run(comando, shell=True, capture_output=True, 
                                      text=True, timeout=10)
            
            # Mostrar salida
            if resultado.stdout:
                self.terminal_text.insert("end", resultado.stdout, "output")
                self.terminal_text.tag_config("output", foreground="#b5cea8")
            
            if resultado.stderr:
                self.terminal_text.insert("end", resultado.stderr, "error")
                self.terminal_text.tag_config("error", foreground="#f48771")
            
            if resultado.returncode != 0:
                self.terminal_text.insert("end", f"\n[Proceso terminó con código {resultado.returncode}]\n", "info")
            else:
                self.terminal_text.insert("end", f"\n[Completado exitosamente]\n", "success")
                self.terminal_text.tag_config("success", foreground="#4ec9b0")
                
        except subprocess.TimeoutExpired:
            self.terminal_text.insert("end", "\n[ERROR: Comando excedió tiempo máximo de ejecución]\n", "error")
        except Exception as e:
            self.terminal_text.insert("end", f"\n[ERROR: {str(e)}]\n", "error")
        
        self.terminal_text.insert("end", "=" * 70 + "\n")
        self.terminal_text.see("end")
        self.terminal_text.config(state=tk.DISABLED)
        
        # Limpiar entrada
        self.terminal_input.delete(0, tk.END)
    
    def limpiar_terminal(self):
        """Limpia el contenido del terminal"""
        if self.terminal_text:
            self.terminal_text.config(state=tk.NORMAL)
            self.terminal_text.delete("1.0", tk.END)
            self.terminal_text.insert("1.0", "Terminal limpiado\n")
            self.terminal_text.insert("end", "=" * 70 + "\n")
            self.terminal_text.config(state=tk.DISABLED)
    
    def exportar_codigo_c(self):
        """Muestra el bytecode del archivo Python actual"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return

        codigo = tab_actual.texto_codigo.get("1.0", tk.END).strip()
        if not codigo:
            messagebox.showwarning("Aviso", "El editor está vacío")
            return

        try:
            mi_compiler = Compiler(None, source=codigo)
            salida = mi_compiler.compile()

            ruta = filedialog.asksaveasfilename(
                title="Guardar Bytecode",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            if ruta:
                with open(ruta, 'w', encoding='utf-8') as f:
                    f.write(salida)
                messagebox.showinfo("Exportar", f"Bytecode exportado a:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar bytecode:\n{str(e)}")
    
    def cambiar_tema(self):
        """Cambia entre tema claro y oscuro"""
        # Alternar tema
        self.tema_actual = "claro" if self.tema_actual == "oscuro" else "oscuro"
        tema = self.temas[self.tema_actual]
        
        # Aplicar colores generales
        self.bg_color = tema["bg"]
        self.fg_color = tema["fg"]
        self.root.configure(bg=self.bg_color)
        
        # NOTA: Para aplicar completamente el tema, se necesitaría recrear todos los widgets
        # Por ahora, informamos al usuario y el tema se aplicará en el reinicio
        messagebox.showinfo("Cambiar Tema", 
                           f"Tema cambiado a '{self.tema_actual.capitalize()}'.\n" +
                           "Reinicia el IDE para aplicar completamente los cambios.")
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas del código actual"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        codigo = tab_actual.texto_codigo.get("1.0", tk.END)
        lineas = codigo.split('\n')
        
        # Calcular estadísticas
        total_lineas = len(lineas) - 1  # -1 porque tk.Text agrega línea extra
        lineas_codigo = 0
        lineas_comentario = 0
        lineas_vacias = 0
        
        for linea in lineas:
            linea_stripped = linea.strip()
            if not linea_stripped:
                lineas_vacias += 1
            elif linea_stripped.startswith('//'):
                lineas_comentario += 1
            else:
                lineas_codigo += 1
        
        # Contar palabras y caracteres
        palabras = len(codigo.split())
        caracteres = len(codigo)
        caracteres_sin_espacios = len(codigo.replace(' ', '').replace('\n', '').replace('\t', ''))
        
        # Contar funciones
        import re
        funciones = len(re.findall(r'\bfunc\s+\w+', codigo))
        variables = len(re.findall(r'\b(var\s+\w+|\w+\s*:=)', codigo))
        
        nombre_arch = (os.path.basename(tab_actual.ruta_actual)
                       if tab_actual.ruta_actual else "Sin título")
        # Mostrar en ventana
        stats_texto = f"""
📊 ESTADÍSTICAS DEL CÓDIGO

📄 Archivo: {nombre_arch}

📏 Líneas:
   • Total: {total_lineas}
   • Código: {lineas_codigo}
   • Comentarios: {lineas_comentario}
   • Vacías: {lineas_vacias}

✏️ Contenido:
   • Palabras: {palabras}
   • Caracteres: {caracteres}
   • Caracteres (sin espacios): {caracteres_sin_espacios}

🔧 Elementos:
   • Funciones: {funciones}
   • Variables: {variables}
"""
        messagebox.showinfo("Estadísticas", stats_texto)
    
    def mostrar_acerca_de(self):
        """Muestra información sobre el IDE"""
        acerca_texto = """
🚀 Python-IDE-FULL VERSION
        
Un IDE completo para programación en Python

✨ Características:
  • Multi-tab con pestañas independientes
  • Resaltado de sintaxis Python
  • Detección de errores en tiempo real (ast)
  • Explorador de archivos
  • Autocompletado inteligente (Ctrl+Space)
  • Go to Definition (F12) — busca def / class
  • Rename Symbol (F2)
  • Snippets Python (ej: "def" + Tab, "class" + Tab)
  • Terminal integrado (F8)
  • Zoom con Ctrl+Rueda / Ctrl+0
  • Bytecode Python (F6)
  • AST dump + dis (F7)
  • Ejecución real con subprocess (F5)
  • Temas Claro/Oscuro
  • Y mucho más...

⌨️ Atajos de teclado:
  F5  - Ejecutar
  F6  - Ver Bytecode
  F7  - Generar AST + dis
  F8  - Toggle terminal
  F12 - Ir a definición
  F2  - Renombrar símbolo
  Ctrl+S - Guardar
  Ctrl+F - Buscar
  Ctrl+G - Ir a línea
  Ctrl+D - Duplicar línea
  Ctrl+/ - Comentar/Descomentar (#)
  Ctrl+Space - Autocompletar
  Ctrl+W - Cerrar pestaña
  Ctrl+0 - Resetear zoom

© 2026 - Versión 2.0 (Python Edition)
"""
        messagebox.showinfo("Acerca de", acerca_texto)
    
    def agregar_archivo_reciente(self, ruta):
        """Agrega un archivo a la lista de recientes"""
        if ruta in self.archivos_recientes:
            self.archivos_recientes.remove(ruta)
        
        self.archivos_recientes.insert(0, ruta)
        
        # Limitar cantidad
        if len(self.archivos_recientes) > self.max_recientes:
            self.archivos_recientes = self.archivos_recientes[:self.max_recientes]

    # --- MÉTODOS GENERALES ---
    def crear_boton(self, parent, icon, tooltip_text, command, bg, side=tk.LEFT):
        """Crea un botón circular con icono y tooltip al pasar el cursor."""
        btn = CircleButton(parent, icon, bg, command, size=34)
        btn.config(bg=parent["bg"])
        btn.pack(side=side, padx=5, pady=3)
        Tooltip(btn, tooltip_text)
        return btn
    
    # --- MÉTODOS ADAPTADOS PARA EDITOR TAB ---
    
    def resaltar_sintaxis_tab(self, tab, event=None):
        """Resalta sintaxis Python para una pestaña específica"""
        # Limpiar tags previos
        for tag in ["keyword", "type", "string", "numeros", "comment", "caracteres"]:
            tab.texto_codigo.tag_remove(tag, "1.0", tk.END)

        # Patrones Python
        keywords = (
            r'\b(False|None|True|and|as|assert|async|await|break|class|continue|'
            r'def|del|elif|else|except|finally|for|from|global|if|import|in|is|'
            r'lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b'
        )
        builtins = (
            r'\b(print|input|len|range|int|float|str|bool|list|dict|tuple|set|'
            r'type|bytes|super|property|staticmethod|classmethod|isinstance|'
            r'hasattr|getattr|setattr|enumerate|zip|map|filter|sorted|reversed|'
            r'sum|min|max|abs|round|open|vars|dir|repr|format|chr|ord|any|all)\b'
        )
        decoradores    = r'@\w+'
        numeros        = r'\b(0b[01]+|0o[0-7]+|0x[\da-fA-F]+|\d+(\.\d+)?([eE][+-]?\d+)?)\b'
        strings_triple = r'(""".*?""\'|\'\'\'.+?\'\'\')'   # multilinea básico (no perfecto en regex)
        strings_simple = r'("[^"\n]*"|\' [^\'\n]*\')'
        comment        = r'#.*'
        caracteres_esp = r'[:=+\-*/%&|^!<>(){}\[\],.]'

        self.aplicar_regex_tab(tab, keywords,     "keyword")
        self.aplicar_regex_tab(tab, builtins,     "type")
        self.aplicar_regex_tab(tab, decoradores,  "caracteres")
        self.aplicar_regex_tab(tab, numeros,      "numeros")
        self.aplicar_regex_tab(tab, strings_simple, "string")
        self.aplicar_regex_tab(tab, comment,      "comment")
        self.aplicar_regex_tab(tab, caracteres_esp, "caracteres")
    
    def aplicar_regex_tab(self, tab, pattern, tag):
        """Aplica regex para resaltado en una pestaña específica"""
        start = "1.0"
        while True:
            pos = tab.texto_codigo.search(pattern, start, stopindex=tk.END, regexp=True)
            if not pos: 
                break
            
            length = tk.IntVar()
            tab.texto_codigo.search(pattern, pos, stopindex=tk.END, regexp=True, count=length)
            
            if length.get() == 0:
                start = f"{pos}+1c"
                continue
                
            end = f"{pos}+{length.get()}c"
            tab.texto_codigo.tag_add(tag, pos, end)
            start = end
    
    def actualizar_barra_estado_tab(self, tab, event=None):
        """Actualiza la barra de estado para una pestaña específica"""
        try:
            # Obtener posición del cursor
            cursor_pos = tab.texto_codigo.index(tk.INSERT)
            linea, columna = cursor_pos.split('.')
            
            #Contar total de líneas
            total_lineas = int(tab.texto_codigo.index('end-1c').split('.')[0])
            
            # Actualizar labels
            self.label_linea_col.config(text=f"Ln {linea}, Col {columna}")
            
            if total_lineas == 1:
                self.label_total_lineas.config(text="Total: 1 línea")
            else:
                self.label_total_lineas.config(text=f"Total: {total_lineas} líneas")
            
            # Actualizar nivel de zoom
            porcentaje = int((tab.font_size / 13) * 100)
            self.label_zoom.config(text=f"{porcentaje}%")
            
            # Marcar como modificado si se está escribiendo
            if event and event.keysym not in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 
                                               'Prior', 'Next', 'Control_L', 'Control_R',
                                               'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R']:
                if not tab.archivo_modificado:
                    tab.archivo_modificado = True
                    self.actualizar_nombre_tab(tab)
                    self.actualizar_titulo()
        except:
            pass
    
    def auto_indentacion_tab(self, tab):
        """Auto-indentación para Python (basada en ':' al final de línea)"""
        try:
            cursor_pos = tab.texto_codigo.index(tk.INSERT)
            linea_num = int(cursor_pos.split('.')[0])
            contenido_linea = tab.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")

            # Obtener indentación actual (espacios y tabs)
            indentacion_actual = ""
            for char in contenido_linea:
                if char in (" ", "\t"):
                    indentacion_actual += char
                else:
                    break

            linea_stripped = contenido_linea.strip()
            nueva_indentacion = indentacion_actual

            # Si la línea termina en ':' y no es un comentario → indentar
            if linea_stripped.endswith(":") and not linea_stripped.startswith("#"):
                nueva_indentacion = indentacion_actual + "    "  # 4 espacios

            # Si la línea anterior es return/pass/break/continue/raise → des-indentar
            elif linea_stripped in ('return', 'pass', 'break', 'continue') or \
                 linea_stripped.startswith(('return ', 'raise ', 'break', 'continue', 'pass')):
                if len(indentacion_actual) >= 4:
                    nueva_indentacion = indentacion_actual[4:]
                else:
                    nueva_indentacion = ""

            # Insertar nueva línea con indentación
            tab.texto_codigo.insert(tk.INSERT, "\n" + nueva_indentacion)

            # Marcar como modificado
            tab.archivo_modificado = True
            self.actualizar_titulo_tab()

            return "break"

        except Exception as e:
            print(f"Error en auto_indentacion_tab: {e}")
            tab.texto_codigo.insert(tk.INSERT, "\n")
            return "break"
    
    def auto_desindentar_cierre(self, tab):
        """
        Des-indenta automáticamente cuando se escribe }
        Mueve el } a la indentación correcta según el bloque que cierra
        """
        try:
            cursor_pos = tab.texto_codigo.index(tk.INSERT)
            linea_num, col_num = map(int, cursor_pos.split('.'))
            
            # Obtener contenido de la línea actual
            contenido_linea = tab.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")
            
            # Verificar que la línea solo contenga espacios/tabs y el }
            linea_stripped = contenido_linea.strip()
            if linea_stripped != '}':
                return  # No hacer nada si hay más contenido
            
            # Contar la indentación actual
            indentacion_actual = 0
            for char in contenido_linea:
                if char == '\t':
                    indentacion_actual += 1
                elif char == ' ':
                    continue  # Ignorar espacios (Go usa tabs)
                else:
                    break
            
            # Si no hay indentación, no hacer nada
            if indentacion_actual == 0:
                return
            
            # Buscar el bloque que abre este cierre mirando hacia atrás
            nivel_bloques = 1  # Ya tenemos un } que queremos cerrar
            linea_busqueda = linea_num - 1
            indent_objetivo = 0
            
            while linea_busqueda > 0 and nivel_bloques > 0:
                linea_contenido = tab.texto_codigo.get(f"{linea_busqueda}.0", f"{linea_busqueda}.end")
                linea_strip = linea_contenido.strip()
                
                # Ignorar líneas vacías y comentarios
                if not linea_strip or linea_strip.startswith('//'):
                    linea_busqueda -= 1
                    continue
                
                # Contar cierres } en esta línea
                nivel_bloques += linea_strip.count('}')
                
                # Contar aperturas { en esta línea
                if '{' in linea_strip:
                    nivel_bloques -= linea_strip.count('{')
                    
                    # Si encontramos el bloque que abre
                    if nivel_bloques == 0:
                        # Calcular indentación de la línea que abre
                        indent_objetivo = 0
                        for char in linea_contenido:
                            if char == '\t':
                                indent_objetivo += 1
                            elif char == ' ':
                                continue
                            else:
                                break
                        break
                
                linea_busqueda -= 1
            
            # Si la indentación actual es diferente a la objetivo, corregir
            if indentacion_actual != indent_objetivo:
                # Eliminar la línea actual
                tab.texto_codigo.delete(f"{linea_num}.0", f"{linea_num}.end")
                
                # Insertar con la indentación correcta
                nueva_linea = ('\t' * indent_objetivo) + '}'
                tab.texto_codigo.insert(f"{linea_num}.0", nueva_linea)
                
                # Posicionar cursor después del }
                tab.texto_codigo.mark_set(tk.INSERT, f"{linea_num}.{indent_objetivo + 1}")
                
                # Marcar como modificado
                tab.archivo_modificado = True
                self.actualizar_titulo_tab()
                
        except Exception as e:
            print(f"Error en auto_desindentar_cierre: {e}")
    
    def zoom_editor_tab(self, tab, event):
        """Zoom para una pestaña específica"""
        if event.delta > 0:
            tab.font_size = min(tab.font_size + 1, 30)
        else:
            tab.font_size = max(tab.font_size - 1, 8)
        
        tab.texto_codigo.config(font=("Consolas", tab.font_size))
        
        porcentaje = int((tab.font_size / 13) * 100)
        self.label_zoom.config(text=f"{porcentaje}%")
        
        tab.linenumbers.redraw()
        
        return "break"

    def resaltar_sintaxis(self, event=None):
        tab_actual = self.get_tab_actual()
        if tab_actual:
            self.resaltar_sintaxis_tab(tab_actual, event)
        
    def aplicar_regex(self, pattern, tag):
        tab_actual = self.get_tab_actual()
        if tab_actual:
            self.aplicar_regex_tab(tab_actual, pattern, tag)
            
    def auto_indentacion(self, event):
        tab_actual = self.get_tab_actual()
        if tab_actual:
            return self.auto_indentacion_tab(tab_actual)

    def obtener_codigo(self):
        """Obtiene el código de la pestaña actual"""
        tab_actual = self.get_tab_actual()
        if tab_actual:
            return tab_actual.texto_codigo.get("1.0", tk.END).strip()
        return ""

    def procesar_tokens(self):
        """Tokeniza el código Python y lo muestra en la pestaña de análisis léxico."""
        codigo = self.obtener_codigo()
        if not codigo:
            return None

        self.texto_tokens.delete("1.0", tk.END)
        self.consola.delete("1.0", tk.END)

        # 1. Validar sintaxis con ast
        import ast as _ast
        try:
            _ast.parse(codigo)
        except IndentationError as e:
            self.consola.insert(tk.END, f"❌ ERROR DE INDENTACIÓN en línea {e.lineno}: {e.msg}\n")
            return None
        except SyntaxError as e:
            self.consola.insert(tk.END, f"❌ ERROR DE SINTAXIS en línea {e.lineno}: {e.msg}\n")
            return None

        # 2. Tokenizar con el módulo tokenize
        lexer_instancia = Lexer(codigo)
        try:
            lista_tokens = lexer_instancia.tokenize()

            texto_formateado = ""
            for t in lista_tokens:
                texto_formateado += f"<{t.type.name}, '{t.value}', fila {t.line}>\n"

            self.texto_tokens.insert(tk.END, texto_formateado)
            return lista_tokens
        except Exception as e:
            self.consola.insert(tk.END, f"Error Léxico: {e}\n")
            return None

    def accion_ejecutar(self, event=None):
        """Ejecutar codigo Python: tokenizar + bytecode + AST + ejecutar con subprocess"""
        lista_tokens = self.procesar_tokens()
        if not lista_tokens:
            return

        codigo = self.obtener_codigo()

        # 1. BYTECODE (pestaña Bytecode Python)
        try:
            self.output_c.delete("1.0", tk.END)
            mi_compiler = Compiler(None, source=codigo)
            bytecode_out = mi_compiler.compile()
            self.output_c.insert(tk.END, bytecode_out)
            self.consola.insert(tk.END, "✅ Bytecode generado\n")
        except Exception as e:
            self.output_c.delete("1.0", tk.END)
            self.output_c.insert(tk.END, f"Error al generar bytecode: {e}\n")
            self.consola.insert(tk.END, f"⚠️ Error al generar bytecode: {e}\n")

        # 2. AST + DIS (pestañas Intermedio y ASM)
        try:
            asm_gen = AssemblyGenerator(None, source=codigo)
            tac_code, asm_code = asm_gen.generate()
            self.output_tac.delete("1.0", tk.END)
            self.output_tac.insert(tk.END, tac_code)
            self.output_asm.delete("1.0", tk.END)
            self.output_asm.insert(tk.END, asm_code)
            self.consola.insert(tk.END, "✅ AST y bytecode generados\n")
        except Exception as e:
            self.output_asm.delete("1.0", tk.END)
            self.output_asm.insert(tk.END, f"Error: {e}\n")
            self.consola.insert(tk.END, f"⚠️ Error al generar AST: {e}\n")

        # 3. EJECUTAR
        self.consola.insert(tk.END, "\n=== EJECUCIÓN DEL PROGRAMA ===\n")
        self.notebook.select(self.tab_consola)
        try:
            interpreter = Interpreter(None, self.consola, source=codigo)
            interpreter.run()
            self.consola.insert(tk.END, "\n✅ Ejecución completada\n")
        except Exception as e:
            self.consola.insert(tk.END, f"\n❌ Error de ejecución: {e}\n")

    def accion_compilar(self, event=None):
        """Muestra el bytecode Python del código actual (F6)"""
        lista_tokens = self.procesar_tokens()
        if not lista_tokens:
            return
        codigo = self.obtener_codigo()
        try:
            self.output_c.delete("1.0", tk.END)
            self.notebook.select(self.tab_c)
            mi_compiler = Compiler(None, source=codigo)
            bytecode_out = mi_compiler.compile()
            self.output_c.insert(tk.END, bytecode_out)
        except Exception as e:
            self.output_c.delete("1.0", tk.END)
            self.output_c.insert(tk.END, f"Error al generar bytecode: {e}\n")

    def accion_generar_asm(self, event=None):
        """Genera AST dump (TAC) y bytecode dis (ASM) del código Python (F7)"""
        lista_tokens = self.procesar_tokens()
        if not lista_tokens:
            return
        codigo = self.obtener_codigo()
        try:
            asm_gen = AssemblyGenerator(None, source=codigo)
            tac_code, asm_code = asm_gen.generate()

            self.output_tac.delete("1.0", tk.END)
            self.output_tac.insert(tk.END, tac_code)

            self.output_asm.delete("1.0", tk.END)
            self.output_asm.insert(tk.END, asm_code)

            self.notebook.select(self.tab_asm)
            self.consola.insert(tk.END, ">> AST y bytecode generados correctamente.\n")
            self.consola.insert(tk.END, ">> Use 'Guardar Ensamblador' para exportar el archivo .asm\n")
        except Exception as e:
            self.output_asm.delete("1.0", tk.END)
            self.output_asm.insert(tk.END, f"Error al generar AST/bytecode: {e}\n")
            self.consola.insert(tk.END, f"Error: {e}\n")

    def guardar_asm(self):
        """Guarda el código ensamblador en un archivo .asm"""
        asm_content = self.output_asm.get("1.0", tk.END).strip()
        tac_content = self.output_tac.get("1.0", tk.END).strip()
        
        if not asm_content or asm_content.startswith("Error"):
            messagebox.showwarning("Aviso", "Primero debe generar el código ensamblador (F7)")
            return
        
        # Determinar nombre base del archivo
        tab_actual = self.get_tab_actual()
        if tab_actual and tab_actual.ruta_actual:
            base_name = os.path.splitext(os.path.basename(tab_actual.ruta_actual))[0]
            default_dir = os.path.dirname(tab_actual.ruta_actual)
        else:
            base_name = "output"
            default_dir = os.getcwd()
        
        # Diálogo para guardar
        ruta_asm = filedialog.asksaveasfilename(
            initialdir=default_dir,
            initialfile=f"{base_name}.asm",
            defaultextension=".asm",
            filetypes=[("Assembly Files", "*.asm"), ("All Files", "*.*")]
        )
        
        if ruta_asm:
            try:
                # Guardar archivo .asm
                with open(ruta_asm, "w", encoding="utf-8") as f:
                    f.write(asm_content)
                
                # También guardar el código intermedio (.tac)
                ruta_tac = os.path.splitext(ruta_asm)[0] + ".tac"
                with open(ruta_tac, "w", encoding="utf-8") as f:
                    f.write(tac_content)
                
                self.consola.insert(tk.END, f">> Archivo guardado: {os.path.basename(ruta_asm)}\n")
                self.consola.insert(tk.END, f">> Código intermedio: {os.path.basename(ruta_tac)}\n")
                messagebox.showinfo("Éxito", f"Archivos guardados:\n- {ruta_asm}\n- {ruta_tac}")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def abrir_archivo(self):
        """Abre un archivo Python en una nueva pestaña o en la actual si está vacía"""
        ruta = filedialog.askopenfilename(
            filetypes=[("Python Files", "*.py"), ("Text", "*.txt"), ("All Files", "*.*")]
        )
        if not ruta:
            return
        
        # Leer contenido
        with open(ruta, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Agregar a lista de recientes
        self.agregar_archivo_reciente(ruta)
        
        # Verificar si la pestaña actual está vacía
        tab_actual = self.get_tab_actual()
        if (tab_actual and not tab_actual.ruta_actual and 
            not tab_actual.archivo_modificado and 
            not tab_actual.texto_codigo.get("1.0", tk.END).strip()):
            # Usar la pestaña actual
            tab_actual.ruta_actual = ruta
            tab_actual.archivo_modificado = False
            tab_actual.texto_codigo.delete("1.0", tk.END)
            tab_actual.texto_codigo.insert(tk.END, content)
            self.resaltar_sintaxis_tab(tab_actual)
            self.actualizar_nombre_tab(tab_actual)
        else:
            # Crear nueva pestaña
            self.crear_nueva_tab(ruta, content)
            tab_actual = self.get_tab_actual()
            self.resaltar_sintaxis_tab(tab_actual)
        
        self.actualizar_titulo()
        self.actualizar_barra_estado_tab(tab_actual)

    def guardar(self, event=None):
        """Guarda la pestaña actual"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return "break"
        
        if tab_actual.ruta_actual:
            try:
                with open(tab_actual.ruta_actual, "w", encoding="utf-8") as f:
                    f.write(tab_actual.texto_codigo.get("1.0", tk.END))
                tab_actual.archivo_modificado = False
                self.actualizar_nombre_tab(tab_actual)
                self.actualizar_titulo()
                self.consola.insert(tk.END, f">> Guardado en {os.path.basename(tab_actual.ruta_actual)}\n")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")
        else:
            self.guardar_como()
        return "break"

    def guardar_como(self):
        """Guarda la pestaña actual con un nuevo nombre"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        ruta = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        if ruta:
            tab_actual.ruta_actual = ruta
            tab_actual.archivo_modificado = False
            self.actualizar_nombre_tab(tab_actual)
            self.actualizar_titulo()
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(tab_actual.texto_codigo.get("1.0", tk.END))
                
    def nuevo_archivo(self):
        """Crea una nueva pestaña vacía"""
        # Crear nueva pestaña
        self.crear_nueva_tab()
        self.consola.insert(tk.END, ">> Nuevo archivo creado\n") 
    
    def abrir_buscador(self, event=None):
        """Buscar y reemplazar en la pestaña actual"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        # 1. Configuración de la Ventana Flotante
        ventana_buscar = tk.Toplevel(self.root)
        ventana_buscar.title("Buscar y Reemplazar")
        ventana_buscar.geometry("420x175")
        ventana_buscar.configure(bg="#1e1e2e")
        ventana_buscar.transient(self.root)
        ventana_buscar.resizable(False, False)

        # Configurar la cuadrícula
        ventana_buscar.columnconfigure(1, weight=1)

        # --- INTERFAZ ---
        tk.Label(ventana_buscar, text="🔍  Buscar:", bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 10)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        entry_buscar = tk.Entry(ventana_buscar, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                                font=("Consolas", 10), relief="flat", bd=4)
        entry_buscar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        entry_buscar.focus_set()
        entry_buscar.bind("<KeyRelease>", lambda e: buscar())

        tk.Label(ventana_buscar, text="✏️  Reemplazar con:", bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 10)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        entry_remplazar = tk.Entry(ventana_buscar, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                                   font=("Consolas", 10), relief="flat", bd=4)
        entry_remplazar.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # --- LÓGICA INTERNA ---
        def buscar(event=None):
            query = entry_buscar.get()
            
            tab_actual.texto_codigo.tag_remove("search_highlight", "1.0", tk.END)
            
            if not query.strip(): 
                return
            
            tab_actual.texto_codigo.tag_config("search_highlight", background="#f1c40f", foreground="black")
            
            start = "1.0"
            count = 0
            while True:
                pos = tab_actual.texto_codigo.search(query, start, stopindex=tk.END, nocase=True)
                if not pos: break
                end = f"{pos}+{len(query)}c"
                tab_actual.texto_codigo.tag_add("search_highlight", pos, end)
                start = end
                count += 1
            
            if count == 0 and event is None:
                messagebox.showinfo("Buscador", f"No se encontró '{query}'")

        def reemplazar():
            query = entry_buscar.get()
            replace_text = entry_remplazar.get()
            if not query: return
            
            contenido = tab_actual.texto_codigo.get("1.0", tk.END)
            
            if re.search(re.escape(query), contenido, re.IGNORECASE):
                nuevo_contenido = re.sub(re.escape(query), replace_text, contenido, flags=re.IGNORECASE)
                tab_actual.texto_codigo.delete("1.0", tk.END)
                tab_actual.texto_codigo.insert("1.0", nuevo_contenido)
                self.resaltar_sintaxis_tab(tab_actual)
                messagebox.showinfo("Éxito", "Reemplazo completado.")
                ventana_buscar.destroy()
            else:
                messagebox.showwarning("Aviso", f"No se encontró '{query}' para reemplazar.")

        # --- BOTONES ---
        frame_botones = tk.Frame(ventana_buscar, bg="#1e1e2e")
        frame_botones.grid(row=2, column=0, columnspan=2, pady=10)

        btn_buscar = tk.Button(frame_botones, text="Buscar", command=buscar, bg="#007acc", fg="white",
                               width=12, relief="flat", cursor="hand2")
        btn_buscar.pack(side=tk.LEFT, padx=5)

        btn_reemplazar = tk.Button(frame_botones, text="Reemplazar Todo", command=reemplazar,
                                   bg="#c2410c", fg="white", width=15, relief="flat", cursor="hand2")
        btn_reemplazar.pack(side=tk.LEFT, padx=5)
        
    def limpiar(self):
        self.texto_tokens.delete("1.0", tk.END)
        self.consola.delete("1.0", tk.END)
        self.output_c.delete("1.0", tk.END)
        self.output_asm.delete("1.0", tk.END)
        self.output_tac.delete("1.0", tk.END)
        self.consola.insert(tk.END, ">> Área de trabajo limpiada.\n")
    
    # === NUEVOS MÉTODOS - QUICK WINS ===
    
    def actualizar_titulo(self):
        """Actualiza el título de la ventana con el nombre del archivo y estado de modificación"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            self.root.title("Python-IDE - FULL VERSION")
            return
        
        if tab_actual.ruta_actual:
            nombre = os.path.basename(tab_actual.ruta_actual)
        else:
            nombre = "Sin título"
        
        modificado = " *" if tab_actual.archivo_modificado else ""
        self.root.title(f"Python-IDE - {nombre}{modificado}")
    
    def actualizar_titulo_tab(self):
        """Alias de conveniencia: actualiza título y nombre visual de la pestaña activa"""
        tab_actual = self.get_tab_actual()
        if tab_actual:
            self.actualizar_nombre_tab(tab_actual)
        self.actualizar_titulo()

    def actualizar_status_bar(self):
        """Alias de conveniencia para actualizar_barra_estado"""
        self.actualizar_barra_estado()
    
    def actualizar_barra_estado(self, event=None):
        """Actualiza la barra de estado con línea/columna, total de líneas, etc."""
        tab_actual = self.get_tab_actual()
        if tab_actual:
            self.actualizar_barra_estado_tab(tab_actual, event)
    
    def ir_a_linea(self):
        """Abre un diálogo para ir a una línea específica (Ctrl+G)"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        ventana = tk.Toplevel(self.root)
        ventana.title("Ir a línea")
        ventana.geometry("300x110")
        ventana.configure(bg="#1e1e2e")
        ventana.transient(self.root)
        ventana.resizable(False, False)
        
        tk.Label(ventana, text="Número de línea:", bg="#1e1e2e", fg="#a6adc8", 
                font=("Segoe UI", 10)).pack(pady=10)
        
        entry = tk.Entry(ventana, font=("Consolas", 11), width=20, bg="#313244",
                         fg="#cdd6f4", insertbackground="#cdd6f4", relief="flat", bd=4)
        entry.pack(pady=5)
        entry.focus_set()
        
        def ir():
            try:
                linea = int(entry.get())
                total_lineas = int(tab_actual.texto_codigo.index('end-1c').split('.')[0])
                
                if 1 <= linea <= total_lineas:
                    # Ir a la línea
                    tab_actual.texto_codigo.mark_set(tk.INSERT, f"{linea}.0")
                    tab_actual.texto_codigo.see(f"{linea}.0")
                    
                    # Resaltar la línea temporalmente
                    tab_actual.texto_codigo.tag_remove("goto_highlight", "1.0", tk.END)
                    tab_actual.texto_codigo.tag_add("goto_highlight", f"{linea}.0", f"{linea}.end")
                    tab_actual.texto_codigo.tag_config("goto_highlight", background="#264f78")
                    
                    # Quitar resaltado después de 1 segundo
                    self.root.after(1000, lambda: tab_actual.texto_codigo.tag_remove("goto_highlight", "1.0", tk.END))
                    
                    ventana.destroy()
                    tab_actual.texto_codigo.focus_set()
                else:
                    messagebox.showwarning("Línea inválida", f"Ingrese un número entre 1 y {total_lineas}")
            except ValueError:
                messagebox.showwarning("Entrada inválida", "Por favor ingrese un número válido")
        
        entry.bind("<Return>", lambda e: ir())
        
        btn = tk.Button(ventana, text="Ir", command=ir, bg="#007acc", fg="white", 
                       font=("Segoe UI", 9, "bold"), width=10)
        btn.pack(pady=5)
    
    def duplicar_linea(self):
        """Duplica la línea actual o selección hacia abajo (Ctrl+D)"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            # Verificar si hay selección
            try:
                sel_start = tab_actual.texto_codigo.index(tk.SEL_FIRST)
                sel_end = tab_actual.texto_codigo.index(tk.SEL_LAST)
                texto_seleccionado = tab_actual.texto_codigo.get(sel_start, sel_end)
                
                # Insertar el texto seleccionado justo después
                tab_actual.texto_codigo.insert(sel_end, texto_seleccionado)
            except tk.TclError:
                # No hay selección, duplicar línea actual
                cursor_pos = tab_actual.texto_codigo.index(tk.INSERT)
                linea = cursor_pos.split('.')[0]
                
                # Obtener contenido de la línea
                contenido_linea = tab_actual.texto_codigo.get(f"{linea}.0", f"{linea}.end")
                
                # Insertar al final de la línea actual
                tab_actual.texto_codigo.insert(f"{linea}.end", "\n" + contenido_linea)
                
                # Mover cursor a la nueva línea
                nueva_linea = int(linea) + 1
                tab_actual.texto_codigo.mark_set(tk.INSERT, f"{nueva_linea}.0")
            
            self.resaltar_sintaxis_tab(tab_actual)
            return "break"
        except:
            return "break"
    
    def comentar_descomentar(self):
        """Agrega o quita // al inicio de las líneas seleccionadas (Ctrl+/)"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        try:
            # Verificar si hay selección
            try:
                start_line = int(tab_actual.texto_codigo.index(tk.SEL_FIRST).split('.')[0])
                end_line = int(tab_actual.texto_codigo.index(tk.SEL_LAST).split('.')[0])
            except tk.TclError:
                # No hay selección, usar línea actual
                current_line = int(tab_actual.texto_codigo.index(tk.INSERT).split('.')[0])
                start_line = end_line = current_line
            
            # Verificar si todas las líneas están comentadas (con #)
            todas_comentadas = True
            for linea in range(start_line, end_line + 1):
                contenido = tab_actual.texto_codigo.get(f"{linea}.0", f"{linea}.end").lstrip()
                if contenido and not contenido.startswith("#"):
                    todas_comentadas = False
                    break
            
            # Comentar/descomentar con # (Python)
            for linea in range(start_line, end_line + 1):
                contenido = tab_actual.texto_codigo.get(f"{linea}.0", f"{linea}.end")
                
                if todas_comentadas:
                    # Descomentar: quitar # y espacio siguiente
                    sin_espacios = contenido.lstrip()
                    if sin_espacios.startswith("#"):
                        espacios_iniciales = len(contenido) - len(sin_espacios)
                        resto = sin_espacios[1:]
                        if resto.startswith(" "):
                            resto = resto[1:]
                        nuevo_contenido = contenido[:espacios_iniciales] + resto
                        tab_actual.texto_codigo.delete(f"{linea}.0", f"{linea}.end")
                        tab_actual.texto_codigo.insert(f"{linea}.0", nuevo_contenido)
                else:
                    # Comentar: agregar # al inicio (respetando indentación)
                    sin_espacios = contenido.lstrip()
                    if sin_espacios:  # Solo si la línea no está vacía
                        espacios_iniciales = len(contenido) - len(sin_espacios)
                        nuevo_contenido = contenido[:espacios_iniciales] + "# " + sin_espacios
                        tab_actual.texto_codigo.delete(f"{linea}.0", f"{linea}.end")
                        tab_actual.texto_codigo.insert(f"{linea}.0", nuevo_contenido)
            
            self.resaltar_sintaxis_tab(tab_actual)
            return "break"
        except:
            return "break"

    def cerrar(self):
        # Verificar si hay tabs con cambios sin guardar
        for tab_id in self.editor_notebook.tabs():
            tab = self.editor_notebook.nametowidget(tab_id)
            if isinstance(tab, EditorTab) and tab.archivo_modificado:
                # Seleccionar el tab con cambios sin guardar
                self.editor_notebook.select(tab)
                respuesta = messagebox.askyesnocancel("¿Guardar cambios?", 
                                                       f"¿Desea guardar los cambios en '{tab.get_nombre_para_tab()}' antes de salir?")
                if respuesta is None:  # Canceló
                    return
                elif respuesta:  # Sí, guardar
                    self.guardar()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorPython(root)
    root.mainloop()