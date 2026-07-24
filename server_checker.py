"""Monitor del servidor multiplayer.

Comprueba de forma continua:
  1. Si hay conexion TCP con 193.84.49.20:25565
  2. Si existe Data/serverinfo.ini y su contenido es el esperado
"""

import os
import queue
import socket
import sys
import threading
import tkinter as tk
from tkinter import font as tkfont

HOST = "193.84.49.20"
PORT = 25565
TIMEOUT = 3.0
INTERVALO_MS = 5000

# Ruta base: junto al .py o junto al .exe si se empaqueta
BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__))
INI_PATH = os.path.join(BASE_DIR, "Data", "serverinfo.ini")

CONTENIDO_ESPERADO = {"HOST": HOST, "PORT": str(PORT)}

# Paleta
BG = "#12141c"
CARD = "#1c1f2b"
CARD_BORDE = "#2b3040"
TXT = "#e6e8ef"
TXT_SUAVE = "#8b90a3"
VERDE = "#3ddc84"
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
    """
    if not os.path.isfile(INI_PATH):
        return "falta", "Juego no preparado para jugar online"

    try:
        with open(INI_PATH, "r", encoding="utf-8-sig") as f:
            lineas = f.read().splitlines()
    except OSError as e:
        return "malo", f"No se pudo leer serverinfo.ini ({e.strerror})"

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
        actual = valores.get(clave)
        if actual is None:
            return "malo", f"Falta '{clave}' en serverinfo.ini"
        if actual != esperado:
            return "malo", f"{clave} incorrecto: '{actual}' (esperado '{esperado}')"

    return "ok", "Juego preparado para jugar online"


class Tarjeta(tk.Frame):
    """Tarjeta con titulo, punto de estado y texto de estado."""

    def __init__(self, padre, titulo, subtitulo):
        super().__init__(padre, bg=CARD, highlightbackground=CARD_BORDE,
                         highlightthickness=1, bd=0)

        tk.Label(self, text=titulo.upper(), bg=CARD, fg=TXT_SUAVE,
                 font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                 anchor="w").pack(fill="x", padx=18, pady=(14, 0))

        fila = tk.Frame(self, bg=CARD)
        fila.pack(fill="x", padx=18, pady=(6, 0))

        self.punto = tk.Canvas(fila, width=14, height=14, bg=CARD,
                               highlightthickness=0)
        self._circulo = self.punto.create_oval(2, 2, 12, 12, fill=AMBAR,
                                               outline="")
        self.punto.pack(side="left", pady=(3, 0))

        self.estado = tk.Label(fila, text="Comprobando...", bg=CARD, fg=TXT,
                               font=tkfont.Font(family="Segoe UI", size=13,
                                                weight="bold"),
                               anchor="w", justify="left", wraplength=380)
        self.estado.pack(side="left", padx=(10, 0), fill="x", expand=True)

        self.detalle = tk.Label(self, text=subtitulo, bg=CARD, fg=TXT_SUAVE,
                                font=tkfont.Font(family="Segoe UI", size=9),
                                anchor="w", justify="left", wraplength=400)
        self.detalle.pack(fill="x", padx=18, pady=(4, 16))

    def actualizar(self, texto, color, detalle=None):
        self.estado.config(text=texto, fg=color)
        self.punto.itemconfig(self._circulo, fill=color)
        if detalle is not None:
            self.detalle.config(text=detalle)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PokeOnline - Estado del servidor")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.minsize(470, 0)

        cab = tk.Frame(self, bg=BG)
        cab.pack(fill="x", padx=24, pady=(22, 4))
        tk.Label(cab, text="Estado del multijugador", bg=BG, fg=TXT,
                 font=tkfont.Font(family="Segoe UI", size=16, weight="bold"),
                 anchor="w").pack(fill="x")
        tk.Label(cab, text=f"{HOST}:{PORT}", bg=BG, fg=TXT_SUAVE,
                 font=tkfont.Font(family="Consolas", size=9),
                 anchor="w").pack(fill="x")

        self.tarjeta_red = Tarjeta(self, "Conexion", f"Puerto TCP {PORT}")
        self.tarjeta_red.pack(fill="x", padx=24, pady=(16, 10))

        self.tarjeta_ini = Tarjeta(self, "Configuracion local",
                                   os.path.join("Data", "serverinfo.ini"))
        self.tarjeta_ini.pack(fill="x", padx=24)

        pie = tk.Frame(self, bg=BG)
        pie.pack(fill="x", padx=24, pady=(14, 16), side="bottom")

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
            self.tarjeta_red.actualizar("Servidor multiplayer online", VERDE,
                                        f"Conexion establecida con {HOST}:{PORT}")
        else:
            self.tarjeta_red.actualizar("Servidor multiplayer offline", ROJO,
                                        f"Sin respuesta de {HOST}:{PORT}")

        colores = {"ok": VERDE, "malo": AMBAR, "falta": ROJO}
        detalle = INI_PATH if estado_ini != "falta" else f"No encontrado: {INI_PATH}"
        self.tarjeta_ini.actualizar(msg_ini, colores[estado_ini], detalle)

        self._trabajando = False
        self.boton.config(state="normal", text="Comprobar ahora")
        self.pie_txt.config(
            text=f"Actualizacion automatica cada {INTERVALO_MS // 1000} s")
        self.after(INTERVALO_MS, self.comprobar)


if __name__ == "__main__":
    App().mainloop()
