import json
import zipfile

import pytest

from partes_salida.almacen import Almacen
from partes_salida.cifrado import Cifrador
from partes_salida.importar_excel import ErrorDeImportacion, formatear_telefono, importar_excel
from partes_salida.importar_fotos import importar_fotos, preparar_jpeg
from tests import ficticios


def test_excel_lee_el_alumnado(excel):
    r = importar_excel(excel)
    assert len(r.alumnos) == len(ficticios.ALUMNOS)
    nerea = next(a for a in r.alumnos if a.nombre == "NEREA")
    assert nerea.id == nerea.nia == "10519873"
    assert nerea.sexo == "F" and nerea.curso == "2º Bach. Ciencias C"
    assert nerea.nacimiento == "2009-01-22"
    madre = nerea.tutores[0]
    assert (madre.parentesco_texto, madre.nombre, madre.email) == ("Madre", "Amparo Roig Sala", "amparo.roig@ejemplo.es")
    assert madre.telefono.count(" ") == 2


def test_excel_descarta_lo_que_no_hace_falta(excel):
    r = importar_excel(excel)
    guardado = json.dumps([a.a_dict() for a in r.alumnos])
    assert "00000001X" not in guardado, "el DNI no debe guardarse"
    assert "ES00" not in guardado, "el IBAN no debe guardarse"
    assert r.columnas_leidas < r.columnas_total


def test_excel_sin_nia_usa_id_de_persona(excel):
    r = importar_excel(excel)
    sin_nia = next(a for a in r.alumnos if a.nombre == "LUCÍA")
    assert sin_nia.nia == "" and sin_nia.id.startswith("P")
    assert any("sin NIA" in a for a in r.avisos)


def test_excel_respeta_recibe_informacion(excel):
    pau = next(a for a in importar_excel(excel).alumnos if a.nombre == "PAU")
    assert pau.tutores[0].puede_recibir_correo and not pau.tutores[1].puede_recibir_correo


def test_excel_sin_cabeceras_da_error_claro(tmp_path):
    from openpyxl import Workbook

    libro = Workbook()
    libro.active.append(["A", "B"])
    libro.save(tmp_path / "x.xlsx")
    with pytest.raises(ErrorDeImportacion, match="cabeceras"):
        importar_excel(tmp_path / "x.xlsx")
    with pytest.raises(ErrorDeImportacion, match="Formato"):
        importar_excel(tmp_path / "x.csv")


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("963637354", "963 637 354"), ("963637354 A", "963 637 354 (A)"), ("", ""), ("12345", "12345")],
)
def test_formato_de_telefono(texto, esperado):
    assert formatear_telefono(texto) == esperado


def test_fotos_casan_por_nombre_y_se_cifran(datos, alumnos, zip_fotos):
    almacen = Almacen(datos, Cifrador.del_llavero())
    inf = importar_fotos([zip_fotos], alumnos, almacen)
    assert inf.leidas == len(ficticios.ALUMNOS)  # 12 fotos + 1 sobrante; la basura de macOS no cuenta
    assert inf.asignadas == 11
    assert [d.nombre_alumno for d in inf.dudosas] == ["DOMÉNECH SANZ, CARLA"]
    assert inf.sobrantes == 1
    nerea = next(a for a in alumnos if a.nombre == "NEREA")
    foto = almacen.leer_foto(nerea.id)
    assert foto[:2] == b"\xff\xd8", "se guarda como JPEG"
    for archivo in (datos / "fotos").glob("*.bin"):
        assert "BELTR" not in archivo.name and archivo.read_bytes()[:2] != b"\xff\xd8"


def test_fotos_con_nombre_sin_marca_utf8(datos, alumnos, tmp_path):
    class SinMarcaUtf8(zipfile.ZipInfo):
        """Como los compresores antiguos de Windows: bytes UTF-8 sin el bit 0x800."""

        def _encodeFilenameFlags(self):
            return self.filename.encode("cp437"), self.flag_bits & ~0x800

    ruta = tmp_path / "windows.zip"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr(SinMarcaUtf8("BELTRÁN ROIG, NEREA.jpg".encode().decode("cp437")), ficticios.retrato(1))
    with zipfile.ZipFile(ruta) as z:
        assert not z.infolist()[0].flag_bits & 0x800
    inf = importar_fotos([ruta], alumnos, Almacen(datos, Cifrador.del_llavero()))
    assert inf.asignadas == 1


def test_foto_reducida_a_tres_cuartos():
    from io import BytesIO

    from PIL import Image

    with Image.open(BytesIO(preparar_jpeg(ficticios.retrato(0)))) as im:
        assert im.size == (360, 480)


@pytest.mark.datos_reales
def test_datos_reales_de_educamos(material_real, datos):
    r = importar_excel(material_real / "ExportacionDatosAlumnos.xls")
    assert len(r.alumnos) > 2000 and len(r.etapas) >= 7
    zips = sorted(material_real.glob("*.zip"))
    inf = importar_fotos(zips, r.alumnos, Almacen(datos, Cifrador.del_llavero()))
    assert inf.asignadas > 400 and not inf.errores
