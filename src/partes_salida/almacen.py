"""Padrón y fotos cifrados en la carpeta de datos del equipo.

- `alumnado.bin`: el padrón entero (JSON cifrado).
- `fotos/<huella>.bin`: una foto por alumno, cifrada; el nombre no dice de quién es.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .cifrado import Cifrador, ErrorDeCifrado
from .modelo import Alumno

ARCHIVO_PADRON = "alumnado.bin"


class DatosIlegibles(Exception):
    """Hay datos guardados pero la clave del llavero ya no los abre."""


@dataclass
class Padron:
    alumnos: list[Alumno]
    importado: str = ""
    origen: str = ""


def _escribir(ruta: Path, datos: bytes) -> None:
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_bytes(datos)
    os.replace(temporal, ruta)


class Almacen:
    def __init__(self, carpeta: Path, cifrador: Cifrador):
        self.carpeta = Path(carpeta)
        self.fotos = self.carpeta / "fotos"
        self.fotos.mkdir(parents=True, exist_ok=True)
        self._cifrador = cifrador

    # Padrón
    def guardar_padron(self, alumnos: list[Alumno], origen: str) -> Padron:
        padron = Padron(alumnos, datetime.now().isoformat(timespec="seconds"), origen)
        datos = {
            "version": 1,
            "importado": padron.importado,
            "origen": origen,
            "alumnos": [a.a_dict() for a in alumnos],
        }
        crudo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        _escribir(self.carpeta / ARCHIVO_PADRON, self._cifrador.cifrar(crudo, b"alumnado"))
        return padron

    def cargar_padron(self) -> Padron | None:
        ruta = self.carpeta / ARCHIVO_PADRON
        if not ruta.exists():
            return None
        try:
            crudo = self._cifrador.descifrar(ruta.read_bytes(), b"alumnado")
        except ErrorDeCifrado as e:
            raise DatosIlegibles(str(e)) from e
        datos = json.loads(crudo)
        return Padron(
            [Alumno.de_dict(a) for a in datos.get("alumnos", [])],
            datos.get("importado", ""),
            datos.get("origen", ""),
        )

    # Fotos
    def _ruta_foto(self, id_alumno: str) -> Path:
        return self.fotos / f"{self._cifrador.huella(id_alumno)}.bin"

    def guardar_foto(self, id_alumno: str, jpeg: bytes) -> None:
        _escribir(self._ruta_foto(id_alumno), self._cifrador.cifrar(jpeg, b"foto:" + id_alumno.encode()))

    def leer_foto(self, id_alumno: str) -> bytes | None:
        ruta = self._ruta_foto(id_alumno)
        if not ruta.exists():
            return None
        try:
            return self._cifrador.descifrar(ruta.read_bytes(), b"foto:" + id_alumno.encode())
        except ErrorDeCifrado:
            return None

    def tiene_foto(self, id_alumno: str) -> bool:
        return self._ruta_foto(id_alumno).exists()

    def contar_fotos(self, ids) -> int:
        return sum(1 for i in ids if self.tiene_foto(i))

    def limpiar_fotos(self, ids_vigentes) -> int:
        """Borra las fotos de quien ya no está en el padrón. Devuelve cuántas."""
        validas = {self._ruta_foto(i).name for i in ids_vigentes}
        borradas = 0
        for f in self.fotos.glob("*.bin"):
            if f.name not in validas:
                f.unlink()
                borradas += 1
        return borradas

    def borrar_todo(self) -> None:
        ruta = self.carpeta / ARCHIVO_PADRON
        if ruta.exists():
            ruta.unlink()
        shutil.rmtree(self.fotos, ignore_errors=True)
        self.fotos.mkdir(parents=True, exist_ok=True)
