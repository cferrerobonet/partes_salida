"""Fotos del alumnado desde uno o varios ZIP, con carpetas y subcarpetas.

Cada foto se llama `APELLIDOS, NOMBRE.png` (o .jpg). Se casa con el padrón sin
tener en cuenta tildes ni mayúsculas; las que casi coinciden (una tilde, una
errata) se dejan para confirmar, y las que no son de nadie se ignoran. Nada se
descomprime en disco: se lee del ZIP en memoria, se reduce y se guarda cifrada.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .modelo import Alumno, clave_nombre

EXTENSIONES = (".png", ".jpg", ".jpeg")
TAMANO = (360, 480)
MAX_BYTES = 40 * 1024 * 1024
UMBRAL_PARECIDA = 88


@dataclass
class Dudosa:
    archivo: str
    id_alumno: str
    nombre_alumno: str
    curso: str
    puntuacion: float
    jpeg: bytes


@dataclass
class InformeFotos:
    leidas: int = 0
    asignadas: int = 0
    dudosas: list[Dudosa] = field(default_factory=list)
    sobrantes: int = 0
    errores: list[str] = field(default_factory=list)


def preparar_jpeg(datos: bytes) -> bytes:
    """Reduce la foto a 360 × 480 (3:4), recortando lo justo y respetando la cabeza."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(datos)) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            fondo = Image.new("RGB", im.size, (255, 255, 255))
            fondo.paste(im, mask=im.split()[-1])
            im = fondo
        else:
            im = im.convert("RGB")
        im = ImageOps.fit(im, TAMANO, Image.Resampling.LANCZOS, centering=(0.5, 0.4))
        salida = io.BytesIO()
        im.save(salida, "JPEG", quality=86, optimize=True)
        return salida.getvalue()


def _nombre_real(info: zipfile.ZipInfo) -> str:
    """Nombre con sus tildes aunque el ZIP no marque UTF-8 (pasa con algunos de Windows)."""
    nombre = info.filename
    if not info.flag_bits & 0x800:
        try:
            nombre = nombre.encode("cp437").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return nombre


def _entradas(rutas):
    for ruta in rutas:
        with zipfile.ZipFile(ruta) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                nombre = PurePosixPath(_nombre_real(info))
                if "__MACOSX" in nombre.parts or nombre.name.startswith("."):
                    continue
                if nombre.suffix.lower() not in EXTENSIONES or info.file_size > MAX_BYTES:
                    continue
                yield str(ruta), info, nombre


def importar_fotos(
    rutas_zip,
    alumnos: list[Alumno],
    almacen,
    progreso: Callable[[int, int, str], None] | None = None,
) -> InformeFotos:
    from rapidfuzz import fuzz, process

    informe = InformeFotos()
    por_clave = {a.clave_foto: a for a in alumnos}
    elegidas: dict[str, tuple] = {}
    sin_pareja = []
    for ruta, info, nombre in _entradas([Path(r) for r in rutas_zip]):
        informe.leidas += 1
        clave = clave_nombre(nombre.stem)
        alumno = por_clave.get(clave)
        if alumno is None:
            sin_pareja.append((ruta, info, nombre, clave))
            continue
        # Si un alumno sale dos veces (carpeta de un curso y de otro), la más reciente.
        previa = elegidas.get(alumno.id)
        if previa is None or info.date_time > previa[1].date_time:
            elegidas[alumno.id] = (ruta, info, nombre)

    libres = {a.clave_foto: a for a in alumnos if a.id not in elegidas}
    opciones = list(libres)
    parecidas: dict[str, tuple] = {}
    for ruta, info, nombre, clave in sin_pareja:
        m = process.extractOne(clave, opciones, scorer=fuzz.ratio, score_cutoff=UMBRAL_PARECIDA) if opciones else None
        if not m:
            informe.sobrantes += 1
            continue
        alumno = libres[m[0]]
        previa = parecidas.get(alumno.id)
        if previa is None or m[1] > previa[0]:
            if previa is not None:
                informe.sobrantes += 1
            parecidas[alumno.id] = (m[1], ruta, info, nombre)
        else:
            informe.sobrantes += 1

    total = len(elegidas) + len(parecidas)
    hechas = 0
    abiertos: dict[str, zipfile.ZipFile] = {}
    try:

        def leer(ruta, info):
            if ruta not in abiertos:
                abiertos[ruta] = zipfile.ZipFile(ruta)
            return abiertos[ruta].read(info)

        for id_alumno, (ruta, info, nombre) in elegidas.items():
            try:
                almacen.guardar_foto(id_alumno, preparar_jpeg(leer(ruta, info)))
                informe.asignadas += 1
            except Exception:  # noqa: BLE001 - una foto rota no para el resto
                informe.errores.append(nombre.name)
            hechas += 1
            if progreso:
                progreso(hechas, total, nombre.name)
        alumnos_por_id = {a.id: a for a in alumnos}
        for id_alumno, (puntos, ruta, info, nombre) in parecidas.items():
            try:
                a = alumnos_por_id[id_alumno]
                informe.dudosas.append(
                    Dudosa(nombre.name, id_alumno, a.nombre_listado, a.curso, puntos, preparar_jpeg(leer(ruta, info)))
                )
            except Exception:  # noqa: BLE001
                informe.errores.append(nombre.name)
            hechas += 1
            if progreso:
                progreso(hechas, total, nombre.name)
    finally:
        for z in abiertos.values():
            z.close()
    informe.dudosas.sort(key=lambda d: d.nombre_alumno)
    return informe
