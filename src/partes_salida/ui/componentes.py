"""Piezas reutilizables de la interfaz."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import estilo


def etiqueta(texto: str = "", rol: str | None = None, envolver: bool = False) -> QLabel:
    e = QLabel(texto)
    if rol:
        e.setProperty("rol", rol)
    if rol == "etiqueta":
        e.setFont(estilo.etiqueta_fuente(12))
    e.setWordWrap(envolver)
    return e


def boton(texto: str, **propiedades) -> QPushButton:
    b = QPushButton(texto)
    for k, v in propiedades.items():
        b.setProperty(k, v)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def separador_vertical() -> QFrame:
    f = QFrame()
    f.setObjectName("separador")
    f.setFixedWidth(1)
    return f


def refrescar_estilo(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)


class FlujoLayout(QLayout):
    """Coloca los botones de etapa en filas que se parten solas."""

    def __init__(self, parent=None, espacio: int = 6):
        super().__init__(parent)
        self._items = []
        self._espacio = espacio
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):  # noqa: N802
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):  # noqa: N802
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, ancho):  # noqa: N802
        return self._colocar(QRect(0, 0, ancho, 0), True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._colocar(rect, False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        tam = QSize()
        for item in self._items:
            tam = tam.expandedTo(item.minimumSize())
        return tam

    def _colocar(self, rect: QRect, solo_medir: bool) -> int:
        x, y, alto_fila = rect.x(), rect.y(), 0
        for item in self._items:
            ancho = item.sizeHint().width()
            if x + ancho > rect.right() + 1 and alto_fila > 0:
                x, y = rect.x(), y + alto_fila + self._espacio
                alto_fila = 0
            if not solo_medir:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += ancho + self._espacio
            alto_fila = max(alto_fila, item.sizeHint().height())
        return y + alto_fila - rect.y()


class AvisoFlotante(QLabel):
    """Mensaje breve sobre la ventana («Parte impreso…»), que se va solo."""

    def __init__(self, padre: QWidget):
        super().__init__(padre)
        self.setObjectName("aviso_flotante")
        self.setWordWrap(True)
        self.hide()
        self._temporizador = QTimer(self, singleShot=True, timeout=self.hide)

    def mostrar(self, texto: str, ms: int = 3500) -> None:
        self.setText(texto)
        padre = self.parentWidget()
        self.setMaximumWidth(min(560, padre.width() - 40))
        self.adjustSize()
        self.move((padre.width() - self.width()) // 2, padre.height() - self.height() - 24)
        self.raise_()
        self.show()
        self._temporizador.start(ms)


class ZonaSoltar(QFrame):
    """Fila con icono, explicación y botón; también admite arrastrar archivos encima."""

    archivos = pyqtSignal(list)

    def __init__(self, titulo: str, explicacion: str, texto_boton: str, extensiones: tuple[str, ...], icono: str):
        super().__init__()
        self.setProperty("rol", "soltar")
        self.setAcceptDrops(True)
        self._extensiones = extensiones
        fila = QHBoxLayout(self)
        fila.setContentsMargins(14, 14, 14, 14)
        fila.setSpacing(14)
        simbolo = QLabel(icono)
        simbolo.setFixedSize(38, 38)
        simbolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        simbolo.setStyleSheet(
            f"background:{estilo.T['accent_soft']};color:{estilo.T['accent']};border-radius:9px;font-size:18px;"
        )
        fila.addWidget(simbolo, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        t = etiqueta(titulo)
        t.setStyleSheet("font-weight:700;")
        textos.addWidget(t)
        self.explicacion = etiqueta(explicacion, "muted", envolver=True)
        textos.addWidget(self.explicacion)
        fila.addLayout(textos, 1)
        self.boton = boton(texto_boton, pequeno=True)
        fila.addWidget(self.boton, 0, Qt.AlignmentFlag.AlignVCenter)

    def _validos(self, evento) -> list[str]:
        urls = evento.mimeData().urls() if evento.mimeData().hasUrls() else []
        return [u.toLocalFile() for u in urls if Path(u.toLocalFile()).suffix.lower() in self._extensiones]

    def dragEnterEvent(self, e):  # noqa: N802
        if self._validos(e):
            self.setProperty("encima", True)
            refrescar_estilo(self)
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):  # noqa: N802
        self.setProperty("encima", False)
        refrescar_estilo(self)

    def dropEvent(self, e):  # noqa: N802
        self.setProperty("encima", False)
        refrescar_estilo(self)
        validos = self._validos(e)
        if validos:
            self.archivos.emit(validos)


class Miniatura(QFrame):
    """Hueco de 120 × 64 para un logo, el sello o la firma."""

    def __init__(self):
        super().__init__()
        self.setProperty("rol", "miniatura")
        self.setFixedSize(124, 68)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(6, 6, 6, 6)
        self._imagen = QLabel()
        self._imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caja.addWidget(self._imagen)

    def poner(self, ruta: Path | None, pendiente: str = "Pendiente") -> None:
        if ruta:
            pm = QPixmap(str(ruta))
            dpr = self.devicePixelRatioF() or 2
            pm = pm.scaled(int(110 * dpr), int(54 * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            self._imagen.setPixmap(pm)
            self._imagen.setProperty("rol", None)
            self.setProperty("rol", "miniatura")
        else:
            self._imagen.setPixmap(QPixmap())
            self._imagen.setText(pendiente)
            self._imagen.setProperty("rol", "pendiente")
            self._imagen.setWordWrap(True)
        refrescar_estilo(self._imagen)


class Tarea(QThread):
    """Ejecuta un trabajo largo (importar) fuera de la interfaz, con progreso."""

    progreso = pyqtSignal(int, int, str)
    terminado = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, trabajo: Callable, *args):
        super().__init__()
        self._trabajo = trabajo
        self._args = args

    def run(self):
        try:
            self.terminado.emit(self._trabajo(*self._args, self.progreso.emit))
        except Exception as e:  # noqa: BLE001 - nada puede escapar de run()
            self.fallo.emit(str(e))


def politica(w: QWidget, h: QSizePolicy.Policy, v: QSizePolicy.Policy) -> QWidget:
    w.setSizePolicy(h, v)
    return w
