"""Ventana principal: buscar a la izquierda, comprobar en el centro, imprimir a la derecha."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from datetime import time as dtime

from PyQt6.QtCore import QAbstractListModel, QRectF, QSize, Qt, QTime, QTimer
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QPainter, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QStyle,
    QStyledItemDelegate,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from .. import NOMBRE_APP, __version__
from ..correo import mensajes_del_parte
from ..impresion import imprimir_varios, parte_adjunto
from ..modelo import ETAPA_CORTA, Alumno, Tutor
from ..parte import DatosParte, imagen_parte, maqueta
from ..seguimiento import CORREO, PAPEL, Salida
from . import estilo
from .componentes import AvisoFlotante, FlujoLayout, boton, etiqueta, refrescar_estilo, separador_vertical
from .envios import Envios, Lote
from .seguimiento import DialogoHistorial, DialogoRecurrente, DialogoRecurrentes, resumen_historial

logger = logging.getLogger(__name__)
ROL_ALUMNO = Qt.ItemDataRole.UserRole + 1


@dataclass
class Emision:
    """Un parte que se va a emitir: en papel o por correo al alumno, y a quién avisar."""

    datos: DatosParte
    entrega: str = PAPEL
    familia: list[Tutor] = field(default_factory=list)
    recurrente: bool = False


def _redondear_hora(momento: datetime, minutos: int = 5) -> QTime:
    extra = (-momento.minute) % minutos
    m = momento + timedelta(minutes=extra)
    return QTime(m.hour, m.minute)


class ModeloAlumnos(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.alumnos: list[Alumno] = []

    def poner(self, alumnos: list[Alumno]) -> None:
        self.beginResetModel()
        self.alumnos = alumnos
        self.endResetModel()

    def rowCount(self, padre=None):  # noqa: N802
        return 0 if padre is not None and padre.isValid() else len(self.alumnos)

    def data(self, indice, rol=Qt.ItemDataRole.DisplayRole):
        if not indice.isValid():
            return None
        a = self.alumnos[indice.row()]
        if rol == Qt.ItemDataRole.DisplayRole:
            return a.nombre_listado
        if rol == ROL_ALUMNO:
            return a
        return None


class DelegadoAlumno(QStyledItemDelegate):
    ALTO = 58

    def __init__(self, contexto, padre=None):
        super().__init__(padre)
        self._ctx = contexto

    def sizeHint(self, opcion, indice):  # noqa: N802
        return QSize(opcion.rect.width(), self.ALTO)

    def paint(self, p: QPainter, opcion, indice):
        a: Alumno = indice.data(ROL_ALUMNO)
        r = opcion.rect.adjusted(0, 1, 0, -1)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        estado = opcion.state
        if estado & QStyle.StateFlag.State_Selected:
            p.setBrush(QColor(estilo.T["accent_soft"]))
        elif estado & QStyle.StateFlag.State_MouseOver:
            p.setBrush(QColor(estilo.T["surface2"]))
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(r), 8, 8)
        dpr = p.device().devicePixelRatioF() if p.device() else 2.0
        foto = self._ctx.miniatura(a.id, 36, 46, dpr, 6)
        p.drawPixmap(r.x() + 8, r.y() + (r.height() - 46) // 2, foto)
        x = r.x() + 56
        p.setPen(QColor(estilo.T["fg"]))
        p.setFont(estilo.fuente(14, QFont.Weight.DemiBold))
        ancho = r.width() - 64
        fm = p.fontMetrics()
        p.drawText(x, r.y() + 24, fm.elidedText(a.nombre_listado, Qt.TextElideMode.ElideRight, ancho))
        p.setPen(QColor(estilo.T["muted"]))
        p.setFont(estilo.fuente(12.5))
        p.drawText(x, r.y() + 43, p.fontMetrics().elidedText(f"{a.curso} · {a.etapa}", Qt.TextElideMode.ElideRight, ancho))
        p.restore()


class FilaContacto(QFrame):
    def __init__(self, quien: str, detalle: str, telefono: str, primera: bool, ventana):
        super().__init__()
        if not primera:
            self.setProperty("rol", "fila")
        rejilla = QGridLayout(self)
        rejilla.setContentsMargins(0, 0 if primera else 10, 0, 6)
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(4)
        texto = f"<b>{quien}</b>"
        if detalle:
            texto += f" <span style='color:{estilo.T['muted']};font-size:13px'>· {detalle}</span>"
        rejilla.addWidget(QLabel(texto), 0, 0)
        tel = etiqueta(telefono or "—", "tel")
        tel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        rejilla.addWidget(tel, 0, 1)
        copiar = boton("Copiar", pequeno=True)
        copiar.setEnabled(bool(telefono))
        copiar.clicked.connect(lambda: ventana.copiar_telefono(telefono))
        rejilla.addWidget(copiar, 0, 2)
        rejilla.setColumnStretch(0, 1)
        self.rejilla = rejilla


class Ficha(QWidget):
    """Foto, nombre, etapa y curso, y los contactos con la casilla de aviso."""

    def __init__(self, ventana):
        super().__init__()
        self._ventana = ventana
        self.avisos: dict[str, dict[int, bool]] = {}
        self.alumno: Alumno | None = None
        self.pila = QStackedLayout(self)

        vacio = QWidget()
        cv = QVBoxLayout(vacio)
        cv.addStretch(1)
        self.vacio_titulo = QLabel()
        self.vacio_titulo.setFont(estilo.fuente(26, QFont.Weight.Bold, estilo.TITULAR))
        self.vacio_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vacio_texto = etiqueta("", "muted", envolver=True)
        self.vacio_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vacio_boton = boton("Importar datos…", primario=True)
        self.vacio_boton.clicked.connect(lambda: ventana.abrir_ajustes("Datos del alumnado"))
        cv.addWidget(self.vacio_titulo)
        cv.addWidget(self.vacio_texto)
        cv.addSpacing(10)
        cv.addWidget(self.vacio_boton, 0, Qt.AlignmentFlag.AlignCenter)
        cv.addStretch(2)
        self.pila.addWidget(vacio)

        ficha = QWidget()
        col = QVBoxLayout(ficha)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(18)
        arriba = QHBoxLayout()
        arriba.setSpacing(16)
        self.foto = QLabel()
        self.foto.setFixedSize(104, 132)
        arriba.addWidget(self.foto, 0, Qt.AlignmentFlag.AlignTop)
        datos = QVBoxLayout()
        datos.setSpacing(6)
        self.nombre = QLabel()
        self.nombre.setFont(estilo.fuente(30, QFont.Weight.Bold, estilo.TITULAR))
        self.nombre.setWordWrap(True)
        self.nombre.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        datos.addWidget(self.nombre)
        etiquetas = QHBoxLayout()
        etiquetas.setSpacing(6)
        self.etapa = etiqueta("", "tag-etapa")
        self.curso = etiqueta("", "tag")
        etiquetas.addWidget(self.etapa)
        etiquetas.addWidget(self.curso)
        etiquetas.addStretch(1)
        datos.addLayout(etiquetas)
        self.meta = etiqueta("", "muted")
        datos.addWidget(self.meta)
        datos.addStretch(1)
        arriba.addLayout(datos, 1)
        col.addLayout(arriba)

        self.caja = QFrame()
        self.caja.setProperty("rol", "caja")
        self.caja_capa = QVBoxLayout(self.caja)
        self.caja_capa.setContentsMargins(16, 14, 16, 12)
        self.caja_capa.setSpacing(8)
        col.addWidget(self.caja)
        col.addWidget(self._caja_seguimiento())
        col.addStretch(1)
        self.pila.addWidget(ficha)
        self.vacia(True)

    def _caja_seguimiento(self) -> QFrame:
        caja = QFrame()
        caja.setProperty("rol", "caja")
        rejilla = QGridLayout(caja)
        rejilla.setContentsMargins(16, 10, 16, 10)
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(6)
        for fila, texto in enumerate(("Historial", "Parte recurrente")):
            t = QLabel(texto)
            t.setStyleSheet("font-weight:700;")
            rejilla.addWidget(t, fila, 0)
        self.seg_historial = etiqueta("", "muted", envolver=True)
        self.seg_recurrente = etiqueta("", "muted", envolver=True)
        rejilla.addWidget(self.seg_historial, 0, 1)
        rejilla.addWidget(self.seg_recurrente, 1, 1)
        self.boton_historial = boton("Ver historial", pequeno=True)
        self.boton_historial.clicked.connect(lambda: self._ventana.abrir_historial())
        self.boton_recurrente = boton("Configurar…", pequeno=True)
        self.boton_recurrente.clicked.connect(lambda: self._ventana.configurar_recurrente())
        rejilla.addWidget(self.boton_historial, 0, 2)
        rejilla.addWidget(self.boton_recurrente, 1, 2)
        rejilla.setColumnStretch(1, 1)
        return caja

    def actualizar_seguimiento(self) -> None:
        a = self.alumno
        if a is None:
            return
        seg = self._ventana.ctx.seguimiento
        self.seg_historial.setText(resumen_historial(seg.salidas(a.id)))
        r = seg.recurrentes.get(a.id)
        if r:
            entrega = "por correo" if r.entrega == CORREO and a.email else "en papel"
            self.seg_recurrente.setText(f"{r.resumen} · {entrega}")
            self.seg_recurrente.setToolTip(r.motivo)
            self.boton_recurrente.setText("Cambiar…")
        else:
            self.seg_recurrente.setText("No")
            self.seg_recurrente.setToolTip("")
            self.boton_recurrente.setText("Configurar…")

    def vacia(self, sin_datos: bool) -> None:
        self.alumno = None
        if sin_datos:
            self.vacio_titulo.setText("Empieza importando los datos")
            self.vacio_texto.setText(
                "Necesitas el Excel de alumnado de Educamos y los ZIP con las fotos. "
                "Se guardan cifrados en este equipo."
            )
            self.vacio_boton.show()
        else:
            self.vacio_titulo.setText("Busca un alumno")
            self.vacio_texto.setText("Escribe su nombre o apellidos, o filtra por etapa y curso.")
            self.vacio_boton.hide()
        self.pila.setCurrentIndex(0)

    def mostrar(self, a: Alumno) -> None:
        self.alumno = a
        ctx = self._ventana.ctx
        self.foto.setPixmap(ctx.miniatura(a.id, 104, 132, self.devicePixelRatioF() or 2, 8))
        self.nombre.setText(f"{a.nombre}<br>{a.apellidos}")
        self.etapa.setText(a.etapa)
        self.curso.setText(a.curso)
        edad = a.edad()
        partes = [f"NIA <span style='font-family:\"{estilo.MONO}\"'>{a.nia}</span>" if a.nia else "Sin NIA"]
        if edad is not None:
            partes.append(f"{edad} años")
        self.meta.setText(" · ".join(partes))
        self._contactos(a)
        self.actualizar_seguimiento()
        self.pila.setCurrentIndex(1)

    def _contactos(self, a: Alumno) -> None:
        while self.caja_capa.count():
            w = self.caja_capa.takeAt(0).widget()
            if w:
                w.setParent(None)  # fuera ya, aunque el borrado llegue después
                w.deleteLater()
        titulo = QLabel("Contactos")
        titulo.setFont(estilo.fuente(19, QFont.Weight.Bold, estilo.TITULAR))
        self.caja_capa.addWidget(titulo)
        mayor = (a.edad() or 0) >= 18
        if mayor and any(t.puede_recibir_correo for t in a.tutores):
            self.caja_capa.addWidget(etiqueta("Mayor de edad: el aviso a la familia sale desmarcado.", "aviso", True))
        marcas = self.avisos.setdefault(a.id, {})
        for i, t in enumerate(a.tutores):
            fila = FilaContacto(t.parentesco_texto, t.nombre, t.telefono, i == 0, self._ventana)
            casilla = QCheckBox("Avisar por correo" if t.puede_recibir_correo else
                                ("No recibe información según Educamos" if t.email else "Sin correo en Educamos"))
            casilla.setEnabled(t.puede_recibir_correo)
            casilla.setChecked(marcas.setdefault(i, t.puede_recibir_correo and not mayor))
            casilla.toggled.connect(lambda v, i=i: self._marcar(i, v))
            aviso = QHBoxLayout()
            aviso.setSpacing(8)
            aviso.addWidget(casilla)
            if t.puede_recibir_correo:
                aviso.addWidget(etiqueta(t.email, "correo"))
            aviso.addStretch(1)
            fila.rejilla.addLayout(aviso, 1, 0, 1, 3)
            self.caja_capa.addWidget(fila)
        if not a.tutores:
            self.caja_capa.addWidget(etiqueta("Educamos no tiene datos de la familia.", "muted"))
        moviles = [("móvil", a.movil), ("emergencia", a.tel_emergencia)]
        for tipo, tel in (x for x in moviles if x[1]):
            quien = ("Alumna" if a.es_mujer else "Alumno") if tipo == "móvil" else "Emergencia"
            detalle = "móvil" if tipo == "móvil" else ""
            self.caja_capa.addWidget(FilaContacto(quien, detalle, tel, False, self._ventana))
        self._ventana.avisos_cambiados()

    def _marcar(self, i: int, valor: bool) -> None:
        if self.alumno:
            self.avisos.setdefault(self.alumno.id, {})[i] = valor
            self._ventana.avisos_cambiados()

    def destinatarios(self) -> list:
        if not self.alumno:
            return []
        marcas = self.avisos.get(self.alumno.id, {})
        return [t for i, t in enumerate(self.alumno.tutores) if t.puede_recibir_correo and marcas.get(i)]


class VistaPrevia(QLabel):
    def __init__(self, ventana):
        super().__init__()
        self._ventana = ventana
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(26)
        sombra.setOffset(0, 8)
        sombra.setColor(QColor(0, 0, 0, 55))
        self.setGraphicsEffect(sombra)
        self._temporizador = QTimer(self, singleShot=True, interval=60, timeout=self._pintar)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    #: El parte vertical se limita en alto para que quepa el botón de imprimir.
    ALTO_MAXIMO = 320

    def _maqueta(self):
        return maqueta(self._ventana.ctx.gestor.valores.orientacion)

    def heightForWidth(self, ancho):  # noqa: N802
        m = self._maqueta()
        return min(round(ancho * m.alto / m.ancho), self.ALTO_MAXIMO)

    def actualizar(self) -> None:
        self._temporizador.start()

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self.setFixedHeight(self.heightForWidth(self.width()))
        self.actualizar()

    def _pintar(self) -> None:
        datos = self._ventana.datos_parte()
        if datos is None:
            self.setPixmap(QPixmap())
            return
        dpr = self.devicePixelRatioF() or 2
        m = self._maqueta()
        self.setFixedHeight(self.heightForWidth(self.width()))
        ancho = min(self.width(), self.height() * m.ancho / m.alto)
        img = imagen_parte(datos, self._ventana.ctx.gestor, self._ventana.ctx.imagenes, int(ancho * dpr))
        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)
        self.setPixmap(pm)


class VentanaPrincipal(QMainWindow):
    def __init__(self, contexto):
        super().__init__()
        self.ctx = contexto
        self.saliendo = False
        self._avisado_bandeja = False
        self.setWindowTitle(NOMBRE_APP)
        self.resize(1100, 700)
        self.setMinimumSize(980, 620)

        raiz = QWidget()
        raiz.setObjectName("lienzo_raiz")
        raiz.setStyleSheet(f"#lienzo_raiz {{ background: {estilo.T['surface']}; }}")
        self.setCentralWidget(raiz)
        vertical = QVBoxLayout(raiz)
        vertical.setContentsMargins(0, 0, 0, 0)
        vertical.setSpacing(0)
        vertical.addWidget(self._barra())
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        cuerpo.addWidget(self._columna_buscar())
        cuerpo.addWidget(separador_vertical())
        cuerpo.addWidget(self._columna_ficha(), 1)
        cuerpo.addWidget(separador_vertical())
        cuerpo.addWidget(self._columna_imprimir())
        vertical.addLayout(cuerpo, 1)
        self.aviso = AvisoFlotante(raiz)

        QShortcut(QKeySequence(QKeySequence.StandardKey.Print), self, activated=self.imprimir)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self, activated=self.enfocar_buscador)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=lambda: self.abrir_ajustes())
        self._reloj = QTimer(self, interval=30_000, timeout=self.vista.actualizar)
        self._reloj.start()
        self.envios = Envios(self.ctx, self)
        self._reloj.timeout.connect(self.actualizar_recurrentes)
        self.ctx.padron_cambiado.connect(self.recargar)
        self.ctx.ajustes_cambiados.connect(self.recargar)
        self.ctx.seguimiento_cambiado.connect(self._seguimiento_cambiado)
        self.recargar()

    # Construcción
    def _barra(self) -> QWidget:
        barra = QWidget()
        barra.setObjectName("barra")
        barra.setStyleSheet(
            f"#barra {{ background: {estilo.T['surface2']}; border-bottom: 1px solid {estilo.T['line']}; }}"
        )
        fila = QHBoxLayout(barra)
        fila.setContentsMargins(16, 9, 12, 9)
        titulo = QLabel(NOMBRE_APP)
        titulo.setFont(estilo.fuente(19, QFont.Weight.Bold, estilo.TITULAR))
        fila.addWidget(titulo)
        self.equipo = etiqueta("", "muted")
        fila.addWidget(self.equipo)
        fila.addStretch(1)
        candado = QLabel()
        candado.setPixmap(estilo.icono_candado(estilo.T["accent"]))
        fila.addWidget(candado)
        fila.addWidget(etiqueta("Datos cifrados", "cifrado"))
        self.recuento = etiqueta("", "muted")
        fila.addSpacing(8)
        fila.addWidget(self.recuento)
        fila.addSpacing(12)
        # Partes recurrentes del día: verde y con la cuenta mientras quede alguno por emitir.
        self.boton_recurrentes = boton("", pequeno=True)
        self.boton_recurrentes.setToolTip("Imprimir o enviar de golpe los partes recurrentes de hoy")
        self.boton_recurrentes.clicked.connect(self.abrir_recurrentes)
        self.boton_recurrentes.hide()
        fila.addWidget(self.boton_recurrentes)
        fila.addSpacing(8)
        # Aviso de versión nueva: dorado y bien visible; abre el diálogo de actualizar.
        self.boton_actualizar = boton("", pequeno=True)
        self.boton_actualizar.setStyleSheet(
            f"QPushButton {{ background: {estilo.T['gold']}; border-color: {estilo.T['gold']}; color: #ffffff; }}"
            f"QPushButton:hover {{ border-color: {estilo.T['fg']}; }}"
        )
        self.boton_actualizar.hide()
        self.boton_actualizar.clicked.connect(self._ofrecer_actualizacion)
        fila.addWidget(self.boton_actualizar)
        fila.addSpacing(8)
        ajustes = boton("Ajustes", pequeno=True)
        ajustes.setToolTip("Ajustes (Ctrl+,)")
        ajustes.clicked.connect(lambda: self.abrir_ajustes())
        fila.addWidget(ajustes)
        return barra

    def _columna_buscar(self) -> QWidget:
        col = QWidget()
        col.setFixedWidth(300)
        v = QVBoxLayout(col)
        v.setContentsMargins(14, 14, 14, 10)
        v.setSpacing(12)
        self.buscador = QLineEdit()
        self.buscador.setObjectName("buscador")
        self.buscador.setPlaceholderText("Buscar por nombre o apellidos")
        self.buscador.setClearButtonEnabled(True)
        self.buscador.addAction(estilo.icono_lupa(estilo.T["muted"]), QLineEdit.ActionPosition.LeadingPosition)
        self.buscador.textChanged.connect(lambda: self._filtro.start())
        self.buscador.returnPressed.connect(self._elegir_primero)
        self.buscador.installEventFilter(self)
        v.addWidget(self.buscador)
        self.chips_caja = QWidget()
        self.chips = FlujoLayout(self.chips_caja, 5)
        self.grupo_etapas = QButtonGroup(self)
        self.grupo_etapas.setExclusive(True)
        self.grupo_etapas.buttonClicked.connect(self._etapa_elegida)
        v.addWidget(self.chips_caja)
        fila = QHBoxLayout()
        self.curso = QComboBox()
        self.curso.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.curso.currentIndexChanged.connect(lambda: self._filtro.start())
        fila.addWidget(self.curso, 1)
        limpiar = boton("Limpiar", pequeno=True)
        limpiar.clicked.connect(self.limpiar_filtros)
        fila.addWidget(limpiar)
        v.addLayout(fila)
        self.cuenta = etiqueta("", "pequeno")
        v.addWidget(self.cuenta)
        self.modelo = ModeloAlumnos()
        self.lista = QListView()
        self.lista.setObjectName("resultados")
        self.lista.setModel(self.modelo)
        self.lista.setItemDelegate(DelegadoAlumno(self.ctx, self.lista))
        self.lista.setMouseTracking(True)
        self.lista.setUniformItemSizes(True)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.lista.selectionModel().currentChanged.connect(self._actual_cambiado)
        v.addWidget(self.lista, 1)
        self._filtro = QTimer(self, singleShot=True, interval=110, timeout=self.actualizar_lista)
        self.etapa_actual = ""
        return col

    def _columna_ficha(self) -> QWidget:
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(18, 16, 18, 14)
        self.ficha = Ficha(self)
        v.addWidget(self.ficha)
        return col

    def _columna_imprimir(self) -> QWidget:
        col = QWidget()
        col.setFixedWidth(340)
        v = QVBoxLayout(col)
        v.setContentsMargins(16, 16, 16, 14)
        v.setSpacing(10)
        v.addWidget(etiqueta("Hora de salida", "etiqueta"))
        fila = QHBoxLayout()
        self.hora = QTimeEdit()
        self.hora.setObjectName("hora")
        self.hora.setDisplayFormat("HH:mm")
        self.hora.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
        self.hora.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hora.setToolTip("Escribe la hora o usa las flechas del teclado")
        self.hora.setTime(_redondear_hora(datetime.now()))
        self.hora.timeChanged.connect(self._hora_cambiada)
        fila.addWidget(self.hora, 1)
        ahora = boton("Ahora")
        ahora.setMinimumHeight(58)
        ahora.clicked.connect(lambda: self.hora.setTime(QTime.currentTime()))
        fila.addWidget(ahora)
        v.addLayout(fila)
        self.aviso_hora = etiqueta("", "pequeno")
        v.addWidget(self.aviso_hora)
        v.addSpacing(4)
        v.addWidget(etiqueta("Vista previa", "etiqueta"))
        self.vista = VistaPrevia(self)
        v.addWidget(self.vista)
        v.addStretch(1)
        v.addWidget(etiqueta("Entrega del parte", "etiqueta"))
        fila_entrega = QHBoxLayout()
        fila_entrega.setSpacing(6)
        self.grupo_entrega = QButtonGroup(self)
        self.entrega_papel = boton("En papel", chip=True)
        self.entrega_correo = boton("Por correo al alumno", chip=True)
        for b in (self.entrega_papel, self.entrega_correo):
            b.setCheckable(True)
            self.grupo_entrega.addButton(b)
            fila_entrega.addWidget(b)
        fila_entrega.addStretch(1)
        self.entrega_papel.setChecked(True)
        self.grupo_entrega.buttonClicked.connect(lambda _b: self.avisos_cambiados())
        v.addLayout(fila_entrega)
        self.entrega_detalle = etiqueta("", "correo")
        v.addWidget(self.entrega_detalle)
        self.boton_imprimir = boton("", primario=True, grande=True)
        self.boton_imprimir.clicked.connect(self.imprimir)
        v.addWidget(self.boton_imprimir)
        self.resumen = etiqueta("", "muted")
        self.resumen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resumen.setWordWrap(True)
        v.addWidget(self.resumen)
        return col

    # Datos y filtros
    def recargar(self) -> None:
        a = self.ctx.gestor.valores
        self.equipo.setText(f"· {a.nombre_equipo}" if a.nombre_equipo else "")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, a.siempre_encima)
        if self.ctx.hay_datos:
            self.recuento.setText(f"{len(self.ctx.alumnos):,} alumnos · {self.ctx.con_foto:,} con foto".replace(",", "."))
        else:
            self.recuento.setText("Sin datos importados")
        self._chips()
        self.actualizar_lista()
        if self.ficha.alumno and self.ficha.alumno.id in self.ctx.por_id:
            self.ficha.mostrar(self.ctx.por_id[self.ficha.alumno.id])
        else:
            self.ficha.vacia(not self.ctx.hay_datos)
        self.buscador.setEnabled(self.ctx.hay_datos)
        self.avisos_cambiados()
        self.actualizar_recurrentes()

    def _seguimiento_cambiado(self) -> None:
        self.ficha.actualizar_seguimiento()
        self.actualizar_recurrentes()

    def actualizar_recurrentes(self) -> None:
        """Botón de la barra: visible si hay recurrentes en las etapas visibles; verde si quedan por emitir hoy."""
        seg, visibles = self.ctx.seguimiento, self.ctx.etapas_visibles()
        hay = any(
            i in self.ctx.por_id and (visibles is None or self.ctx.por_id[i].etapa_codigo in visibles)
            for i in seg.recurrentes
        )
        pendientes = sum(
            1 for p in seg.partes_del_dia(date.today(), self.ctx.por_id, visibles) if p.emitido is None
        )
        self.boton_recurrentes.setVisible(hay)
        self.boton_recurrentes.setText(
            f"Partes recurrentes · {pendientes} hoy" if pendientes else "Partes recurrentes"
        )
        if bool(self.boton_recurrentes.property("primario")) != bool(pendientes):
            self.boton_recurrentes.setProperty("primario", bool(pendientes))
            refrescar_estilo(self.boton_recurrentes)

    def _chips(self) -> None:
        for b in self.grupo_etapas.buttons():
            self.grupo_etapas.removeButton(b)
            b.deleteLater()
        while self.chips.count():
            self.chips.takeAt(0)
        visibles = self.ctx.etapas_visibles()
        codigos = [e for e in self.ctx.etapas if visibles is None or e in visibles]
        if self.etapa_actual not in codigos:
            self.etapa_actual = ""
        for cod in ["", *codigos] if len(codigos) > 1 else []:
            b = QPushButton("Todas" if not cod else ETAPA_CORTA.get(cod, cod))
            b.setProperty("chip", True)
            b.setCheckable(True)
            b.setChecked(cod == self.etapa_actual)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setProperty("codigo", cod)
            self.grupo_etapas.addButton(b)
            self.chips.addWidget(b)
        self.chips_caja.setVisible(len(codigos) > 1)
        self._cursos()

    def _cursos(self) -> None:
        visibles = self.ctx.etapas_visibles()
        clases = sorted(
            {a.clase: a.curso for a in self.ctx.alumnos
             if (not self.etapa_actual or a.etapa_codigo == self.etapa_actual)
             and (visibles is None or a.etapa_codigo in visibles)}.items(),
            key=lambda c: c[0],
        )
        self.curso.blockSignals(True)
        self.curso.clear()
        self.curso.addItem("Todos los cursos", "")
        for clase, nombre in clases:
            self.curso.addItem(nombre if self.etapa_actual else f"{nombre} · {clase}", clase)
        self.curso.blockSignals(False)

    def _etapa_elegida(self, b) -> None:
        self.etapa_actual = b.property("codigo") or ""
        self._cursos()
        self.actualizar_lista()

    def limpiar_filtros(self) -> None:
        self.buscador.clear()
        self.etapa_actual = ""
        for b in self.grupo_etapas.buttons():
            b.setChecked(not b.property("codigo"))
        self._cursos()
        self.actualizar_lista()
        self.enfocar_buscador()

    def actualizar_lista(self) -> None:
        resultados = self.ctx.buscador.buscar(
            self.buscador.text(), self.etapa_actual, self.curso.currentData() or "", self.ctx.etapas_visibles()
        )
        actual = self.ficha.alumno
        self.modelo.poner(resultados)
        n = len(resultados)
        self.cuenta.setText("" if not self.ctx.hay_datos else f"{n:,} alumno{'s' if n != 1 else ''}".replace(",", "."))
        fila = next((i for i, a in enumerate(resultados) if actual and a.id == actual.id), None)
        if fila is None and self.buscador.text().strip() and resultados:
            fila = 0
        if fila is not None:
            self.lista.setCurrentIndex(self.modelo.index(fila))
            self.lista.scrollTo(self.modelo.index(fila))

    def _elegir_primero(self) -> None:
        if self.modelo.rowCount():
            self.lista.setCurrentIndex(self.modelo.index(0))
            self.lista.setFocus()

    def _actual_cambiado(self, actual, _anterior) -> None:
        if actual.isValid():
            a = actual.data(ROL_ALUMNO)
            if not self.ficha.alumno or self.ficha.alumno.id != a.id:
                self.entrega_papel.setChecked(True)  # cada parte se decide de nuevo: papel de serie
            self.ficha.mostrar(a)
            self.vista.actualizar()

    def eventFilter(self, objeto, evento):  # noqa: N802
        from PyQt6.QtCore import QEvent

        if objeto is self.buscador and evento.type() == QEvent.Type.KeyPress:
            if evento.key() == Qt.Key.Key_Down and self.modelo.rowCount():
                self.lista.setFocus()
                if not self.lista.currentIndex().isValid():
                    self.lista.setCurrentIndex(self.modelo.index(0))
                return True
            if evento.key() == Qt.Key.Key_Escape:
                self.buscador.clear()
                return True
        return super().eventFilter(objeto, evento)

    def enfocar_buscador(self) -> None:
        self.buscador.setFocus()
        self.buscador.selectAll()

    # Parte
    def salida(self) -> datetime:
        t = self.hora.time()
        return datetime.combine(date.today(), dtime(t.hour(), t.minute()))

    def datos_parte(self) -> DatosParte | None:
        a = self.ficha.alumno
        if a is None:
            return None
        ahora = datetime.now().replace(second=0, microsecond=0)
        salida = self.salida()
        return DatosParte(a, self.ctx.foto(a.id), salida, ahora, self.ctx.firmante.contenido_qr(a.id, salida, ahora))

    def _hora_cambiada(self) -> None:
        pasada = self.salida() < datetime.now() - timedelta(minutes=10)
        self.aviso_hora.setText("Esa hora ya ha pasado." if pasada else "")
        self.vista.actualizar()

    def entrega(self) -> str:
        a = self.ficha.alumno
        return CORREO if self.entrega_correo.isChecked() and a is not None and a.email else PAPEL

    def avisos_cambiados(self) -> None:
        a = self.ficha.alumno
        self.boton_imprimir.setEnabled(a is not None)
        self.entrega_correo.setEnabled(bool(a and a.email))
        if not (a and a.email) and self.entrega_correo.isChecked():
            self.entrega_papel.setChecked(True)
        self.entrega_detalle.setText(
            "" if a is None else (a.email or f"Sin correo {'de la alumna' if a.es_mujer else 'del alumno'} en Educamos")
        )
        atajo = QKeySequence(QKeySequence.StandardKey.Print).toString(QKeySequence.SequenceFormat.NativeText)
        por_correo = self.entrega() == CORREO
        self.boton_imprimir.setText(f"{'Enviar parte' if por_correo else 'Imprimir parte'}   {atajo}")
        if a is None:
            self.resumen.setText("Elige un alumno para emitir su parte." if self.ctx.hay_datos else "")
            self.vista.actualizar()
            return
        destinatarios = self.ficha.destinatarios()
        familia = " y ".join(t.parentesco_texto.lower() for t in destinatarios)
        if por_correo:
            texto = f"Sin papel: el parte irá al correo {'de la alumna' if a.es_mujer else 'del alumno'}"
            texto += f" y el aviso a {familia}." if familia else "."
        else:
            texto = f"Se avisará por correo a: {familia}" if familia else "Sin aviso por correo"
        self.resumen.setText(texto)
        self.vista.actualizar()

    def copiar_telefono(self, telefono: str) -> None:
        numero = re.sub(r"\D", "", telefono.split("(")[0])
        QGuiApplication.clipboard().setText(numero)
        self.aviso.mostrar(f"Teléfono copiado: {telefono}")

    def emision(self, a: Alumno, salida: datetime, entrega: str = PAPEL, familia: list[Tutor] | None = None,
                recurrente: bool = False) -> Emision:
        ahora = datetime.now().replace(second=0, microsecond=0)
        datos = DatosParte(a, self.ctx.foto(a.id), salida, ahora, self.ctx.firmante.contenido_qr(a.id, salida, ahora))
        return Emision(datos, entrega, list(familia or []), recurrente)

    def imprimir(self) -> None:
        """⌘P y el botón grande: emite el parte del alumno elegido como diga «Entrega del parte»."""
        a = self.ficha.alumno
        if a is None:
            return
        self.emitir_partes([self.emision(a, self.salida(), self.entrega(), self.ficha.destinatarios())])

    def emitir_partes(self, emisiones: list[Emision], padre=None) -> bool:
        """Imprime los de papel (uno por hoja, en un solo trabajo), apunta cada parte en el
        historial y manda los correos (parte al alumno, aviso a la familia) en un hilo.

        Si la impresión se cancela o falla no se apunta ni se envía nada.
        """
        padre = padre or self
        por_correo = [e for e in emisiones if e.entrega == CORREO]
        if por_correo and not self.envios.clave():
            uno = len(emisiones) == 1
            r = QMessageBox.question(
                padre, "Falta la contraseña del correo",
                "Sin la contraseña del correo (Ajustes → Correo) "
                + ("el parte no puede salir por correo.\n\n¿Lo imprimo en papel?" if uno else
                   f"{len(por_correo)} partes no pueden salir por correo.\n\n¿Los imprimo en papel?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if r != QMessageBox.StandardButton.Yes:
                return False
            for e in por_correo:
                e.entrega = PAPEL
        papel = [e for e in emisiones if e.entrega == PAPEL]
        if papel:
            try:
                if not imprimir_varios([e.datos for e in papel], self.ctx, padre):
                    return False
            except Exception as ex:  # noqa: BLE001
                logger.exception("Fallo al imprimir")
                QMessageBox.critical(padre, "No se ha podido imprimir", str(ex))
                return False
        equipo = self.ctx.gestor.valores.nombre_equipo
        lotes = []
        for e in emisiones:
            a = e.datos.alumno
            al_alumno = e.entrega == CORREO
            quienes = [t.parentesco_texto.lower() for t in e.familia]
            if al_alumno:
                quienes.append("alumna" if a.es_mujer else "alumno")
            registro = self.ctx.seguimiento.registrar(
                a.id, Salida.nueva(e.datos.salida, e.entrega, quienes, e.recurrente, equipo, e.datos.expedido)
            )
            if quienes:
                mensajes = mensajes_del_parte(
                    self.ctx.gestor, a, e.datos.salida, [t.email for t in e.familia], al_alumno,
                    parte_adjunto(e.datos, self.ctx),
                )
                lotes.append(Lote(
                    a.id, registro.id, f"{a.nombre} {a.apellido1}", " y ".join(quienes),
                    ", ".join(t.telefono for t in e.familia if t.telefono), mensajes,
                ))
        self.ctx.seguimiento_cambiado.emit()
        self.envios.lanzar(lotes)
        self.aviso.mostrar(self._texto_emitido(emisiones, papel, bool(lotes)))
        return True

    @staticmethod
    def _texto_emitido(emisiones: list[Emision], papel: list[Emision], hay_correo: bool) -> str:
        if len(emisiones) == 1:
            a = emisiones[0].datos.alumno
            if papel:
                return f"Parte de {a.nombre} {a.apellido1} enviado a la impresora." + (
                    " Enviando el aviso por correo…" if hay_correo else "")
            return f"Parte de {a.nombre} {a.apellido1}: enviándolo por correo…"
        n_correo = len(emisiones) - len(papel)
        partes = [f"{len(papel)} a la impresora"] if papel else []
        if n_correo:
            partes.append(f"{n_correo} por correo")
        return f"{len(emisiones)} partes: " + " y ".join(partes) + "."

    # Seguimiento
    @staticmethod
    def _abrir(dialogo) -> None:
        dialogo.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # que no quede escuchando cambios
        dialogo.exec()

    def abrir_historial(self) -> None:
        if self.ficha.alumno:
            self._abrir(DialogoHistorial(self.ctx, self.ficha.alumno, self))

    def configurar_recurrente(self) -> None:
        if self.ficha.alumno:
            self._abrir(DialogoRecurrente(self.ctx, self.ficha.alumno, self))

    def abrir_recurrentes(self) -> None:
        self._abrir(DialogoRecurrentes(self.ctx, self))

    # Actualizaciones
    def actualizacion_disponible(self, version: str, url: str, notas: str) -> None:
        """Hay versión nueva: botón dorado fijo y, la primera vez, el diálogo por encima."""
        nueva = getattr(self, "_actualizacion", None) is None or self._actualizacion[0] != version
        self._actualizacion = (version, url, notas)
        self.boton_actualizar.setText(f"↑  Actualizar a {version}")
        self.boton_actualizar.setToolTip("Hay una versión nueva de la aplicación")
        self.boton_actualizar.show()
        if not nueva:
            return
        bandeja = getattr(self, "bandeja", None)
        if bandeja:
            bandeja.showMessage(NOMBRE_APP, f"Hay una versión nueva ({version}). Pulsa «Actualizar» en la ventana.")
        if self.isVisible():
            self._ofrecer_actualizacion()

    def _ofrecer_actualizacion(self) -> None:
        from .dialogos import ofrecer

        if getattr(self, "_actualizacion", None):
            self.mostrar_al_frente()
            ofrecer(self, *self._actualizacion)

    def buscar_actualizaciones(self) -> None:
        from .dialogos import buscar_actualizaciones

        buscar_actualizaciones(self, al_encontrar=self.actualizacion_disponible)

    # Ventana
    def abrir_ajustes(self, apartado: str | None = None) -> None:
        from .ajustes import DialogoAjustes

        dialogo = DialogoAjustes(self.ctx, self, apartado)
        dialogo.exec()
        self.ctx.ajustes_cambiados.emit()

    def mostrar_al_frente(self) -> None:
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()
        self.enfocar_buscador()

    def closeEvent(self, evento):  # noqa: N802
        if self.saliendo:
            evento.accept()
            return
        evento.ignore()
        self.hide()
        bandeja = getattr(self, "bandeja", None)
        if bandeja and not self._avisado_bandeja:
            self._avisado_bandeja = True
            bandeja.showMessage(NOMBRE_APP, "Sigue abierta en la barra: pulsa su icono para volver.")

    def acerca_de(self) -> str:
        return f"{NOMBRE_APP} {__version__}"
