"""Compila la app a un unico .exe con PyInstaller.

Uso:
    pip install pyinstaller
    python build.py

Deja el resultado en dist\\PokeOnline.exe
"""

import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
NOMBRE = "PokeOnline"
ICONO = os.path.join("images", "icono.ico")
BANNER = os.path.join("images", "banner.jpg")


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("Falta PyInstaller. Instalalo con:\n\n    "
                 "pip install pyinstaller\n")

    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("Falta Pillow (hace falta para el banner). Instalalo con:"
                 "\n\n    pip install pillow\n")

    for recurso in (ICONO, BANNER):
        if not os.path.isfile(os.path.join(AQUI, recurso)):
            sys.exit(f"No se encuentra el recurso: {recurso}")

    orden = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",           # un solo .exe, sin carpeta de dependencias
        "--windowed",          # sin ventana de consola detras
        "--name", NOMBRE,
        "--icon", ICONO,
        # icono y banner viajan dentro del exe
        "--add-data", f"{ICONO};images",
        "--add-data", f"{BANNER};images",
        "server_checker.py",
    ]

    print(" ".join(orden), "\n")
    subprocess.run(orden, cwd=AQUI, check=True)

    # el .spec y build/ son basura intermedia
    shutil.rmtree(os.path.join(AQUI, "build"), ignore_errors=True)
    spec = os.path.join(AQUI, f"{NOMBRE}.spec")
    if os.path.isfile(spec):
        os.remove(spec)

    exe = os.path.join(AQUI, "dist", f"{NOMBRE}.exe")
    print(f"\nListo: {exe}")
    print("Copialo a la carpeta del juego, junto a Game.exe y Data\\")


if __name__ == "__main__":
    main()
