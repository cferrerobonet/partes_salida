"""Impresión del parte: cabe en el área imprimible real (márgenes físicos) y modo color o blanco y negro.

Sin impresora real: se imprime a PDF con márgenes no nulos y se rasteriza con QtPdf para mirar la tinta.
"""

from datetime import datetime

import pytest
from PyQt6.QtCore import QMarginsF, QRectF, QSize
from PyQt6.QtGui import QColor, QImage, QPageLayout, QPageSize
from PyQt6.QtPrintSupport import QPrinter

from partes_salida import impresion
from partes_salida.ajustes import GestorAjustes
from partes_salida.modelo import Alumno
from partes_salida.parte import DatosParte, ImagenesParte, a_grises, imagen_parte
from tests import ficticios

#: Márgenes físicos simulados (izquierda, arriba, derecha, abajo) en mm, como los de una impresora
#: que no imprime hasta el filo: el derecho y el inferior, los más anchos (donde se recortaba).
MARGENES = (3.0, 4.0, 6.0, 7.0)
RES = 150


def _datos(semilla=0):
    a = Alumno(id=str(semilla + 1), nia=str(semilla + 1), nombre="NEREA", apellido1="BELTRÁN", apellido2="ROIG",
               sexo="F", clase="2BACC")
    ahora = datetime(2026, 10, 8, 9, 14)
    return DatosParte(a, ficticios.retrato(semilla), datetime(2026, 10, 8, 12, 30), ahora,
                      "PS1|X|1|202610081230|202610080914|firma")


class _Contexto:
    def __init__(self, gestor):
        self.gestor = gestor
        self.imagenes = ImagenesParte(gestor)


def _impresora_pdf(ruta, orientacion="horizontal", margenes=MARGENES, color=True) -> QPrinter:
    impresora = QPrinter(QPrinter.PrinterMode.HighResolution)
    impresora.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    impresora.setOutputFileName(str(ruta))
    impresora.setResolution(RES)
    impresora.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.A6),
        QPageLayout.Orientation.Landscape if orientacion == "horizontal" else QPageLayout.Orientation.Portrait,
        QMarginsF(*margenes), QPageLayout.Unit.Millimeter,
    ))
    impresora.setFullPage(True)
    impresora.setColorMode(QPrinter.ColorMode.Color if color else QPrinter.ColorMode.GrayScale)
    return impresora


def _paginas(ruta, ancho_px):
    """Cada página del PDF como imagen de `ancho_px` de ancho (fondo blanco)."""
    from PyQt6.QtPdf import QPdfDocument

    doc = QPdfDocument(None)
    assert doc.load(str(ruta)) == QPdfDocument.Error.None_
    paginas = []
    for i in range(doc.pageCount()):
        tam = doc.pagePointSize(i)
        img = doc.render(i, QSize(ancho_px, round(ancho_px * tam.height() / tam.width())))
        fondo = QImage(img.size(), QImage.Format.Format_RGB32)
        fondo.fill(QColor("white"))
        from PyQt6.QtGui import QPainter

        p = QPainter(fondo)
        p.drawImage(0, 0, img)
        p.end()
        paginas.append(fondo)
    return paginas


def _caja_de_tinta(img: QImage) -> QRectF:
    """Rectángulo que encierra todo lo que no es blanco."""
    xs, ys = [], []
    for y in range(0, img.height()):
        for x in range(0, img.width(), 1):
            c = img.pixelColor(x, y)
            if min(c.red(), c.green(), c.blue()) < 235:
                xs.append(x)
                ys.append(y)
    assert xs, "página en blanco"
    return QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


@pytest.mark.parametrize("orientacion", ["horizontal", "vertical"])
def test_el_parte_cabe_entero_en_el_area_imprimible(qapp, datos, tmp_path, orientacion):
    g = GestorAjustes(datos)
    g.poner(orientacion=orientacion)
    ruta = tmp_path / "parte.pdf"
    impresora = _impresora_pdf(ruta, orientacion)
    impresion.pintar_partes(impresora, [_datos()], _Contexto(g))

    ancho_mm = 148 if orientacion == "horizontal" else 105
    alto_mm = 105 if orientacion == "horizontal" else 148
    px_mm = 4  # rasterizado a 4 px por mm
    (pagina,) = _paginas(ruta, ancho_mm * px_mm)
    izq, arr, der, aba = (m * px_mm for m in MARGENES)
    tinta = _caja_de_tinta(pagina)
    tolerancia = 1.5  # antialiasing del rasterizado
    assert tinta.left() >= izq - tolerancia, "tinta en el margen izquierdo"
    assert tinta.top() >= arr - tolerancia, "tinta en el margen superior"
    assert tinta.right() <= ancho_mm * px_mm - der + tolerancia, "tinta en el margen derecho (se recortaría)"
    assert tinta.bottom() <= alto_mm * px_mm - aba + tolerancia, "tinta en el margen inferior (se recortaría)"
    # El marco del parte (a 4 mm del borde de la tarjeta, escalada) llega cerca del borde del área: no se ha
    # encogido de más ni se ha deformado (la proporción se conserva).
    assert tinta.width() / tinta.height() == pytest.approx((ancho_mm - 8) / (alto_mm - 8), rel=0.03)


def test_en_bloque_cada_hoja_cabe_en_el_area_imprimible(qapp, datos, tmp_path):
    g = GestorAjustes(datos)
    ruta = tmp_path / "bloque.pdf"
    impresion.pintar_partes(_impresora_pdf(ruta), [_datos(i) for i in range(3)], _Contexto(g))
    paginas = _paginas(ruta, 148 * 4)
    assert len(paginas) == 3
    for pagina in paginas:
        tinta = _caja_de_tinta(pagina)
        assert tinta.right() <= (148 - MARGENES[2]) * 4 + 1.5 and tinta.bottom() <= (105 - MARGENES[3]) * 4 + 1.5


def test_area_imprimible_resta_los_margenes_de_la_impresora(qapp, tmp_path):
    impresora = _impresora_pdf(tmp_path / "x.pdf")
    area = impresion.area_imprimible(impresora)
    px_mm = RES / 25.4
    assert area.left() == pytest.approx(MARGENES[0] * px_mm, abs=3)  # redondeo de A6 a puntos y píxeles
    assert area.top() == pytest.approx(MARGENES[1] * px_mm, abs=3)  # redondeo de A6 a puntos y píxeles
    assert area.width() == pytest.approx((148 - MARGENES[0] - MARGENES[2]) * px_mm, abs=3)  # redondeo de A6 a puntos y píxeles
    assert area.height() == pytest.approx((105 - MARGENES[1] - MARGENES[3]) * px_mm, abs=3)  # redondeo de A6 a puntos y píxeles


def test_colocacion_escala_en_proporcion_centra_y_no_amplia():
    px_mm = RES / 25.4
    # Área más pequeña que el parte: se reduce lo justo y se centra en el sentido que sobra
    area = QRectF(10, 20, 130 * px_mm, 100 * px_mm)
    escala, origen = impresion.colocacion(area, 148, 105, RES)
    assert escala == pytest.approx(px_mm * 130 / 148)
    assert origen.x() == pytest.approx(10)
    assert origen.y() == pytest.approx(20 + (100 * px_mm - 105 * escala) / 2)
    # Área mayor (papel A4 elegido en el diálogo): tamaño real, sin ampliar
    escala, _ = impresion.colocacion(QRectF(0, 0, 297 * px_mm, 210 * px_mm), 148, 105, RES)
    assert escala == pytest.approx(px_mm)
    # El ajuste fino no saca el parte del área
    escala, origen = impresion.colocacion(area, 148, 105, RES, (10, 0))
    assert origen.x() + 148 * escala <= area.right() + 1e-6


def test_colocacion_aplica_el_tamano_de_ajustes_y_lo_acota():
    px_mm = RES / 25.4
    area = QRectF(10, 20, 130 * px_mm, 100 * px_mm)
    base, _ = impresion.colocacion(area, 148, 105, RES)
    # Reducido: proporcional y centrado
    escala, origen = impresion.colocacion(area, 148, 105, RES, escala_pct=80)
    assert escala == pytest.approx(base * 0.8)
    assert origen.x() == pytest.approx(10 + (130 * px_mm - 148 * escala) / 2)
    assert origen.y() == pytest.approx(20 + (100 * px_mm - 105 * escala) / 2)
    # Ampliado por encima del área: sigue centrado y sobresale por igual a los dos lados
    escala, origen = impresion.colocacion(area, 148, 105, RES, escala_pct=120)
    assert escala == pytest.approx(base * 1.2)
    assert origen.x() == pytest.approx(10 + (130 * px_mm - 148 * escala) / 2)
    assert origen.x() < area.left()
    # Ampliado pero cabe: el ajuste fino no lo saca del área
    escala, origen = impresion.colocacion(area, 148, 105, RES, (10, 0), escala_pct=90)
    assert origen.x() + 148 * escala <= area.right() + 1e-6
    # Fuera de los límites del control, se acota
    assert impresion.colocacion(area, 148, 105, RES, escala_pct=500)[0] == pytest.approx(base * 2)
    assert impresion.colocacion(area, 148, 105, RES, escala_pct=1)[0] == pytest.approx(base * 0.5)


def test_el_tamano_se_guarda_y_llega_a_la_colocacion(qapp, datos, tmp_path, monkeypatch):
    g = GestorAjustes(datos)
    assert g.valores.escala_pct == 100
    g.poner(escala_pct=115)
    assert GestorAjustes(datos).valores.escala_pct == 115

    recibidos = []
    original = impresion.colocacion

    def espia(*args, **kwargs):
        recibidos.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(impresion, "colocacion", espia)
    impresion.pintar_partes(_impresora_pdf(tmp_path / "t.pdf"), [_datos()], _Contexto(g))
    assert recibidos and recibidos[0][0][5] == 115


def test_el_ajuste_de_color_se_guarda_y_llega_a_la_impresora(qapp, datos, monkeypatch):
    g = GestorAjustes(datos)
    assert g.valores.color_impresion == "color"
    g.poner(color_impresion="grises", impresora="Ficticia", imprimir_directo=True)
    assert GestorAjustes(datos).valores.color_impresion == "grises"

    usadas = []
    original = QPrinter.setColorMode
    monkeypatch.setattr(QPrinter, "setColorMode", lambda imp, modo: (usadas.append(modo), original(imp, modo)))
    monkeypatch.setattr(impresion, "impresoras", lambda: ["Ficticia"])
    monkeypatch.setattr(impresion, "pintar_partes", lambda imp, partes, ctx: None)
    assert impresion.imprimir_varios([_datos()], _Contexto(g))
    g.poner(color_impresion="color")
    assert impresion.imprimir_varios([_datos()], _Contexto(g))
    assert usadas == [QPrinter.ColorMode.GrayScale, QPrinter.ColorMode.Color]


def test_en_blanco_y_negro_se_dibuja_en_grises(qapp, datos, tmp_path, monkeypatch):
    g = GestorAjustes(datos)
    (tmp_path / "sello.png").write_bytes(ficticios.retrato(2))
    g.poner_imagen("sello", tmp_path / "sello.png")
    imagenes = ImagenesParte(g)

    def colores(img):
        return sum(1 for y in range(0, img.height(), 3) for x in range(0, img.width(), 3)
                   if (c := img.pixelColor(x, y)) and max(c.red(), c.green(), c.blue()) - min(c.red(), c.green(), c.blue()) > 8)

    assert colores(imagen_parte(_datos(), g, imagenes, 600)) > 100  # la foto y el sello, en color
    assert colores(imagen_parte(_datos(), g, imagenes, 600, grises=True)) == 0

    # La impresora en GrayScale hace que pintar_partes dibuje en grises (no depende del controlador)
    pedidos = []
    monkeypatch.setattr(impresion, "dibujar_parte", lambda *a, **k: pedidos.append(k.get("grises")))
    impresion.pintar_partes(_impresora_pdf(tmp_path / "g.pdf", color=False), [_datos()], _Contexto(g))
    impresion.pintar_partes(_impresora_pdf(tmp_path / "c.pdf"), [_datos()], _Contexto(g))
    assert pedidos == [True, False]


def test_a_grises_conserva_la_transparencia(qapp):
    img = QImage(4, 1, QImage.Format.Format_ARGB32)
    img.setPixelColor(0, 0, QColor(200, 30, 30, 255))
    img.setPixelColor(1, 0, QColor(30, 200, 30, 128))
    img.setPixelColor(2, 0, QColor(255, 255, 255, 0))
    img.setPixelColor(3, 0, QColor(30, 30, 200, 255))
    g = a_grises(img)
    for x, alfa in ((0, 255), (1, 128), (2, 0), (3, 255)):
        c = g.pixelColor(x, 0)
        assert c.alpha() == pytest.approx(alfa, abs=1)
        if alfa:
            assert c.red() == c.green() == c.blue()
