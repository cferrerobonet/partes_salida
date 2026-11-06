"""Revisión del buzón de envío mientras la app está abierta: rebotes al historial y mensajes a jefatura."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from ..correo import contrasena_smtp, correo_configurado, correo_jefatura, enviar, nuevo_id
from ..modelo import Alumno
from ..vuelta import Estado, Mensaje, abrir, imap_configurado, mensaje_de_reenvio, revisar
from .componentes import Tarea

logger = logging.getLogger(__name__)

PRIMERA_MS = 60_000
CADA_MS = 5 * 60_000


def por_correo(alumnos: list[Alumno]) -> dict[str, list[Alumno]]:
    """Cada dirección del padrón (familiares y alumno) → los alumnos con ella (hermanos: varios)."""
    indice: dict[str, list[Alumno]] = {}
    for a in alumnos:
        for d in {a.email, *(t.email for t in a.tutores)}:
            if d and d.strip():
                indice.setdefault(d.strip().lower(), []).append(a)
    return indice


class Vuelta:
    """Cada pocos minutos, una pasada por el buzón en un hilo; nunca dos a la vez."""

    def __init__(self, contexto, ventana):
        self._ctx = contexto
        self._ventana = ventana
        self._estado = Estado()
        self._tarea: Tarea | None = None
        self._ultimo_error = ""
        self._temporizador = QTimer(ventana, interval=CADA_MS, timeout=self.revisar)

    def empezar(self) -> None:
        QTimer.singleShot(PRIMERA_MS, self.revisar)
        self._temporizador.start()

    def parar(self, espera_ms: int = 30_000) -> None:
        """Al salir: no empezar otra pasada y dejar acabar la que esté en marcha."""
        self._temporizador.stop()
        if self._tarea is not None:
            self._tarea.wait(espera_ms)

    def revisar(self) -> None:
        ajustes = self._ctx.gestor.valores
        if self._tarea is not None or not imap_configurado(ajustes) or not correo_configurado(ajustes):
            return
        clave = contrasena_smtp(ajustes)
        if not clave:
            return
        conocidos = self._ctx.seguimiento.mensajes_conocidos()
        por_id = dict(self._ctx.por_id)
        indice = por_correo(self._ctx.alumnos)
        dominio = ajustes.smtp_usuario.rpartition("@")[2].strip()

        def alumnos_de(mensaje: Mensaje, id_alumno: str | None) -> list[Alumno]:
            if id_alumno:
                return [por_id[id_alumno]] if id_alumno in por_id else []
            return indice.get(mensaje.remitente, [])

        def enviar_a(destino: str, alumnos: list[Alumno], mensaje: Mensaje) -> None:
            enviar(mensaje_de_reenvio(ajustes, alumnos, mensaje, destino, nuevo_id), ajustes, clave)

        def trabajo(_progreso):
            imap = abrir(ajustes, clave)
            try:
                return revisar(imap, conocidos, alumnos_de, lambda a: correo_jefatura(ajustes, a), enviar_a,
                               self._estado, dominio)
            finally:
                try:
                    imap.logout()
                except Exception:  # noqa: BLE001, S110 - la conexión ya puede estar cerrada
                    pass

        tarea = Tarea(trabajo)
        tarea.terminado.connect(self._terminado)
        tarea.fallo.connect(self._fallo)
        tarea.finished.connect(self._fin)
        self._tarea = tarea
        tarea.start()

    def _fin(self) -> None:
        self._tarea = None

    def _fallo(self, error: str) -> None:
        # Sin ventanas cada cinco minutos: al registro, una vez por error distinto.
        if error != self._ultimo_error:
            logger.warning("No se ha podido revisar el buzón de envío: %s", error[:200])
            self._ultimo_error = error

    def _terminado(self, resultado) -> None:
        if resultado.error:
            self._fallo(resultado.error)
        else:
            self._ultimo_error = ""
        if resultado.revisados:
            logger.info("Buzón revisado: %d mensaje(s), %d rebote(s), %d reenviado(s) a jefatura",
                        resultado.revisados, len(resultado.rebotes), resultado.reenviados)
        lineas = []
        for id_alumno, id_salida, direcciones in resultado.rebotes:
            if self._ctx.seguimiento.marcar_rebote(id_alumno, id_salida, direcciones) is None:
                continue
            a = self._ctx.por_id.get(id_alumno)
            if a is None:
                continue
            linea = f"• {a.nombre} {a.apellido1} ({a.curso}): " + (", ".join(direcciones) or "dirección sin identificar")
            telefonos = ", ".join(t.telefono for t in a.tutores if t.telefono and t.email.lower() in direcciones)
            if not telefonos:
                telefonos = ", ".join(t.telefono for t in a.tutores if t.telefono)
            if telefonos:
                linea += f"\n   Llamar: {telefonos}"
            lineas.append(linea)
        if resultado.rebotes:
            self._ctx.seguimiento_cambiado.emit()
        if resultado.reenviados:
            n = resultado.reenviados
            self._ventana.aviso.mostrar(
                "Un mensaje de una familia reenviado a jefatura." if n == 1 else f"{n} mensajes de familias reenviados a jefatura."
            )
        if resultado.sin_reenviar:
            QMessageBox.warning(
                self._ventana, "Mensajes sin reenviar",
                "No se ha podido reenviar a jefatura "
                + ("un mensaje de una familia" if resultado.sin_reenviar == 1
                   else f"{resultado.sin_reenviar} mensajes de familias")
                + " tras varios intentos. Sigue en el buzón de envío: hay que mirarlo allí.",
            )
        if lineas:
            QMessageBox.warning(
                self._ventana, "Correos devueltos",
                "Estos correos no han llegado: la dirección ya no existe o está mal escrita. Llama a la familia "
                "y pide que se corrija el correo en Educamos. En el historial del alumno queda como «Rebotado».\n\n"
                + "\n".join(lineas),
            )
