"""Lectura de la exportación de alumnado de Educamos (.xls o .xlsx).

El Excel trae más de doscientas columnas (DNI, IBAN, tarjeta sanitaria,
direcciones…). Sólo se leen las de `COLUMNAS`; el resto no llega a guardarse.
Las columnas se buscan por su cabecera, así que el orden da igual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .modelo import Alumno, Tutor, etapas_presentes, nombre_propio, sin_tildes

OBLIGATORIAS = ("APELLIDO1 ALUMNO", "NOMBRE ALUMNO", "SEXO", "CLASE")


def _columnas_tutor(n: int) -> tuple[str, ...]:
    return (
        f"NOMBRE TUTOR{n}",
        f"APELLIDO1 TUTOR{n}",
        f"APELLIDO2 TUTOR{n}",
        f"PARENTESCO TUTOR{n}",
        f"RECIBE INFORMACION TUTOR{n}",
        f"EMAIL TUTOR{n}",
        f"TEL PERSONAL TUTOR{n}",
        f"MOVIL TRABAJO T{n}",
        f"TEL CASA TUTOR{n}",
        f"TEL TRABAJO TUTOR{n}",
    )


#: Las únicas columnas que se leen. Cabeceras sin tildes y en mayúsculas.
COLUMNAS = (
    *OBLIGATORIAS,
    "APELLIDO2 ALUMNO",
    "NIA",
    "ID PERSONA",
    "FECHA NACIMIENTO ALUMNO",
    "MOVIL1 ALUMNO",
    "TEL EMERGENCIA ALUMNO",
    *_columnas_tutor(1),
    *_columnas_tutor(2),
)

_SI = {"TRUE", "VERDADERO", "SI", "S", "1", "X", "YES"}


class ErrorDeImportacion(Exception):
    pass


@dataclass
class ResultadoExcel:
    alumnos: list[Alumno]
    avisos: list[str] = field(default_factory=list)
    columnas_leidas: int = 0
    columnas_total: int = 0

    @property
    def etapas(self) -> list[str]:
        return etapas_presentes(self.alumnos)

    @property
    def clases(self) -> int:
        return len({a.clase for a in self.alumnos})


def _cabecera(texto) -> str:
    return re.sub(r"\s+", " ", sin_tildes(str(texto or "")).upper()).strip()


def _celda_xls(celda, datemode) -> str:
    import xlrd

    if celda.ctype == xlrd.XL_CELL_NUMBER:
        v = celda.value
        return str(int(v)) if float(v).is_integer() else str(v)
    if celda.ctype == xlrd.XL_CELL_DATE:
        try:
            return xlrd.xldate_as_datetime(celda.value, datemode).strftime("%d/%m/%Y")
        except Exception:  # noqa: BLE001
            return ""
    if celda.ctype == xlrd.XL_CELL_BOOLEAN:
        return "TRUE" if celda.value else "FALSE"
    return str(celda.value or "")


def _valor_xlsx(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (datetime, date)):
        return v.strftime("%d/%m/%Y")
    return str(v)


def leer_filas(ruta: str | Path) -> list[list[str]]:
    ruta = Path(ruta)
    ext = ruta.suffix.lower()
    if ext == ".xls":
        import xlrd

        try:
            libro = xlrd.open_workbook(str(ruta), on_demand=True)
        except xlrd.XLRDError as e:
            raise ErrorDeImportacion(f"No se puede leer el Excel: {e}") from e
        hoja = libro.sheet_by_index(0)
        return [
            [_celda_xls(hoja.cell(f, c), libro.datemode) for c in range(hoja.ncols)]
            for f in range(hoja.nrows)
        ]
    if ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook

        libro = load_workbook(str(ruta), read_only=True, data_only=True)
        try:
            hoja = libro.worksheets[0]
            return [[_valor_xlsx(v) for v in fila] for fila in hoja.iter_rows(values_only=True)]
        finally:
            libro.close()
    raise ErrorDeImportacion("Formato no admitido: usa la exportación .xls o .xlsx de Educamos")


def formatear_telefono(texto: str) -> str:
    """`963637354 A` → `963 637 354 (A)`."""
    texto = (texto or "").strip()
    digitos = re.sub(r"\D", "", texto)
    if not digitos:
        return ""
    num = f"{digitos[:3]} {digitos[3:6]} {digitos[6:]}" if len(digitos) == 9 else digitos
    resto = re.sub(r"[\d\s+().-]", "", texto)
    return f"{num} ({resto})" if resto else num


def _fecha(texto: str) -> str:
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})", texto or "")
    if not m:
        return ""
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return ""


def _email(texto: str) -> str:
    e = (texto or "").strip().lower()
    return e if re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", e) else ""


def _sexo(texto: str) -> str:
    s = (texto or "").strip().upper()[:1]
    return "F" if s == "F" else ("M" if s in ("M", "H", "V") else "")


def importar_excel(ruta: str | Path) -> ResultadoExcel:
    filas = leer_filas(ruta)
    cab = next(
        (
            i
            for i, f in enumerate(filas[:15])
            if {"NOMBRE ALUMNO", "CLASE"} <= {_cabecera(c) for c in f}
        ),
        None,
    )
    if cab is None:
        raise ErrorDeImportacion(
            "No se encuentra la fila de cabeceras (NOMBRE ALUMNO, CLASE…). "
            "¿Es la exportación de alumnado de Educamos?"
        )
    indice: dict[str, int] = {}
    for i, c in enumerate(filas[cab]):
        indice.setdefault(_cabecera(c), i)
    faltan = [c for c in OBLIGATORIAS if c not in indice]
    if faltan:
        raise ErrorDeImportacion("Faltan columnas en el Excel: " + ", ".join(faltan))

    def v(fila: list[str], col: str) -> str:
        i = indice.get(col)
        return fila[i].strip() if i is not None and i < len(fila) else ""

    def tutor(fila: list[str], n: int) -> Tutor | None:
        nombre = " ".join(
            p for p in (v(fila, f"NOMBRE TUTOR{n}"), v(fila, f"APELLIDO1 TUTOR{n}"), v(fila, f"APELLIDO2 TUTOR{n}")) if p
        )
        tel = next(
            (
                t
                for t in (
                    v(fila, f"TEL PERSONAL TUTOR{n}"),
                    v(fila, f"MOVIL TRABAJO T{n}"),
                    v(fila, f"TEL CASA TUTOR{n}"),
                    v(fila, f"TEL TRABAJO TUTOR{n}"),
                )
                if re.sub(r"\D", "", t)
            ),
            "",
        )
        email = _email(v(fila, f"EMAIL TUTOR{n}"))
        if not (nombre or email or tel):
            return None
        recibe = v(fila, f"RECIBE INFORMACION TUTOR{n}")
        return Tutor(
            parentesco=v(fila, f"PARENTESCO TUTOR{n}").upper(),
            nombre=nombre_propio(nombre),
            email=email,
            telefono=formatear_telefono(tel),
            recibe_informacion=(recibe.upper() in _SI) if f"RECIBE INFORMACION TUTOR{n}" in indice else True,
        )

    alumnos: list[Alumno] = []
    avisos: list[str] = []
    vistos: set[str] = set()
    sin_nia = 0
    for num, fila in enumerate(filas[cab + 1 :], start=cab + 2):
        nombre, ap1 = v(fila, "NOMBRE ALUMNO"), v(fila, "APELLIDO1 ALUMNO")
        if not (nombre or ap1):
            continue
        nia = re.sub(r"\D", "", v(fila, "NIA"))
        id_persona = re.sub(r"\s", "", v(fila, "ID PERSONA"))
        ident = nia or (f"P{id_persona}" if id_persona else f"F{num}")
        if not nia:
            sin_nia += 1
        if ident in vistos:
            avisos.append(f"Fila {num}: identificador repetido ({ident}); se queda la primera.")
            continue
        vistos.add(ident)
        alumnos.append(
            Alumno(
                id=ident,
                nia=nia,
                nombre=re.sub(r"\s+", " ", nombre.upper()),
                apellido1=re.sub(r"\s+", " ", ap1.upper()),
                apellido2=re.sub(r"\s+", " ", v(fila, "APELLIDO2 ALUMNO").upper()),
                sexo=_sexo(v(fila, "SEXO")),
                clase=v(fila, "CLASE").upper(),
                nacimiento=_fecha(v(fila, "FECHA NACIMIENTO ALUMNO")),
                movil=formatear_telefono(v(fila, "MOVIL1 ALUMNO")),
                tel_emergencia=formatear_telefono(v(fila, "TEL EMERGENCIA ALUMNO")),
                tutores=[t for t in (tutor(fila, 1), tutor(fila, 2)) if t],
            )
        )
    if not alumnos:
        raise ErrorDeImportacion("El Excel no tiene ninguna fila de alumnado.")
    if sin_nia:
        avisos.append(f"{sin_nia} alumnos sin NIA: se identifican por su ID de persona de Educamos.")
    sin_sexo = sum(1 for a in alumnos if not a.sexo)
    if sin_sexo:
        avisos.append(f"{sin_sexo} alumnos sin sexo en el Excel: su parte usará el masculino.")
    return ResultadoExcel(
        alumnos,
        avisos,
        columnas_leidas=sum(1 for c in COLUMNAS if c in indice),
        columnas_total=len([c for c in filas[cab] if str(c).strip()]),
    )
