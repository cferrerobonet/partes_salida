"""Cifrado en reposo con una clave que nadie teclea.

La clave (AES-256) la genera la aplicación la primera vez y la guarda el llavero
del sistema: el Llavero de macOS o el Administrador de credenciales de Windows.
Quien copie la carpeta de datos, o una copia de seguridad del equipo, se lleva
archivos que no puede leer.

Sin llavero (Linux sin servicio de secretos, pruebas con
`PARTES_SALIDA_SIN_LLAVERO=1`) el secreto va a un archivo junto a los datos, con
permisos sólo para el usuario, y queda anotado en el registro.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .rutas import carpeta_datos

logger = logging.getLogger(__name__)

SERVICIO = "PartesSalida"
_CABECERA = b"PS1"


class ErrorDeCifrado(Exception):
    """El archivo no se puede descifrar con la clave de este equipo."""


def _sin_llavero() -> bool:
    return os.environ.get("PARTES_SALIDA_SIN_LLAVERO") == "1"


def _archivo(nombre: str):
    carpeta = carpeta_datos() / ".secretos"
    carpeta.mkdir(exist_ok=True)
    return carpeta / nombre


def _leer_archivo(nombre: str) -> str | None:
    ruta = _archivo(nombre)
    return ruta.read_text(encoding="utf-8").strip() if ruta.exists() else None


def _escribir_archivo(nombre: str, valor: str) -> None:
    ruta = _archivo(nombre)
    ruta.write_text(valor, encoding="utf-8")
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass


def leer_secreto(nombre: str) -> str | None:
    if _sin_llavero():
        return _leer_archivo(nombre)
    try:
        import keyring

        valor = keyring.get_password(SERVICIO, nombre)
    except Exception as e:  # noqa: BLE001 - sin llavero en este sistema
        logger.warning("Llavero no disponible (%s); se usa el archivo local", e)
        return _leer_archivo(nombre)
    return valor if valor is not None else _leer_archivo(nombre)


def guardar_secreto(nombre: str, valor: str) -> None:
    if _sin_llavero():
        _escribir_archivo(nombre, valor)
        return
    try:
        import keyring

        keyring.set_password(SERVICIO, nombre, valor)
    except Exception as e:  # noqa: BLE001
        logger.warning("Llavero no disponible (%s); el secreto va a un archivo local", e)
        _escribir_archivo(nombre, valor)


def borrar_secreto(nombre: str) -> None:
    ruta = _archivo(nombre)
    if ruta.exists():
        ruta.unlink()
    if _sin_llavero():
        return
    try:
        import keyring

        keyring.delete_password(SERVICIO, nombre)
    except Exception:  # noqa: BLE001 - no estaba
        pass


class Cifrador:
    def __init__(self, clave: bytes):
        self._clave = clave
        self._aes = AESGCM(clave)

    @classmethod
    def del_llavero(cls, nombre: str = "clave-datos") -> Cifrador:
        guardada = leer_secreto(nombre)
        if guardada:
            return cls(base64.b64decode(guardada))
        clave = AESGCM.generate_key(bit_length=256)
        guardar_secreto(nombre, base64.b64encode(clave).decode("ascii"))
        logger.info("Clave de datos nueva creada en el llavero")
        return cls(clave)

    def cifrar(self, datos: bytes, contexto: bytes = b"") -> bytes:
        nonce = os.urandom(12)
        return _CABECERA + nonce + self._aes.encrypt(nonce, datos, contexto)

    def descifrar(self, blob: bytes, contexto: bytes = b"") -> bytes:
        if not blob.startswith(_CABECERA) or len(blob) < 31:
            raise ErrorDeCifrado("El archivo no tiene el formato esperado")
        try:
            return self._aes.decrypt(blob[3:15], blob[15:], contexto)
        except InvalidTag as e:
            raise ErrorDeCifrado("La clave de este equipo no abre el archivo") from e

    def huella(self, texto: str) -> str:
        """Nombre de archivo que no delata a quién pertenece (HMAC del identificador)."""
        return hmac.new(self._clave, texto.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
