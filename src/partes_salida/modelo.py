"""Alumnado y familias, con lo justo para emitir un parte y avisar."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date

#: Código de etapa que trae la columna CLASE de Educamos (`2CFS-SEA` → `CFS`).
ETAPAS = {
    "INF": "Infantil",
    "PRI": "Primaria",
    "ESO": "ESO",
    "BAC": "Bachillerato",
    "BAH": "Bachillerato",
    "CFB": "FP Grado Básico",
    "CFM": "FP Grado Medio",
    "CFS": "FP Grado Superior",
}
#: Orden y nombre corto de los botones de etapa. BAH (Humanidades) va con BAC.
ORDEN_ETAPAS = ["INF", "PRI", "ESO", "BAC", "CFB", "CFM", "CFS", "OTR"]
ETAPA_CORTA = {
    "INF": "Infantil",
    "PRI": "Primaria",
    "ESO": "ESO",
    "BAC": "Bachillerato",
    "CFB": "G. Básico",
    "CFM": "G. Medio",
    "CFS": "G. Superior",
    "OTR": "Otros",
}

_CLASE = re.compile(r"^(\d)([A-Z]{3})-?(.*)$")
_PARTICULAS = {"de", "del", "la", "las", "los", "y", "i", "da", "das", "do", "dos", "van", "von"}


def analizar_clase(clase: str) -> tuple[str, str, str]:
    """`2CFS-SEA` → `("CFS", "FP Grado Superior", "2º SEA")`."""
    c = (clase or "").strip().upper()
    m = _CLASE.match(c)
    if not m or m.group(2) not in ETAPAS:
        return "OTR", "Otros", c or "—"
    n, cod, resto = m.groups()
    grupo = re.sub(r"\s+", " ", resto.replace("-", " ")).strip()
    if cod.startswith("CF"):
        curso = f"{n}º {grupo}"
    elif cod == "BAC":
        curso = f"{n}º Bach. Ciencias {grupo}"
    elif cod == "BAH":
        curso = f"{n}º Bach. Humanidades {grupo}"
    elif cod == "INF":
        curso = f"Infantil {n} años {grupo}"
    elif cod == "PRI":
        curso = f"{n}º Primaria {grupo}"
    else:
        curso = f"{n}º ESO {grupo}"
    return ("BAC" if cod == "BAH" else cod), ETAPAS[cod], curso.strip()


def sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    )


def clave_nombre(texto: str) -> str:
    """Forma comparable de un nombre: sin tildes, en mayúsculas y sin signos.

    `Peña  Mejía , Enmanuel` y `PENA MEJIA, ENMANUEL` dan lo mismo, que es como se
    casan las fotos (`APELLIDOS, NOMBRE.png`) con el alumnado del Excel.
    """
    t = sin_tildes(texto).upper()
    t = re.sub(r"[^A-Z, ]", " ", t)
    t = re.sub(r"\s*,\s*", ", ", t)
    return re.sub(r"\s+", " ", t).strip(" ,")


def nombre_propio(texto: str) -> str:
    """`MARIA DE LA O GARCIA-PONS` → `Maria de la O Garcia-Pons`."""
    palabras = (texto or "").strip().lower().split()
    return " ".join(
        p if i and p in _PARTICULAS else "-".join(s[:1].upper() + s[1:] for s in p.split("-"))
        for i, p in enumerate(palabras)
    )


@dataclass
class Tutor:
    parentesco: str = ""
    nombre: str = ""
    email: str = ""
    telefono: str = ""
    recibe_informacion: bool = True

    @property
    def parentesco_texto(self) -> str:
        p = (self.parentesco or "").strip().upper()
        return {
            "MADRE": "Madre",
            "PADRE": "Padre",
            "TUTOR LEGAL": "Tutor legal",
            "TUTORA LEGAL": "Tutora legal",
            "OTROS": "Otro familiar",
            "": "Familiar",
        }.get(p, nombre_propio(p))

    @property
    def puede_recibir_correo(self) -> bool:
        return bool(self.email) and self.recibe_informacion


@dataclass
class Alumno:
    id: str
    nia: str = ""
    nombre: str = ""
    apellido1: str = ""
    apellido2: str = ""
    sexo: str = ""
    clase: str = ""
    nacimiento: str = ""
    movil: str = ""
    tel_emergencia: str = ""
    tutores: list[Tutor] = field(default_factory=list)

    def __post_init__(self):
        self._etapa = analizar_clase(self.clase)

    @property
    def etapa_codigo(self) -> str:
        return self._etapa[0]

    @property
    def etapa(self) -> str:
        return self._etapa[1]

    @property
    def curso(self) -> str:
        return self._etapa[2]

    @property
    def apellidos(self) -> str:
        return " ".join(p for p in (self.apellido1, self.apellido2) if p)

    @property
    def nombre_completo(self) -> str:
        return " ".join(p for p in (self.nombre, self.apellidos) if p)

    @property
    def nombre_listado(self) -> str:
        return f"{self.apellidos}, {self.nombre}" if self.apellidos else self.nombre

    @property
    def clave_foto(self) -> str:
        return clave_nombre(self.nombre_listado)

    @property
    def es_mujer(self) -> bool:
        return self.sexo == "F"

    def edad(self, hoy: date | None = None) -> int | None:
        if not self.nacimiento:
            return None
        try:
            n = date.fromisoformat(self.nacimiento)
        except ValueError:
            return None
        hoy = hoy or date.today()
        return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))

    def a_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def de_dict(cls, d: dict) -> Alumno:
        d = dict(d)
        d["tutores"] = [Tutor(**t) for t in d.get("tutores", [])]
        return cls(**d)


def etapas_presentes(alumnos) -> list[str]:
    """Códigos de etapa que hay en el padrón, en el orden de los botones."""
    hay = {a.etapa_codigo for a in alumnos}
    return [c for c in ORDEN_ETAPAS if c in hay]
