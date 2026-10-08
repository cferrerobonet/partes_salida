"""Aspecto de la maqueta aprobada: tipografías, colores claro/oscuro e iconos."""

from __future__ import annotations

import hashlib

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)

from ..rutas import recursos

CUERPO = "Barlow"
TITULAR = "Barlow Condensed"
MONO = "JetBrains Mono"

CLARO = {
    "bg": "#f3f5f1", "surface": "#ffffff", "surface2": "#eef2ec", "line": "#d9e0d5",
    "fg": "#1d2a20", "muted": "#5d6b60", "accent": "#2c7a3a", "accent_ink": "#ffffff",
    "accent_soft": "#e2f0e3", "gold": "#b97a12", "gold_soft": "#fbf0d9",
    "warn": "#9a5b00", "warn_soft": "#fff3dc", "danger": "#a32d2d",
}
OSCURO = {
    "bg": "#121713", "surface": "#1a211c", "surface2": "#222b24", "line": "#323d35",
    "fg": "#e4ebe5", "muted": "#9aa89d", "accent": "#5fbf6e", "accent_ink": "#0d1a10",
    "accent_soft": "#1f3524", "gold": "#e3a94a", "gold_soft": "#3a2e17",
    "warn": "#f0b45a", "warn_soft": "#3a2c14", "danger": "#f08a8a",
}

T: dict[str, str] = dict(CLARO)


def cargar_fuentes() -> None:
    for f in sorted((recursos() / "fuentes").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))


def es_oscuro() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def fuente(tam: float, peso: QFont.Weight = QFont.Weight.Normal, familia: str = CUERPO) -> QFont:
    f = QFont(familia)
    f.setPixelSize(round(tam))
    f.setWeight(peso)
    return f


def etiqueta_fuente(tam: float = 12) -> QFont:
    f = fuente(tam, QFont.Weight.Bold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.9)
    f.setCapitalization(QFont.Capitalization.AllUppercase)
    return f


def hoja(t: dict[str, str]) -> str:
    return f"""
QMainWindow, QDialog, QWidget#raiz {{ background: {t['bg']}; }}
QWidget#lienzo {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 12px; }}
QWidget#barra {{ background: {t['surface2']}; border-bottom: 1px solid {t['line']};
  border-top-left-radius: 12px; border-top-right-radius: 12px; }}
QFrame#separador {{ background: {t['line']}; }}
QLabel {{ background: transparent; }}
QLabel[rol="muted"] {{ color: {t['muted']}; font-size: 13px; }}
QLabel[rol="pequeno"] {{ color: {t['muted']}; font-size: 12px; }}
QLabel[rol="etiqueta"] {{ color: {t['muted']}; }}
QLabel[rol="cifrado"] {{ color: {t['accent']}; font-weight: 600; }}
QLabel[rol="tag-etapa"] {{ background: {t['gold_soft']}; color: {t['gold']}; font-weight: 600;
  font-size: 13px; padding: 3px 9px; border-radius: 5px; }}
QLabel[rol="tag"] {{ background: {t['surface2']}; font-weight: 600; font-size: 13px; padding: 3px 9px; border-radius: 5px; }}
QLabel[rol="aviso"] {{ background: {t['warn_soft']}; color: {t['warn']}; font-size: 13px; padding: 7px 9px; border-radius: 7px; }}
QLabel[rol="pendiente"] {{ background: {t['warn_soft']}; color: {t['warn']}; font-weight: 600; border-radius: 8px; }}
QLabel[rol="tel"] {{ font-family: "{MONO}"; font-size: 14px; }}
QLabel[rol="correo"] {{ color: {t['muted']}; font-size: 13px; }}
QFrame[rol="caja"] {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 10px; }}
QFrame[rol="fila"] {{ border: 0; border-top: 1px solid {t['line']}; border-radius: 0; background: transparent; }}
QFrame[rol="soltar"] {{ border: 1.5px dashed {t['line']}; border-radius: 10px; background: {t['surface']}; }}
QFrame[rol="soltar"][encima="true"] {{ border-color: {t['accent']}; background: {t['accent_soft']}; }}
QFrame[rol="dato"] {{ border: 1px solid {t['line']}; border-radius: 8px; background: {t['surface']}; }}
QFrame[rol="miniatura"] {{ border: 1px dashed {t['line']}; border-radius: 8px; background: #ffffff; }}
QLineEdit, QComboBox, QTimeEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
  background: {t['bg']}; border: 1px solid {t['line']}; border-radius: 7px; padding: 6px 9px;
  selection-background-color: {t['accent']}; selection-color: {t['accent_ink']}; }}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
  border: 1px solid {t['accent']}; }}
QLineEdit#buscador {{ padding: 9px 10px; font-size: 15px; border-radius: 8px; }}
QComboBox QAbstractItemView {{ background: {t['surface']}; border: 1px solid {t['line']};
  selection-background-color: {t['accent_soft']}; selection-color: {t['fg']}; }}
QTimeEdit#hora {{ font-family: "{TITULAR}"; font-size: 40px; font-weight: 700; padding: 2px 12px; }}
QPushButton {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 8px;
  padding: 7px 13px; font-weight: 600; }}
QPushButton:hover {{ border-color: {t['accent']}; }}
QPushButton:pressed {{ background: {t['surface2']}; }}
QPushButton:disabled {{ color: {t['muted']}; }}
QPushButton[pequeno="true"] {{ font-size: 13px; padding: 4px 10px; border-radius: 7px; }}
QPushButton[peligro="true"] {{ color: {t['danger']}; }}
QPushButton[primario="true"] {{ background: {t['accent']}; border-color: {t['accent']}; color: {t['accent_ink']}; }}
QPushButton[primario="true"]:hover {{ background: {t['accent']}; border-color: {t['fg']}; }}
QPushButton[primario="true"]:disabled {{ background: {t['line']}; border-color: {t['line']}; color: {t['muted']}; }}
QPushButton[grande="true"] {{ font-size: 18px; padding: 14px 16px; border-radius: 10px; }}
QPushButton[chip="true"] {{ font-size: 13px; padding: 4px 11px; border-radius: 13px; }}
QPushButton[chip="true"]:checked {{ background: {t['accent']}; border-color: {t['accent']}; color: {t['accent_ink']}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {t['line']}; border-radius: 4px; background: {t['surface']}; }}
QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; image: url(:/marca); }}
QCheckBox::indicator:disabled {{ background: {t['surface2']}; }}
QCheckBox:disabled {{ color: {t['muted']}; }}
QListView#resultados {{ background: transparent; border: 0; outline: 0; }}
QListWidget#navegacion {{ background: {t['surface2']}; border: 0; border-right: 1px solid {t['line']};
  padding: 10px; outline: 0; }}
QListWidget#navegacion::item {{ padding: 0 10px; border-radius: 7px; font-weight: 600; margin-bottom: 2px; }}
QListWidget#navegacion::item:selected {{ background: {t['surface']}; color: {t['accent']}; border: 1px solid {t['line']}; }}
QListWidget {{ background: {t['surface']}; border: 1px solid {t['line']}; border-radius: 8px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['line']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollArea {{ background: transparent; border: 0; }}
QToolTip {{ background: {t['fg']}; color: {t['bg']}; border: 0; padding: 5px 8px; }}
QProgressBar {{ border: 1px solid {t['line']}; border-radius: 6px; background: {t['surface2']}; text-align: center; height: 14px; }}
QProgressBar::chunk {{ background: {t['accent']}; border-radius: 5px; }}
QLabel#aviso_flotante {{ background: {t['fg']}; color: {t['bg']}; padding: 10px 16px; border-radius: 9px; font-weight: 600; }}
"""


def aplicar(app) -> None:
    from PyQt6.QtCore import QDir

    T.clear()
    T.update(OSCURO if es_oscuro() else CLARO)
    app.setStyle("Fusion")
    pal = app.palette()
    for rol, clave in (
        (QPalette.ColorRole.Window, "bg"),
        (QPalette.ColorRole.Base, "surface"),
        (QPalette.ColorRole.AlternateBase, "surface2"),
        (QPalette.ColorRole.Text, "fg"),
        (QPalette.ColorRole.WindowText, "fg"),
        (QPalette.ColorRole.ButtonText, "fg"),
        (QPalette.ColorRole.Button, "surface"),
        (QPalette.ColorRole.Highlight, "accent"),
        (QPalette.ColorRole.HighlightedText, "accent_ink"),
        (QPalette.ColorRole.PlaceholderText, "muted"),
    ):
        pal.setColor(rol, QColor(T[clave]))
    app.setPalette(pal)
    marca = _marca()
    QDir.addSearchPath("icono", str(marca.parent))
    app.setStyleSheet(hoja(T).replace("url(:/marca)", f"url('{marca.as_posix()}')"))
    app.setFont(fuente(14))


def _marca():
    """La marca blanca de las casillas, dibujada una vez en la carpeta temporal."""
    import tempfile
    from pathlib import Path

    ruta = Path(tempfile.gettempdir()) / "partes-salida-marca.png"
    if not ruta.exists():
        pm = QPixmap(32, 32)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#ffffff"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPolyline([QPointF(7, 17), QPointF(13, 23), QPointF(25, 9)])
        p.end()
        pm.save(str(ruta))
    return ruta


def icono_lupa(color: str, tam: int = 18) -> QIcon:
    pm = QPixmap(tam * 2, tam * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawEllipse(QRectF(5, 5, tam * 1.15, tam * 1.15))
    p.drawLine(QPointF(tam * 1.32, tam * 1.32), QPointF(tam * 1.8, tam * 1.8))
    p.end()
    return QIcon(pm)


def icono_candado(color: str, tam: int = 14) -> QPixmap:
    pm = QPixmap(tam * 2, tam * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color)
    p.setPen(QPen(c, tam * 0.28))
    p.drawArc(QRectF(tam * 0.55, tam * 0.2, tam * 0.9, tam * 1.2), 0, 180 * 16)
    p.drawLine(QPointF(tam * 0.55, tam * 0.8), QPointF(tam * 0.55, tam * 0.95))
    p.drawLine(QPointF(tam * 1.45, tam * 0.8), QPointF(tam * 1.45, tam * 0.95))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawRoundedRect(QRectF(tam * 0.25, tam * 0.9, tam * 1.5, tam * 1.05), 3, 3)
    p.end()
    pm.setDevicePixelRatio(2)
    return pm


def silueta(clave: str, ancho: int, alto: int, dpr: float = 2.0, texto: bool = True) -> QPixmap:
    """Hueco de foto: el mismo dibujo de la maqueta, con un tono distinto por alumno."""
    tono = int(hashlib.md5(clave.encode()).hexdigest()[:4], 16) % 360
    pm = QPixmap(int(ancho * dpr), int(alto * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(QColor.fromHsl(tono, 46, 222))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor.fromHsl(tono, 36, 168))
    r = ancho * 0.22
    p.drawEllipse(QPointF(ancho / 2, alto * 0.375), r, r)
    cuerpo = QPainterPath()
    cuerpo.moveTo(ancho * 0.1, alto)
    cuerpo.cubicTo(ancho * 0.14, alto * 0.72, ancho * 0.3, alto * 0.66, ancho / 2, alto * 0.66)
    cuerpo.cubicTo(ancho * 0.7, alto * 0.66, ancho * 0.86, alto * 0.72, ancho * 0.9, alto)
    cuerpo.closeSubpath()
    p.drawPath(cuerpo)
    if texto and alto > 60:
        p.setPen(QColor.fromHsl(tono, 50, 96))
        p.setFont(fuente(max(7, alto * 0.07)))
        p.drawText(QRectF(0, alto * 0.86, ancho, alto * 0.12), Qt.AlignmentFlag.AlignCenter, "FOTO")
    p.end()
    return pm


def redondear(pm: QPixmap, radio: float) -> QPixmap:
    dpr = pm.devicePixelRatio()
    salida = QPixmap(pm.size())
    salida.setDevicePixelRatio(dpr)
    salida.fill(Qt.GlobalColor.transparent)
    p = QPainter(salida)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    camino = QPainterPath()
    camino.addRoundedRect(QRectF(0, 0, pm.width() / dpr, pm.height() / dpr), radio, radio)
    p.setClipPath(camino)
    p.drawPixmap(0, 0, pm)
    p.end()
    return salida
