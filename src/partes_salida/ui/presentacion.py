"""Pantalla de presentación al abrir (con la carga real de cada paso) y «Acerca de».

Diseño fijo y corporativo, igual en modo claro y oscuro: banda verde EPLA con el
escudo y el título, barra de carga dorada y pie con el centro y la autoría.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, QVariantAnimation
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from .. import NOMBRE_APP, __version__
from ..rutas import recursos
from . import estilo

VERDE_OSCURO = QColor("#1c5226")
VERDE = QColor("#2c7a3a")
DORADO = QColor("#b97a12")
DORADO_CLARO = QColor("#e3a94a")
TEXTO = QColor("#1d2a20")
GRIS = QColor("#5d6b60")
PISTA = QColor("#e6ece4")
AUTORIA = "Diseño y desarrollo: Carlos Ferrero Bonet"
CENTRO = "Escuelas Profesionales Luis Amigó · Godella"
MINIMO_MS = 1400


class Presentacion(QWidget):
    def __init__(self, acerca_de: bool = False, padre=None):
        tipo = Qt.WindowType.Dialog if acerca_de else Qt.WindowType.SplashScreen
        super().__init__(padre, tipo | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedSize(620, 380)
        self.setWindowTitle(NOMBRE_APP)
        self._acerca = acerca_de
        self._texto = "Iniciando…"
        self._valor = 0.0
        self._inicio = time.monotonic()
        self._escudo = QPixmap(str(recursos() / "logo_izquierdo.png"))
        self._amigo = QPixmap(str(recursos() / "logo_derecho.png"))
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(320)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._mover)
        pantalla = QGuiApplication.primaryScreen()
        if pantalla is not None:
            centro = pantalla.availableGeometry().center()
            self.move(centro.x() - self.width() // 2, centro.y() - self.height() // 2)
        if acerca_de:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Pulsa para cerrar")

    # Progreso
    def _mover(self, v) -> None:
        self._valor = float(v)
        self.update()

    def paso(self, texto: str, porcentaje: float) -> None:
        """Muestra el paso de carga en curso; la barra avanza con suavidad."""
        self._texto = texto
        self._anim.stop()
        self._anim.setStartValue(self._valor)
        self._anim.setEndValue(max(0.0, min(1.0, porcentaje / 100)))
        self._anim.start()
        self.update()
        QApplication.processEvents()

    def terminar(self, despues) -> None:
        """Cierra con un fundido, sin desaparecer antes de que se haya podido leer."""
        self.paso("Listo", 100)
        espera = max(0, int(MINIMO_MS - (time.monotonic() - self._inicio) * 1000))

        def fundido():
            despues()
            anim = QPropertyAnimation(self, b"windowOpacity", self)
            anim.setDuration(260)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.finished.connect(self.close)
            anim.start()

        QTimer.singleShot(espera, fundido)

    def mousePressEvent(self, e):  # noqa: N802
        if self._acerca:
            self.close()

    def keyPressEvent(self, e):  # noqa: N802
        if self._acerca and e.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Space):
            self.close()

    # Dibujo
    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        tarjeta = QRectF(self.rect()).adjusted(16, 14, -16, -18)

        # Sombra suave
        for i in range(10):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(10, 30, 15, 7))
            p.drawRoundedRect(tarjeta.adjusted(-i * 0.8, -i * 0.4 + 3, i * 0.8, i * 1.2 + 3), 18 + i, 18 + i)

        forma = QPainterPath()
        forma.addRoundedRect(tarjeta, 18, 18)
        p.setClipPath(forma)
        p.fillPath(forma, QColor("#ffffff"))

        # Banda corporativa con el engranaje del escudo en filigrana
        banda = QRectF(tarjeta.x(), tarjeta.y(), tarjeta.width(), 200)
        degradado = QLinearGradient(banda.topLeft(), banda.bottomRight())
        degradado.setColorAt(0, VERDE_OSCURO)
        degradado.setColorAt(1, VERDE)
        p.fillRect(banda, degradado)
        centro = QPointF(banda.right() - 70, banda.y() + 60)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for r, alfa in ((150, 22), (118, 18), (86, 14)):
            p.setPen(QPen(QColor(255, 255, 255, alfa), 14 if r == 150 else 6))
            p.drawEllipse(centro, r, r)
        p.setPen(QPen(DORADO_CLARO, 4))
        p.drawLine(QPointF(banda.x(), banda.bottom() - 2), QPointF(banda.right(), banda.bottom() - 2))

        # Escudo en su medallón
        medallon = QPointF(banda.x() + 86, banda.y() + 100)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawEllipse(medallon, 58, 58)
        if not self._escudo.isNull():
            lado = 100
            escudo = self._escudo.scaled(lado * 2, lado * 2, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(QRectF(medallon.x() - lado / 2, medallon.y() - lado / 2, lado, lado), escudo,
                         QRectF(escudo.rect()))

        # Título, lema y versión
        x = banda.x() + 168
        p.setPen(QColor("#ffffff"))
        p.setFont(estilo.fuente(13, QFont.Weight.Bold))
        f = p.font()
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        p.setFont(f)
        p.drawText(QRectF(x, banda.y() + 46, 400, 20), int(Qt.AlignmentFlag.AlignLeft), "JEFATURA DE ESTUDIOS · EPLA")
        p.setFont(estilo.fuente(46, QFont.Weight.ExtraBold, estilo.TITULAR))
        p.drawText(QRectF(x, banda.y() + 66, 420, 56), int(Qt.AlignmentFlag.AlignLeft), NOMBRE_APP)
        p.setFont(estilo.fuente(15))
        p.setPen(QColor(255, 255, 255, 225))
        p.drawText(QRectF(x, banda.y() + 124, 420, 22), int(Qt.AlignmentFlag.AlignLeft),
                   "Pase de salida del alumnado en DIN-A6")
        version = f"v{__version__}"
        p.setFont(estilo.fuente(12, QFont.Weight.DemiBold))
        ancho = p.fontMetrics().horizontalAdvance(version) + 18
        pastilla = QRectF(x, banda.y() + 154, ancho, 22)
        p.setPen(QPen(QColor(255, 255, 255, 170), 1))
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(pastilla, 11, 11)
        p.setPen(QColor("#ffffff"))
        p.drawText(pastilla, int(Qt.AlignmentFlag.AlignCenter), version)

        # Estado de carga (o datos de «Acerca de»)
        izq = tarjeta.x() + 34
        ancho_util = tarjeta.width() - 68
        y = banda.bottom() + 26
        p.setFont(estilo.fuente(15, QFont.Weight.DemiBold))
        p.setPen(TEXTO)
        if self._acerca:
            p.drawText(QRectF(izq, y, ancho_util, 22), int(Qt.AlignmentFlag.AlignLeft),
                       "Datos del alumnado cifrados en este equipo")
            p.setFont(estilo.fuente(13))
            p.setPen(GRIS)
            p.drawText(QRectF(izq, y + 24, ancho_util, 20), int(Qt.AlignmentFlag.AlignLeft),
                       "QR firmado para la app del vigilante · github.com/cferrerobonet/partes_salida")
        else:
            p.drawText(QRectF(izq, y, ancho_util, 22), int(Qt.AlignmentFlag.AlignLeft), self._texto)
            pista = QRectF(izq, y + 32, ancho_util, 6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(PISTA)
            p.drawRoundedRect(pista, 3, 3)
            if self._valor > 0:
                lleno = QRectF(pista.x(), pista.y(), max(6.0, pista.width() * self._valor), pista.height())
                oro = QLinearGradient(lleno.topLeft(), lleno.topRight())
                oro.setColorAt(0, DORADO)
                oro.setColorAt(1, DORADO_CLARO)
                p.setBrush(oro)
                p.drawRoundedRect(lleno, 3, 3)

        # Pie: centro, autoría y Colegios Amigó
        pie = tarjeta.bottom() - 52
        p.setPen(QPen(PISTA, 1))
        p.drawLine(QPointF(izq, pie - 10), QPointF(izq + ancho_util, pie - 10))
        p.setFont(estilo.fuente(12, QFont.Weight.DemiBold))
        p.setPen(TEXTO)
        p.drawText(QRectF(izq, pie, 380, 18), int(Qt.AlignmentFlag.AlignLeft), CENTRO)
        p.setFont(estilo.fuente(12))
        p.setPen(GRIS)
        p.drawText(QRectF(izq, pie + 18, 380, 18), int(Qt.AlignmentFlag.AlignLeft), f"{AUTORIA} · © 2026")
        if not self._amigo.isNull():
            alto = 36
            logo = self._amigo.scaledToHeight(alto * 2, Qt.TransformationMode.SmoothTransformation)
            w = logo.width() / 2
            p.drawPixmap(QRectF(izq + ancho_util - w, pie - 2, w, alto), logo, QRectF(logo.rect()))
        p.end()


def acerca_de(padre=None) -> Presentacion:
    ventana = Presentacion(acerca_de=True, padre=padre)
    ventana.show()
    ventana.raise_()
    ventana.activateWindow()
    return ventana
