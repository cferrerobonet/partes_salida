"""Lo que comparte toda la aplicación: ajustes, claves, padrón y fotos."""

from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from .ajustes import GestorAjustes
from .almacen import Almacen, DatosIlegibles, Padron
from .busqueda import Buscador
from .cifrado import Cifrador
from .firma import Firmante
from .modelo import Alumno, etapas_presentes
from .parte import ImagenesParte
from .rutas import carpeta_datos

logger = logging.getLogger(__name__)


class Contexto(QObject):
    padron_cambiado = pyqtSignal()
    ajustes_cambiados = pyqtSignal()

    def __init__(self, carpeta: Path | None = None, avance=None):
        """`avance(texto, porcentaje)` cuenta cada paso a la pantalla de presentación."""
        super().__init__()
        avance = avance or (lambda _t, _p: None)
        avance("Abriendo la configuración de este equipo…", 8)
        self.carpeta = Path(carpeta or carpeta_datos())
        self.gestor = GestorAjustes(self.carpeta)
        avance("Recuperando las claves del llavero del sistema…", 22)
        self.cifrador = Cifrador.del_llavero()
        self.almacen = Almacen(self.carpeta, self.cifrador)
        avance("Preparando la firma de los partes…", 36)
        self.firmante = Firmante.del_llavero()
        self.imagenes = ImagenesParte(self.gestor)
        self.aviso_inicio = ""
        self._miniaturas: OrderedDict = OrderedDict()
        avance("Descifrando los datos del alumnado…", 52)
        try:
            padron = self.almacen.cargar_padron()
        except DatosIlegibles:
            logger.warning("Datos guardados ilegibles con la clave actual; se borran")
            self.almacen.borrar_todo()
            padron = None
            self.aviso_inicio = (
                "Los datos del alumnado guardados no se pueden abrir con la clave de este equipo "
                "(el llavero del sistema ha cambiado). Vuelve a importar el Excel y las fotos."
            )
        avance("Preparando el buscador…", 70)
        self._poner(padron or Padron([]))

    def _poner(self, padron: Padron) -> None:
        self.alumnos: list[Alumno] = padron.alumnos
        self.importado = padron.importado
        self.origen = padron.origen
        self.por_id = {a.id: a for a in self.alumnos}
        self.buscador = Buscador(self.alumnos)
        self.etapas = etapas_presentes(self.alumnos)
        self._con_foto: int | None = None
        self._miniaturas.clear()

    @property
    def hay_datos(self) -> bool:
        return bool(self.alumnos)

    @property
    def con_foto(self) -> int:
        if self._con_foto is None:
            self._con_foto = self.almacen.contar_fotos(self.por_id)
        return self._con_foto

    def fotos_cambiadas(self) -> None:
        self._con_foto = None
        self._miniaturas.clear()
        self.padron_cambiado.emit()

    def nuevo_padron(self, alumnos: list[Alumno], origen: str) -> int:
        padron = self.almacen.guardar_padron(alumnos, origen)
        borradas = self.almacen.limpiar_fotos([a.id for a in alumnos])
        self._poner(padron)
        self.padron_cambiado.emit()
        return borradas

    def borrar_datos(self) -> None:
        self.almacen.borrar_todo()
        self._poner(Padron([]))
        self.padron_cambiado.emit()

    def etapas_visibles(self) -> set[str] | None:
        ocultas = set(self.gestor.valores.etapas_ocultas)
        return {e for e in self.etapas if e not in ocultas} if ocultas else None

    def foto(self, id_alumno: str) -> bytes | None:
        return self.almacen.leer_foto(id_alumno)

    def miniatura(self, id_alumno: str, ancho: int, alto: int, dpr: float, radio: float):
        """Foto o silueta, ya recortada y redondeada, con caché de las últimas 400."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPixmap

        from .ui.estilo import redondear, silueta

        clave = (id_alumno, ancho, alto, dpr, radio)
        if clave in self._miniaturas:
            self._miniaturas.move_to_end(clave)
            return self._miniaturas[clave]
        datos = self.foto(id_alumno)
        pm = QPixmap()
        if datos and pm.loadFromData(datos):
            pm = pm.scaled(
                int(ancho * dpr), int(alto * dpr),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation,
            )
            x, y = (pm.width() - int(ancho * dpr)) // 2, int((pm.height() - int(alto * dpr)) * 0.4)
            pm = pm.copy(x, y, int(ancho * dpr), int(alto * dpr))
            pm.setDevicePixelRatio(dpr)
        else:
            pm = silueta(id_alumno, ancho, alto, dpr, texto=alto > 60)
        pm = redondear(pm, radio)
        self._miniaturas[clave] = pm
        if len(self._miniaturas) > 400:
            self._miniaturas.popitem(last=False)
        return pm
