"""Impresión del parte en la bandeja A6 (uno o varios, uno por hoja), el parte en
PNG y PDF para el correo y el historial de un alumno en A4."""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import QBuffer, QIODevice, QMarginsF, QPointF
from PyQt6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo

from .correo import ParteAdjunto
from .modelo import Alumno
from .parte import DatosParte, dibujar_parte, imagen_parte

logger = logging.getLogger(__name__)


def impresoras() -> list[str]:
    return sorted(QPrinterInfo.availablePrinterNames())


def _pagina_a6(orientacion: str) -> QPageLayout:
    return QPageLayout(
        QPageSize(QPageSize.PageSizeId.A6),
        QPageLayout.Orientation.Portrait if orientacion == "vertical" else QPageLayout.Orientation.Landscape,
        QMarginsF(0, 0, 0, 0),
        QPageLayout.Unit.Millimeter,
    )


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
    impresora.setPageLayout(_pagina_a6(a.orientacion))
    impresora.setFullPage(True)
    if not directa:
        dialogo = QPrintDialog(impresora, padre)
        dialogo.setWindowTitle("Imprimir parte de salida" if len(partes) == 1 else "Imprimir partes de salida")
        if dialogo.exec() != QPrintDialog.DialogCode.Accepted:
            return False
    pintor = QPainter()
    if not pintor.begin(impresora):
        raise RuntimeError(f"No se puede usar la impresora «{impresora.printerName()}»")
    try:
        escala = impresora.resolution() / 25.4
        origen = QPointF(a.ajuste_x_mm * escala, a.ajuste_y_mm * escala)
        for i, datos in enumerate(partes):
            if i:
                impresora.newPage()
            dibujar_parte(pintor, escala, datos, contexto.gestor, contexto.imagenes, origen)
    finally:
        pintor.end()
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
