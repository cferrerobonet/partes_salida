"""Diálogos: fotos por confirmar y actualización de la aplicación."""

from __future__ import annotations

import logging
import tempfile
import urllib.request
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import NOMBRE_APP, __version__
from ..actualizaciones import PAGINA_DE_RELEASES, abrir_instalador, comprobar, contexto_ssl, url_de_confianza
from .componentes import boton, etiqueta

logger = logging.getLogger(__name__)


class RevisarFotos(QDialog):
    """Fotos cuyo nombre casi coincide con un alumno: se confirma cada una."""

    def __init__(self, dudosas, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Fotos por confirmar")
        self.resize(640, 560)
        self._dudosas = dudosas
        self._casillas: list[QCheckBox] = []
        capa = QVBoxLayout(self)
        capa.setContentsMargins(20, 18, 20, 16)
        capa.addWidget(etiqueta(
            "El nombre de estas fotos se parece mucho al de un alumno, pero no es igual (una tilde, una errata). "
            "Desmarca las que no sean suyas.", "muted", envolver=True))
        lista = QWidget()
        filas = QVBoxLayout(lista)
        filas.setSpacing(8)
        for d in dudosas:
            fila = QFrame()
            fila.setProperty("rol", "caja")
            h = QHBoxLayout(fila)
            h.setContentsMargins(10, 8, 10, 8)
            casilla = QCheckBox()
            casilla.setChecked(True)
            self._casillas.append(casilla)
            h.addWidget(casilla)
            foto = QLabel()
            pm = QPixmap()
            pm.loadFromData(d.jpeg)
            dpr = self.devicePixelRatioF() or 2
            pm = pm.scaled(int(42 * dpr), int(56 * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            foto.setPixmap(pm)
            h.addWidget(foto)
            textos = QVBoxLayout()
            textos.setSpacing(1)
            textos.addWidget(QLabel(f"<b>{d.nombre_alumno}</b> · {d.curso}"))
            textos.addWidget(etiqueta(f"Archivo: {d.archivo} · parecido {round(d.puntuacion)} %", "pequeno"))
            h.addLayout(textos, 1)
            filas.addWidget(fila)
        filas.addStretch(1)
        desplazar = QScrollArea()
        desplazar.setWidgetResizable(True)
        desplazar.setFrameShape(QFrame.Shape.NoFrame)
        desplazar.setWidget(lista)
        capa.addWidget(desplazar, 1)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = boton("Ahora no")
        aceptar = boton("Asignar las marcadas", primario=True)
        cancelar.clicked.connect(self.reject)
        aceptar.clicked.connect(self.accept)
        botones.addWidget(cancelar)
        botones.addWidget(aceptar)
        capa.addLayout(botones)

    def elegidas(self):
        return [d for d, c in zip(self._dudosas, self._casillas, strict=True) if c.isChecked()]


class _Puente(QObject):
    """Lleva la respuesta de GitHub del hilo de comprobación a la interfaz."""

    respuesta = pyqtSignal(str, str, str)


_puentes: list[_Puente] = []


def buscar_actualizaciones(padre, avisar_si_al_dia: bool = False, al_encontrar=None) -> None:
    """Pregunta a GitHub en segundo plano.

    Si hay versión nueva, llama a `al_encontrar(version, url, notas)` (la ventana
    principal enseña su aviso) o, sin él, abre directamente el diálogo.
    """
    puente = _Puente()
    _puentes.append(puente)

    def recibir(version: str, url: str, notas: str):
        _puentes.remove(puente)
        if version:
            (al_encontrar or (lambda v, u, n: ofrecer(padre, v, u, n)))(version, url, notas)
        elif avisar_si_al_dia:
            if notas:
                QMessageBox.information(padre, "Actualizaciones", f"No se ha podido comprobar:\n{notas}")
            else:
                QMessageBox.information(padre, "Actualizaciones", f"Tienes la última versión ({__version__}).")

    puente.respuesta.connect(recibir)
    comprobar(__version__, puente.respuesta.emit, siempre=avisar_si_al_dia)


class DialogoActualizacion(QDialog):
    """Aviso de versión nueva, por encima de la app: actualizar es la opción destacada."""

    def __init__(self, version: str, notas: str, padre=None):
        super().__init__(padre)
        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import QTextBrowser

        from . import estilo

        self.setWindowTitle("Actualización disponible")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(520, 420 if notas else 240)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(26, 22, 26, 20)
        capa.setSpacing(12)
        cabecera = QHBoxLayout()
        cabecera.setSpacing(14)
        circulo = QLabel("↑")
        circulo.setFixedSize(46, 46)
        circulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circulo.setStyleSheet(
            f"background:{estilo.T['gold']};color:#ffffff;border-radius:23px;font-size:24px;font-weight:700;"
        )
        cabecera.addWidget(circulo)
        titulo = QLabel(f"Hay una versión nueva: {version}")
        titulo.setFont(estilo.fuente(24, QFont.Weight.Bold, estilo.TITULAR))
        titulo.setWordWrap(True)
        cabecera.addWidget(titulo, 1)
        capa.addLayout(cabecera)
        capa.addWidget(etiqueta(
            f"Tienes la {__version__}. Se descarga, se cierra la app y se abre el instalador; "
            "los datos y los ajustes se conservan.", "muted", envolver=True))
        if notas:
            capa.addWidget(etiqueta("Novedades", "etiqueta"))
            texto = QTextBrowser()
            texto.setOpenExternalLinks(True)
            texto.setMarkdown(notas)
            capa.addWidget(texto, 1)
        else:
            capa.addStretch(1)
        botones = QHBoxLayout()
        botones.addStretch(1)
        luego = boton("Más tarde")
        ahora = boton("Actualizar ahora", primario=True)
        ahora.setDefault(True)
        luego.clicked.connect(self.reject)
        ahora.clicked.connect(self.accept)
        botones.addWidget(luego)
        botones.addWidget(ahora)
        capa.addLayout(botones)


def ofrecer(padre, version: str, url: str, notas: str) -> None:
    dialogo = DialogoActualizacion(version, notas, padre)
    dialogo.raise_()
    dialogo.activateWindow()
    if dialogo.exec() != QDialog.DialogCode.Accepted:
        return
    if not url:
        webbrowser.open(PAGINA_DE_RELEASES)
        return
    _descargar(padre, url, version)


class _Descargador(QThread):
    avance = pyqtSignal(int)
    listo = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url: str, destino: Path):
        super().__init__()
        self._url = url
        self._destino = destino

    def run(self):
        try:
            if not url_de_confianza(self._url):
                self.error.emit("La dirección de descarga no es de confianza; se cancela.")
                return
            with urllib.request.urlopen(self._url, context=contexto_ssl()) as r:  # nosec B310
                total = int(r.headers.get("Content-Length") or 0)
                hecho = 0
                with open(self._destino, "wb") as f:
                    while trozo := r.read(64 * 1024):
                        f.write(trozo)
                        hecho += len(trozo)
                        if total:
                            self.avance.emit(min(100, hecho * 100 // total))
            self.listo.emit(str(self._destino))
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))


def _descargar(padre, url: str, version: str) -> None:
    destino = Path(tempfile.gettempdir()) / url.rsplit("/", 1)[-1]
    progreso = QProgressDialog(f"Descargando {NOMBRE_APP} {version}…", "Cancelar", 0, 100, padre)
    progreso.setWindowTitle("Actualización")
    progreso.setMinimumDuration(0)
    hilo = _Descargador(url, destino)
    progreso._hilo = hilo
    hilo.avance.connect(progreso.setValue)
    progreso.canceled.connect(hilo.terminate)

    def instalar(ruta):
        progreso.close()
        abrir_instalador(ruta)
        app = QApplication.instance()
        ventana = getattr(app, "ventana", None)
        if ventana is not None:
            ventana.saliendo = True
        app.quit()

    hilo.listo.connect(instalar)
    hilo.error.connect(lambda e: (progreso.close(), QMessageBox.critical(padre, "Error de descarga", e)))
    hilo.start()
