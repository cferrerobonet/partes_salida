"""Monta la web del vigilante (`vigilante/`) lista para publicar en GitHub Pages.

    python scripts/web_vigilante.py _site

Copia la app, las fuentes de la app de escritorio y los iconos de `imagenes/`, y pone la
versión de `pyproject.toml` (más el commit, si lo da GitHub) en `app.js` y `sw.js`: así cada
publicación cambia el service worker y los móviles se actualizan solos. Los documentos del
contrato (`ESPECIFICACION_QR.md`, `vectores_qr.json`) no se publican.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "vigilante"
FUENTES = RAIZ / "src" / "partes_salida" / "recursos" / "fuentes"

NO_SE_PUBLICA = {"ESPECIFICACION_QR.md", "vectores_qr.json", "README.md"}
FUENTES_USADAS = [
    "Barlow-Regular.ttf",
    "Barlow-SemiBold.ttf",
    "Barlow-Bold.ttf",
    "BarlowCondensed-Bold.ttf",
    "JetBrainsMono.ttf",
    "OFL-Barlow.txt",
    "OFL-JetBrainsMono.txt",
]
ICONOS = {
    "icono-192.png": "vigilante-192.png",
    "icono-512.png": "vigilante-512.png",
    "icono-maskable-512.png": "vigilante-512.png",
    "apple-touch-icon.png": "vigilante-apple-touch-icon.png",
}


def version() -> str:
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    v = re.search(r'^version = "(.+)"', texto, re.M).group(1)
    commit = os.environ.get("GITHUB_SHA", "")[:7]
    return f"{v}+{commit}" if commit else v


def montar(destino: Path, marca: str | None = None) -> Path:
    marca = marca or version()
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(ORIGEN, destino, ignore=lambda _d, nombres: [n for n in nombres if n in NO_SE_PUBLICA])
    for nombre in ("app.js", "sw.js"):
        ruta = destino / nombre
        ruta.write_text(ruta.read_text(encoding="utf-8").replace("__VERSION__", marca), encoding="utf-8")
    (destino / "fuentes").mkdir()
    for nombre in FUENTES_USADAS:
        shutil.copy2(FUENTES / nombre, destino / "fuentes" / nombre)
    (destino / "iconos").mkdir()
    for publicado, origen in ICONOS.items():
        shutil.copy2(RAIZ / "imagenes" / origen, destino / "iconos" / publicado)
    (destino / ".nojekyll").write_text("", encoding="utf-8")
    return destino


if __name__ == "__main__":
    salida = montar(Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve())
    print(f"Web del vigilante {version()} en {salida}")
