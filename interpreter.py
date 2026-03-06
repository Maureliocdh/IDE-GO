"""
interpreter.py — Ejecutor de codigo Python usando subprocess.
"""
import subprocess
import tempfile
import os
import sys
import tkinter as tk


class Interpreter:
    """Ejecuta codigo Python en un proceso separado y muestra la salida."""

    def __init__(self, program, console, source: str = ""):
        # program puede ser None (compatibilidad con interfaz anterior)
        self.program = program
        self.console = console
        self.source = source

    def set_source(self, source: str):
        self.source = source

    def run(self):
        if not self.source:
            self.console.insert(tk.END, "Error: No hay codigo fuente para ejecutar\n")
            return

        # Guardar en archivo temporal
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        )
        tmp.write(self.source)
        tmp.close()
        tmp_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )

            if result.stdout:
                self.console.insert(tk.END, result.stdout)

            if result.stderr:
                self.console.insert(tk.END, "\n--- Errores/Advertencias ---\n")
                self.console.insert(tk.END, result.stderr)

            if result.returncode != 0:
                self.console.insert(
                    tk.END, f"\n[Proceso termino con codigo {result.returncode}]\n"
                )
        except subprocess.TimeoutExpired:
            self.console.insert(
                tk.END, "\n[ERROR: El programa excedio el tiempo maximo de ejecucion (30s)]\n"
            )
        except Exception as e:
            self.console.insert(tk.END, f"\n[ERROR al ejecutar: {e}]\n")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
