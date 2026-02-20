
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
            self.create_text(2, y, anchor="nw", text=linenum, fill="#888", font=("Consolas", 12))
            i = self.text_widget.index("%s+1line" % i)

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
                                       insertbackground="white", 
                                       selectbackground="#264f78",
                                       yscrollcommand=self.scrollbar.set, 
                                       borderwidth=0)
        
        # Números de línea
        self.linenumbers = LineNumbers(self.frame, width=35, bg="#252526", highlightthickness=0)
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
        self.ide.validar_codigo_en_tiempo_real()  # Nueva validación en tiempo real
        self.ide.manejar_autocompletado(event)  # Autocompletado
        
        # Des-indentar automáticamente al escribir }
        if event.keysym == 'braceright':  # El usuario escribió }
            self.ide.auto_desindentar_cierre(self)
    
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
        self.texto_codigo.tag_config("keyword", foreground="#e572db")
        self.texto_codigo.tag_config("type", foreground="#569cd6")
        self.texto_codigo.tag_config("string", foreground="#ce9178")
        self.texto_codigo.tag_config("numeros", foreground="#4ac73e")
        self.texto_codigo.tag_config("comment", foreground="#ababab")
        self.texto_codigo.tag_config("caracteres", foreground="#fffb00")
        # Tag para errores
        self.texto_codigo.tag_config("error", underline=True, foreground="#ff0000")
        self.texto_codigo.tag_config("error_line", background="#3d1f1f")  # Fondo rojo oscuro para líneas con error
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
class SimuladorGo:
    def __init__(self, root):
        self.root = root
        self.root.title("Go-APK-IDE-FULL VERSION")
        self.root.geometry("1200x750")
        
        self.font_size = 13  # Tamaño de fuente por defecto para nuevas tabs

        # Temas disponibles
        self.tema_actual = "oscuro"
        self.temas = {
            "oscuro": {
                "bg": "#1e1e1e",
                "fg": "#d4d4d4",
                "bg_editor": "#1e1e1e",
                "fg_editor": "#d4d4d4",
                "bg_toolbar": "#333333",
                "bg_lineas": "#252526",
                "select_bg": "#264f78",
            },
            "claro": {
                "bg": "#ffffff",
                "fg": "#000000",
                "bg_editor": "#ffffff",
                "fg_editor": "#000000",
                "bg_toolbar": "#f3f3f3",
                "bg_lineas": "#f0f0f0",
                "select_bg": "#add6ff",
            }
        }

        self.bg_color = self.temas[self.tema_actual]["bg"]
        self.fg_color = self.temas[self.tema_actual]["fg"]
        self.root.configure(bg=self.bg_color)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#252526", borderwidth=0)
        style.configure("TNotebook.Tab", background="#333", foreground="white", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#1e1e1e")])

        #NUEVO: BARRA DE MENÚ SUPERIOR
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # -> Menú Archivo
        archivo_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        archivo_menu.add_command(label="Nuevo", command=self.nuevo_archivo, accelerator="Ctrl+N")
        archivo_menu.add_command(label="Abrir", command=self.abrir_archivo, accelerator="Ctrl+O")
        archivo_menu.add_command(label="Abrir Carpeta...", command=self.abrir_carpeta_proyecto)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Guardar", command=self.guardar, accelerator="Ctrl+S")
        archivo_menu.add_command(label="Guardar Como", command=self.guardar_como)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Exportar a C...", command=self.exportar_codigo_c)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Cerrar Pestaña", command=self.cerrar_tab_actual, accelerator="Ctrl+W")
        archivo_menu.add_command(label="Salir", command=self.cerrar)
        menubar.add_cascade(label="Archivo", menu=archivo_menu)

        # -> Menú Edición
        edicion_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        edicion_menu.add_command(label="Buscar y Reemplazar", command=self.abrir_buscador, accelerator="Ctrl+F")
        edicion_menu.add_command(label="Ir a Línea", command=self.ir_a_linea, accelerator="Ctrl+G")
        edicion_menu.add_separator()
        edicion_menu.add_command(label="Duplicar Línea", command=self.duplicar_linea, accelerator="Ctrl+D")
        edicion_menu.add_command(label="Comentar/Descomentar", command=self.comentar_descomentar, accelerator="Ctrl+/")
        edicion_menu.add_separator()
        edicion_menu.add_command(label="Autocompletar", command=self.activar_autocompletado_manual, accelerator="Ctrl+Space")
        menubar.add_cascade(label="Edición", menu=edicion_menu)
        
        # -> Menú Navegación
        navegacion_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        navegacion_menu.add_command(label="Ir a Definición", command=self.ir_a_definicion, accelerator="F12")
        menubar.add_cascade(label="Navegación", menu=navegacion_menu)
        
        # -> Menú Refactoring
        refactor_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        refactor_menu.add_command(label="Renombrar Símbolo", command=self.renombrar_simbolo, accelerator="F2")
        menubar.add_cascade(label="Refactoring", menu=refactor_menu)
        
        # -> Menú Vista
        vista_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        vista_menu.add_command(label="Cambiar Tema (Claro/Oscuro)", command=self.cambiar_tema)
        vista_menu.add_separator()
        vista_menu.add_command(label="Aumentar Zoom", accelerator="Ctrl+Rueda")
        vista_menu.add_command(label="Resetear Zoom", command=self.resetear_zoom, accelerator="Ctrl+0")
        vista_menu.add_separator()
        vista_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal, accelerator="F8")
        menubar.add_cascade(label="Vista", menu=vista_menu)

        # -> Menú Terminal
        terminal_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        terminal_menu.add_command(label="Ejecutar Código", command=self.accion_ejecutar, accelerator="F5")
        terminal_menu.add_command(label="Compilar a C", command=self.accion_compilar, accelerator="F6")
        terminal_menu.add_command(label="Generar Ensamblador", command=self.accion_generar_asm, accelerator="F7")
        terminal_menu.add_separator()
        terminal_menu.add_command(label="Guardar Ensamblador (.asm)", command=self.guardar_asm)
        menubar.add_cascade(label="Ejecutar", menu=terminal_menu)
        
        # -> Menú Herramientas
        herramientas_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        herramientas_menu.add_command(label="Estadísticas del Código", command=self.mostrar_estadisticas)
        menubar.add_cascade(label="Herramientas", menu=herramientas_menu)
        
        # -> Menú Ayuda
        ayuda_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        ayuda_menu.add_command(label="Acerca de", command=self.mostrar_acerca_de)
        menubar.add_cascade(label="Ayuda", menu=ayuda_menu)

        # --- 1. BARRA DE HERRAMIENTAS (Puedes mantenerla o quitarla si prefieres solo menú) ---
        toolbar = tk.Frame(self.root, bg="#333333", padx=5, pady=5)
        
        # --- 1. BARRA DE HERRAMIENTAS ---
        toolbar = tk.Frame(self.root, bg="#333333", padx=5, pady=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.crear_boton(toolbar, "📂 Abrir", self.abrir_archivo, "#555")
        self.crear_boton(toolbar, "💾 Guardar (Ctrl+S)", self.guardar, "#555")
        self.crear_boton(toolbar, "💾 Guardar Como...", self.guardar_como, "#555")
        
        tk.Frame(toolbar, width=20, bg="#333333").pack(side=tk.LEFT)

        self.crear_boton(toolbar, "🔨 COMPILAR (F6)", self.accion_compilar, "#007acc")
        self.crear_boton(toolbar, "📝 ASM (F7)", self.accion_generar_asm, "#9c27b0")
        self.crear_boton(toolbar, "▶️ EJECUTAR (F5)", self.accion_ejecutar, "#4CAF50")

        self.crear_boton(toolbar, "❌ Salir", self.cerrar, "#d32f2f", side=tk.RIGHT)
        self.crear_boton(toolbar, "🧹 Limpiar", self.limpiar, "#e65100", side=tk.RIGHT)

        # --- 2. ÁREA PRINCIPAL ---
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.bg_color, sashwidth=4)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 2.1. EXPLORADOR DE ARCHIVOS (SIDEBAR IZQUIERDO) ---
        self.panel_explorador = tk.Frame(self.paned_window, bg="#252526", width=250)
        self.paned_window.add(self.panel_explorador, minsize=200)
        self.crear_explorador_archivos()
        
        # Variable para carpeta del proyecto
        self.carpeta_proyecto = None

        # --- 3. EDITOR DE CÓDIGO CON PESTAÑAS Y PANEL DE ERRORES ---
        frame_editor = tk.Frame(self.paned_window, bg=self.bg_color)
        self.paned_window.add(frame_editor, minsize=400)

        # PanedWindow vertical para dividir editor y panel de errores
        self.editor_paned = tk.PanedWindow(frame_editor, orient=tk.VERTICAL, bg=self.bg_color, sashwidth=3)
        self.editor_paned.pack(fill=tk.BOTH, expand=True)

        # Frame superior para el editor con tabs
        frame_editor_tabs = tk.Frame(self.editor_paned, bg=self.bg_color)
        self.editor_paned.add(frame_editor_tabs, minsize=300)

        # Barra de pestañas personalizada con botones ×
        self.tab_bar = tk.Frame(frame_editor_tabs, bg="#252526", height=35)
        self.tab_bar.pack(side=tk.TOP, fill=tk.X)
        self.tab_bar.pack_propagate(False)

        # Notebook sin cabeceras nativas (las sustituimos por tab_bar)
        style.layout('TabEditor.TNotebook', [('Notebook.client', {'sticky': 'nswe'})])
        style.configure('TabEditor.TNotebook', background=self.bg_color, borderwidth=0)
        self.editor_notebook = ttk.Notebook(frame_editor_tabs, style='TabEditor.TNotebook')
        self.editor_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Lista de pestañas editoras
        self.tabs_editoras = []
        
        # Panel inferior para errores
        self.panel_errores = tk.Frame(self.editor_paned, bg="#2d2d2d", height=150)
        self.editor_paned.add(self.panel_errores, minsize=100)
        
        # Crear widgets del panel de errores
        self.crear_panel_errores()
        
        # Variables para control de validación
        self.validation_timer = None
        self.errores_actuales = []  # Lista de errores encontrados
        
        # Variables para autocompletado
        self.autocomplete_window = None  # Ventana flotante de sugerencias
        self.autocomplete_listbox = None  # Listbox con sugerencias
        self.autocomplete_activo = False  # Estado del autocompletado
        self.palabra_actual = ""  # Palabra que se está escribiendo
        self.sugerencias_actuales = []  # Lista de sugerencias filtradas
        
        # Palabras clave de Go
        self.palabras_clave = [
            'break', 'case', 'chan', 'const', 'continue', 'default', 'defer',
            'else', 'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import',
            'interface', 'map', 'package', 'range', 'return', 'select', 'struct',
            'switch', 'type', 'var',
            # Tipos básicos
            'int', 'int8', 'int16', 'int32', 'int64',
            'uint', 'uint8', 'uint16', 'uint32', 'uint64',
            'float32', 'float64', 'complex64', 'complex128',
            'bool', 'byte', 'rune', 'string', 'error',
            # Funciones comunes
            'fmt.Println', 'fmt.Printf', 'fmt.Sprintf',
            'len', 'cap', 'append', 'copy', 'delete', 'make', 'new',
            'panic', 'recover', 'close',
            # Valores especiales
            'true', 'false', 'nil', 'iota',
        ]
        
        # Variables para Go to Definition y navegación
        self.historial_navegacion = []  # Pila de posiciones visitadas
        self.indice_historial = -1  # Índice actual en el historial
        
        # Variables para renombrado de símbolos
        self.renombrando = False
        self.simbolo_a_renombrar = None
        
        # Snippets disponibles
        self.snippets = {
            'main': 'func main() {\n\t\n}',
            'func': 'func nombre() {\n\t\n}',
            'for': 'for i := 0; i < 10; i++ {\n\t\n}',
            'fori': 'for i := 0; i < len(arr); i++ {\n\t\n}',
            'forr': 'for _, v := range collection {\n\t\n}',
            'if': 'if condition {\n\t\n}',
            'ife': 'if condition {\n\t\n} else {\n\t\n}',
            'sw': 'switch expr {\ncase value1:\n\t\ncase value2:\n\t\ndefault:\n\t\n}',
            'struct': 'type Name struct {\n\t\n}',
            'interface': 'type Name interface {\n\t\n}',
            'var': 'var name type',
            'const': 'const name = value',
            'fmt': 'fmt.Println()',
            'err': 'if err != nil {\n\treturn err\n}',
            'errlog': 'if err != nil {\n\tlog.Fatal(err)\n}',
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

        # --- 4. ÁREA DE SALIDA ---
        frame_derecho = tk.Frame(self.paned_window, bg=self.bg_color)
        self.paned_window.add(frame_derecho, minsize=400)

        self.notebook = ttk.Notebook(frame_derecho)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_consola = tk.Frame(self.notebook, bg="#1e1e1e")
        self.consola = scrolledtext.ScrolledText(self.tab_consola, bg="black", fg="#cccccc", font=("Consolas", 11))
        self.consola.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_consola, text="  📟 Consola (Output)  ")

        self.tab_c = tk.Frame(self.notebook, bg="#1e1e1e")
        self.output_c = scrolledtext.ScrolledText(self.tab_c, bg="#2d2d2d", fg="#569cd6", font=("Consolas", 11))
        self.output_c.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_c, text="  ⚙️ Código C Generado  ")

        self.tab_tokens = tk.Frame(self.notebook, bg="#1e1e1e")
        self.texto_tokens = scrolledtext.ScrolledText(self.tab_tokens, bg="#222", fg="#00ff00", font=("Consolas", 10))
        self.texto_tokens.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_tokens, text="  🔍 Análisis Léxico  ")

        # Nueva pestaña para código ensamblador
        self.tab_asm = tk.Frame(self.notebook, bg="#1e1e1e")
        self.output_asm = scrolledtext.ScrolledText(self.tab_asm, bg="#1a1a2e", fg="#e94560", font=("Consolas", 11))
        self.output_asm.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_asm, text="  📝 Ensamblador (ASM)  ")

        # Nueva pestaña para código intermedio TAC
        self.tab_tac = tk.Frame(self.notebook, bg="#1e1e1e")
        self.output_tac = scrolledtext.ScrolledText(self.tab_tac, bg="#0f0f23", fg="#00d4ff", font=("Consolas", 11))
        self.output_tac.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.tab_tac, text="  🔧 Código Intermedio  ")
        
        # --- 5. BARRA DE ESTADO ---
        self.barra_estado = tk.Frame(self.root, bg="#007acc", height=25)
        self.barra_estado.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.label_linea_col = tk.Label(self.barra_estado, text="Ln 1, Col 0", bg="#007acc", fg="white", 
                                         font=("Segoe UI", 9), padx=10)
        self.label_linea_col.pack(side=tk.LEFT)
        
        self.label_total_lineas = tk.Label(self.barra_estado, text="Total: 1 línea", bg="#007acc", fg="white",
                                           font=("Segoe UI", 9), padx=10)
        self.label_total_lineas.pack(side=tk.LEFT)
        
        self.label_encoding = tk.Label(self.barra_estado, text="UTF-8", bg="#007acc", fg="white",
                                       font=("Segoe UI", 9), padx=10)
        self.label_encoding.pack(side=tk.LEFT)
        
        self.label_tipo_archivo = tk.Label(self.barra_estado, text="Go", bg="#007acc", fg="white",
                                           font=("Segoe UI", 9), padx=10)
        self.label_tipo_archivo.pack(side=tk.LEFT)
        
        self.label_zoom = tk.Label(self.barra_estado, text="100%", bg="#007acc", fg="white",
                                   font=("Segoe UI", 9), padx=10)
        self.label_zoom.pack(side=tk.RIGHT)
        
        # Actualizar título inicial
        self.actualizar_titulo()

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
        btn_frame = tk.Frame(self.tab_bar, bg="#2d2d2d", padx=0, pady=0)
        btn_frame.pack(side=tk.LEFT, padx=(0, 1), pady=(0, 0))

        lbl = tk.Button(btn_frame, text=nombre, bg="#2d2d2d", fg="#aaaaaa",
                        border=0, padx=10, pady=6,
                        activebackground="#3c3c3c", activeforeground="white",
                        font=("Segoe UI", 10), cursor="arrow",
                        command=lambda t=tab: self._seleccionar_tab(t))
        lbl.pack(side=tk.LEFT)

        close = tk.Button(btn_frame, text="✕", bg="#2d2d2d", fg="#666666",
                          border=0, padx=5, pady=6,
                          activebackground="#c42b1c", activeforeground="white",
                          font=("Segoe UI", 9), cursor="hand2",
                          command=lambda t=tab: self.cerrar_tab(t))
        close.pack(side=tk.LEFT)

        # Hover: resaltar cierre al pasar el ratón
        def on_enter(e, f=btn_frame, l=lbl, c=close):
            tab_actual = self.get_tab_actual()
            bg = "#1e1e1e" if tab is tab_actual else "#3c3c3c"
            f.config(bg=bg); l.config(bg=bg); c.config(bg=bg, fg="#cccccc")
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
                t._tab_btn_frame.config(bg="#1e1e1e")
                t._tab_label.config(bg="#1e1e1e", fg="#ffffff")
                t._tab_close.config(bg="#1e1e1e", fg="#888888")
            else:
                t._tab_btn_frame.config(bg="#2d2d2d")
                t._tab_label.config(bg="#2d2d2d", fg="#aaaaaa")
                t._tab_close.config(bg="#2d2d2d", fg="#555555")

    # --- MÉTODOS PARA PANEL DE ERRORES Y VALIDACIÓN EN TIEMPO REAL ---
    
    def crear_panel_errores(self):
        """Crea el panel de errores en la parte inferior"""
        # Header del panel
        header_frame = tk.Frame(self.panel_errores, bg="#1e1e1e", height=30)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="⚠️ PROBLEMAS", bg="#1e1e1e", fg="#ffffff", 
                 font=("Segoe UI", 10, "bold"), padx=10, anchor="w").pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.label_contador_errores = tk.Label(header_frame, text="0 errores", bg="#1e1e1e", fg="#cccccc",
                                                font=("Segoe UI", 9), padx=10)
        self.label_contador_errores.pack(side=tk.RIGHT)
        
        # Frame con scroll para la lista de errores
        canvas_frame = tk.Frame(self.panel_errores, bg="#2d2d2d")
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        scrollbar_errores = tk.Scrollbar(canvas_frame, orient="vertical")
        scrollbar_errores.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas_errores = tk.Canvas(canvas_frame, bg="#2d2d2d", highlightthickness=0,
                                         yscrollcommand=scrollbar_errores.set)
        self.canvas_errores.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_errores.config(command=self.canvas_errores.yview)
        
        self.frame_lista_errores = tk.Frame(self.canvas_errores, bg="#2d2d2d")
        self.canvas_errores.create_window((0, 0), window=self.frame_lista_errores, anchor="nw")
        
        # Configurar scroll region
        self.frame_lista_errores.bind("<Configure>", 
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
        
        # 1. Validar indentación
        try:
            from indentation_checker import IndentationChecker
            checker = IndentationChecker(codigo)
            indent_errors = checker.check()
            for line_num, message in indent_errors:
                errores.append({
                    'linea': line_num,
                    'tipo': 'Indentación',
                    'mensaje': message
                })
        except Exception as e:
            pass  # Ignorar errores del checker
        
        # 2. Validar sintaxis léxica
        try:
            lexer_instancia = Lexer(codigo)
            lista_tokens = lexer_instancia.tokenize()
            
            # 3. Validar sintaxis con parser
            try:
                mi_parser = Parser(lista_tokens)
                program = mi_parser.parse()
            except SyntaxError as e:
                # Extraer número de línea del mensaje de error si es posible
                error_msg = str(e)
                linea = self.extraer_numero_linea(error_msg)
                errores.append({
                    'linea': linea if linea else 1,
                    'tipo': 'Sintaxis',
                    'mensaje': error_msg
                })
            except Exception as e:
                errores.append({
                    'linea': 1,
                    'tipo': 'Parser',
                    'mensaje': str(e)
                })
        except Exception as e:
            # Error léxico
            error_msg = str(e)
            linea = self.extraer_numero_linea(error_msg)
            errores.append({
                'linea': linea if linea else 1,
                'tipo': 'Léxico',
                'mensaje': error_msg
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
        """Actualiza el panel de errores con la lista actual"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        # Limpiar lista actual
        for widget in self.frame_lista_errores.winfo_children():
            widget.destroy()
        
        errores = tab_actual.errores
        
        # Actualizar contador
        num_errores = len(errores)
        if num_errores == 0:
            self.label_contador_errores.config(text="✓ Sin errores", fg="#4ec9b0")
        elif num_errores == 1:
            self.label_contador_errores.config(text="1 error", fg="#f48771")
        else:
            self.label_contador_errores.config(text=f"{num_errores} errores", fg="#f48771")
        
        # Mostrar cada error
        for i, error in enumerate(errores):
            self.crear_item_error(i, error, tab_actual)
    
    def crear_item_error(self, index, error, tab):
        """Crea un item visual para un error en la lista"""
        # Frame del error
        error_frame = tk.Frame(self.frame_lista_errores, bg="#2d2d2d", cursor="hand2")
        error_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Frame interno con borde
        inner_frame = tk.Frame(error_frame, bg="#3d3d3d", relief="solid", bd=1)
        inner_frame.pack(fill=tk.BOTH, expand=True)
        
        # Icono y tipo
        tipo_color = {
            'Sintaxis': '#f48771',
            'Léxico': '#ff6b6b',
            'Indentación': '#ffa500',
            'Parser': '#ff0000'
        }
        color = tipo_color.get(error['tipo'], '#ff0000')
        
        icon_label = tk.Label(inner_frame, text="✖", bg="#3d3d3d", fg=color,
                              font=("Segoe UI", 10, "bold"), width=3)
        icon_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Frame para texto
        text_frame = tk.Frame(inner_frame, bg="#3d3d3d")
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tipo y línea
        header_text = f"{error['tipo']} [Línea {error['linea']}]"
        header_label = tk.Label(text_frame, text=header_text, bg="#3d3d3d", fg=color,
                                font=("Segoe UI", 9, "bold"), anchor="w")
        header_label.pack(fill=tk.X)
        
        # Mensaje
        msg_label = tk.Label(text_frame, text=error['mensaje'], bg="#3d3d3d", fg="#cccccc",
                            font=("Segoe UI", 9), anchor="w", wraplength=600, justify="left")
        msg_label.pack(fill=tk.X)
        
        # Hacer todo el frame clicable
        linea = error['linea']
        for widget in [error_frame, inner_frame, icon_label, text_frame, header_label, msg_label]:
            widget.bind("<Button-1>", lambda e, l=linea: self.ir_a_linea_error(l))
            widget.bind("<Enter>", lambda e, f=inner_frame: f.config(bg="#4d4d4d"))
            widget.bind("<Leave>", lambda e, f=inner_frame: f.config(bg="#3d3d3d"))
    
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
        header_explorador = tk.Frame(self.panel_explorador, bg="#1e1e1e", height=40)
        header_explorador.pack(side=tk.TOP, fill=tk.X)
        header_explorador.pack_propagate(False)
        
        tk.Label(header_explorador, text="📁 EXPLORADOR", bg="#1e1e1e", fg="#ffffff",
                 font=("Segoe UI", 10, "bold"), padx=10, anchor="w").pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Botón para abrir carpeta
        btn_abrir_carpeta = tk.Button(header_explorador, text="📂", command=self.abrir_carpeta_proyecto,
                                       bg="#1e1e1e", fg="#ffffff", relief="flat", font=("Segoe UI", 12),
                                       cursor="hand2", borderwidth=0)
        btn_abrir_carpeta.pack(side=tk.RIGHT, padx=5)
        
        # Botón para refrescar
        btn_refrescar = tk.Button(header_explorador, text="🔄", command=self.refrescar_explorador,
                                   bg="#1e1e1e", fg="#ffffff", relief="flat", font=("Segoe UI", 12),
                                   cursor="hand2", borderwidth=0)
        btn_refrescar.pack(side=tk.RIGHT, padx=2)
        
        # Frame para el árbol de archivos
        tree_frame = tk.Frame(self.panel_explorador, bg="#252526")
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        scrollbar_y = tk.Scrollbar(tree_frame, orient="vertical")
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = tk.Scrollbar(tree_frame, orient="horizontal")
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview para estructura de archivos
        style = ttk.Style()
        style.configure("Treeview", background="#252526", foreground="#cccccc",
                       fieldbackground="#252526", borderwidth=0)
        style.configure("Treeview.Heading", background="#1e1e1e", foreground="#ffffff")
        style.map("Treeview", background=[("selected", "#094771")])
        
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
        """Obtiene lista completa de sugerencias posibles"""
        sugerencias = list(self.palabras_clave)
        
        # Agregar funciones y variables definidas en el código actual
        tab_actual = self.get_tab_actual()
        if tab_actual:
            codigo = tab_actual.texto_codigo.get("1.0", tk.END)
            
            # Buscar definiciones de funciones: func nombre(
            import re
            funciones = re.findall(r'\bfunc\s+(\w+)\s*\(', codigo)
            sugerencias.extend(funciones)
            
            # Buscar declaraciones de variables: var nombre
            variables = re.findall(r'\bvar\s+(\w+)', codigo)
            sugerencias.extend(variables)
            
            # Buscar asignaciones cortas: nombre :=
            variables_cortas = re.findall(r'\b(\w+)\s*:=', codigo)
            sugerencias.extend(variables_cortas)
        
        # Eliminar duplicados y ordenar
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
            
            # Buscar definición en el código
            codigo = tab_actual.texto_codigo.get("1.0", tk.END)
            lineas = codigo.split('\n')
            
            import re
            
            # Buscar func nombre(
            patron_func = rf'\bfunc\s+{re.escape(simbolo)}\s*\('
            # Buscar var nombre
            patron_var = rf'\bvar\s+{re.escape(simbolo)}\b'
            # Buscar nombre :=
            patron_short = rf'\b{re.escape(simbolo)}\s*:='
            # Buscar const nombre
            patron_const = rf'\bconst\s+{re.escape(simbolo)}\b'
            # Buscar type nombre
            patron_type = rf'\btype\s+{re.escape(simbolo)}\b'
            
            for i, linea in enumerate(lineas):
                if (re.search(patron_func, linea) or 
                    re.search(patron_var, linea) or 
                    re.search(patron_short, linea) or
                    re.search(patron_const, linea) or
                    re.search(patron_type, linea)):
                    
                    # No navegar a la misma línea donde estamos
                    if i + 1 == linea_num:
                        continue
                    
                    # Ir a la línea de definición
                    tab_actual.texto_codigo.mark_set(tk.INSERT, f"{i+1}.0")
                    tab_actual.texto_codigo.see(f"{i+1}.0")
                    
                    # Resaltar temporalmente la línea
                    tab_actual.texto_codigo.tag_remove("definicion_highlight", "1.0", tk.END)
                    tab_actual.texto_codigo.tag_add("definicion_highlight", f"{i+1}.0", f"{i+1}.end")
                    tab_actual.texto_codigo.tag_config("definicion_highlight", background="#FFD700", foreground="#000")
                    
                    # Remover resaltado después de 1 segundo
                    self.root.after(1000, lambda: tab_actual.texto_codigo.tag_remove("definicion_highlight", "1.0", tk.END))
                    
                    # Mostrar en barra de estado
                    self.actualizar_status_bar()
                    break
            else:
                # No se encontró definición
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
        self.terminal_frame = tk.Frame(self.editor_frame, bg="#1e1e1e", height=200)
        self.terminal_frame.pack(side=tk.BOTTOM, fill=tk.BOTH)
        
        # Label de título
        titulo_term = tk.Label(self.terminal_frame, text="TERMINAL", 
                              bg="#007acc", fg="white", 
                              font=("Segoe UI", 9, "bold"), 
                              anchor="w", padx=10)
        titulo_term.pack(fill=tk.X)
        
        # Frame para entrada y botones
        frame_controles = tk.Frame(self.terminal_frame, bg="#2d2d30")
        frame_controles.pack(fill=tk.X, pady=2)
        
        # Entry para comandos
        self.terminal_input = tk.Entry(frame_controles, bg="#3c3c3c", fg="white",
                                       font=("Consolas", 10), insertbackground="white",
                                       relief="flat")
        self.terminal_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.terminal_input.bind('<Return>', lambda e: self.ejecutar_comando_terminal())
        
        # Botón ejecutar
        btn_ejecutar = tk.Button(frame_controles, text="▶ Ejecutar", 
                                command=self.ejecutar_comando_terminal,
                                bg="#007acc", fg="white", 
                                font=("Segoe UI", 9), relief="flat")
        btn_ejecutar.pack(side=tk.LEFT, padx=5)
        
        # Botón limpiar
        btn_limpiar = tk.Button(frame_controles, text="🗑 Limpiar", 
                               command=self.limpiar_terminal,
                               bg="#c93c37", fg="white", 
                               font=("Segoe UI", 9), relief="flat")
        btn_limpiar.pack(side=tk.LEFT, padx=5)
        
        # Área de salida
        scroll_term = tk.Scrollbar(self.terminal_frame)
        scroll_term.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.terminal_text = tk.Text(self.terminal_frame, 
                                     bg="#1e1e1e", fg="#cccccc",
                                     font=("Consolas", 10),
                                     yscrollcommand=scroll_term.set,
                                     wrap=tk.WORD, height=10)
        self.terminal_text.pack(fill=tk.BOTH, expand=True)
        scroll_term.config(command=self.terminal_text.yview)
        
        # Mensaje de bienvenida
        self.terminal_text.insert("1.0", "Terminal integrado - Escribe comandos y presiona Enter\n")
        self.terminal_text.insert("end", "=" * 70 + "\n")
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
        """Exporta el código C generado a un archivo"""
        tab_actual = self.get_tab_actual()
        if not tab_actual:
            return
        
        codigo_go = tab_actual.texto_codigo.get("1.0", tk.END)
        
        try:
            # Compilar a C
            from lexer import Lexer
            from parser import Parser
            from compiler import Compiler
            
            lexer = Lexer(codigo_go)
            tokens = lexer.tokenize()
            
            parser = Parser(tokens)
            ast = parser.parse()
            
            compiler = Compiler()
            codigo_c = compiler.compile(ast)
            
            # Preguntar dónde guardar
            from tkinter import filedialog
            archivo_salida = filedialog.asksaveasfilename(
                title="Exportar código C",
                defaultextension=".c",
                filetypes=[("C Source", "*.c"), ("Todos los archivos", "*.*")]
            )
            
            if archivo_salida:
                with open(archivo_salida, 'w', encoding='utf-8') as f:
                    f.write(codigo_c)
                
                messagebox.showinfo("Exportar", f"Código C exportado exitosamente a:\n{archivo_salida}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar código C:\n{str(e)}")
    
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
        
        # Mostrar en ventana
        stats_texto = f"""
📊 ESTADÍSTICAS DEL CÓDIGO

📄 Archivo: {tab_actual.get_display_name()}

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
🚀 Go-APK-IDE-FULL VERSION
        
Un IDE completo para programación en Go-like

✨ Características:
  • Multi-tab con pestañas independientes
  • Resaltado de sintaxis
  • Detección de errores en tiempo real
  • Explorador de archivos
  • Autocompletado inteligente (Ctrl+Space)
  • Go to Definition (F12)
  • Rename Symbol (F2)
  • Snippets (ej: "main" + Tab)
  • Terminal integrado (F8)
  • Zoom con Ctrl+Rueda / Ctrl+0
  • Exportar a C
  • Temas Claro/Oscuro
  • Y mucho más...

⌨️ Atajos de teclado:
  F5  - Ejecutar
  F6  - Compilar a C
  F7  - Generar ensamblador
  F8  - Toggle terminal
  F12 - Ir a definición
  F2  - Renombrar símbolo
  Ctrl+S - Guardar
  Ctrl+F - Buscar
  Ctrl+G - Ir a línea
  Ctrl+D - Duplicar línea
  Ctrl+/ - Comentar/Descomentar
  Ctrl+Space - Autocompletar
  Ctrl+W - Cerrar pestaña
  Ctrl+0 - Resetear zoom

© 2026 - Versión 1.0
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
    def crear_boton(self, parent, text, command, bg, side=tk.LEFT):
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg="white", 
                        font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2, bd=0)
        btn.pack(side=side, padx=3, pady=2)
        btn.bind("<Enter>", lambda e: btn.config(bg=bg)) 
        return btn
    
    # --- MÉTODOS ADAPTADOS PARA EDITOR TAB ---
    
    def resaltar_sintaxis_tab(self, tab, event=None):
        """Resalta sintaxis para una pestaña específica"""
        # Limpiar tags previos
        for tag in ["keyword", "type", "string", "numeros", "comment", "caracteres"]:
            tab.texto_codigo.tag_remove(tag, "1.0", tk.END)

        # Definir patrones
        types = r'(int|Println|string|bool|float64|chan|struct|interface|type)'
        caracteres_especiales = r'[:=+\-*/%&|^!<>(){}\[\],.]'
        keywords = r'(func|var|if|else|for|return|package|import|switch|case|default|range|break|continue|make|append|copy|len|cap|delete|clear|map|fmt)'
        numeros = r'(0b[01]+|0o[0-7]+|0x[\da-fA-F]+|\d+(\.\d+)?([eE][+-]?\d+)?)'
        string = r'".*?"'
        
        # Aplicar en orden
        self.aplicar_regex_tab(tab, keywords, "keyword")
        self.aplicar_regex_tab(tab, types, "type")
        self.aplicar_regex_tab(tab, numeros, "numeros")
        self.aplicar_regex_tab(tab, string, "string")
        self.aplicar_regex_tab(tab, r'//.*', "comment")
        self.aplicar_regex_tab(tab, caracteres_especiales, "caracteres")
    
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
        """Auto-indentación mejorada para Go"""
        try:
            cursor_pos = tab.texto_codigo.index(tk.INSERT)
            linea_num = int(cursor_pos.split('.')[0])
            contenido_linea = tab.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")
            
            # Obtener indentación actual (solo tabs, estándar Go)
            indentacion_actual = ""
            for char in contenido_linea:
                if char == "\t":
                    indentacion_actual += "\t"
                elif char == " ":
                    # Convertir 4 espacios a 1 tab (compatibilidad)
                    continue
                else:
                    break
            
            linea_stripped = contenido_linea.strip()
            nueva_indentacion = indentacion_actual
            
            # CASO 1: Línea termina con { → incrementar indentación
            if linea_stripped.endswith("{"):
                nueva_indentacion = indentacion_actual + "\t"
            
            # CASO 2: Línea termina con { pero también tiene ) antes
            # Ejemplo: func main() {
            elif "{" in linea_stripped and linea_stripped.endswith("{"):
                nueva_indentacion = indentacion_actual + "\t"
            
            # CASO 3: Estructuras de control sin { en la misma línea
            # if, for, switch necesitan { en siguiente línea o ya tienen contenido
            elif any(linea_stripped.startswith(kw) for kw in ['if ', 'for ', 'switch ', 'select ']):
                if not linea_stripped.endswith("{"):
                    # Si no termina en {, mantener misma indentación para poner el {
                    nueva_indentacion = indentacion_actual
                else:
                    nueva_indentacion = indentacion_actual + "\t"
            
            # CASO 4: case o default → mantener indentación del switch
            elif linea_stripped.startswith("case ") or linea_stripped.startswith("default"):
                if linea_stripped.endswith(":"):
                    # Después de case: o default:, incrementar para el contenido
                    nueva_indentacion = indentacion_actual + "\t"
                else:
                    nueva_indentacion = indentacion_actual
            
            # CASO 5: Línea solo tiene } → des-indentar el cursor
            elif linea_stripped == "}":
                # El } ya está escrito, la nueva línea vuelve al nivel del }
                if len(indentacion_actual) > 0:
                    nueva_indentacion = indentacion_actual[:-1] if indentacion_actual.endswith("\t") else indentacion_actual
                else:
                    nueva_indentacion = ""
            
            # CASO 6: } seguido de más código (} else {, } else if {)
            elif "}" in linea_stripped and not linea_stripped.startswith("}"):
                if linea_stripped.endswith("{"):
                    nueva_indentacion = indentacion_actual + "\t"
                else:
                    nueva_indentacion = indentacion_actual
            
            # CASO 7: func nombre() sin { → mantener para próxima línea
            elif linea_stripped.startswith("func ") and not linea_stripped.endswith("{"):
                nueva_indentacion = indentacion_actual
            
            # CASO 8: type, var, const, import 
            elif any(linea_stripped.startswith(kw) for kw in ['type ', 'var ', 'const ', 'import ']):
                nueva_indentacion = indentacion_actual
            
            # CASO 9: Línea termina en coma o operador → probable continuación
            elif linea_stripped.endswith((",", "&&", "||", "+", "-", "*", "/")):
                # Mantener indentación, es continuación
                nueva_indentacion = indentacion_actual
            
            # CASO 10: Apertura de slice/array/struct literal
            elif linea_stripped.endswith("[]int{") or linea_stripped.endswith("]{") or "= []" in linea_stripped:
                if linea_stripped.endswith("{"):
                    nueva_indentacion = indentacion_actual + "\t"
                else:
                    nueva_indentacion = indentacion_actual
            
            # CASO DEFAULT: mantener misma indentación
            else:
                nueva_indentacion = indentacion_actual
            
            # Insertar nueva línea con indentación
            tab.texto_codigo.insert(tk.INSERT, "\n" + nueva_indentacion)
            
            # Marcar como modificado
            tab.archivo_modificado = True
            self.actualizar_titulo_tab()
            
            return "break"
            
        except Exception as e:
            print(f"Error en auto_indentacion_tab: {e}")
            # Fallback: insertar nueva línea sin indentación especial
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
        codigo = self.obtener_codigo()
        if not codigo: return None
        
        self.texto_tokens.delete("1.0", tk.END)
        self.consola.delete("1.0", tk.END)
        
        # 1. VALIDAR INDENTACIÓN PRIMERO
        try:
            checker = IndentationChecker(codigo)
            errors = checker.check()
            if errors:
                self.consola.insert(tk.END, "❌ ERRORES DE INDENTACIÓN DETECTADOS:\n\n", "error")
                for line_num, message in errors:
                    self.consola.insert(tk.END, f"  Línea {line_num}: {message}\n", "error")
                self.consola.insert(tk.END, "\n⚠️ Por favor, corrige la indentación antes de continuar.\n", "error")
                return None
        except Exception as e:
            self.consola.insert(tk.END, f"Error al validar indentación: {e}\n", "error")
            return None
        
        # 2. Crear instancia del Lexer
        lexer_instancia = Lexer(codigo)
        try:
            lista_tokens = lexer_instancia.tokenize()
            
            # Generar el texto para la pestaña de Análisis Léxico
            texto_formateado = ""
            for t in lista_tokens:
                texto_formateado += f"<{t.type.name}, '{t.value}', fila {t.line}>\n"
            
            self.texto_tokens.insert(tk.END, texto_formateado)
            return lista_tokens
        except Exception as e:
            self.consola.insert(tk.END, f"Error Léxico: {e}\n", "error")
            return None

    def accion_ejecutar(self, event=None):
        """Ejecutar código - Pipeline completo: Compilar C + Generar ASM + Ejecutar"""
        lista_tokens = self.procesar_tokens()
        if lista_tokens:
            mi_parser = Parser(lista_tokens) 
            try:
                program = mi_parser.parse()
                if program:
                    # 1. COMPILAR A C
                    try:
                        self.output_c.delete("1.0", tk.END)
                        mi_compiler = Compiler(program)
                        codigo_c = mi_compiler.compile()
                        self.output_c.insert(tk.END, codigo_c)
                        self.consola.insert(tk.END, "✅ Código C generado\n")
                    except Exception as e:
                        self.output_c.delete("1.0", tk.END)
                        self.output_c.insert(tk.END, f"Error de Compilación: {e}\n")
                        self.consola.insert(tk.END, f"⚠️ Error al compilar a C: {e}\n")
                    
                    # 2. GENERAR ENSAMBLADOR
                    try:
                        asm_gen = AssemblyGenerator(program)
                        tac_code, asm_code = asm_gen.generate()
                        
                        # Mostrar código intermedio (TAC)
                        self.output_tac.delete("1.0", tk.END)
                        self.output_tac.insert(tk.END, tac_code)
                        
                        # Mostrar código ensamblador
                        self.output_asm.delete("1.0", tk.END)
                        self.output_asm.insert(tk.END, asm_code)
                        
                        self.consola.insert(tk.END, "✅ Código ensamblador generado\n")
                    except Exception as e:
                        self.output_asm.delete("1.0", tk.END)
                        self.output_asm.insert(tk.END, f"Error al generar ensamblador: {e}\n")
                        self.consola.insert(tk.END, f"⚠️ Error al generar ASM: {e}\n")
                    
                    # 3. EJECUTAR
                    self.consola.insert(tk.END, "\n=== EJECUCIÓN DEL PROGRAMA ===\n")
                    self.notebook.select(self.tab_consola)
                    try:
                        interpreter = Interpreter(program, self.consola)
                        interpreter.run()
                        self.consola.insert(tk.END, "\n✅ Ejecución completada\n")
                    except Exception as e:
                        self.consola.insert(tk.END, f"\n❌ Error de ejecución: {e}\n")
                        
            except Exception as e:
                self.consola.insert(tk.END, f"Error de Sintaxis: {e}\n", "error")

    def accion_compilar(self, event=None):
        lista_tokens = self.procesar_tokens()
        if lista_tokens:
            # Primero generamos el AST con el Parser
            mi_parser = Parser(lista_tokens)
            try:
                program = mi_parser.parse()
                
                if program:
                    self.output_c.delete("1.0", tk.END)
                    self.notebook.select(self.tab_c)
                    # Crear el compilador con el programa AST
                    mi_compiler = Compiler(program)
                    codigo_c = mi_compiler.compile()
                    self.output_c.insert(tk.END, codigo_c)
            except Exception as e:
                self.output_c.delete("1.0", tk.END)
                self.output_c.insert(tk.END, f"Error de Compilación: {e}\n")

    def accion_generar_asm(self, event=None):
        """Genera código ensamblador y código intermedio (TAC)"""
        lista_tokens = self.procesar_tokens()
        if lista_tokens:
            mi_parser = Parser(lista_tokens)
            try:
                program = mi_parser.parse()
                
                if program:
                    # Crear el generador de ensamblador
                    asm_gen = AssemblyGenerator(program)
                    tac_code, asm_code = asm_gen.generate()
                    
                    # Mostrar código intermedio (TAC)
                    self.output_tac.delete("1.0", tk.END)
                    self.output_tac.insert(tk.END, tac_code)
                    
                    # Mostrar código ensamblador
                    self.output_asm.delete("1.0", tk.END)
                    self.output_asm.insert(tk.END, asm_code)
                    
                    # Cambiar a la pestaña de ensamblador
                    self.notebook.select(self.tab_asm)
                    
                    self.consola.insert(tk.END, ">> Código ensamblador generado correctamente.\n")
                    self.consola.insert(tk.END, ">> Use 'Guardar Ensamblador' para exportar el archivo .asm\n")
                    
            except Exception as e:
                self.output_asm.delete("1.0", tk.END)
                self.output_asm.insert(tk.END, f"Error al generar ensamblador: {e}\n")
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
        """Abre un archivo en una nueva pestaña o en la actual si está vacía"""
        ruta = filedialog.askopenfilename(filetypes=[("Go Files", "*.go"), ("Text", "*.txt"), ("All Files", "*.*")])
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
        
        ruta = filedialog.asksaveasfilename(defaultextension=".go", filetypes=[("Go Files", "*.go"), ("All Files", "*.*")])
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
        ventana_buscar.geometry("400x160")
        ventana_buscar.configure(bg="#252526")
        ventana_buscar.transient(self.root)
        ventana_buscar.resizable(False, False)

        # Configurar la cuadrícula
        ventana_buscar.columnconfigure(1, weight=1)

        # --- INTERFAZ ---
        tk.Label(ventana_buscar, text="🔍 Buscar:", bg="#252526", fg="white", font=("Segoe UI", 10)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        entry_buscar = tk.Entry(ventana_buscar, bg="white", fg="black", font=("Consolas", 10))
        entry_buscar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        entry_buscar.focus_set()
        entry_buscar.bind("<KeyRelease>", lambda e: buscar())

        tk.Label(ventana_buscar, text="✏️ Reemplazar con:", bg="#252526", fg="white", font=("Segoe UI", 10)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        entry_remplazar = tk.Entry(ventana_buscar, bg="white", fg="black", font=("Consolas", 10))
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
        frame_botones = tk.Frame(ventana_buscar, bg="#252526")
        frame_botones.grid(row=2, column=0, columnspan=2, pady=10)

        btn_buscar = tk.Button(frame_botones, text="Buscar", command=buscar, bg="#007acc", fg="white", width=12, relief="flat")
        btn_buscar.pack(side=tk.LEFT, padx=5)

        btn_reemplazar = tk.Button(frame_botones, text="Reemplazar Todo", command=reemplazar, bg="#d35400", fg="white", width=15, relief="flat")
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
            self.root.title("Go-APK-IDE - FULL VERSION")
            return
        
        if tab_actual.ruta_actual:
            nombre = os.path.basename(tab_actual.ruta_actual)
        else:
            nombre = "Sin título"
        
        modificado = " *" if tab_actual.archivo_modificado else ""
        self.root.title(f"Go-APK-IDE - {nombre}{modificado}")
    
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
        ventana.geometry("300x100")
        ventana.configure(bg="#252526")
        ventana.transient(self.root)
        ventana.resizable(False, False)
        
        tk.Label(ventana, text="Número de línea:", bg="#252526", fg="white", 
                font=("Segoe UI", 10)).pack(pady=10)
        
        entry = tk.Entry(ventana, font=("Consolas", 11), width=20)
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
            
            # Verificar si todas las líneas están comentadas
            todas_comentadas = True
            for linea in range(start_line, end_line + 1):
                contenido = tab_actual.texto_codigo.get(f"{linea}.0", f"{linea}.end").lstrip()
                if contenido and not contenido.startswith("//"):
                    todas_comentadas = False
                    break
            
            # Comentar o descomentar
            for linea in range(start_line, end_line + 1):
                contenido = tab_actual.texto_codigo.get(f"{linea}.0", f"{linea}.end")
                
                if todas_comentadas:
                    # Descomentar: quitar // y espacios siguientes
                    sin_espacios = contenido.lstrip()
                    if sin_espacios.startswith("//"):
                        espacios_iniciales = len(contenido) - len(sin_espacios)
                        nuevo_contenido = contenido[:espacios_iniciales] + sin_espacios[2:].lstrip()
                        tab_actual.texto_codigo.delete(f"{linea}.0", f"{linea}.end")
                        tab_actual.texto_codigo.insert(f"{linea}.0", nuevo_contenido)
                else:
                    # Comentar: agregar // al inicio (respetando indentación)
                    sin_espacios = contenido.lstrip()
                    if sin_espacios:  # Solo si la línea no está vacía
                        espacios_iniciales = len(contenido) - len(sin_espacios)
                        nuevo_contenido = contenido[:espacios_iniciales] + "// " + sin_espacios
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
    app = SimuladorGo(root)
    root.mainloop()