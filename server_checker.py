"""Monitor del servidor multiplayer.

Comprueba de forma continua:
  1. Si hay conexion TCP con el servidor
  2. Si existe Data/serverinfo.ini y su contenido es el esperado

Ademas permite lanzar Game.exe desde el boton "Jugar!".
"""

import os
import queue
import socket
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

HOST = "193.84.49.20"
PORT = 25565
TIMEOUT = 3.0
INTERVALO_MS = 5000

# Ruta base: junto al .py o junto al .exe si se empaqueta
BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__))
INI_PATH = os.path.join(BASE_DIR, "Data", "serverinfo.ini")
GAME_PATH = os.path.join(BASE_DIR, "Game.exe")

CONTENIDO_ESPERADO = {"HOST": HOST, "PORT": str(PORT)}

# Paleta
BG = "#12141c"
CARD = "#1c1f2b"
CARD_BORDE = "#2b3040"
TXT = "#e6e8ef"
TXT_SUAVE = "#8b90a3"
VERDE = "#3ddc84"
VERDE_OSCURO = "#2fae68"
ROJO = "#ff5c5c"
AMBAR = "#ffb340"


def comprobar_servidor():
    """Devuelve True si el puerto acepta conexiones."""
    try:
        with socket.create_connection((HOST, PORT), timeout=TIMEOUT):
            return True
    except OSError:
        return False


def comprobar_ini():
    """Devuelve (estado, mensaje).

    estado: 'ok' | 'malo' | 'falta'
    Los mensajes no revelan la direccion del servidor.
    """
    if not os.path.isfile(INI_PATH):
        return "falta", "Juego no preparado para jugar online"

    try:
        with open(INI_PATH, "r", encoding="utf-8-sig") as f:
            lineas = f.read().splitlines()
    except OSError:
        return "malo", "No se pudo leer la configuracion"

    valores = {}
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith((";", "#", "[")):
            continue
        if "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        valores[clave.strip().upper()] = valor.strip()

    for clave, esperado in CONTENIDO_ESPERADO.items():
        if valores.get(clave) != esperado:
            return "malo", "Configuracion de servidor incorrecta"

    return "ok", "Juego preparado para jugar online"


class Tarjeta(tk.Frame):
    """Tarjeta con titulo, punto de estado y texto de estado."""

    def __init__(self, padre, titulo):
        super().__init__(padre, bg=CARD, highlightbackground=CARD_BORDE,
                         highlightthickness=1, bd=0)

        tk.Label(self, text=titulo.upper(), bg=CARD, fg=TXT_SUAVE,
                 font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                 anchor="w").pack(fill="x", padx=18, pady=(14, 0))

        fila = tk.Frame(self, bg=CARD)
        fila.pack(fill="x", padx=18, pady=(6, 16))

        self.punto = tk.Canvas(fila, width=14, height=14, bg=CARD,
                               highlightthickness=0)
        self._circulo = self.punto.create_oval(2, 2, 12, 12, fill=AMBAR,
                                               outline="")
        self.punto.pack(side="left", pady=(3, 0))

        self.estado = tk.Label(fila, text="Comprobando...", bg=CARD, fg=TXT,
                               font=tkfont.Font(family="Segoe UI", size=13,
                                                weight="bold"),
                               anchor="w", justify="left", wraplength=370)
        self.estado.pack(side="left", padx=(10, 0), fill="x", expand=True)

    def actualizar(self, texto, color):
        self.estado.config(text=texto, fg=color)
        self.punto.itemconfig(self._circulo, fill=color)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PokeOnline - Estado del servidor")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.minsize(470, 0)

        tk.Label(self, text="Estado del multijugador", bg=BG, fg=TXT,
                 font=tkfont.Font(family="Segoe UI", size=16, weight="bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(22, 0))

        self.tarjeta_red = Tarjeta(self, "Conexion")
        self.tarjeta_red.pack(fill="x", padx=24, pady=(16, 10))

        self.tarjeta_ini = Tarjeta(self, "Configuracion local")
        self.tarjeta_ini.pack(fill="x", padx=24)

        self.boton_jugar = tk.Button(self, text="Jugar!", command=self.jugar,
                                     bg=VERDE, fg="#0d2018",
                                     activebackground=VERDE_OSCURO,
                                     activeforeground="#0d2018",
                                     bd=0, relief="flat", pady=11,
                                     cursor="hand2",
                                     font=tkfont.Font(family="Segoe UI",
                                                      size=12, weight="bold"))
        self.boton_jugar.pack(fill="x", padx=24, pady=(16, 0))

        pie = tk.Frame(self, bg=BG)
        pie.pack(fill="x", padx=24, pady=(12, 16))

        self.boton = tk.Button(pie, text="Comprobar ahora",
                               command=self.comprobar,
                               bg=CARD, fg=TXT, activebackground=CARD_BORDE,
                               activeforeground=TXT, bd=0, relief="flat",
                               padx=14, pady=7, cursor="hand2",
                               font=tkfont.Font(family="Segoe UI", size=9,
                                                weight="bold"))
        self.boton.pack(side="right")

        self.pie_txt = tk.Label(pie, text="", bg=BG, fg=TXT_SUAVE,
                                font=tkfont.Font(family="Segoe UI", size=8),
                                anchor="w")
        self.pie_txt.pack(side="left", pady=(6, 0))

        # Ancho fijo, alto ajustado al contenido real
        self.update_idletasks()
        self.geometry(f"470x{self.winfo_reqheight()}")

        self._trabajando = False
        self._cola = queue.Queue()
        self.comprobar()
        self._vaciar_cola()

    def jugar(self):
        """Lanza Game.exe desde la carpeta de la aplicacion."""
        if not os.path.isfile(GAME_PATH):
            messagebox.showerror("Jugar",
                                 "No se encuentra Game.exe en la carpeta "
                                 "del juego.")
            return
        try:
            subprocess.Popen([GAME_PATH], cwd=BASE_DIR)
        except OSError as e:
            messagebox.showerror("Jugar", f"No se pudo abrir Game.exe:\n{e}")

    def comprobar(self):
        if self._trabajando:
            return
        self._trabajando = True
        self.boton.config(state="disabled", text="Comprobando...")
        self.pie_txt.config(text="Comprobando...")
        threading.Thread(target=self._trabajo, daemon=True).start()

    def _trabajo(self):
        """Se ejecuta en un hilo aparte para no congelar la ventana."""
        online = comprobar_servidor()
        estado_ini, msg_ini = comprobar_ini()
        self._cola.put((online, estado_ini, msg_ini))

    def _vaciar_cola(self):
        """Recoge resultados del hilo desde el hilo principal de tkinter."""
        try:
            while True:
                self._pintar(*self._cola.get_nowait())
        except queue.Empty:
            pass
        self.after(150, self._vaciar_cola)

    def _pintar(self, online, estado_ini, msg_ini):
        if online:
            self.tarjeta_red.actualizar("Servidor multiplayer online", VERDE)
        else:
            self.tarjeta_red.actualizar("Servidor multiplayer offline", ROJO)

        colores = {"ok": VERDE, "malo": AMBAR, "falta": ROJO}
        self.tarjeta_ini.actualizar(msg_ini, colores[estado_ini])

        self._trabajando = False
        self.boton.config(state="normal", text="Comprobar ahora")
        self.pie_txt.config(
            text=f"Actualizacion automatica cada {INTERVALO_MS // 1000} s")
        self.after(INTERVALO_MS, self.comprobar)


if __name__ == "__main__":
    App().mainloop()
