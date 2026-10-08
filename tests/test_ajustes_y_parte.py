from datetime import datetime

import pytest

from partes_salida.ajustes import GestorAjustes, quitar_fondo_blanco
from partes_salida.modelo import Alumno
from partes_salida.parte import DatosParte, ImagenesParte, imagen_parte, texto_parte
from tests import ficticios


def test_ajustes_por_defecto_y_persistencia(datos):
    g = GestorAjustes(datos)
    assert g.valores.smtp_usuario == "no_contestar@aplicaciones.epla.es"
    assert g.ruta_imagen("logo_izquierdo").exists() and g.ruta_imagen("sello") is None
    g.poner(localidad="Valencia")
    assert GestorAjustes(datos).valores.localidad == "Valencia"


def test_ajustes_ignora_claves_desconocidas(datos):
    (datos / "ajustes.json").write_text('{"localidad": "X", "campo_viejo": 1}', encoding="utf-8")
    assert GestorAjustes(datos).valores.localidad == "X"


def test_exportar_e_importar_ajustes(datos, tmp_path):
    g = GestorAjustes(datos)
    (tmp_path / "sello.png").write_bytes(ficticios.retrato(1))
    g.poner_imagen("sello", tmp_path / "sello.png")
    g.poner(cargo_firma="La Jefa de Estudios")
    g.exportar(tmp_path / "copia.zip")
    otro = GestorAjustes(tmp_path / "otro")
    otro.importar(tmp_path / "copia.zip")
    assert otro.valores.cargo_firma == "La Jefa de Estudios" and otro.es_propia("sello")


def test_quitar_fondo_blanco():
    from PIL import Image

    im = Image.new("RGB", (4, 1), (255, 255, 255))
    im.putpixel((0, 0), (20, 40, 160))
    alfa = quitar_fondo_blanco(im).getchannel("A")
    assert alfa.getpixel((0, 0)) == 255 and alfa.getpixel((3, 0)) == 0


@pytest.mark.parametrize(
    ("sexo", "esperado"), [("F", "La alumna arriba indicada está autorizada"), ("M", "El alumno arriba indicado está autorizado")]
)
def test_texto_del_parte_segun_genero(datos, sexo, esperado):
    g = GestorAjustes(datos)
    a = Alumno(id="1", sexo=sexo)
    plantilla = g.valores.texto_alumna if a.es_mujer else g.valores.texto_alumno
    html = texto_parte(plantilla, a, datetime(2026, 10, 8, 12, 30))
    assert html.startswith(esperado) and "<b>12:30</b>" in html and "<br>" in html


def test_texto_del_parte_escapa_html(datos):
    html = texto_parte("<script>{nombre}</script>", Alumno(id="1", nombre="A&B"), datetime(2026, 1, 1))
    assert "<script>" not in html and "A&amp;B" in html


def _datos(alumno, foto=None):
    ahora = datetime(2026, 10, 8, 9, 14)
    return DatosParte(alumno, foto, datetime(2026, 10, 8, 12, 30), ahora, "PS1|X|1|202610081230|202610080914|firma")


def test_parte_a6_se_dibuja_en_proporcion(qapp, datos):
    from partes_salida.ui import estilo

    estilo.cargar_fuentes()
    g = GestorAjustes(datos)
    a = Alumno(id="1", nia="1", nombre="NEREA", apellido1="BELTRÁN", apellido2="ROIG", sexo="F", clase="2BACC")
    img = imagen_parte(_datos(a, ficticios.retrato(0)), g, ImagenesParte(g), 1480)
    assert (img.width(), img.height()) == (1480, 1050)
    oscuros = sum(1 for x in range(0, 1480, 7) for y in range(0, 1050, 7) if img.pixelColor(x, y).lightness() < 100)
    assert oscuros > 500, "el parte no puede salir en blanco"


def test_parte_con_nombre_muy_largo_no_falla(qapp, datos):
    g = GestorAjustes(datos)
    a = Alumno(id="1", nombre="MARÍA DE LOS REMEDIOS INMACULADA", apellido1="FERNÁNDEZ-CASTELLANOS",
               apellido2="DE LA SANTÍSIMA TRINIDAD", sexo="F", clase="1BAHC")
    assert not imagen_parte(_datos(a), g, ImagenesParte(g), 600).isNull()


def test_hora_y_h_no_se_separan(datos):
    g = GestorAjustes(datos)
    html = texto_parte(g.valores.texto_alumna, Alumno(id="1", sexo="F"), datetime(2026, 10, 8, 12, 30))
    assert "<b>12:30</b>&nbsp;h" in html


@pytest.mark.parametrize(("orientacion", "tamano"), [("horizontal", (1480, 1050)), ("vertical", (1050, 1480))])
def test_parte_en_las_dos_orientaciones(qapp, datos, orientacion, tamano):
    g = GestorAjustes(datos)
    g.poner(orientacion=orientacion)
    a = Alumno(id="1", nia="1", nombre="NEREA", apellido1="BELTRÁN", apellido2="ROIG", sexo="F", clase="2BACC")
    img = imagen_parte(_datos(a, ficticios.retrato(0)), g, ImagenesParte(g), tamano[0])
    assert (img.width(), img.height()) == tamano


def test_maquetas_caben_en_su_papel():
    from partes_salida.parte import HORIZONTAL, VERTICAL

    for m in (HORIZONTAL, VERTICAL):
        for nombre in ("logo_izq", "logo_der", "titulo", "foto", "nombre", "hora", "texto", "qr", "sello", "firma", "cargo"):
            x, y, w, h = getattr(m, nombre)
            assert x >= 4 and x + w <= m.ancho - 4 and y >= 4 and y + h <= m.alto - 4, (m.ancho, nombre)


def test_la_impresora_recibe_la_orientacion(qapp, datos, tmp_path):
    from PyQt6.QtGui import QPageLayout
    from PyQt6.QtPrintSupport import QPrinter

    from partes_salida.impresion import _a6

    for orientacion, esperada in (("horizontal", QPageLayout.Orientation.Landscape),
                                  ("vertical", QPageLayout.Orientation.Portrait)):
        impresora = QPrinter()
        impresora.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        impresora.setOutputFileName(str(tmp_path / f"{orientacion}.pdf"))
        _a6(impresora, orientacion)
        assert impresora.pageLayout().orientation() == esperada
