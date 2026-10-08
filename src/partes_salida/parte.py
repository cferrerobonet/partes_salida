"""El parte DIN-A6 horizontal (148 × 105 mm), dibujado en milímetros.

Un solo dibujo para la vista previa (QImage) y la impresora (QPrinter): sólo
cambia la escala de píxeles por milímetro. Así lo que se ve es lo que sale.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QTextDocument,
)

from .ajustes import GestorAjustes
from .fechas import fecha_corta, fecha_larga
from .modelo import Alumno
from .ui.estilo import CUERPO, MONO, TITULAR

ANCHO_MM = 148.0
ALTO_MM = 105.0
TINTA = QColor("#1b1f1c")
TINTA_SUAVE = QColor("#5a625c")
FONDO_FOTO = QColor("#e9ece8")

_A = Qt.AlignmentFlag
UNA = Qt.TextFlag.TextSingleLine.value
AJUSTE = Qt.TextFlag.TextWordWrap.value
IZQ = _A.AlignLeft.value | _A.AlignTop.value
ARRIBA_CENTRO = _A.AlignHCenter.value | _A.AlignTop.value
ARRIBA_DCHA = _A.AlignRight.value | _A.AlignTop.value
CENTRO = _A.AlignCenter.value


@dataclass
class DatosParte:
    alumno: Alumno
    foto: bytes | None
    salida: datetime
    expedido: datetime
    qr: str


class ImagenesParte:
    """Logos, sello y firma ya cargados; se recargan cuando cambian en Ajustes."""

    def __init__(self, gestor: GestorAjustes):
        self._gestor = gestor
        self._version = -1
        self._cache: dict[str, QImage | None] = {}

    def __getitem__(self, nombre: str) -> QImage | None:
        if self._version != self._gestor.version_imagenes:
            self._cache.clear()
            self._version = self._gestor.version_imagenes
        if nombre not in self._cache:
            ruta = self._gestor.ruta_imagen(nombre)
            img = QImage(str(ruta)) if ruta else None
            self._cache[nombre] = img if img is not None and not img.isNull() else None
        return self._cache[nombre]


def texto_parte(plantilla: str, alumno: Alumno, salida: datetime) -> str:
    """Plantilla de Ajustes → HTML de dos líneas, con la hora en negrita."""
    valores = {
        "{hora}": f"<b>{salida:%H:%M}</b>",
        "{nombre}": html.escape(alumno.nombre_completo),
        "{curso}": html.escape(alumno.curso),
        "{etapa}": html.escape(alumno.etapa),
        "{fecha}": html.escape(fecha_larga(salida.date())),
    }
    texto = html.escape(plantilla.strip())
    for k, v in valores.items():
        texto = texto.replace(k, v)
    return texto.replace("\n", "<br>")


class _Lienzo:
    def __init__(self, p: QPainter, escala: float, origen: QPointF):
        self.p = p
        self.s = escala
        self.o = origen

    def r(self, x: float, y: float, w: float, h: float) -> QRectF:
        return QRectF(self.o.x() + x * self.s, self.o.y() + y * self.s, w * self.s, h * self.s)

    def fuente(self, familia: str, tam_mm: float, peso: QFont.Weight, cursiva: bool = False, espacio: float = 0) -> QFont:
        f = QFont(familia)
        f.setPixelSize(max(1, round(tam_mm * self.s)))
        f.setWeight(peso)
        f.setItalic(cursiva)
        if espacio:
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, espacio * self.s)
        return f

    def texto(self, rect: QRectF, texto: str, f: QFont, color: QColor, flags, minimo_mm: float = 1.6) -> None:
        """Escribe reduciendo el cuerpo hasta que quepa (nombres largos, cursos largos)."""
        minimo = max(1, round(minimo_mm * self.s))
        f = QFont(f)
        while f.pixelSize() > minimo:
            caja = QFontMetricsF(f, self.p.device()).boundingRect(rect, flags, texto)
            if caja.width() <= rect.width() + 0.5 and caja.height() <= rect.height() + 0.5:
                break
            f.setPixelSize(f.pixelSize() - 1)
        self.p.setFont(f)
        self.p.setPen(color)
        self.p.drawText(rect, flags, texto)

    def imagen(self, img: QImage | None, caja: QRectF, alinear=Qt.AlignmentFlag.AlignCenter) -> None:
        if img is None:
            return
        escala = min(caja.width() / img.width(), caja.height() / img.height())
        w, h = img.width() * escala, img.height() * escala
        x = caja.x() if alinear & Qt.AlignmentFlag.AlignLeft else (
            caja.right() - w if alinear & Qt.AlignmentFlag.AlignRight else caja.x() + (caja.width() - w) / 2
        )
        y = caja.y() + (caja.height() - h) / 2
        self.p.drawImage(QRectF(x, y, w, h), img)


def _foto_recortada(img: QImage, caja: QRectF) -> tuple[QRectF, QRectF]:
    """Recorte central de la foto para llenar el hueco sin deformarla."""
    rel = caja.width() / caja.height()
    w, h = img.width(), img.height()
    if w / h > rel:
        nw = h * rel
        return caja, QRectF((w - nw) / 2, 0, nw, h)
    nh = w / rel
    return caja, QRectF(0, (h - nh) * 0.4, w, nh)


def _qr(lienzo: _Lienzo, texto: str, caja: QRectF) -> None:
    import segno

    codigo = segno.make(texto, error="m", micro=False, boost_error=False)
    filas = list(codigo.matrix_iter(border=0))
    n = len(filas)
    modulo = caja.width() / n
    camino = QPainterPath()
    for y, fila in enumerate(filas):
        x0 = None
        for x, v in enumerate(list(fila) + [0]):
            if v and x0 is None:
                x0 = x
            elif not v and x0 is not None:
                camino.addRect(QRectF(caja.x() + x0 * modulo, caja.y() + y * modulo, (x - x0) * modulo, modulo))
                x0 = None
    p = lienzo.p
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    p.fillPath(camino.simplified(), QBrush(TINTA))
    p.restore()


def dibujar_parte(
    p: QPainter,
    escala: float,
    datos: DatosParte,
    gestor: GestorAjustes,
    imagenes: ImagenesParte,
    origen: QPointF | None = None,
) -> None:
    """Dibuja el parte con `escala` píxeles del dispositivo por milímetro."""
    a = gestor.valores
    al = datos.alumno
    lz = _Lienzo(p, escala, origen or QPointF(0, 0))
    B = QFont.Weight
    A = Qt.AlignmentFlag
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Marco
    p.setPen(QPen(TINTA, 0.35 * escala))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(lz.r(4, 4, ANCHO_MM - 8, ALTO_MM - 8), 1.5 * escala, 1.5 * escala)

    # Logos y título
    lz.imagen(imagenes["logo_izquierdo"], lz.r(7, 6.5, 19, 19), A.AlignLeft)
    lz.imagen(imagenes["logo_derecho"], lz.r(111, 7.5, 30, 16), A.AlignRight)
    lz.texto(lz.r(29, 8.5, 80, 9), a.titulo, lz.fuente(TITULAR, 7.4, B.ExtraBold, espacio=0.1), TINTA,
             ARRIBA_CENTRO | UNA)
    lz.texto(lz.r(29, 17.4, 80, 4), f"{a.centro} · {a.localidad}", lz.fuente(CUERPO, 2.5, B.Normal), TINTA_SUAVE,
             ARRIBA_CENTRO | UNA)

    # Foto
    caja = lz.r(7, 29, 25, 32)
    p.fillRect(caja, FONDO_FOTO)
    foto = QImage.fromData(datos.foto) if datos.foto else QImage()
    if not foto.isNull():
        destino, origen_foto = _foto_recortada(foto, caja)
        p.drawImage(destino, foto, origen_foto)
    else:
        from .ui.estilo import silueta

        p.drawPixmap(caja.toRect(), silueta(al.id, 100, 128, 1.0))
    p.setPen(QPen(TINTA, 0.3 * escala))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(caja)

    # Datos
    etiqueta = lz.fuente(CUERPO, 2.3, B.Bold, espacio=0.18)
    valor = lz.fuente(CUERPO, 3.8, B.DemiBold)
    lz.texto(lz.r(36, 29, 30, 3), "ETAPA", etiqueta, TINTA_SUAVE, IZQ | UNA)
    lz.texto(lz.r(36, 32, 30, 5), al.etapa, valor, TINTA, IZQ | UNA)
    lz.texto(lz.r(68, 29, 34, 3), "CURSO", etiqueta, TINTA_SUAVE, IZQ | UNA)
    lz.texto(lz.r(68, 32, 34, 5), al.curso, valor, TINTA, IZQ | UNA)
    lz.texto(lz.r(36, 38.6, 40, 3), "ALUMNA" if al.es_mujer else "ALUMNO", etiqueta, TINTA_SUAVE, IZQ | UNA)
    lz.texto(lz.r(36, 41.6, 66, 14), f"{al.nombre}\n{al.apellidos}", lz.fuente(TITULAR, 5.6, B.Bold), TINTA,
             IZQ | AJUSTE, minimo_mm=2.6)
    if al.nia:
        lz.texto(lz.r(36, 57, 66, 3.5), f"NIA {al.nia}", lz.fuente(MONO, 2.4, B.Medium), TINTA_SUAVE, IZQ | UNA)

    # Hora de salida
    p.setPen(QPen(TINTA, 0.6 * escala))
    p.drawRoundedRect(lz.r(105, 29, 36, 32), 2 * escala, 2 * escala)
    centro = ARRIBA_CENTRO | UNA
    lz.texto(lz.r(105, 33, 36, 3), "HORA DE SALIDA", etiqueta, TINTA, centro)
    lz.texto(lz.r(106, 37, 34, 14), f"{datos.salida:%H:%M}", lz.fuente(TITULAR, 13, B.ExtraBold), TINTA,
             CENTRO | UNA)
    lz.texto(lz.r(105, 53.5, 36, 3.5), f"hoy, {fecha_corta(datos.salida.date())}", lz.fuente(CUERPO, 2.4, B.Normal),
             TINTA_SUAVE, centro)

    # Texto de autorización
    plantilla = a.texto_alumna if al.es_mujer else a.texto_alumno
    doc = QTextDocument()
    doc.documentLayout().setPaintDevice(p.device())
    doc.setDocumentMargin(0)
    doc.setDefaultFont(lz.fuente(CUERPO, 3.15, B.Normal))
    doc.setDefaultStyleSheet(f"body {{ color: {TINTA.name()}; }}")
    doc.setHtml(f"<body style='line-height:135%'>{texto_parte(plantilla, al, datos.salida)}</body>")
    doc.setTextWidth(134 * escala)
    p.save()
    p.translate(lz.r(7, 64.5, 0, 0).topLeft())
    doc.drawContents(p, QRectF(0, 0, 134 * escala, 12 * escala))
    p.restore()

    # Pie: QR, fecha, sello y firma
    _qr(lz, datos.qr, lz.r(7, 77, 20, 20))
    lz.texto(lz.r(30, 83.5, 78, 5), f"{a.localidad}, {fecha_larga(datos.expedido.date())}",
             lz.fuente(CUERPO, 3.1, B.Bold), TINTA, IZQ | UNA)
    lz.texto(lz.r(30, 88.4, 78, 4), f"Expedido a las {datos.expedido:%H:%M}", lz.fuente(CUERPO, 2.7, B.Normal),
             TINTA, IZQ | UNA)
    lz.imagen(imagenes["sello"], lz.r(117, 70, 25, 25))
    lz.imagen(imagenes["firma"], lz.r(110, 78, 27, 15))
    lz.texto(lz.r(90, 95.8, 51, 3.5), a.cargo_firma, lz.fuente(CUERPO, 2.4, B.Normal, cursiva=True), TINTA,
             ARRIBA_DCHA | UNA)


def imagen_parte(datos: DatosParte, gestor: GestorAjustes, imagenes: ImagenesParte, ancho_px: int) -> QImage:
    escala = ancho_px / ANCHO_MM
    img = QImage(ancho_px, round(ALTO_MM * escala), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor("#ffffff"))
    p = QPainter(img)
    dibujar_parte(p, escala, datos, gestor, imagenes)
    p.end()
    return img
