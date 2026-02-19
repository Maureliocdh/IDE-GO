
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import re

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

# --- CLASE PRINCIPAL ---
class SimuladorGo:
    def __init__(self, root):
        self.root = root
        self.root.title("Go-APK-IDE-FULL VERSION")
        self.root.geometry("1200x750")
        
        self.ruta_actual = None 

        self.bg_color = "#1e1e1e"
        self.fg_color = "#d4d4d4"
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
        archivo_menu.add_command(label="Nuevo", command=self.nuevo_archivo)
        archivo_menu.add_command(label="Abrir", command=self.abrir_archivo)
        archivo_menu.add_command(label="Guardar", command=self.guardar)
        archivo_menu.add_command(label="Guardar Como", command=self.guardar_como)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Salir", command=self.cerrar)
        menubar.add_cascade(label="Archivo", menu=archivo_menu)

        # -> Menú Edición
        edicion_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        edicion_menu.add_command(label="Buscar y Reemplazar", command=self.abrir_buscador)
        menubar.add_cascade(label="Edición", menu=edicion_menu)

        # -> Menú Terminal
        terminal_menu = tk.Menu(menubar, tearoff=0, bg="#333", fg="white")
        terminal_menu.add_command(label="Ejecutar Código (F5)", command=self.accion_ejecutar)
        terminal_menu.add_command(label="Compilar a C (F6)", command=self.accion_compilar)
        terminal_menu.add_command(label="Generar Ensamblador (F7)", command=self.accion_generar_asm)
        terminal_menu.add_separator()
        terminal_menu.add_command(label="Guardar Ensamblador (.asm)", command=self.guardar_asm)
        menubar.add_cascade(label="Terminal", menu=terminal_menu)

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

        # --- 3. EDITOR DE CÓDIGO ---
        frame_editor = tk.Frame(self.paned_window, bg=self.bg_color)
        self.paned_window.add(frame_editor, minsize=400)

        self.scrollbar = tk.Scrollbar(frame_editor, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")

        #  AQUI ESTÁ EL CAMBIO IMPORTANTE: Usamos CustomText en lugar de tk.Text
        self.texto_codigo = CustomText(frame_editor, undo=True, width=60, height=30, 
                                    font=("Consolas", 13), bg=self.bg_color, fg=self.fg_color,
                                    insertbackground="white", selectbackground="#264f78",
                                    yscrollcommand=self.scrollbar.set, borderwidth=0)
        
        self.linenumbers = LineNumbers(frame_editor, width=35, bg="#252526", highlightthickness=0)
        self.linenumbers.attach(self.texto_codigo)
        self.linenumbers.pack(side="left", fill="y")
        
        self.texto_codigo.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.texto_codigo.yview)

        # Eventos (Ahora sí funcionan gracias a CustomText)
        self.texto_codigo.bind("<<Change>>", self._on_change)
        self.texto_codigo.bind("<Configure>", self._on_change)
        self.texto_codigo.bind("<KeyRelease>", self.resaltar_sintaxis)
        
        self.root.bind('<Control-s>', self.guardar)      
        self.root.bind('<Control-S>', self.guardar)      
        self.root.bind('<F5>', self.accion_ejecutar)  
        self.root.bind('<F6>', self.accion_compilar)
        self.root.bind('<F7>', self.accion_generar_asm)
        self.root.bind('<Control-f>', lambda e: self.abrir_buscador())
        self.root.bind('<Control-F>', lambda e: self.abrir_buscador())
        

        self.configurar_tags()

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
        
        self.texto_codigo.bind("<Return>", self.auto_indentacion)

    # --- MÉTODOS ---
    def crear_boton(self, parent, text, command, bg, side=tk.LEFT):
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg="white", 
                        font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2, bd=0)
        btn.pack(side=side, padx=3, pady=2)
        btn.bind("<Enter>", lambda e: btn.config(bg=bg)) 
        return btn

    def _on_change(self, event):
        self.linenumbers.redraw()

    def configurar_tags(self):
        self.texto_codigo.tag_config("keyword", foreground="#e572db") 
        self.texto_codigo.tag_config("type", foreground="#569cd6")    
        self.texto_codigo.tag_config("string", foreground="#ce9178")  
        self.texto_codigo.tag_config("numeros", foreground="#4ac73e")  
        self.texto_codigo.tag_config("comment", foreground="#ababab") 
        self.texto_codigo.tag_config("caracteres", foreground="#fffb00")

    def resaltar_sintaxis(self, event=None):
        # 1. Limpiar tags previos
        for tag in ["keyword", "type", "string", "numeros", "comment", "caracteres"]:
            self.texto_codigo.tag_remove(tag, "1.0", tk.END)

        # 2. Definir patrones (Sin \b porque Tkinter.search no siempre lo reconoce bien)
                                    # Usamos una lista de tuplas para mantener el orden)'
        types = r'(int|Println|string|bool|float64|chan|struct|interface|type)'
        caracteres_especiales = r'[:=+\-*/%&|^!<>(){}\[\],.]'
        keywords = r'(func|var|if|else|for|return|package|import|switch|case|default|range|break|continue|make|append|copy|len|cap|delete|clear|map|fmt)'
        numeros = r'(0b[01]+|0o[0-7]+|0x[\da-fA-F]+|\d+(\.\d+)?([eE][+-]?\d+)?)'
        string = r'".*?"'
        
        
        # Aplicar en orden: primero tipos y palabras, luego strings y comentarios
        self.aplicar_regex(keywords, "keyword")
        self.aplicar_regex(types, "type")
        self.aplicar_regex(numeros, "numeros")
        self.aplicar_regex(string, "string")
        self.aplicar_regex(r'//.*', "comment")
        self.aplicar_regex(caracteres_especiales, "caracteres")
        
    def aplicar_regex(self, pattern, tag):
        start = "1.0"
        while True:
            # Buscamos usando el motor de regex de Tkinter
            pos = self.texto_codigo.search(pattern, start, stopindex=tk.END, regexp=True)
            if not pos: 
                break
            
            # Necesitamos saber cuánto midió lo que encontró para calcular el final
            length = tk.IntVar()
            self.texto_codigo.search(pattern, pos, stopindex=tk.END, regexp=True, count=length)
            
            # Si por alguna razón la longitud es 0, avanzamos manualmente para evitar bucle infinito
            if length.get() == 0:
                start = f"{pos}+1c"
                continue
                
            end = f"{pos}+{length.get()}c"
            self.texto_codigo.tag_add(tag, pos, end)
            start = end # El siguiente ciclo empieza donde terminó este
            
    def auto_indentacion(self, event):
        # 1. Obtener la línea actual antes de presionar Enter
        cursor_pos = self.texto_codigo.index(tk.INSERT)
        linea_num = cursor_pos.split('.')[0]
        contenido_linea = self.texto_codigo.get(f"{linea_num}.0", f"{linea_num}.end")

        # 2. Calcular la indentación de la línea actual (espacios/tabs al inicio)
        indentacion = ""
        for char in contenido_linea:
            if char in (" ", "\t"):
                indentacion += char
            else:
                break

        # 3. Si la línea termina con '{', aumentamos la indentación
        if contenido_linea.strip().endswith("{"):
            # Añadimos un tabulador (o 4 espacios si prefieres)
            self.texto_codigo.insert(tk.INSERT, "\n" + indentacion + "\t")
            # Colocamos el cursor al final de la nueva línea
            return "break" # Evita que Tkinter inserte un Enter extra

        # 4. Si no hay llave, solo mantenemos la indentación actual
        else:
            self.texto_codigo.insert(tk.INSERT, "\n" + indentacion)
            return "break"

    def obtener_codigo(self):
        return self.texto_codigo.get("1.0", tk.END).strip()

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
        if self.ruta_actual:
            base_name = os.path.splitext(os.path.basename(self.ruta_actual))[0]
            default_dir = os.path.dirname(self.ruta_actual)
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
        ruta = filedialog.askopenfilename(filetypes=[("Go Files", "*.go"), ("Text", "*.txt")])
        if ruta:
            self.ruta_actual = ruta
            nombre_archivo = os.path.basename(ruta)
            self.root.title(f"Go-Like IDE - {nombre_archivo}")
            
            with open(ruta, "r", encoding="utf-8") as f:
                content = f.read()
                self.texto_codigo.delete("1.0", tk.END)
                self.texto_codigo.insert(tk.END, content)
                self.resaltar_sintaxis()
                # Forzamos redibujo de números
                self.texto_codigo.event_generate("<<Change>>")

    def guardar(self, event=None):
        if self.ruta_actual:
            try:
                with open(self.ruta_actual, "w", encoding="utf-8") as f:
                    f.write(self.texto_codigo.get("1.0", tk.END))
                self.consola.insert(tk.END, f">> Guardado en {os.path.basename(self.ruta_actual)}\n")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")
        else:
            self.guardar_como()

    def guardar_como(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".go", filetypes=[("Go Files", "*.go")])
        if ruta:
            self.ruta_actual = ruta
            nombre_archivo = os.path.basename(ruta)
            self.root.title(f"Go-Like IDE - {nombre_archivo}")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(self.texto_codigo.get("1.0", tk.END))
                
    def nuevo_archivo(self):
        self.ruta_actual = None 
        self.root.title("Go-Like IDE - Sin Título")
        self.texto_codigo.delete("1.0", tk.END)
        self.texto_tokens.delete("1.0", tk.END)
        self.consola.delete("1.0", tk.END)
        self.output_c.delete("1.0", tk.END)
        self._on_change(None) 
    
    def abrir_buscador(self, event=None):
        
        # 1. Configuración de la Ventana Flotante
        ventana_buscar = tk.Toplevel(self.root)
        ventana_buscar.title("Buscar y Reemplazar")
        ventana_buscar.geometry("400x160") # Tamaño fijo suficiente
        ventana_buscar.configure(bg="#252526") # Fondo gris oscuro estilo VSCode
        ventana_buscar.transient(self.root)
        ventana_buscar.resizable(False, False)

        # Configurar la cuadrícula para que se vea ordenado
        ventana_buscar.columnconfigure(1, weight=1) # La columna 1 (inputs) se estira

        # --- INTERFAZ ---
        # Fila 0: Buscar
        tk.Label(ventana_buscar, text="🔍 Buscar:", bg="#252526", fg="white", font=("Segoe UI", 10)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        entry_buscar = tk.Entry(ventana_buscar, bg="white", fg="black", font=("Consolas", 10))
        entry_buscar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        entry_buscar.focus_set() # <--- IMPORTANTE: Pone el cursor aquí automáticamente
        entry_buscar.bind("<KeyRelease>", lambda e: buscar()) # Enter para buscar

        # Fila 1: Reemplazar
        tk.Label(ventana_buscar, text="✏️ Reemplazar con:", bg="#252526", fg="white", font=("Segoe UI", 10)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        entry_remplazar = tk.Entry(ventana_buscar, bg="white", fg="black", font=("Consolas", 10))
        entry_remplazar.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # --- LÓGICA INTERNA ---
        # --- REEMPLAZA TU FUNCIÓN buscar() POR ESTA ---
        def buscar(event=None):
            query = entry_buscar.get()
            
            # Limpiar siempre resaltados previos antes de empezar
            self.texto_codigo.tag_remove("search_highlight", "1.0", tk.END)
            
            # Si el campo está vacío o solo tiene espacios, no hacer nada
            if not query.strip(): 
                return
            
            # Configurar el color del resaltado
            self.texto_codigo.tag_config("search_highlight", background="#f1c40f", foreground="black")
            
            start = "1.0"
            count = 0
            while True:
                pos = self.texto_codigo.search(query, start, stopindex=tk.END, nocase=True)
                if not pos: break
                end = f"{pos}+{len(query)}c"
                self.texto_codigo.tag_add("search_highlight", pos, end)
                start = end
                count += 1
            
            # Solo mostrar el mensaje de error si el usuario presionó el botón "Buscar" 
            # (detectamos esto si el event es None)
            if count == 0 and event is None:
                messagebox.showinfo("Buscador", f"No se encontró '{query}'")

        def reemplazar():
            query = entry_buscar.get()
            replace_text = entry_remplazar.get()
            if not query: return
            
            # Obtener texto actual
            contenido = self.texto_codigo.get("1.0", tk.END)
            
            # Verificar si existe antes de borrar todo
            if re.search(re.escape(query), contenido, re.IGNORECASE):
                nuevo_contenido = re.sub(re.escape(query), replace_text, contenido, flags=re.IGNORECASE)
                # Reemplazo seguro (borrar y pegar)
                self.texto_codigo.delete("1.0", tk.END)
                self.texto_codigo.insert("1.0", nuevo_contenido)
                self.resaltar_sintaxis() # Re-colorear sintaxis
                self.texto_codigo.event_generate("<<Change>>") # Actualizar números de línea
                messagebox.showinfo("Éxito", "Reemplazo completado.")
                ventana_buscar.destroy() # Cerrar ventana al terminar
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

    def cerrar(self):
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorGo(root)
    root.mainloop()