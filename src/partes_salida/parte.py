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

TINTA = QColor("#1b1f1c")
TINTA_SUAVE = QColor("#5a625c")
FONDO_FOTO = QColor("#e9ece8")
_TINTAS = (TINTA, TINTA_SUAVE, FONDO_FOTO)

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


def a_grises(img: QImage | None) -> QImage | None:
    """La misma imagen en escala de grises, conservando la transparencia (el sello se ve sobre la firma)."""
    if img is None or img.isNull():
        return img
    argb = img.convertToFormat(QImage.Format.Format_ARGB32)
    gris = argb.convertToFormat(QImage.Format.Format_Grayscale8).convertToFormat(QImage.Format.Format_ARGB32)
    if argb.hasAlphaChannel():
        gris.setAlphaChannel(argb.convertToFormat(QImage.Format.Format_Alpha8))
    return gris


def color_gris(c: QColor) -> QColor:
    v = round(0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
    return QColor(v, v, v, c.alpha())


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

    def en_grises(self, nombre: str) -> QImage | None:
        clave = f"{nombre}:grises"
        original = self[nombre]  # recarga la caché si cambiaron las imágenes
        if clave not in self._cache:
            self._cache[clave] = a_grises(original)
        return self._cache[clave]


def texto_parte(plantilla: str, alumno: Alumno, salida: datetime) -> str:
    """Plantilla de Ajustes → HTML de dos líneas, con la hora en negrita."""
    valores = {
        "{hora}": f"<b>{salida:%H:%M}</b>",
        "{nombre}": html.escape(alumno.nombre_completo),
        "{curso}": html.escape(alumno.curso),
        "{etapa}": html.escape(alumno.etapa),
        "{fecha}": html.escape(fecha_larga(salida.date())),
    }
    # «12:30 h» nunca se parte: la «h» sola en otra línea despista.
    texto = html.escape(plantilla.strip()).replace("{hora} h", f"<b>{salida:%H:%M}</b>&nbsp;h")
    for k, v in valores.items():
        texto = texto.replace(k, v)
    return texto.replace("\n", "<br>")


_MAYUSCULAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


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
            # En porcentaje del ancho medio de la letra: el espaciado absoluto Qt lo multiplica por
            # ppp/96 en la impresora y el PDF (a 1200 ppp, «HORA DE SALIDA» no cabía en su recuadro).
            ancho = QFontMetricsF(f).horizontalAdvance(_MAYUSCULAS) / len(_MAYUSCULAS)
            f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 * (1 + espacio * self.s / ancho))
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


def _qr(lienzo: _Lienzo, texto: str, caja: QRectF, tinta: QColor = TINTA) -> None:
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
    # Un solo trazado con relleno de bobinado: los tramos que se tocan se pintan como uno, sin rendijas.
    # Nada de `simplified()`: con escala decimal (PDF, impresora) perdía módulos y rompía el QR.
    camino.setFillRule(Qt.FillRule.WindingFill)
    p = lienzo.p
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    p.fillPath(camino, QBrush(tinta))
    p.restore()


@dataclass(frozen=True)
class Maqueta:
    """Posición y tamaño (mm) de cada elemento: `(x, y, ancho, alto)`."""

    ancho: float
    alto: float
    logo_izq: tuple
    logo_der: tuple
    titulo: tuple
    titulo_mm: float
    centro: tuple
    foto: tuple
    etapa: tuple
    curso: tuple
    alumno: tuple
    nombre: tuple
    nia: tuple
    hora: tuple
    hora_etiqueta: tuple
    fecha_valor: tuple
    hora_valor: tuple
    hora_mm: float
    texto: tuple
    texto_mm: float
    qr: tuple
    lugar: tuple
    lugar_ajusta: bool
    expedido: tuple
    sello: tuple
    firma: tuple
    cargo: tuple


#: Foto a la izquierda; etapa y curso en una fila y, bajo ella, el nombre y el recuadro con la fecha
#: y la hora de salida, igual de grandes (CarlosFB, 2026-10-23).
HORIZONTAL = Maqueta(
    ancho=148, alto=105,
    logo_izq=(7, 6.5, 19, 19), logo_der=(111, 7.5, 30, 16),
    titulo=(29, 8.5, 80, 9), titulo_mm=7.4, centro=(29, 17.4, 80, 4),
    foto=(7, 29, 25, 32),
    etapa=(36, 29, 50, 8), curso=(88, 29, 53, 8), alumno=(36, 38.6, 44, 3), nombre=(36, 41.6, 44, 14),
    nia=(36, 57, 44, 3.5),
    hora=(82, 38.5, 59, 22.5), hora_etiqueta=(82, 40.5, 59, 3), fecha_valor=(84, 44, 35, 15),
    hora_valor=(121, 44, 18, 15), hora_mm=8,
    texto=(7, 64.5, 134, 12), texto_mm=3.15,
    qr=(7, 77, 20, 20), lugar=(30, 83.5, 78, 5), lugar_ajusta=False, expedido=(30, 88.4, 78, 4),
    sello=(117, 70, 25, 25), firma=(110, 78, 27, 15), cargo=(90, 95.8, 51, 3.5),
)

#: Misma información en 105 × 148 mm: la fecha y la hora van en una franja a todo el ancho.
VERTICAL = Maqueta(
    ancho=105, alto=148,
    logo_izq=(7, 7, 17, 17), logo_der=(70, 9, 28, 13),
    titulo=(7, 27, 91, 8), titulo_mm=6.6, centro=(7, 35, 91, 4),
    foto=(7, 42, 26, 33),
    etapa=(37, 42, 61, 8), curso=(37, 51, 61, 8), alumno=(37, 60, 61, 3), nombre=(37, 63, 61, 10),
    nia=(37, 73, 61, 3.5),
    hora=(7, 79, 91, 22), hora_etiqueta=(7, 81, 91, 3), fecha_valor=(9, 84.5, 51, 14),
    hora_valor=(62, 84.5, 34, 14), hora_mm=11.5,
    texto=(7, 103.5, 91, 14), texto_mm=2.8,
    qr=(7, 121, 20, 20), lugar=(30, 122, 40, 8), lugar_ajusta=True, expedido=(30, 130.5, 40, 4),
    sello=(74, 117, 24, 22), firma=(67, 124, 26, 12), cargo=(40, 139.5, 58, 3.5),
)

ANCHO_MM, ALTO_MM = HORIZONTAL.ancho, HORIZONTAL.alto


def maqueta(orientacion: str) -> Maqueta:
    return VERTICAL if orientacion == "vertical" else HORIZONTAL


def dibujar_parte(
    p: QPainter,
    escala: float,
    datos: DatosParte,
    gestor: GestorAjustes,
    imagenes: ImagenesParte,
    origen: QPointF | None = None,
    grises: bool = False,
) -> None:
    """Dibuja el parte con `escala` píxeles del dispositivo por milímetro, en la orientación de los ajustes.

    `grises`: blanco y negro (tintas, foto, logos, sello y firma en escala de grises), sin depender del controlador.
    """
    a = gestor.valores
    tinta, suave, fondo_foto = (color_gris(c) for c in _TINTAS) if grises else _TINTAS
    imagen = imagenes.en_grises if grises else imagenes.__getitem__
    m = maqueta(a.orientacion)
    al = datos.alumno
    lz = _Lienzo(p, escala, origen or QPointF(0, 0))
    B = QFont.Weight
    A = Qt.AlignmentFlag
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Marco
    p.setPen(QPen(tinta, 0.35 * escala))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(lz.r(4, 4, m.ancho - 8, m.alto - 8), 1.5 * escala, 1.5 * escala)

    # Logos y título
    lz.imagen(imagen("logo_izquierdo"), lz.r(*m.logo_izq), A.AlignLeft)
    lz.imagen(imagen("logo_derecho"), lz.r(*m.logo_der), A.AlignRight)
    lz.texto(lz.r(*m.titulo), a.titulo, lz.fuente(TITULAR, m.titulo_mm, B.ExtraBold, espacio=0.1), tinta,
             ARRIBA_CENTRO | UNA)
    lz.texto(lz.r(*m.centro), f"{a.centro} · {a.localidad}", lz.fuente(CUERPO, 2.5, B.Normal), suave,
             ARRIBA_CENTRO | UNA)

    # Foto
    caja = lz.r(*m.foto)
    p.fillRect(caja, fondo_foto)
    foto = QImage.fromData(datos.foto) if datos.foto else QImage()
    if grises:
        foto = a_grises(foto)
    if not foto.isNull():
        destino, origen_foto = _foto_recortada(foto, caja)
        p.drawImage(destino, foto, origen_foto)
    else:
        from .ui.estilo import silueta

        figura = silueta(al.id, 100, 128, 1.0)
        if grises:
            p.drawImage(caja, a_grises(figura.toImage()))
        else:
            p.drawPixmap(caja.toRect(), figura)
    p.setPen(QPen(tinta, 0.3 * escala))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(caja)

    # Datos: etiqueta pequeña encima de cada valor
    etiqueta = lz.fuente(CUERPO, 2.3, B.Bold, espacio=0.18)
    valor = lz.fuente(CUERPO, 3.8, B.DemiBold)
    for (x, y, w, _h), titulo, texto in ((m.etapa, "ETAPA", al.etapa), (m.curso, "CURSO", al.curso)):
        lz.texto(lz.r(x, y, w, 3), titulo, etiqueta, suave, IZQ | UNA)
        lz.texto(lz.r(x, y + 3, w, 5), texto, valor, tinta, IZQ | UNA)
    lz.texto(lz.r(*m.alumno), "ALUMNA" if al.es_mujer else "ALUMNO", etiqueta, suave, IZQ | UNA)
    lz.texto(lz.r(*m.nombre), f"{al.nombre}\n{al.apellidos}", lz.fuente(TITULAR, 5.6, B.Bold), tinta,
             IZQ | AJUSTE, minimo_mm=2.6)
    if al.nia:
        lz.texto(lz.r(*m.nia), f"NIA {al.nia}", lz.fuente(MONO, 2.4, B.Medium), suave, IZQ | UNA)

    # Fecha y hora de salida: igual de grandes, la fecha a la izquierda y la hora a la derecha
    p.setPen(QPen(tinta, 0.6 * escala))
    p.drawRoundedRect(lz.r(*m.hora), 2 * escala, 2 * escala)
    lz.texto(lz.r(*m.hora_etiqueta), "FECHA Y HORA DE SALIDA", etiqueta, tinta, ARRIBA_CENTRO | UNA)
    grande = lz.fuente(TITULAR, m.hora_mm, B.ExtraBold)
    lz.texto(lz.r(*m.fecha_valor), fecha_corta(datos.salida.date()), grande, tinta, CENTRO | UNA)
    lz.texto(lz.r(*m.hora_valor), f"{datos.salida:%H:%M}", grande, tinta, CENTRO | UNA)
    fx, fy, fw, fh = m.fecha_valor
    medio = (fx + fw + m.hora_valor[0]) / 2
    p.setPen(QPen(suave, 0.3 * escala))
    p.drawLine(lz.r(medio, fy + 1, 0, 0).topLeft(), lz.r(medio, fy + fh - 1, 0, 0).topLeft())

    # Texto de autorización
    x, y, w, h = m.texto
    plantilla = a.texto_alumna if al.es_mujer else a.texto_alumno
    doc = QTextDocument()
    doc.documentLayout().setPaintDevice(p.device())
    doc.setDocumentMargin(0)
    doc.setDefaultFont(lz.fuente(CUERPO, m.texto_mm, B.Normal))
    doc.setDefaultStyleSheet(f"body {{ color: {tinta.name()}; }}")
    doc.setHtml(f"<body style='line-height:135%'>{texto_parte(plantilla, al, datos.salida)}</body>")
    doc.setTextWidth(w * escala)
    p.save()
    p.translate(lz.r(x, y, 0, 0).topLeft())
    doc.drawContents(p, QRectF(0, 0, w * escala, h * escala))
    p.restore()

    # Pie: QR, fecha, sello y firma
    _qr(lz, datos.qr, lz.r(*m.qr), tinta)
    lz.texto(lz.r(*m.lugar), f"{a.localidad}, {fecha_larga(datos.expedido.date())}",
             lz.fuente(CUERPO, 3.1 if not m.lugar_ajusta else 2.8, B.Bold), tinta,
             IZQ | (AJUSTE if m.lugar_ajusta else UNA))
    lz.texto(lz.r(*m.expedido), f"Expedido a las {datos.expedido:%H:%M}", lz.fuente(CUERPO, 2.7, B.Normal),
             tinta, IZQ | UNA)
    lz.imagen(imagen("sello"), lz.r(*m.sello))
    lz.imagen(imagen("firma"), lz.r(*m.firma))
    lz.texto(lz.r(*m.cargo), a.cargo_firma, lz.fuente(CUERPO, 2.4, B.Normal, cursiva=True), tinta,
             ARRIBA_DCHA | UNA)


def imagen_parte(
    datos: DatosParte, gestor: GestorAjustes, imagenes: ImagenesParte, ancho_px: int, grises: bool = False
) -> QImage:
    m = maqueta(gestor.valores.orientacion)
    escala = ancho_px / m.ancho
    img = QImage(ancho_px, round(m.alto * escala), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor("#ffffff"))
    p = QPainter(img)
    dibujar_parte(p, escala, datos, gestor, imagenes, grises=grises)
    p.end()
    return img
