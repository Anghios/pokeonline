"""Monitor del servidor multiplayer.

Comprueba de forma continua:
  1. Si hay conexion TCP con el servidor
  2. Si existe Data/serverinfo.ini y su contenido es el esperado

Al arrancar mira ademas si hay una version nueva publicada en GitHub.
Permite lanzar Game.exe desde el boton "Jugar!".
"""

import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # sin Pillow la app funciona, solo se queda sin banner
    Image = ImageTk = None

VERSION = "0.1.1"
GITHUB_URL = "https://github.com/Anghios/pokeonline"
RELEASES_URL = f"{GITHUB_URL}/releases"
API_ULTIMA = "https://api.github.com/repos/Anghios/pokeonline/releases/latest"
DONACIONES_URL = "https://www.paypal.com/paypalme/Anghios"

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
BANNER_GRACIAS = os.path.join(RES_DIR, "images", "agradecimientos.jpg")

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
AZUL = "#4c8dff"
AVISO = "#2a2412"
AVISO_BORDE = "#5a4a1c"

# Historial de cambios. Cada entrada: (version, fecha, [cambios]).
# La columna izquierda de la ventana de changelog es la app (este .exe);
# la derecha es el servidor online, que evoluciona por su cuenta.
CHANGELOG_APP = [
    ("0.1.1", "25/07/2026", [
        "Aviso automatico cuando hay una version nueva en GitHub.",
        "Ventana de agradecimientos.",
        "Ventana de changelog con el historial de la app y del servidor.",
        "Boton de donaciones.",
    ]),
    ("0.1.0", "25/07/2026", [
        "Primera version publica del lanzador.",
        "Comprobacion continua del estado del servidor multijugador.",
        "Boton de parcheo que escribe Data/serverinfo.ini.",
        "Boton de Jugar! que lanza Game.exe y cierra el lanzador.",
        "Compilado a un unico .exe con PyInstaller.",
    ]),
]

CHANGELOG_SERVIDOR = [
    ("1.0.0", "25/07/2026", [
        "Servidor propio en marcha: batallas e intercambios de vuelta.",
        "Emparejamiento por codigo de sala compartido, como espera el juego.",
        "Lectura del formato de equipos del cliente: shinys especiales, "
        "habilidades de Mega y correo.",
        "Validacion de equipos abierta: el modo Random ya no da equipos "
        "rechazados.",
        "Compatibilidad con Python moderno en la maquina del servidor.",
        "Arranque automatico como servicio, pensado para estar 24/7.",
    ]),
]

AGRADECIMIENTOS = [
    ("El proyecto original", [
        "Al equipo de Pokemon Añil, por un juego que sigue mereciendo la "
        "pena aunque su online se apagara.",
    ]),
    ("La comunidad", [
        "Al plugin Cable Club de Eevee Expo, base del protocolo online.",
        "A Vendily y a su fork del plugin, util para entender el formato.",
        "Al hilo de PokeCommunity, donde esta documentado casi todo.",
    ]),
    ("Herramientas", [
        "Python y tkinter, que mueven esta ventana.",
        "Pillow y PyInstaller, que la dejan en un solo .exe.",
    ]),
    ("Y sobre todo", [
        "A Markitos, por empeñarse en jugar con Mei y aguantar ser mi "
        "rata de laboratorio.",
        "A ti, por seguir jugando a algo que ya daban por muerto.",
    ]),
]


_ESTILO_BARRA = False


def barra_scroll(padre, comando):
    """Barra de scroll oscura. La clasica de tkinter sale blanca en
    Windows y desentona, asi que se usa la de ttk con el tema 'clam',
    que si deja elegir los colores."""
    global _ESTILO_BARRA
    if not _ESTILO_BARRA:
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("Oscura.Vertical.TScrollbar", troughcolor=CARD,
                         background=CARD_BORDE, bordercolor=CARD,
                         darkcolor=CARD_BORDE, lightcolor=CARD_BORDE,
                         arrowcolor=TXT_SUAVE, relief="flat")
        estilo.map("Oscura.Vertical.TScrollbar",
                   background=[("active", TXT_SUAVE)])
        _ESTILO_BARRA = True
    return ttk.Scrollbar(padre, orient="vertical", command=comando,
                         style="Oscura.Vertical.TScrollbar")


def cargar_banner(ruta, ancho, alto_max=None):
    """Devuelve la imagen escalada al ancho pedido, o None si no se puede
    (sin Pillow no se leen .jpg). Con alto_max se recorta por el centro en
    vez de deformarla."""
    if Image is None or not os.path.isfile(ruta):
        return None
    try:
        imagen = Image.open(ruta)
        alto = round(imagen.height * ancho / imagen.width)
        imagen = imagen.resize((ancho, alto), Image.LANCZOS)
        if alto_max and alto > alto_max:
            sobra = (alto - alto_max) // 2
            imagen = imagen.crop((0, sobra, ancho, sobra + alto_max))
        return ImageTk.PhotoImage(imagen)
    except OSError:
        return None


_PATRON_VERSION = re.compile(r"\d+(?:\.\d+)+")


def _buscar_version(*textos):
    """Saca el numero de version del primer texto donde aparezca.

    La etiqueta de la release no siempre es la version ('PokeOnline'), asi
    que se mira tambien el titulo ('PokeOnline 0.1.0'). Si en ninguno hay
    algo con pinta de version, devuelve None y no se avisa de nada.
    """
    for texto in textos:
        encontrado = _PATRON_VERSION.search(texto or "")
        if encontrado:
            return encontrado.group(0)
    return None


def _numeros_version(texto):
    """Convierte '1.2.3' en [1, 2, 3]. Los trozos raros cuentan como 0."""
    partes = []
    for trozo in texto.strip().lstrip("vV").split("."):
        digitos = ""
        for caracter in trozo:
            if not caracter.isdigit():
                break
            digitos += caracter
        partes.append(int(digitos) if digitos else 0)
    return partes


def _es_mas_nueva(remota, local):
    a, b = _numeros_version(remota), _numeros_version(local)
    largo = max(len(a), len(b))
    a += [0] * (largo - len(a))
    b += [0] * (largo - len(b))
    return a > b


def comprobar_actualizacion():
    """Mira la ultima release de GitHub.

    Devuelve (version, enlace) si hay una mas nueva que la instalada, o
    None si no la hay, no hay releases todavia o no hay red.
    """
    peticion = urllib.request.Request(API_ULTIMA, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"PokeOnline/{VERSION}",
    })
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None

    version = _buscar_version(datos.get("tag_name"), datos.get("name"))
    if version and _es_mas_nueva(version, VERSION):
        return version, datos.get("html_url") or RELEASES_URL
    return None


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


class Pastilla(tk.Label):
    """Boton pequeno del pie, con cambio de color al pasar el raton."""

    def __init__(self, padre, texto, orden, fondo=GH, fondo_claro=GH_CLARO):
        super().__init__(padre, text=texto, bg=fondo, fg=TXT, cursor="hand2",
                         padx=9, pady=4,
                         font=tkfont.Font(family="Segoe UI", size=9,
                                          weight="bold"))
        self.bind("<Button-1>", lambda _e: orden())
        self.bind("<Enter>", lambda _e: self.config(bg=fondo_claro))
        self.bind("<Leave>", lambda _e: self.config(bg=fondo))


class Ventana(tk.Toplevel):
    """Ventana secundaria con el mismo aspecto que la principal."""

    def __init__(self, padre, titulo, ancho, alto):
        super().__init__(padre, bg=BG)
        self.title(titulo)
        self.transient(padre)
        self.resizable(False, False)
        try:
            self.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass
        self._centrar(padre, ancho, alto)

    def _centrar(self, padre, ancho, alto):
        x = padre.winfo_rootx() + (padre.winfo_width() - ancho) // 2
        y = padre.winfo_rooty() + (padre.winfo_height() - alto) // 2
        # sin dejarla salir de la pantalla
        x = max(0, min(x, self.winfo_screenwidth() - ancho))
        y = max(0, min(y, self.winfo_screenheight() - alto))
        self.geometry(f"{ancho}x{alto}+{x}+{y}")


class VentanaAgradecimientos(Ventana):
    ANCHO = 470
    ALTO = 620

    def __init__(self, padre):
        super().__init__(padre, "PokeOnline - Agradecimientos",
                         self.ANCHO, self.ALTO)

        # cabecera propia; si falta la imagen se cae a un titulo de texto
        self._banner = cargar_banner(BANNER_GRACIAS, self.ANCHO, alto_max=175)
        if self._banner is not None:
            tk.Label(self, image=self._banner, bg=BG, bd=0).pack()
        else:
            tk.Label(self, text="Agradecimientos", bg=BG, fg=TXT, anchor="w",
                     font=tkfont.Font(family="Segoe UI", size=17,
                                      weight="bold")).pack(fill="x", padx=24,
                                                           pady=(20, 2))

        tk.Label(self, text="Esto no sale de la nada.", bg=BG, fg=TXT_SUAVE,
                 anchor="w",
                 font=tkfont.Font(family="Segoe UI",
                                  size=10)).pack(fill="x", padx=24,
                                                 pady=(16, 12))

        # el boton va primero para que se reserve su sitio: lo que queda
        # es para el texto, que ya lleva su propia barra de scroll
        Pastilla(self, "Cerrar", self.destroy).pack(side="bottom",
                                                    pady=(14, 18))

        tarjeta = tk.Frame(self, bg=CARD, highlightbackground=CARD_BORDE,
                           highlightthickness=1, bd=0)
        tarjeta.pack(fill="both", expand=True, padx=24)

        texto = tk.Text(tarjeta, bg=CARD, fg=TXT, bd=0, highlightthickness=0,
                        wrap="word", padx=16, pady=14, cursor="arrow",
                        font=tkfont.Font(family="Segoe UI", size=10),
                        spacing1=2, spacing3=4)
        barra = barra_scroll(tarjeta, texto.yview)
        texto.config(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        texto.pack(side="left", fill="both", expand=True)

        texto.tag_config("titulo", foreground=VERDE,
                         font=tkfont.Font(family="Segoe UI", size=9,
                                          weight="bold"),
                         spacing1=10, spacing3=4)
        texto.tag_config("linea", lmargin1=10, lmargin2=22)

        for titulo, lineas in AGRADECIMIENTOS:
            texto.insert("end", titulo.upper() + "\n", "titulo")
            for linea in lineas:
                texto.insert("end", f"•  {linea}\n", "linea")
        texto.config(state="disabled")


class VentanaChangelog(Ventana):
    ANCHO = 800
    ALTO = 560

    def __init__(self, padre):
        super().__init__(padre, "PokeOnline - Changelog",
                         self.ANCHO, self.ALTO)

        tk.Label(self, text="Changelog", bg=BG, fg=TXT, anchor="w",
                 font=tkfont.Font(family="Segoe UI", size=17,
                                  weight="bold")).pack(fill="x", padx=24,
                                                       pady=(20, 2))
        tk.Label(self, text="La app y el servidor se actualizan por "
                            "separado.", bg=BG, fg=TXT_SUAVE, anchor="w",
                 font=tkfont.Font(family="Segoe UI",
                                  size=10)).pack(fill="x", padx=24,
                                                 pady=(0, 14))

        Pastilla(self, "Cerrar", self.destroy).pack(side="bottom",
                                                    pady=(14, 18))

        columnas = tk.Frame(self, bg=BG)
        columnas.pack(fill="both", expand=True, padx=24)

        izquierda = self._columna(columnas, "[APP]",
                                  "El lanzador que tienes abierto",
                                  CHANGELOG_APP, VERDE)
        izquierda.pack(side="left", fill="both", expand=True)

        derecha = self._columna(columnas, "[SERVERSIDE]",
                                "El servidor multijugador",
                                CHANGELOG_SERVIDOR, AZUL)
        derecha.pack(side="left", fill="both", expand=True, padx=(14, 0))

    @staticmethod
    def _columna(padre, titulo, subtitulo, entradas, color):
        marco = tk.Frame(padre, bg=CARD, highlightbackground=CARD_BORDE,
                         highlightthickness=1, bd=0)

        tk.Label(marco, text=titulo, bg=CARD, fg=color, anchor="w",
                 font=tkfont.Font(family="Segoe UI", size=11,
                                  weight="bold")).pack(fill="x", padx=16,
                                                       pady=(12, 0))
        tk.Label(marco, text=subtitulo, bg=CARD, fg=TXT_SUAVE, anchor="w",
                 font=tkfont.Font(family="Segoe UI",
                                  size=8)).pack(fill="x", padx=16,
                                                pady=(1, 8))

        caja = tk.Frame(marco, bg=CARD)
        caja.pack(fill="both", expand=True, padx=(16, 0), pady=(0, 14))

        texto = tk.Text(caja, bg=CARD, fg=TXT, bd=0, highlightthickness=0,
                        wrap="word", padx=0, pady=0, cursor="arrow", width=1,
                        font=tkfont.Font(family="Segoe UI", size=10),
                        spacing1=2, spacing3=4)
        barra = barra_scroll(caja, texto.yview)
        texto.config(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y", padx=(6, 6))
        texto.pack(side="left", fill="both", expand=True)

        texto.tag_config("version", foreground=color,
                         font=tkfont.Font(family="Segoe UI", size=11,
                                          weight="bold"), spacing1=12)
        texto.tag_config("fecha", foreground=TXT_SUAVE,
                         font=tkfont.Font(family="Segoe UI", size=8),
                         spacing3=4)
        texto.tag_config("linea", lmargin1=8, lmargin2=20)

        for version, fecha, cambios in entradas:
            texto.insert("end", f"v{version}\n", "version")
            texto.insert("end", f"{fecha}\n", "fecha")
            for cambio in cambios:
                texto.insert("end", f"•  {cambio}\n", "linea")
        texto.config(state="disabled")
        return marco


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PokeOnline - Estado del servidor")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.minsize(470, 0)
        self._poner_icono()
        self._poner_banner()

        # Aviso de version nueva: oculto hasta que GitHub diga que la hay
        self.aviso = tk.Label(self, text="", bg=AVISO, fg=AMBAR,
                              highlightbackground=AVISO_BORDE,
                              highlightthickness=1, bd=0,
                              cursor="hand2", pady=10, wraplength=400,
                              font=tkfont.Font(family="Segoe UI", size=10,
                                               weight="bold"))
        self.aviso.bind("<Button-1>", lambda _e: self.abrir_releases())
        self._url_descarga = RELEASES_URL

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

        # se empaquetan de derecha a izquierda: GitHub queda el ultimo
        Pastilla(pie, "GitHub ↗", self.abrir_github).pack(side="right")
        Pastilla(pie, "Changelog", self.abrir_changelog,
                 CARD, CARD_BORDE).pack(side="right", padx=(0, 6))
        Pastilla(pie, "Gracias", self.abrir_agradecimientos,
                 CARD, CARD_BORDE).pack(side="right", padx=(0, 6))
        Pastilla(pie, "Donaciones", self.abrir_donaciones,
                 CARD, CARD_BORDE).pack(side="right", padx=(0, 6))

        self._ventanas = {}
        self._ajustar_alto()

        self._trabajando = False
        self._cola = queue.Queue()
        # ids de los dos temporizadores, para cancelarlos al cerrar
        self._id_cola = self._id_ciclo = None
        self.comprobar()
        self.buscar_actualizacion()
        self._vaciar_cola()

    def _ajustar_alto(self):
        """Ancho fijo, alto al contenido (cambia al aparecer el parche)."""
        self.update_idletasks()
        self.geometry(f"{ANCHO}x{self.winfo_reqheight()}")

    def _poner_banner(self):
        """Banner a lo ancho de la ventana. Si no hay imagen (o falta
        Pillow) simplemente no se muestra."""
        # se guarda en el objeto: si se recolecta, tkinter la borra
        self._banner = cargar_banner(BANNER_PATH, ANCHO)
        if self._banner is not None:
            tk.Label(self, image=self._banner, bg=BG, bd=0).pack()

    def abrir_github(self):
        webbrowser.open_new_tab(GITHUB_URL)

    def abrir_donaciones(self):
        webbrowser.open_new_tab(DONACIONES_URL)

    def abrir_releases(self):
        webbrowser.open_new_tab(self._url_descarga)

    def abrir_changelog(self):
        self._abrir_ventana("changelog", VentanaChangelog)

    def abrir_agradecimientos(self):
        self._abrir_ventana("gracias", VentanaAgradecimientos)

    def _abrir_ventana(self, clave, clase):
        """Abre la ventana, o la trae al frente si ya estaba abierta."""
        ventana = self._ventanas.get(clave)
        if ventana is not None and ventana.winfo_exists():
            ventana.lift()
            ventana.focus_set()
            return
        self._ventanas[clave] = clase(self)

    def buscar_actualizacion(self):
        """Consulta GitHub una vez, al arrancar, sin bloquear la ventana."""
        threading.Thread(target=self._trabajo_actualizacion,
                         daemon=True).start()

    def _trabajo_actualizacion(self):
        novedad = comprobar_actualizacion()
        if novedad:
            self._cola.put(("version", novedad))

    def _mostrar_aviso(self, version, enlace=RELEASES_URL):
        self._url_descarga = enlace
        self.aviso.config(text=f"Hay una version nueva: v{version}  —  "
                               f"pulsa para descargarla")
        if not self.aviso.winfo_ismapped():
            self.aviso.pack(fill="x", padx=24, pady=(18, 0),
                            before=self.tarjeta_red)
            # el aviso se come el hueco de arriba de la primera tarjeta
            self.tarjeta_red.pack_configure(pady=(10, 10))
            self._ajustar_alto()

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
        for ventana in self._ventanas.values():
            if ventana.winfo_exists():
                ventana.destroy()
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
        self._cola.put(("estado", (online, estado_ini, msg_ini)))

    def _vaciar_cola(self):
        """Recoge resultados de los hilos desde el hilo principal de
        tkinter, que es el unico que puede tocar la interfaz."""
        try:
            while True:
                clase, datos = self._cola.get_nowait()
                if clase == "estado":
                    self._pintar(*datos)
                elif clase == "version":
                    self._mostrar_aviso(*datos)
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
