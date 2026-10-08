"""Arranque: una sola instancia, icono en la barra y ventana principal."""

from __future__ import annotations

import getpass
import logging
import os
import sys

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import NOMBRE_APP, __version__
from .rutas import recursos
from .sistema import configurar_registro

logger = logging.getLogger(__name__)
SERVIDOR = f"partes-salida-{getpass.getuser()}"
#: Prueba de humo del ejecutable congelado (CI de Windows): llega a la ventana y sale.
PRUEBA = os.environ.get("PARTES_PRUEBA_DE_ARRANQUE")
MARCA_PRUEBA = "PRUEBA DE ARRANQUE: ventana principal a la vista"


def _ya_abierta() -> bool:
    """Si hay otra abierta, le pide que se muestre y devuelve True."""
    s = QLocalSocket()
    s.connectToServer(SERVIDOR)
    if s.waitForConnected(400):
        s.write(b"mostrar")
        s.flush()
        s.waitForBytesWritten(400)
        s.disconnectFromServer()
        return True
    return False


class _Reactivar(QObject):
    """En macOS, pulsar el icono del Dock con la ventana oculta la vuelve a mostrar."""

    def __init__(self, ventana):
        super().__init__()
        self._ventana = ventana

    def eventFilter(self, objeto, evento):  # noqa: N802
        if evento.type() == QEvent.Type.ApplicationActivate and not self._ventana.isVisible():
            self._ventana.mostrar_al_frente()
        return False


def icono_app() -> QIcon:
    ruta = recursos() / "icono.png"
    return QIcon(str(ruta)) if ruta.exists() else QIcon()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if PRUEBA:
        os.environ.setdefault("PARTES_SALIDA_SIN_LLAVERO", "1")
    ruta_log = configurar_registro()
    logger.info("Arranca %s %s (%s)", NOMBRE_APP, __version__, sys.platform)
    app = QApplication(argv)
    app.setApplicationName(NOMBRE_APP)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("EPLA")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(icono_app())

    if not PRUEBA and _ya_abierta():
        logger.info("Ya había una instancia abierta; se le pide que se muestre")
        return 0
    QLocalServer.removeServer(SERVIDOR)
    servidor = QLocalServer()
    servidor.listen(SERVIDOR)

    from .ui import estilo

    estilo.cargar_fuentes()
    estilo.aplicar(app)

    from .contexto import Contexto
    from .ui.ventana import VentanaPrincipal

    try:
        ctx = Contexto()
    except Exception as e:  # noqa: BLE001
        logger.exception("No se pudo preparar la aplicación")
        QMessageBox.critical(None, NOMBRE_APP, f"No se puede abrir la aplicación:\n{e}\n\nRegistro: {ruta_log}")
        return 1
    ventana = VentanaPrincipal(ctx)
    app.ventana = ventana

    def mostrar():
        ventana.mostrar_al_frente()

    def conexion():
        s = servidor.nextPendingConnection()
        if s is not None:
            s.readyRead.connect(mostrar)

    servidor.newConnection.connect(conexion)
    reactivar = _Reactivar(ventana)
    app.installEventFilter(reactivar)

    def salir():
        ventana.saliendo = True
        app.quit()

    if QSystemTrayIcon.isSystemTrayAvailable():
        bandeja = QSystemTrayIcon(icono_app(), app)
        bandeja.setToolTip(NOMBRE_APP)
        menu = QMenu()
        menu.addAction("Abrir Partes de salida", mostrar)
        menu.addAction("Ajustes…", lambda: (mostrar(), ventana.abrir_ajustes()))
        menu.addSeparator()
        menu.addAction("Salir", salir)
        bandeja.setContextMenu(menu)
        bandeja.activated.connect(
            lambda motivo: mostrar() if motivo == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        bandeja.show()
        ventana.bandeja = bandeja
        ventana._menu_bandeja = menu

    if "--segundo-plano" not in argv:
        mostrar()
    if ctx.aviso_inicio:
        QMessageBox.warning(ventana, NOMBRE_APP, ctx.aviso_inicio)

    if PRUEBA:
        def fin_de_prueba():
            logger.info(MARCA_PRUEBA)
            salir()

        QTimer.singleShot(1500, fin_de_prueba)
    else:
        from .ui.dialogos import buscar_actualizaciones

        QTimer.singleShot(4000, lambda: buscar_actualizaciones(ventana))
    codigo = app.exec()
    logger.info("Cierre normal (%s)", codigo)
    return codigo
