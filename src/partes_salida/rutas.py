"""Dónde vive cada cosa: los datos de este equipo y los recursos de la aplicación."""

import os
import sys
from pathlib import Path

CARPETA = "PartesSalida"


def carpeta_datos() -> Path:
    """Carpeta de datos del usuario. `PARTES_SALIDA_DATOS` la cambia (pruebas)."""
    propia = os.environ.get("PARTES_SALIDA_DATOS")
    if propia:
        base = Path(propia)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / CARPETA
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home()) / CARPETA
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / CARPETA
    base.mkdir(parents=True, exist_ok=True)
    return base


def recursos() -> Path:
    """Logos por defecto y tipografías, dentro del paquete o de la app congelada."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "partes_salida" / "recursos"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "recursos"
