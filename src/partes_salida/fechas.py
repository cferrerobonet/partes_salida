"""Fechas en castellano sin depender del idioma del sistema."""

from datetime import date

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def fecha_larga(d: date) -> str:
    """`jueves, 8 de octubre de 2026`."""
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(d: date) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"
