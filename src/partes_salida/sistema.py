"""Registro de la aplicación y arranque con la sesión del sistema."""

from __future__ import annotations

import faulthandler
import logging
import logging.handlers
import plistlib
import sys
from datetime import date
from pathlib import Path

from .rutas import carpeta_datos

ETIQUETA_MAC = "es.epla.partessalida"
CLAVE_WINDOWS = "PartesDeSalida"
_falta = None


def configurar_registro() -> Path:
    global _falta
    carpeta = carpeta_datos() / "logs"
    carpeta.mkdir(exist_ok=True)
    ruta = carpeta / f"app_{date.today():%Y%m%d}.log"
    manejador = logging.handlers.RotatingFileHandler(ruta, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(manejador)
    if sys.stderr is not None and not getattr(sys, "frozen", False):
        raiz.addHandler(logging.StreamHandler())
    _falta = open(carpeta / "faulthandler.log", "a", encoding="utf-8")  # noqa: SIM115
    faulthandler.enable(_falta)
    return ruta


def _orden() -> list[str]:
    return [sys.executable, "--segundo-plano"]


def arranque_con_sistema(activar: bool) -> bool:
    """Abre la aplicación (oculta en la barra) al iniciar sesión. Sólo instalada."""
    if not getattr(sys, "frozen", False):
        return False
    if sys.platform == "darwin":
        ruta = Path.home() / "Library" / "LaunchAgents" / f"{ETIQUETA_MAC}.plist"
        if activar:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(
                plistlib.dumps({"Label": ETIQUETA_MAC, "ProgramArguments": _orden(), "RunAtLoad": True})
            )
        elif ruta.exists():
            ruta.unlink()
        return True
    if sys.platform == "win32":
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE
        ) as clave:
            if activar:
                winreg.SetValueEx(clave, CLAVE_WINDOWS, 0, winreg.REG_SZ, " ".join(f'"{p}"' if " " in p else p for p in _orden()))
            else:
                try:
                    winreg.DeleteValue(clave, CLAVE_WINDOWS)
                except FileNotFoundError:
                    pass
        return True
    return False
