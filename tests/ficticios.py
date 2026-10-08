"""Alumnado inventado para tests y capturas: nunca datos reales en el repositorio."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

CABECERAS = [
    "APELLIDO1 ALUMNO", "APELLIDO2 ALUMNO", "NOMBRE ALUMNO", "SEXO", "CLASE", "NIA", "ID PERSONA",
    "DNI ALUMNO", "FECHA NACIMIENTO ALUMNO", "MÓVIL1 ALUMNO", "TEL EMERGENCIA ALUMNO",
    "NOMBRE TUTOR1", "APELLIDO1 TUTOR1", "APELLIDO2 TUTOR1", "PARENTESCO TUTOR1", "RECIBE INFORMACIÓN TUTOR1",
    "EMAIL TUTOR1", "TEL PERSONAL TUTOR1",
    "NOMBRE TUTOR2", "APELLIDO1 TUTOR2", "APELLIDO2 TUTOR2", "PARENTESCO TUTOR2", "RECIBE INFORMACIÓN TUTOR2",
    "EMAIL TUTOR2", "TEL PERSONAL TUTOR2", "IBAN PAGADOR1",
]

#: apellido1, apellido2, nombre, sexo, clase, nia, nacimiento, (madre), (padre)
ALUMNOS = [
    ("ALBERT", "FERRANDO", "MARC", "M", "1CFS-SEA", "10482231", "14/03/2006", ("ROSA", "FERRANDO", "GIL"), ("JOAN", "ALBERT", "PLA")),
    ("BELTRÁN", "ROIG", "NEREA", "F", "2BACC", "10519873", "22/01/2009", ("AMPARO", "ROIG", "SALA"), ("VICENT", "BELTRÁN", "MAS")),
    ("CASTELLÓ", "MIRA", "PAU", "M", "4ESOB", "10633407", "02/06/2011", ("ELENA", "MIRA", "BOSCH"), ("ANDREU", "CASTELLÓ", "ROS")),
    ("DOMÉNECH", "SANZ", "CARLA", "F", "1CFM-IEA-A", "10588120", "30/11/2009", ("SILVIA", "SANZ", "LLOP"), ("RAÚL", "DOMÉNECH", "PERIS")),
    ("ESTEVE", "PALAU", "JORDI", "M", "2CFB-EE", "10601555", "18/04/2009", ("LORENA", "PALAU", "VIDAL"), None),
    ("FUSTER", "LLOP", "AITANA", "F", "1BAHA", "10655902", "09/08/2010", ("MARTA", "LLOP", "CANO"), ("TONI", "FUSTER", "RIBES")),
    ("GIMENO", "VIDAL", "HUGO", "M", "2CFS-AUT", "10377214", "05/12/2004", ("PILAR", "VIDAL", "SORIA"), ("ÓSCAR", "GIMENO", "PUIG")),
    ("IBÁÑEZ", "TORMO", "MARTA", "F", "3ESOC", "10690031", "27/02/2012", ("NURIA", "TORMO", "GIL"), ("SERGIO", "IBÁÑEZ", "MORA")),
    ("LLORENS", "BOIX", "ÁLEX", "M", "6PRIB", "10748826", "11/05/2015", ("INMA", "BOIX", "FERRER"), ("DAVID", "LLORENS", "SANCHIS")),
    ("MOLINER", "CERVERA", "SARA", "F", "2CFM-ITE", "10544318", "23/09/2008", ("CARMEN", "CERVERA", "MARTÍ"), ("LUIS", "MOLINER", "ESTEVE")),
    ("NAVARRO", "PONS", "IVÁN", "M", "1CFS-ARI", "10466790", "16/07/2007", None, ("RAFA", "NAVARRO", "GÓMEZ")),
    ("PERIS", "CATALÀ", "LAIA", "F", "2ESOA", "10712264", "08/03/2013", ("EVA", "CATALÀ", "ROCA"), ("XIMO", "PERIS", "VELA")),
    ("QUILES", "ROMERO", "LUCÍA", "F", "4INFA", "", "12/02/2022", ("ANA", "ROMERO", "SOLER"), ("PEDRO", "QUILES", "MARÍN")),
]


def filas() -> list[list[str]]:
    datos = [CABECERAS]
    for i, (ap1, ap2, nom, sexo, clase, nia, nac, madre, padre) in enumerate(ALUMNOS):
        fila = [ap1, ap2, nom, sexo, clase, nia, str(90000 + i), f"0000000{i}X", nac, f"62100{i:04d}", f"96300{i:04d} M"]
        for n, t in enumerate((madre, padre)):
            if t:
                from partes_salida.modelo import sin_tildes

                usuario = sin_tildes(f"{t[0]}.{t[1]}").lower()
                fila += [t[0], t[1], t[2], "MADRE" if n == 0 else "PADRE", "TRUE" if i != 2 or n == 0 else "FALSE",
                         f"{usuario}@ejemplo.es".upper(), f"60{n}11{i:04d}"]
            else:
                fila += [""] * 7
        fila.append("ES00 0000 0000 0000 0000 0000")
        datos.append(fila)
    return datos


def excel(ruta: Path) -> Path:
    from openpyxl import Workbook

    libro = Workbook()
    hoja = libro.active
    for f in filas():
        hoja.append(f)
    libro.save(ruta)
    return ruta


def retrato(semilla: int) -> bytes:
    """Un retrato dibujado (fondo, cabeza y hombros), distinto para cada semilla."""
    from PIL import Image, ImageDraw

    tonos = [(196, 214, 230), (226, 210, 196), (205, 226, 207), (224, 205, 222), (230, 222, 196)]
    piel = [(234, 192, 160), (198, 150, 116), (241, 210, 180), (160, 112, 80)][semilla % 4]
    ropa = [(44, 122, 58), (60, 70, 120), (150, 50, 50), (90, 90, 90), (185, 122, 18)][semilla % 5]
    im = Image.new("RGB", (600, 800), tonos[semilla % 5])
    d = ImageDraw.Draw(im)
    d.ellipse((90, 560, 510, 980), fill=ropa)
    d.rectangle((255, 460, 345, 600), fill=piel)
    d.ellipse((170, 190, 430, 500), fill=piel)
    d.pieslice((160, 160, 440, 400), 180, 360, fill=[(60, 40, 30), (20, 20, 20), (120, 80, 40)][semilla % 3])
    salida = io.BytesIO()
    im.save(salida, "PNG")
    return salida.getvalue()


def zip_fotos(ruta: Path, con_errata: bool = True) -> Path:
    """Fotos en subcarpetas, una con errata, una sobrante y basura de macOS."""
    with zipfile.ZipFile(ruta, "w") as z:
        for i, (ap1, ap2, nom, *_resto) in enumerate(ALUMNOS[:-1]):
            nombre = f"{ap1} {ap2}, {nom}"
            if con_errata and i == 3:
                nombre = nombre.replace("DOMÉNECH", "DOMENEC")
            z.writestr(f"FOTOS/{_resto[1][:4]}/{nombre}.png", retrato(i))
        z.writestr("FOTOS/BAJAS/ANTIGUO ALUMNO, NADIE.png", retrato(99))
        z.writestr("__MACOSX/FOTOS/._x.png", b"basura")
        z.writestr("FOTOS/.DS_Store", b"basura")
    return ruta
