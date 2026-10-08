"""Impresión del parte en la bandeja A6, directa o con el diálogo del sistema."""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import QMarginsF, QPointF
from PyQt6.QtGui import QPageLayout, QPageSize, QPainter
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo

from .modelo import Alumno
from .parte import DatosParte, dibujar_parte

logger = logging.getLogger(__name__)


def impresoras() -> list[str]:
    return sorted(QPrinterInfo.availablePrinterNames())


def _a6(impresora: QPrinter) -> None:
    impresora.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.PageSizeId.A6),
            QPageLayout.Orientation.Landscape,
            QMarginsF(0, 0, 0, 0),
            QPageLayout.Unit.Millimeter,
        )
    )
    impresora.setFullPage(True)


def imprimir(datos: DatosParte, contexto, padre=None) -> bool:
    """`True` si el parte ha ido a la impresora; `False` si se cancela el diálogo."""
    a = contexto.gestor.valores
    impresora = QPrinter(QPrinter.PrinterMode.HighResolution)
    impresora.setDocName(f"Parte de salida {datos.alumno.nombre_listado}")
    directa = a.imprimir_directo and a.impresora and a.impresora in impresoras()
    if a.impresora and a.impresora in impresoras():
        impresora.setPrinterName(a.impresora)
    _a6(impresora)
    if not directa:
        dialogo = QPrintDialog(impresora, padre)
        dialogo.setWindowTitle("Imprimir parte de salida")
        if dialogo.exec() != QPrintDialog.DialogCode.Accepted:
            return False
    pintor = QPainter()
    if not pintor.begin(impresora):
        raise RuntimeError(f"No se puede usar la impresora «{impresora.printerName()}»")
    try:
        escala = impresora.resolution() / 25.4
        origen = QPointF(a.ajuste_x_mm * escala, a.ajuste_y_mm * escala)
        dibujar_parte(pintor, escala, datos, contexto.gestor, contexto.imagenes, origen)
    finally:
        pintor.end()
    logger.info("Parte impreso en %s", impresora.printerName() or "(impresora por defecto)")
    return True


def parte_de_prueba(contexto) -> DatosParte:
    """Un parte ficticio para calibrar la impresora sin datos de nadie."""
    ahora = datetime.now().replace(second=0, microsecond=0)
    alumna = Alumno(id="00000000", nia="00000000", nombre="ALUMNA", apellido1="DE", apellido2="PRUEBA",
                    sexo="F", clase="1CFS-SEA")
    return DatosParte(alumna, None, ahora, ahora, contexto.firmante.contenido_qr(alumna.id, ahora, ahora))
