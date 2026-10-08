# -*- mode: python ; coding: utf-8 -*-
# Un único spec para macOS y Windows (lección de Guardias de patio, BLD-008):
#   · nombre: «Partes de salida» en macOS (así lo busca build_dmg.sh) y
#     `PartesDeSalida` en Windows (así lo esperan el instalador y la CI);
#   · icono: .icns en macOS, .ico en Windows; el BUNDLE sólo existe en macOS.
# Rutas siempre con barra normal. Ningún archivo empaquetado lleva acentos en el
# nombre: rompería la firma del .app al copiarlo (BLD-010 de Guardias).
import os
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ES_MACOS = sys.platform == "darwin"
NOMBRE = "Partes de salida" if ES_MACOS else "PartesDeSalida"
VERSION = re.search(
    r'^version = "([^"]+)"', (Path(SPECPATH) / "pyproject.toml").read_text(encoding="utf-8"), re.M
).group(1)
ICONO = "imagenes/icono.icns" if ES_MACOS else "imagenes/icono.ico"
# Variante de diagnóstico (Actions → Compilar → «depurar»): el arranque de
# PyInstaller cuenta cada paso por la consola.
DEPURAR = os.getenv("PARTES_BUILD_DEPURAR") == "1"

datas = [
    # Logos por defecto, icono y tipografías: PyInstaller sólo empaqueta los .py.
    ("src/partes_salida/recursos", "partes_salida/recursos"),
]
# El llavero elige su almacén al ejecutarse; sin esto la app congelada no
# encuentra dónde guardar la clave de cifrado (SEC-001 de Guardias).
hiddenimports = collect_submodules("keyring.backends")
hiddenimports += ["PyQt6.QtPrintSupport", "PyQt6.QtNetwork", "xlrd", "openpyxl", "segno", "rapidfuzz"]

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "PyQt6.QtWebEngineCore", "PyQt6.QtQml", "PyQt6.QtQuick"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Sin UPX: el empaquetado comprimido dispara los antivirus (BLD-011 de Guardias).
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NOMBRE,
    debug="all" if DEPURAR else False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=DEPURAR,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICONO],
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name=NOMBRE)

if ES_MACOS:
    app = BUNDLE(
        coll,
        name=f"{NOMBRE}.app",
        icon=ICONO,
        bundle_identifier="es.epla.partessalida",
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            # La app vive en la barra de menús, pero también en el Dock para que
            # se encuentre fácil; LSUIElement la escondería del Dock.
            "LSUIElement": False,
        },
    )
