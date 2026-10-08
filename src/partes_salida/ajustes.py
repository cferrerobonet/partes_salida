"""Ajustes de este equipo: textos, logos, sello, firma, correo e impresión.

Cada jefatura instala la aplicación en su equipo y la configura a su manera; no
hay nada compartido. Aquí no hay datos del alumnado ni contraseñas (la del
correo va al llavero), así que se puede exportar a un archivo para rehacer el
equipo o montar otro.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .rutas import recursos

IMAGENES = ("logo_izquierdo", "logo_derecho", "sello", "firma")
LOGOS = ("logo_izquierdo", "logo_derecho")
TEXTO_ALUMNA = (
    "La alumna arriba indicada está autorizada a salir del centro hoy a las {hora} h.\n"
    "Debe mostrar este pase en la puerta. Solo vale para esta fecha y hora."
)
TEXTO_ALUMNO = (
    "El alumno arriba indicado está autorizado a salir del centro hoy a las {hora} h.\n"
    "Debe mostrar este pase en la puerta. Solo vale para esta fecha y hora."
)


@dataclass
class Ajustes:
    centro: str = "Escuelas Profesionales Luis Amigó"
    localidad: str = "Godella"
    titulo: str = "AUTORIZACIÓN DE SALIDA"
    texto_alumna: str = TEXTO_ALUMNA
    texto_alumno: str = TEXTO_ALUMNO
    cargo_firma: str = "Firmado: El Jefe de Estudios"
    smtp_servidor: str = "smtp.ionos.es"
    smtp_puerto: int = 587
    smtp_usuario: str = "no_contestar@aplicaciones.epla.es"
    remitente_nombre: str = "EPLA · Jefatura de Estudios"
    contacto_manana_email: str = "jefaturafpbach@epla.es"
    contacto_manana_tel: str = "96 363 73 54"
    contacto_tarde_email: str = "jefaturafptarde@epla.es"
    contacto_tarde_tel: str = "96 363 73 54"
    impresora: str = ""
    imprimir_directo: bool = True
    ajuste_x_mm: float = 0.0
    ajuste_y_mm: float = 0.0
    etapas_ocultas: list[str] = field(default_factory=list)
    nombre_equipo: str = "Jefatura de Estudios"
    arrancar_con_sistema: bool = False
    siempre_encima: bool = False


def quitar_fondo_blanco(imagen):
    """Vuelve transparente el papel de un sello o una firma escaneados.

    La tinta conserva su color y el blanco desaparece, así que el sello se ve
    encima de la firma como en un papel de verdad, también al imprimir.
    """
    from PIL import Image

    rgba = imagen.convert("RGBA")
    if rgba.getextrema()[3][0] < 250:  # ya trae transparencia
        return rgba
    gris = rgba.convert("L")
    alfa = gris.point(lambda v: 0 if v >= 235 else (255 if v <= 135 else int((235 - v) * 255 / 100)))
    resultado = Image.new("RGBA", rgba.size)
    resultado.paste(rgba.convert("RGB"))
    resultado.putalpha(alfa)
    return resultado


class GestorAjustes:
    def __init__(self, carpeta: Path):
        self.carpeta = Path(carpeta)
        self.ruta = self.carpeta / "ajustes.json"
        self.imagenes = self.carpeta / "imagenes"
        self.imagenes.mkdir(parents=True, exist_ok=True)
        self.valores = self._cargar()
        self.version_imagenes = 0

    def _cargar(self) -> Ajustes:
        if not self.ruta.exists():
            return Ajustes()
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return Ajustes()
        validos = {f.name for f in fields(Ajustes)}
        return Ajustes(**{k: v for k, v in datos.items() if k in validos})

    def guardar(self) -> None:
        temporal = self.ruta.with_suffix(".tmp")
        temporal.write_text(json.dumps(asdict(self.valores), ensure_ascii=False, indent=2), encoding="utf-8")
        temporal.replace(self.ruta)

    def poner(self, **cambios) -> None:
        for k, v in cambios.items():
            setattr(self.valores, k, v)
        self.guardar()

    # Imágenes
    def ruta_imagen(self, nombre: str) -> Path | None:
        propia = self.imagenes / f"{nombre}.png"
        if propia.exists():
            return propia
        if nombre in LOGOS:
            defecto = recursos() / f"{nombre}.png"
            return defecto if defecto.exists() else None
        return None

    def es_propia(self, nombre: str) -> bool:
        return (self.imagenes / f"{nombre}.png").exists()

    def poner_imagen(self, nombre: str, origen: str | Path) -> None:
        from PIL import Image, ImageOps

        with Image.open(origen) as im:
            im = ImageOps.exif_transpose(im)
            im = quitar_fondo_blanco(im) if nombre in ("sello", "firma") else im.convert("RGBA")
            im.thumbnail((1400, 1400))
            im.save(self.imagenes / f"{nombre}.png", "PNG", optimize=True)
        self.version_imagenes += 1

    def quitar_imagen(self, nombre: str) -> None:
        propia = self.imagenes / f"{nombre}.png"
        if propia.exists():
            propia.unlink()
        self.version_imagenes += 1

    # Copia de los ajustes
    def exportar(self, destino: str | Path) -> None:
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("ajustes.json", json.dumps(asdict(self.valores), ensure_ascii=False, indent=2))
            for nombre in IMAGENES:
                if self.es_propia(nombre):
                    z.write(self.imagenes / f"{nombre}.png", f"imagenes/{nombre}.png")

    def importar(self, origen: str | Path) -> None:
        with zipfile.ZipFile(origen) as z:
            nombres = set(z.namelist())
            if "ajustes.json" not in nombres:
                raise ValueError("El archivo no es una copia de ajustes de Partes de salida")
            datos = json.loads(z.read("ajustes.json"))
            validos = {f.name for f in fields(Ajustes)}
            self.valores = Ajustes(**{k: v for k, v in datos.items() if k in validos})
            for nombre in IMAGENES:
                entrada = f"imagenes/{nombre}.png"
                if entrada in nombres:
                    from PIL import Image

                    with Image.open(io.BytesIO(z.read(entrada))) as im:
                        im.convert("RGBA").save(self.imagenes / f"{nombre}.png", "PNG")
                else:
                    self.quitar_imagen(nombre)
        self.guardar()
        self.version_imagenes += 1
