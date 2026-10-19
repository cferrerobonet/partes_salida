"""Impresión del parte en la bandeja A6 (uno o varios, uno por hoja), el parte en
PNG y PDF para el correo y el historial de un alumno en A4."""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import QBuffer, QIODevice, QMarginsF, QPointF, QRectF
from PyQt6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo

from .correo import ParteAdjunto
from .modelo import Alumno
from .parte import DatosParte, dibujar_parte, imagen_parte, maqueta

logger = logging.getLogger(__name__)


def impresoras() -> list[str]:
    return sorted(QPrinterInfo.availablePrinterNames())


A6 = QPageSize(QPageSize.PageSizeId.A6)


def tamano_a6(nombre_impresora: str) -> QPageSize:
    """El A6 tal como lo declara la propia impresora si lo tiene (así el diálogo del sistema lo enseña elegido con su
    nombre); si no, el A6 estándar (105 × 148 mm)."""
    if nombre_impresora:
        for tamano in QPrinterInfo.printerInfo(nombre_impresora).supportedPageSizes():
            if tamano.id() == QPageSize.PageSizeId.A6 or tamano.isEquivalentTo(A6):
                return tamano
    return A6


def _orientacion(orientacion: str) -> QPageLayout.Orientation:
    return QPageLayout.Orientation.Portrait if orientacion == "vertical" else QPageLayout.Orientation.Landscape


def _pagina_a6(orientacion: str, tamano: QPageSize | None = None) -> QPageLayout:
    return QPageLayout(tamano or A6, _orientacion(orientacion), QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)


def aplicar_a6(impresora: QPrinter, orientacion: str) -> None:
    """Pone la impresora en A6, página completa y la orientación de los ajustes.

    No vale `setPageLayout` con el A6 y márgenes cero: los controladores con márgenes mínimos (la Brother del centro,
    4,32 mm) lo rechazan y la impresora se queda en su A4 por defecto, que es lo que enseñaba el diálogo del sistema.
    Primero página completa y después tamaño, orientación y márgenes por separado: así lo aceptan.
    """
    impresora.setFullPage(True)
    impresora.setPageSize(tamano_a6(impresora.printerName()))
    impresora.setPageOrientation(_orientacion(orientacion))
    impresora.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)


def asegurar_a6(impresora: QPrinter, orientacion: str) -> bool:
    """El parte es siempre A6: si el diálogo del sistema ha dejado la impresora en otro papel (el A4 por defecto de la
    impresora) o en otra orientación, se vuelve a poner el A6 de los ajustes. `True` si hubo que corregirlo."""
    capa = impresora.pageLayout()
    bien = capa.pageSize().isEquivalentTo(A6) and capa.orientation() == _orientacion(orientacion)
    if not bien:
        logger.info("El diálogo traía %s en %s: el parte se imprime en A6", capa.pageSize().name(), capa.orientation().name)
        aplicar_a6(impresora, orientacion)
    return not bien


def area_imprimible(impresora: QPrinter) -> QRectF:
    """Rectángulo, en píxeles del dispositivo y coordenadas del pintor, donde la impresora imprime de verdad.

    En página completa el origen es la esquina del papel: se quitan los márgenes físicos de la impresora
    (`minimumMargins`) o los de la página, los que sean mayores. Así el parte no pierde el borde derecho
    ni el inferior en las impresoras que no llegan al filo del papel.
    """
    res = impresora.resolution()
    capa = impresora.pageLayout()
    if not impresora.fullPage():
        r = capa.paintRectPixels(res)
        return QRectF(0, 0, r.width(), r.height())
    m, minimos = capa.margins(), capa.minimumMargins()
    margenes = QMarginsF(max(m.left(), minimos.left()), max(m.top(), minimos.top()),
                         max(m.right(), minimos.right()), max(m.bottom(), minimos.bottom()))
    real = QPageLayout(capa.pageSize(), capa.orientation(), margenes, capa.units())
    return QRectF(real.paintRectPixels(res))


ESCALA_MIN, ESCALA_MAX = 50, 200  # límites del tamaño del parte (%), los mismos que el control de Ajustes


def colocacion(area: QRectF, ancho_mm: float, alto_mm: float, resolucion: int,
               ajuste_mm: tuple[float, float] = (0.0, 0.0), escala_pct: int = 100) -> tuple[float, QPointF]:
    """`(píxeles por mm, origen)` del parte: escalado en proporción para caber en `area` (nunca ampliado),
    multiplicado por el tamaño de Ajustes (`escala_pct`, 100 = lo que cabe), centrado, con el ajuste fino
    y sin salirse del área mientras quepa. Si el tamaño elegido lo hace más grande que el área, se queda
    centrado y sobresale por igual a los dos lados: es decisión de quien ajusta la impresora."""
    px_mm = resolucion / 25.4
    cabe = min(1.0, area.width() / (ancho_mm * px_mm), area.height() / (alto_mm * px_mm))
    escala = px_mm * cabe * min(max(int(escala_pct), ESCALA_MIN), ESCALA_MAX) / 100
    w, h = ancho_mm * escala, alto_mm * escala
    x = area.x() + (area.width() - w) / 2 + ajuste_mm[0] * px_mm
    y = area.y() + (area.height() - h) / 2 + ajuste_mm[1] * px_mm
    x = min(max(x, min(area.left(), area.right() - w)), max(area.left(), area.right() - w))
    y = min(max(y, min(area.top(), area.bottom() - h)), max(area.top(), area.bottom() - h))
    return escala, QPointF(x, y)


def pintar_partes(impresora: QPrinter, partes: list[DatosParte], contexto) -> None:
    """Dibuja los partes, uno por hoja, dentro del área imprimible de `impresora` (ya configurada)."""
    a = contexto.gestor.valores
    m = maqueta(a.orientacion)
    # Blanco y negro si lo dicen los Ajustes o el diálogo de la impresora: se dibuja ya en grises,
    # sin depender de que el controlador respete el modo de color.
    grises = a.color_impresion == "grises" or impresora.colorMode() == QPrinter.ColorMode.GrayScale
    pintor = QPainter()
    if not pintor.begin(impresora):
        raise RuntimeError(f"No se puede usar la impresora «{impresora.printerName()}»")
    try:
        area = area_imprimible(impresora)
        escala, origen = colocacion(area, m.ancho, m.alto, impresora.resolution(), (a.ajuste_x_mm, a.ajuste_y_mm),
                                    a.escala_pct)
        logger.info("Área imprimible %.0f × %.0f px; parte al %.1f %%%s", area.width(), area.height(),
                    escala * 2540 / impresora.resolution(), ", en blanco y negro" if grises else "")
        for i, datos in enumerate(partes):
            if i:
                impresora.newPage()
            dibujar_parte(pintor, escala, datos, contexto.gestor, contexto.imagenes, origen, grises=grises)
    finally:
        pintor.end()


def imprimir(datos: DatosParte, contexto, padre=None) -> bool:
    """`True` si el parte ha ido a la impresora; `False` si se cancela el diálogo."""
    return imprimir_varios([datos], contexto, padre)


def imprimir_varios(partes: list[DatosParte], contexto, padre=None) -> bool:
    """Todos los partes en un solo trabajo, uno por hoja A6. `False` si se cancela."""
    if not partes:
        return False
    a = contexto.gestor.valores
    impresora = QPrinter(QPrinter.PrinterMode.HighResolution)
    impresora.setDocName(
        f"Parte de salida {partes[0].alumno.nombre_listado}" if len(partes) == 1
        else f"Partes de salida ({len(partes)})"
    )
    directa = a.imprimir_directo and a.impresora and a.impresora in impresoras()
    if a.impresora and a.impresora in impresoras():
        impresora.setPrinterName(a.impresora)
    aplicar_a6(impresora, a.orientacion)
    impresora.setColorMode(
        QPrinter.ColorMode.GrayScale if a.color_impresion == "grises" else QPrinter.ColorMode.Color
    )
    if not directa:
        dialogo = QPrintDialog(impresora, padre)
        dialogo.setWindowTitle("Imprimir parte de salida" if len(partes) == 1 else "Imprimir partes de salida")
        if dialogo.exec() != QPrintDialog.DialogCode.Accepted:
            return False
        # Aunque en el diálogo quede el papel por defecto de la impresora (A4), el parte sale en A6
        asegurar_a6(impresora, a.orientacion)
    pintar_partes(impresora, partes, contexto)
    logger.info("%d parte(s) impreso(s) en %s", len(partes), impresora.printerName() or "(impresora por defecto)")
    return True


def parte_adjunto(datos: DatosParte, contexto) -> ParteAdjunto:
    """El parte para el correo: PNG nítido en el móvil (QR legible) y PDF A6 para imprimir.

    Se dibuja en el hilo de la interfaz (QPainter), antes de lanzar el envío.
    """
    gestor, imagenes = contexto.gestor, contexto.imagenes
    img = imagen_parte(datos, gestor, imagenes, 1400)
    buf_png = QBuffer()
    buf_png.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf_png, "PNG")
    buf_pdf = QBuffer()
    buf_pdf.open(QIODevice.OpenModeFlag.WriteOnly)
    pdf = QPdfWriter(buf_pdf)
    pdf.setResolution(300)
    pdf.setPageLayout(_pagina_a6(gestor.valores.orientacion))
    pdf.setTitle("Parte de salida")
    pdf.setCreator(gestor.valores.centro)
    pintor = QPainter(pdf)
    try:
        dibujar_parte(pintor, pdf.resolution() / 25.4, datos, gestor, imagenes)
    finally:
        pintor.end()
    nombre = f"Parte de salida {datos.alumno.nombre_listado} {datos.salida:%Y-%m-%d %H.%M}"
    return ParteAdjunto(bytes(buf_png.data()), bytes(buf_pdf.data()), nombre)


def imprimir_documento(html: str, titulo: str, padre=None) -> bool:
    """Un documento A4 (el historial) con el diálogo del sistema: impresora o PDF.

    No usa la impresora A6 de los ajustes: se elige en el diálogo.
    """
    impresora = QPrinter(QPrinter.PrinterMode.HighResolution)
    impresora.setDocName(titulo)
    impresora.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
        QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter,
    ))
    dialogo = QPrintDialog(impresora, padre)
    dialogo.setWindowTitle(titulo)
    if dialogo.exec() != QPrintDialog.DialogCode.Accepted:
        return False
    documento = QTextDocument()
    documento.setHtml(html)
    documento.print(impresora)
    return True


def parte_de_prueba(contexto) -> DatosParte:
    """Un parte ficticio para calibrar la impresora sin datos de nadie."""
    ahora = datetime.now().replace(second=0, microsecond=0)
    alumna = Alumno(id="00000000", nia="00000000", nombre="ALUMNA", apellido1="DE", apellido2="PRUEBA",
                    sexo="F", clase="1CFS-SEA")
    return DatosParte(alumna, None, ahora, ahora, contexto.firmante.contenido_qr(alumna.id, ahora, ahora))
