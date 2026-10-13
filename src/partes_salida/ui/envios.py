"""Envío de los correos de uno o varios partes en un hilo, con su huella en el historial."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from email.message import EmailMessage

from PyQt6.QtWidgets import QMessageBox

from ..correo import contrasena_smtp, enviar
from .componentes import Tarea

logger = logging.getLogger(__name__)


@dataclass
class Lote:
    """Los correos de un parte: a la familia, al alumno o a los dos."""

    id_alumno: str
    id_salida: str
    nombre: str  # «Nerea Beltrán», para los avisos
    quienes: str  # «madre y alumna»
    telefonos: str = ""
    mensajes: list[EmailMessage] = field(default_factory=list)


class Envios:
    """Lanza los envíos sin bloquear la ventana y apunta el resultado en el historial."""

    def __init__(self, contexto, ventana):
        self._ctx = contexto
        self._ventana = ventana
        self._tareas: list[Tarea] = []

    def clave(self) -> str | None:
        return contrasena_smtp(self._ctx.gestor.valores)

    def lanzar(self, lotes: list[Lote], al_terminar=None) -> None:
        lotes = [lt for lt in lotes if lt.mensajes]
        if not lotes:
            return
        ajustes = self._ctx.gestor.valores
        clave = self.clave()
        if not clave:
            for lt in lotes:
                self._ctx.seguimiento.marcar_correo(lt.id_alumno, lt.id_salida, "no enviado")
            self._ctx.seguimiento_cambiado.emit()
            self._avisar_fallos([(lt, "falta la contraseña del correo en Ajustes → Correo") for lt in lotes])
            return

        def trabajo(_progreso):
            resultado = []
            for lt in lotes:
                try:
                    for m in lt.mensajes:
                        enviar(m, ajustes, clave)
                    resultado.append((lt, None))
                except Exception as e:  # noqa: BLE001 - cada parte, con su resultado
                    resultado.append((lt, str(e)))
            return resultado

        tarea = Tarea(trabajo)
        tarea.terminado.connect(lambda r: self._terminado(r, al_terminar))
        tarea.fallo.connect(lambda err: self._terminado([(lt, err) for lt in lotes], al_terminar))
        tarea.finished.connect(lambda: self._tareas.remove(tarea))
        self._tareas.append(tarea)
        tarea.start()
        logger.info("Envío de %d correo(s) de %d parte(s)", sum(len(lt.mensajes) for lt in lotes), len(lotes))

    def _terminado(self, resultado, al_terminar) -> None:
        for lt, err in resultado:
            self._ctx.seguimiento.marcar_correo(lt.id_alumno, lt.id_salida, "no enviado" if err else "enviado")
        self._ctx.seguimiento_cambiado.emit()
        fallos = [(lt, err) for lt, err in resultado if err]
        if fallos:
            self._avisar_fallos(fallos)
        elif len(resultado) == 1:
            self._ventana.aviso.mostrar(f"Correo enviado a {resultado[0][0].quienes}.")
        else:
            self._ventana.aviso.mostrar(f"Correos de {len(resultado)} partes enviados.")
        if al_terminar:
            al_terminar()

    def _avisar_fallos(self, fallos) -> None:
        lineas = []
        for lt, err in fallos:
            linea = f"• {lt.nombre} ({lt.quienes}): {err}"
            if lt.telefonos:
                linea += f"\n   Llamar: {lt.telefonos}"
            lineas.append(linea)
        QMessageBox.warning(
            self._ventana, "Correo sin enviar",
            "Estos correos no han salido. Si era el parte del alumno, imprímelo; "
            "si era el aviso, llama a la familia.\n\n" + "\n".join(lineas),
        )
