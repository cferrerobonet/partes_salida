"""Cada test trabaja en una carpeta de datos propia y sin tocar el llavero real."""

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["PARTES_SALIDA_SIN_LLAVERO"] = "1"

from tests import ficticios  # noqa: E402

MATERIAL = Path(__file__).resolve().parents[2] / "Material de pruebas"


@pytest.fixture(autouse=True)
def datos(tmp_path, monkeypatch) -> Path:
    carpeta = tmp_path / "datos"
    carpeta.mkdir()
    monkeypatch.setenv("PARTES_SALIDA_DATOS", str(carpeta))
    return carpeta


@pytest.fixture
def excel(tmp_path) -> Path:
    return ficticios.excel(tmp_path / "alumnos.xlsx")


@pytest.fixture
def zip_fotos(tmp_path) -> Path:
    return ficticios.zip_fotos(tmp_path / "fotos.zip")


@pytest.fixture
def alumnos(excel):
    from partes_salida.importar_excel import importar_excel

    return importar_excel(excel).alumnos


@pytest.fixture
def contexto(qapp, datos, alumnos, zip_fotos):
    """Aplicación preparada: estilo, padrón ficticio y fotos importadas."""
    from partes_salida.contexto import Contexto
    from partes_salida.importar_fotos import importar_fotos
    from partes_salida.ui import estilo

    estilo.cargar_fuentes()
    estilo.aplicar(qapp)
    ctx = Contexto(datos)
    ctx.nuevo_padron(alumnos, "alumnos.xlsx")
    importar_fotos([zip_fotos], ctx.alumnos, ctx.almacen)
    ctx.fotos_cambiadas()
    return ctx


@pytest.fixture
def material_real() -> Path:
    if not (MATERIAL / "ExportacionDatosAlumnos.xls").exists():
        pytest.skip("Sin la carpeta «Material de pruebas» (solo existe en el equipo de desarrollo)")
    return MATERIAL
