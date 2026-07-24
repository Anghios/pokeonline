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
import webbrowser
from tkinter import font as tkfont
from tkinter import messagebox

try:
    from PIL import Image, ImageTk
except ImportError:  # sin Pillow la app funciona, solo se queda sin banner
    Image = ImageTk = None

VERSION = "0.1.0"
GITHUB_URL = "https://github.com/Anghios/pokeonline"

HOST = "193.84.49.20"
PORT = 25565
TIMEOUT = 3.0
INTERVALO_MS = 5000
ANCHO = 470

# Carpeta donde vive la app: junto al .py o junto al .exe si se empaqueta.
# De aqui cuelgan los archivos del juego (editables por el usuario).
BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__))
INI_PATH = os.path.join(BASE_DIR, "Data", "serverinfo.ini")
GAME_PATH = os.path.join(BASE_DIR, "Game.exe")

# Carpeta de recursos propios (el icono). PyInstaller los descomprime en
# una carpeta temporal, asi que no es la misma ruta que BASE_DIR.
RES_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
ICON_PATH = os.path.join(RES_DIR, "images", "icono.ico")
BANNER_PATH = os.path.join(RES_DIR, "images", "banner.jpg")

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
AMBAR_OSCURO = "#e09a2e"
GH = "#24292f"
GH_CLARO = "#3a4149"


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


def escribir_ini():
    """Crea (o reescribe) Data/serverinfo.ini con la configuracion correcta."""
    os.makedirs(os.path.dirname(INI_PATH), exist_ok=True)
    contenido = "".join(f"{c}={v}\n" for c, v in CONTENIDO_ESPERADO.items())
    with open(INI_PATH, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(contenido)


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
        self._poner_icono()
        self._poner_banner()

        self.tarjeta_red = Tarjeta(self, "Conexion")
        self.tarjeta_red.pack(fill="x", padx=24, pady=(18, 10))

        self.tarjeta_ini = Tarjeta(self, "Configuracion local")
        self.tarjeta_ini.pack(fill="x", padx=24)

        # Solo se muestra cuando la configuracion falta o esta mal
        self.boton_parche = tk.Button(self, text="Parchear juego",
                                      command=self.parchear,
                                      bg=AMBAR, fg="#2a1a00",
                                      activebackground=AMBAR_OSCURO,
                                      activeforeground="#2a1a00",
                                      bd=0, relief="flat", pady=9,
                                      cursor="hand2",
                                      font=tkfont.Font(family="Segoe UI",
                                                       size=10,
                                                       weight="bold"))

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
        pie.pack(fill="x", padx=24, pady=(14, 16))

        tk.Label(pie, text=f"v{VERSION}", bg=BG, fg=TXT_SUAVE,
                 font=tkfont.Font(family="Segoe UI", size=9),
                 anchor="w").pack(side="left", pady=(4, 0))

        self.enlace = tk.Label(pie, text="  GitHub  ↗  ", bg=GH, fg=TXT,
                               cursor="hand2", padx=6, pady=4,
                               font=tkfont.Font(family="Segoe UI", size=9,
                                                weight="bold"))
        self.enlace.pack(side="right")
        self.enlace.bind("<Button-1>", lambda _e: self.abrir_github())
        self.enlace.bind("<Enter>", lambda _e: self.enlace.config(bg=GH_CLARO))
        self.enlace.bind("<Leave>", lambda _e: self.enlace.config(bg=GH))

        self._ajustar_alto()

        self._trabajando = False
        self._cola = queue.Queue()
        # ids de los dos temporizadores, para cancelarlos al cerrar
        self._id_cola = self._id_ciclo = None
        self.comprobar()
        self._vaciar_cola()

    def _ajustar_alto(self):
        """Ancho fijo, alto al contenido (cambia al aparecer el parche)."""
        self.update_idletasks()
        self.geometry(f"{ANCHO}x{self.winfo_reqheight()}")

    def _poner_banner(self):
        """Banner a lo ancho de la ventana. Sin Pillow no se puede leer
        un .jpg, asi que en ese caso simplemente no se muestra."""
        if Image is None or not os.path.isfile(BANNER_PATH):
            return
        try:
            im = Image.open(BANNER_PATH)
            alto = round(im.height * ANCHO / im.width)
            im = im.resize((ANCHO, alto), Image.LANCZOS)
            # se guarda en el objeto: si se recolecta, tkinter la borra
            self._banner = ImageTk.PhotoImage(im)
        except OSError:
            return
        tk.Label(self, image=self._banner, bg=BG, bd=0).pack()

    def abrir_github(self):
        webbrowser.open_new_tab(GITHUB_URL)

    def _mostrar_parche(self, visible):
        if visible == self.boton_parche.winfo_ismapped():
            return
        if visible:
            self.boton_parche.pack(fill="x", padx=24, pady=(16, 0),
                                   before=self.boton_jugar)
        else:
            self.boton_parche.pack_forget()
        self._ajustar_alto()

    def parchear(self):
        """Crea Data/serverinfo.ini con la configuracion correcta."""
        try:
            escribir_ini()
        except OSError as e:
            messagebox.showerror("Parchear juego",
                                 f"No se pudo crear el archivo:\n{e}")
            return
        self.comprobar()

    def _poner_icono(self):
        """Icono de la ventana. Si falta, la app sigue funcionando igual."""
        try:
            self.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass

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
            return
        # el juego ya corre por su cuenta: el lanzador sobra
        self.cerrar()

    def cerrar(self):
        """Cancela las comprobaciones pendientes y cierra la ventana."""
        for ident in (self._id_cola, self._id_ciclo):
            if ident is not None:
                self.after_cancel(ident)
        self._id_cola = self._id_ciclo = None
        self.destroy()

    def comprobar(self):
        if self._trabajando:
            return
        self._trabajando = True
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
        self._id_cola = self.after(150, self._vaciar_cola)

    def _pintar(self, online, estado_ini, msg_ini):
        if online:
            self.tarjeta_red.actualizar("Servidor multiplayer online", VERDE)
        else:
            self.tarjeta_red.actualizar("Servidor multiplayer offline", ROJO)

        colores = {"ok": VERDE, "malo": AMBAR, "falta": ROJO}
        self.tarjeta_ini.actualizar(msg_ini, colores[estado_ini])
        self._mostrar_parche(estado_ini != "ok")

        self._trabajando = False
        self._id_ciclo = self.after(INTERVALO_MS, self.comprobar)


if __name__ == "__main__":
    App().mainloop()
