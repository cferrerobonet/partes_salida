"""Tabla paginada para los registros que crecen (historial, recurrentes).

El mismo patrón que los listados de las webs de CarlosFB (`list-view-utils.js`
de Web Pedidos): buscador, filas por página (5/10/15/20/50, 10 de serie),
«Limpiar filtros», cabeceras ordenables, pie «Mostrando 1–10 de N» con
primera, anterior, cinco números, siguiente y última (los extremos se
desactivan, no desaparecen) y la fila nueva resaltada.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..modelo import sin_tildes
from . import estilo
from .componentes import boton, etiqueta

POR_PAGINA = (5, 10, 15, 20, 50)


@dataclass
class Columna:
    titulo: str
    texto: Callable[[Any], str]
    orden: Callable[[Any], Any] | None = None  # clave para ordenar; si falta, el texto
    ancho: int = 0  # 0 = se estira


def ventana_paginas(actual: int, total: int) -> list[int]:
    """Los cinco números del pie, como en Web Pedidos: la actual centrada y, junto a un extremo,
    los cinco de ese extremo. Desde la actual − 2 sin más, la última página enseñaba solo tres."""
    inicio = max(1, min(actual - 2, total - 4))
    return list(range(inicio, min(total, inicio + 4) + 1))


def texto_recuento(pagina: int, por_pagina: int, total: int, entidad: str) -> str:
    if total <= 0:
        return "Sin resultados"
    desde = (pagina - 1) * por_pagina + 1
    hasta = min(pagina * por_pagina, total)
    return f"Mostrando {desde}–{hasta} de {total} {entidad}".rstrip()


class TablaPaginada(QWidget):
    elegida = pyqtSignal(object)  # fila elegida (o None)
    activada = pyqtSignal(object)  # doble clic o Intro

    def __init__(self, columnas: list[Columna], entidad: str, id_fila: Callable[[Any], str],
                 orden_inicial: tuple[int, bool] = (0, True), marcador: str = "Buscar"):
        super().__init__()
        self._columnas = columnas
        self._entidad = entidad
        self._id = id_fila
        self._filas: list[Any] = []
        self._visibles: list[Any] = []
        self._pagina = 1
        self._orden_col, self._orden_desc = orden_inicial
        self._resaltada: str | None = None

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        filtros = QHBoxLayout()
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText(marcador)
        self.buscador.setClearButtonEnabled(True)
        self.buscador.addAction(estilo.icono_lupa(estilo.T["muted"]), QLineEdit.ActionPosition.LeadingPosition)
        self.buscador.textChanged.connect(self._filtrar)
        filtros.addWidget(self.buscador, 1)
        filtros.addWidget(etiqueta("Por página", "pequeno"))
        self.por_pagina = QComboBox()
        for n in POR_PAGINA:
            self.por_pagina.addItem(str(n), n)
        self.por_pagina.setCurrentIndex(POR_PAGINA.index(10))
        self.por_pagina.currentIndexChanged.connect(lambda: self._ir(1))
        filtros.addWidget(self.por_pagina)
        self.limpiar = boton("Limpiar filtros", pequeno=True)
        self.limpiar.clicked.connect(self.limpiar_filtros)
        filtros.addWidget(self.limpiar)
        v.addLayout(filtros)

        self.tabla = QTableWidget(0, len(columnas))
        self.tabla.setHorizontalHeaderLabels([c.titulo for c in columnas])
        self.tabla.verticalHeader().hide()
        self.tabla.verticalHeader().setDefaultSectionSize(30)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setAlternatingRowColors(False)
        self.tabla.setShowGrid(False)
        cab = self.tabla.horizontalHeader()
        cab.setSectionsClickable(True)
        cab.setSortIndicatorShown(True)
        cab.sectionClicked.connect(self._ordenar_por)
        for i, c in enumerate(columnas):
            if c.ancho:
                cab.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.tabla.setColumnWidth(i, c.ancho)
            else:
                cab.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        self.tabla.itemSelectionChanged.connect(lambda: self.elegida.emit(self.seleccionada()))
        self.tabla.itemDoubleClicked.connect(lambda _i: self.activada.emit(self.seleccionada()))
        v.addWidget(self.tabla, 1)

        pie = QHBoxLayout()
        self.recuento = etiqueta("", "pequeno")
        pie.addWidget(self.recuento)
        pie.addStretch(1)
        self.paginacion = QWidget()
        self._capa_paginas = QHBoxLayout(self.paginacion)
        self._capa_paginas.setContentsMargins(0, 0, 0, 0)
        self._capa_paginas.setSpacing(4)
        pie.addWidget(self.paginacion)
        v.addLayout(pie)

    # Datos
    def poner(self, filas: list[Any], resaltar: str | None = None) -> None:
        self._filas = list(filas)
        if resaltar is not None:
            self._resaltada = resaltar
        self._filtrar(ir_a_resaltada=resaltar is not None)

    def seleccionada(self) -> Any | None:
        fila = self.tabla.currentRow()
        inicio = (self._pagina - 1) * self._n()
        i = inicio + fila
        return self._visibles[i] if fila >= 0 and i < len(self._visibles) else None

    def limpiar_filtros(self) -> None:
        self.buscador.blockSignals(True)
        self.buscador.clear()
        self.buscador.blockSignals(False)
        self._filtrar()

    @property
    def total(self) -> int:
        return len(self._visibles)

    @property
    def pagina(self) -> int:
        return self._pagina

    # Interno
    def _n(self) -> int:
        return int(self.por_pagina.currentData())

    def _filtrar(self, *_args, ir_a_resaltada: bool = False) -> None:
        q = sin_tildes(self.buscador.text()).lower().split()
        filas = [
            f for f in self._filas
            if all(t in sin_tildes(" ".join(c.texto(f) for c in self._columnas)).lower() for t in q)
        ]
        col = self._columnas[self._orden_col]
        clave = col.orden or col.texto
        self._visibles = sorted(filas, key=clave, reverse=self._orden_desc)
        self.tabla.horizontalHeader().setSortIndicator(
            self._orden_col, Qt.SortOrder.DescendingOrder if self._orden_desc else Qt.SortOrder.AscendingOrder
        )
        pagina = 1
        if ir_a_resaltada and self._resaltada:
            i = next((k for k, f in enumerate(self._visibles) if self._id(f) == self._resaltada), None)
            if i is not None:
                pagina = i // self._n() + 1
        self._ir(pagina)

    def _ordenar_por(self, col: int) -> None:
        if col == self._orden_col:
            self._orden_desc = not self._orden_desc
        else:
            self._orden_col, self._orden_desc = col, False
        self._filtrar()

    def _ir(self, pagina: int) -> None:
        n = self._n()
        paginas = max(1, -(-len(self._visibles) // n))
        self._pagina = max(1, min(pagina, paginas))
        trozo = self._visibles[(self._pagina - 1) * n: self._pagina * n]
        self.tabla.setRowCount(len(trozo))
        fondo = QColor(estilo.T["accent_soft"])
        for r, fila in enumerate(trozo):
            nueva = self._resaltada is not None and self._id(fila) == self._resaltada
            for c, columna in enumerate(self._columnas):
                item = QTableWidgetItem(columna.texto(fila))
                if nueva:
                    item.setBackground(fondo)
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.tabla.setItem(r, c, item)
        self.recuento.setText(texto_recuento(self._pagina, n, len(self._visibles), self._entidad))
        self._pie(paginas)
        self.limpiar.setEnabled(bool(self.buscador.text()))
        self.elegida.emit(None)

    def _pie(self, paginas: int) -> None:
        while self._capa_paginas.count():
            w = self._capa_paginas.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.paginacion.setVisible(paginas > 1)
        if paginas <= 1:
            return
        actual = self._pagina

        def poner(texto: str, destino: int, activo: bool, ayuda: str, marcado: bool = False):
            b = boton(texto, pequeno=True, chip=True)
            b.setCheckable(True)
            b.setChecked(marcado)
            b.setEnabled(activo)
            b.setToolTip(ayuda)
            b.setAccessibleName(ayuda)
            b.clicked.connect(lambda _=False, d=destino: self._ir(d))
            self._capa_paginas.addWidget(b)

        poner("«", 1, actual > 1, "Primera página")
        poner("‹", actual - 1, actual > 1, "Página anterior")
        for p in ventana_paginas(actual, paginas):
            poner(str(p), p, True, f"Página {p}", marcado=p == actual)
        poner("›", actual + 1, actual < paginas, "Página siguiente")
        poner("»", paginas, actual < paginas, "Última página")
