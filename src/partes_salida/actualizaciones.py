"""Aviso de versión nueva publicada en GitHub (mismo esquema que Guardias de patio)."""

from __future__ import annotations

import json
import logging
import platform
import ssl
import urllib.request
from collections.abc import Callable
from threading import Thread
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

REPO = "cferrerobonet/partes_salida"
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
#: Plan B sin API: la API sin autenticar admite 60 consultas por hora y por IP, y
#: en el centro todos los equipos salen por la misma. Esta página redirige a
#: `.../tag/vX.Y.Z`.
RELEASES_WEB = f"https://github.com/{REPO}/releases/latest"
DESCARGAS_WEB = f"https://github.com/{REPO}/releases/download"
PAGINA_DE_RELEASES = RELEASES_WEB

INSTALADOR_POR_SISTEMA = {
    "Darwin": "PartesSalida_v{v}_macOS.dmg",
    "Windows": "PartesDeSalida-{v}-Windows-Setup.exe",
}
_EXTENSION_POR_SISTEMA = {"Darwin": ".dmg", "Windows": ".exe"}
HOSTS_PERMITIDOS = ("api.github.com", "github.com", "objects.githubusercontent.com")


def url_de_confianza(url: str) -> bool:
    partes = urlparse(url or "")
    return partes.scheme == "https" and partes.hostname in HOSTS_PERMITIDOS


def contexto_ssl() -> ssl.SSLContext:
    """TLS con los certificados de `certifi`: el OpenSSL empaquetado no ve los del sistema."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _abrir(url: str):
    if not url_de_confianza(url):
        raise ValueError(f"URL no permitida: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "partes-salida"})
    return urllib.request.urlopen(req, timeout=5, context=contexto_ssl())  # nosec B310


def _buscar_instalador(assets: list) -> str:
    extension = _EXTENSION_POR_SISTEMA.get(platform.system())
    if not extension:
        return ""
    for asset in assets:
        if asset.get("name", "").lower().endswith(extension):
            url = asset.get("browser_download_url", "")
            return url if url_de_confianza(url) else ""
    return ""


def ultima_version() -> tuple[str, str, str]:
    """`(versión, url del instalador, notas)`: la API y, si falla, la web."""
    try:
        with _abrir(RELEASES_URL) as r:
            data = json.loads(r.read())
        return (
            data["tag_name"].lstrip("v"),
            _buscar_instalador(data.get("assets", [])),
            (data.get("body") or "").strip(),
        )
    except Exception as e:  # noqa: BLE001 - límite de la API o red
        logger.info("La API de GitHub no respondió (%s); se pregunta a la web", e)
    with _abrir(RELEASES_WEB) as r:
        destino = r.geturl()
    if "/tag/" not in destino:
        raise ValueError(f"La web no redirigió a una versión: {destino}")
    version = destino.rsplit("/tag/", 1)[1].lstrip("v")
    plantilla = INSTALADOR_POR_SISTEMA.get(platform.system())
    url = f"{DESCARGAS_WEB}/v{version}/{plantilla.format(v=version)}" if plantilla else ""
    return version, url, ""


def es_mas_nueva(nueva: str, actual: str) -> bool:
    try:
        return tuple(int(x) for x in nueva.split(".")) > tuple(int(x) for x in actual.split("."))
    except ValueError:
        return False


def comprobar(actual: str, avisar: Callable[[str, str, str], None], siempre: bool = False) -> None:
    """En segundo plano. `siempre` avisa también si ya está al día (versión vacía)."""

    def _hilo():
        try:
            version, url, notas = ultima_version()
        except Exception as e:  # noqa: BLE001 - nunca debe tumbar la interfaz
            logger.warning("No se pudo comprobar si hay versión nueva: %s", e)
            if siempre:
                avisar("", "", str(e))
            return
        logger.info("Versión instalada %s, última publicada %s", actual, version)
        if es_mas_nueva(version, actual):
            avisar(version, url, notas)
        elif siempre:
            avisar("", "", "")

    Thread(target=_hilo, daemon=True).start()


def abrir_instalador(ruta: str) -> None:
    import os
    import subprocess

    sistema = platform.system()
    if sistema == "Windows":
        os.startfile(ruta)  # noqa: S606  # nosec B606
    elif sistema == "Darwin":
        subprocess.run(["/usr/bin/open", ruta], check=False)  # nosec B603
    else:
        subprocess.run(["/usr/bin/xdg-open", ruta], check=False)  # nosec B603
