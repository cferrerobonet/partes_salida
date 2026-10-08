"""Contenido firmado del QR del parte y su verificación.

Formato (texto, separado por barras; especificación en `android/ESPECIFICACION_QR.md`):

    PS1|<id clave>|<id alumno>|<salida AAAAMMDDhhmm>|<expedido AAAAMMDDhhmm>|<firma>

La firma es Ed25519 sobre todo lo anterior a la última barra, en base64url sin
relleno. Cada equipo tiene su propia clave (en el llavero); la app del vigilante
guarda la pública de cada jefatura, que se le pasa escaneando el QR de Ajustes:

    PSK1|<id clave>|<clave pública base64url>|<nombre del equipo>
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from .cifrado import guardar_secreto, leer_secreto

PREFIJO = "PS1"
PREFIJO_CLAVE = "PSK1"
_FORMATO = "%Y%m%d%H%M"


def b64url(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def de_b64url(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def id_de_clave(publica: bytes) -> str:
    return hashlib.sha256(publica).hexdigest()[:8].upper()


class Firmante:
    def __init__(self, privada: Ed25519PrivateKey):
        self._privada = privada
        self.publica = privada.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.id_clave = id_de_clave(self.publica)

    @classmethod
    def del_llavero(cls, nombre: str = "clave-firma") -> Firmante:
        guardada = leer_secreto(nombre)
        if guardada:
            return cls(Ed25519PrivateKey.from_private_bytes(base64.b64decode(guardada)))
        privada = Ed25519PrivateKey.generate()
        crudo = privada.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        guardar_secreto(nombre, base64.b64encode(crudo).decode("ascii"))
        return cls(privada)

    def contenido_qr(self, id_alumno: str, salida: datetime, expedido: datetime) -> str:
        base = f"{PREFIJO}|{self.id_clave}|{id_alumno}|{salida:{_FORMATO}}|{expedido:{_FORMATO}}"
        return f"{base}|{b64url(self._privada.sign(base.encode('utf-8')))}"

    def qr_de_clave(self, nombre_equipo: str) -> str:
        nombre = (nombre_equipo or "Jefatura de Estudios").replace("|", "/").strip()
        return f"{PREFIJO_CLAVE}|{self.id_clave}|{b64url(self.publica)}|{nombre}"


@dataclass
class Verificacion:
    valido: bool
    motivo: str
    id_clave: str = ""
    id_alumno: str = ""
    salida: datetime | None = None
    expedido: datetime | None = None


def verificar(texto: str, claves: dict[str, bytes]) -> Verificacion:
    """Comprueba un QR de parte con las claves públicas conocidas (`id → clave`)."""
    partes = (texto or "").strip().split("|")
    if len(partes) != 6 or partes[0] != PREFIJO:
        return Verificacion(False, "No es un parte de salida")
    _, kid, id_alumno, salida, expedido, firma = partes
    publica = claves.get(kid)
    if publica is None:
        return Verificacion(False, "Firmado por un equipo desconocido", kid, id_alumno)
    try:
        Ed25519PublicKey.from_public_bytes(publica).verify(
            de_b64url(firma), "|".join(partes[:5]).encode("utf-8")
        )
        hs, he = datetime.strptime(salida, _FORMATO), datetime.strptime(expedido, _FORMATO)
    except (InvalidSignature, ValueError):
        return Verificacion(False, "Firma no válida: el parte está alterado o es falso", kid, id_alumno)
    return Verificacion(True, "Parte auténtico", kid, id_alumno, hs, he)
